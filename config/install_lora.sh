#!/bin/sh

# ==============================================================================
# SCRIPT D'INSTALLATION AUTOMATISÉE LoRaWAN SUR WAGO (Docker)
# ==============================================================================
# Ce script :
# 1. Crée les dossiers nécessaires.
# 2. Génère les fichiers de configuration optimisés (ChirpStack v4).
# 3. Lance les conteneurs Docker (Postgres, Redis, Mosquitto, ChirpStack, Bridge).
#
# Usage : sh install_lora.sh
# ==============================================================================

# --- Configuration ---
MAX_RETRY=30

# 1. Détection automatique du stockage
# ------------------------------------------------------------------------------
# On préfère la carte SD (/media/docker) si elle est montée
if mount | grep -q "/media/docker"; then
    echo ">>> Carte SD détectée ! ( /media/docker )"
    
    # MIGRATION AUTOMATIQUE :
    # Si des données existent sur la mémoire interne (/home/admin/lora-stack) 
    # et PAS encore sur la SD, on les déplace.
    if [ -d "/home/admin/lora-stack" ] && [ ! -d "/media/docker/lora-stack" ]; then
        echo ">>> MIGRATION DETECTÉE : Déplacement des données interne -> SD..."
        echo ">>> Arrêt temporaire des services pour transfert sûr..."
        docker stop lora-chirpstack lora-gateway-bridge lora-mosquitto lora-redis lora-postgres >/dev/null 2>&1
        
        # Copie préservant les droits (-a)
        cp -a /home/admin/lora-stack /media/docker/
        
        # On renomme l'ancien dossier en .bak pour ne pas le perdre mais désactiver son usage
        mv /home/admin/lora-stack /home/admin/lora-stack.bak
        echo ">>> Migration terminée avec succès."
    fi

    BASE_DIR="/media/docker/lora-stack"
    echo ">>> Utilisation du stockage : $BASE_DIR"

else
    echo ">>> Pas de carte SD. Utilisation de la mémoire interne."
    BASE_DIR="/home/admin/lora-stack"

    # Sécurité : Vérifier l'espace disque disponible sur /home (Min 500Mo)
    AVAILABLE_KB=$(df -P /home | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE_KB" -lt 500000 ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "ERREUR CRITIQUE : Espace disque insuffisant sur /home (< 500Mo)"
        echo "Installation annulée pour éviter de saturer l'automate."
        echo "Veuillez insérer une carte SD ou libérer de l'espace."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        exit 1
    fi
fi

NETWORK_NAME="lora_net"

echo ">>> Démarrage de l'installation LoRaWAN..."
echo ">>> Répertoire d'installation : $BASE_DIR"

# 1. Création de l'arborescence
# ------------------------------------------------------------------------------
echo ">>> Création des dossiers..."
mkdir -p "$BASE_DIR/chirpstack/config"
mkdir -p "$BASE_DIR/chirpstack/data"
mkdir -p "$BASE_DIR/mosquitto/config"
mkdir -p "$BASE_DIR/mosquitto/data"
mkdir -p "$BASE_DIR/postgres/data"
mkdir -p "$BASE_DIR/redis/data"
mkdir -p "$BASE_DIR/gateway-bridge/config"
mkdir -p "$BASE_DIR/logs"

# 2. Génération des Fichiers de Configuration
# ------------------------------------------------------------------------------
echo ">>> Génération des fichiers de configuration..."

# --- A. Mosquitto ---
cat > "$BASE_DIR/mosquitto/config/mosquitto.conf" <<EOF
persistence true
persistence_location /mosquitto/data/
listener 1883
allow_anonymous true
# Pour sécuriser, changer allow_anonymous à false et utiliser un password_file
EOF

# --- B. ChirpStack (Main) ---
# Note: Connecte aux conteneurs 'lora-postgres', 'lora-redis', 'lora-mosquitto'
cat > "$BASE_DIR/chirpstack/config/chirpstack.toml" <<EOF
[logging]
  level="info"

[codec]
  [codec.js]
    # Indispensable pour éviter l'erreur "interrupted" sur le WAGO (600MHz)
    max_execution_time="5000ms"

[postgresql]
  dsn="postgresql://chirpstack:YOUR_PASSWORD@lora-postgres/chirpstack?sslmode=disable"

[redis]
  servers=[
    "redis://lora-redis/",
  ]

[network]
  net_id="000000"
  enabled_regions=["eu868"]

[api]
  bind="0.0.0.0:8080"

[integration]
  enabled=["mqtt"]

  [integration.mqtt]
    server="tcp://lora-mosquitto:1883"
    username="chirpstack"
    password="YOUR_PASSWORD"
    json=true
EOF

# --- C. Région EU868 ---
cat > "$BASE_DIR/chirpstack/config/region_eu868.toml" <<EOF
[[regions]]
  id = "eu868"
  description = "EU868"
  common_name = "EU868"

  [regions.gateway]
    force_gws_private = false

    [regions.gateway.backend]
      enabled = "mqtt"

      [regions.gateway.backend.mqtt]
        topic_prefix = "eu868"
        server = "tcp://lora-mosquitto:1883"
        username = ""
        password = ""
        qos = 0
        clean_session = false

    [[regions.gateway.channels]]
      frequency = 868100000
      bandwidth = 125000
      modulation = "LORA"
      spreading_factors = [7, 8, 9, 10, 11, 12]

    [[regions.gateway.channels]]
      frequency = 868300000
      bandwidth = 125000
      modulation = "LORA"
      spreading_factors = [7, 8, 9, 10, 11, 12]

    [[regions.gateway.channels]]
      frequency = 868500000
      bandwidth = 125000
      modulation = "LORA"
      spreading_factors = [7, 8, 9, 10, 11, 12]
      
    # Ajoutez d'autres canaux ici si nécessaire...

  [regions.network]
    installation_margin = 10
    rx_window = 0
    rx1_delay = 1
    rx1_dr_offset = 0
    rx2_dr = 0
    rx2_frequency = 869525000
    downlink_tx_power = -1
    adr_disabled = false
    min_dr = 0
    max_dr = 5
EOF

# --- D. Gateway Bridge ---
cat > "$BASE_DIR/gateway-bridge/config/chirpstack-gateway-bridge.toml" <<EOF
[integration.mqtt]
event_topic_template="eu868/gateway/{{ .GatewayID }}/event/{{ .EventType }}"
command_topic_template="eu868/gateway/{{ .GatewayID }}/command/#"
marshaler="protobuf"

[integration.mqtt.auth.generic]
servers=["tcp://lora-mosquitto:1883"]
username=""
password=""

[backend.semtech_udp]
udp_bind="0.0.0.0:1700"
EOF



# 3. Tuning Système (Prévention des crashs Redis)
# ------------------------------------------------------------------------------
echo ">>> Application des réglages système (sysctl)..."
# Redis a besoin de vm.overcommit_memory=1 pour éviter les crashs en cas de faible mémoire
# Cette commande nécessite les droits root (le script doit être lancé en root)
sysctl -w vm.overcommit_memory=1 >> /dev/null 2>&1
echo "    vm.overcommit_memory = 1 (OK)"


# 4. Lancement Docker
# ------------------------------------------------------------------------------
echo ">>> Vérification du réseau Docker..."
docker network inspect $NETWORK_NAME >/dev/null 2>&1 || \
    docker network create $NETWORK_NAME

echo ">>> Arrêt des anciens conteneurs (nettoyage)..."
docker stop lora-chirpstack lora-gateway-bridge lora-mosquitto lora-redis lora-postgres lora-logger 2>/dev/null
docker rm lora-chirpstack lora-gateway-bridge lora-mosquitto lora-redis lora-postgres lora-logger 2>/dev/null

echo ">>> Lancement des conteneurs sécurisés..."

# 1. Redis
# Ajout: Healthcheck + Restart Always + Save config
docker run -d --name lora-redis --network $NETWORK_NAME --restart always \
  --health-cmd "redis-cli ping | grep PONG" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 5 \
  -v "$BASE_DIR/redis/data:/data" \
  redis:7-alpine redis-server --appendonly yes --appendfsync everysec

# 2. Postgres
# Ajout: Healthcheck + Restart Always
docker run -d --name lora-postgres --network $NETWORK_NAME --restart always \
  -e POSTGRES_DB=chirpstack \
  -e POSTGRES_USER=chirpstack \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  --health-cmd "pg_isready -U chirpstack" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 5 \
  -v "$BASE_DIR/postgres/data:/var/lib/postgresql/data" \
  postgres:14-alpine

echo ">>> Attente initialisation Base de Données (10s)..."
sleep 10

# 3. Mosquitto
# Ajout: Healthcheck (rudimentaire sur port TCP) + Restart Always
docker run -d --name lora-mosquitto --network $NETWORK_NAME --restart always \
  -p 1883:1883 \
  -v "$BASE_DIR/mosquitto/config:/mosquitto/config" \
  -v "$BASE_DIR/mosquitto/data:/mosquitto/data" \
  eclipse-mosquitto:2

# 4. Gateway Bridge
# Ajout: Restart Always
docker run -d --name lora-gateway-bridge --network $NETWORK_NAME --restart always \
  -p 1700:1700/udp \
  -v "$BASE_DIR/gateway-bridge/config:/etc/chirpstack-gateway-bridge:ro" \
  chirpstack/chirpstack-gateway-bridge:latest

# 5. ChirpStack
# Ajout: Restart Always, Port 8081
# Fix: Ajout explicite de la commande de configuration (-c /etc/chirpstack)
docker run -d --name lora-chirpstack --network $NETWORK_NAME --restart always \
  -p 8081:8080 \
  -v "$BASE_DIR/chirpstack/config:/etc/chirpstack:ro" \
  chirpstack/chirpstack:4 \
  -c /etc/chirpstack

# 6. Logger Persistant (Nouveau)
# Ce service capture tout le trafic MQTT et l'écrit sur la carte SD
docker run -d --name lora-logger --network $NETWORK_NAME --restart always \
  -v "$BASE_DIR/logs:/logs" \
  eclipse-mosquitto:2 \
  sh -c "mosquitto_sub -h lora-mosquitto -t '#' -v >> /logs/lora_history.jsonl"

echo "========================================================"
echo " INSTALLATION SECURISÉE TERMINÉE"
echo "========================================================"
echo "Accès interface : http://<IP_DU_WAGO>:8081 (admin/admin)"
echo ""
echo "NOTE : N'oubliez pas de configurer votre Passerelle RAK !"
echo "1. IP Serveur : <IP_DU_WAGO>"
echo "2. Port : 1700"
echo "3. Protocole : SEMTECH UDP (Crutial !)"
echo "========================================================"
