# Guide d'Installation LoRaWAN sur WAGO (Docker + ChirpStack v4)

Ce document décrit la procédure complète pour déployer un serveur LoRaWAN privé sur un contrôleur WAGO (CC100/PFC200) et y connecter une passerelle RAK7268.

## 1. Prérequis Matériels et Logiciels

*   **Contrôleur WAGO** : CC100 ou PFC200 (Linux embarqué).
*   **Stockage** : Carte SD industrielle (Minimum 8Go, Recommandé 16Go+ SLC/pSLC) pour les images Docker.
*   **Gateway LoRaWAN** : RAK7268 (WisGate Edge Lite 2) ou équivalent Packet Forwarder.
*   **Accès** : SSH activé sur le WAGO (`root`) et la Gateway.
*   **Docker** : Installé sur le WAGO (via IPK ou script d'installation WAGO).

---

## 2. Architecture du Système

Le système repose sur des conteneurs isolés communiquant via un réseau Docker interne (`lora_net`).

| Service | Rôle | Port Interne | Port Externe (Hôte) |
| :--- | :--- | :--- | :--- |
| **Mosquitto** | Broker MQTT (Bus de communication) | 1883 | 1883 |
| **Gateway Bridge** | Convertisseur UDP <-> MQTT | 1700 (UDP) | 1700 (UDP) |
| **ChirpStack** | Serveur Réseau (LNS) & Application | 8080 | 8080 (UI) |
| **PostgreSQL** | Base de données principale | 5432 | - |
| **Redis** | Base de donnée cache / performance | 6379 | - |

---

## 3. Installation Automatique (Recommandé)

Nous avons créé un script qui automatise la création des dossiers, la génération des fichiers de configuration et le lancement de Docker.

1.  **Copier le script** : Transférez le fichier `install_lora.sh` sur le WAGO (ex: dans `/home/admin/`).
2.  **Exécuter** :
    ```bash
    chmod +x install_lora.sh
    ./install_lora.sh
    ```
3.  **C'est tout !** Rendez-vous directement à l'étape **6. Configuration de la Passerelle**.

---

## 4. Installation Manuelle (Détail)

Si vous préférez tout contrôler à la main.

### Structure des Dossiers
Nous séparons la configuration (liée au projet) des données (qui grossissent avec le temps).

```bash
# Création de l'arborescence de configuration
mkdir -p /home/admin/lora-stack/{chirpstack,mosquitto,postgres,redis,gateway-bridge}/config

# Création des volumes de données (Idéalement sur carte SD, voir configuration.md)
mkdir -p /home/admin/lora-stack/{chirpstack,mosquitto,postgres,redis}/data
```

---

## 5. Déploiement des Fichiers de Configuration

Copiez les fichiers suivants dans `/home/admin/lora-stack/...`.
*Voir le document `configuration.md` pour le détail du contenu des fichiers.*

1.  **ChirpStack** : `chirpstack/config/chirpstack.toml` (Configuration principale).
2.  **Région** : `chirpstack/config/region_eu868.toml` (Paramètres radio EU868).
3.  **Gateway Bridge** : `gateway-bridge/config/chirpstack-gateway-bridge.toml` (Lien UDP/MQTT).
4.  **Mosquitto** : `mosquitto/config/mosquitto.conf` (+ fichier de mots de passe).

---

## 6. Lancement des Conteneurs (Docker)

Vous pouvez utiliser un script shell ou `docker-compose`. Voici les commandes manuelles critiques pour le démarrage.

### Étape 1 : Créer le réseau
```bash
docker network create lora_net
```

### Étape 2 : Bases de Données (Postgres & Redis)
```bash
# Redis
docker run -d --name lora-redis --network lora_net --restart unless-stopped redis:7-alpine

# Postgres (Attention aux variables d'environnement)
docker run -d --name lora-postgres --network lora_net --restart unless-stopped \
  -e POSTGRES_DB=chirpstack \
  -e POSTGRES_USER=chirpstack \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -v /home/admin/lora-stack/postgres/data:/var/lib/postgresql/data \
  postgres:14-alpine
```
*Note : Attendez quelques secondes que Postgres initialisation la base.*

### Étape 3 : Mosquitto & Gateway Bridge
```bash
# Mosquitto
docker run -d --name lora-mosquitto --network lora_net -p 1883:1883 --restart unless-stopped \
  -v /home/admin/lora-stack/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2

# Gateway Bridge
docker run -d --name lora-gateway-bridge --network lora_net -p 1700:1700/udp --restart unless-stopped \
  -v /home/admin/lora-stack/gateway-bridge/config:/etc/chirpstack-gateway-bridge:ro \
  chirpstack/chirpstack-gateway-bridge:latest
```

### Étape 4 : ChirpStack (Le Serveur)
```bash
docker run -d --name lora-chirpstack --network lora_net -p 8080:8080 --restart unless-stopped \
  -v /home/admin/lora-stack/chirpstack/config:/etc/chirpstack:ro \
  chirpstack/chirpstack:4
```

---

## 7. Configuration de la Passerelle RAK7268

Pour connecter votre Gateway RAK au WAGO, il faut modifier sa configuration interne.

1.  Connectez-vous en SSH à la Gateway : `ssh root@<IP_GATEWAY>`.
2.  **Désactivez le service interne conflictuel** (Souvent présent par défaut) :
    ```bash
    /etc/init.d/lorasrv stop
    /etc/init.d/lorasrv disable
    ```
3.  **Configurez le Packet Forwarder via UCI** :
    Remplacez `192.168.3.100` par l'IP de votre WAGO.
    ```bash
    # Définir l'adresse du serveur (WAGO)
    uci set lora_pkt_fwd.gateway_conf.server_address='192.168.3.100'
    uci set lora_pkt_fwd.gateway_conf.serv_port_up=1700
    uci set lora_pkt_fwd.gateway_conf.serv_port_down=1700
    
    # CRITIQUE : Forcer le mode UDP (sinon WisGateOS écrase l'adresse par localhost)
    uci set lora_pkt_fwd.gateway_conf.proto='udp' 
    
    # Sauvegarder et redémarrer
    uci commit lora_pkt_fwd
    /etc/init.d/sx130x_lora_pkt_fwd restart
    ```

## 8. Vérification finale

1.  Accédez à l'interface web : `http://<IP_WAGO>:8080`.
2.  Loguez-vous (admin / admin).
3.  Vérifiez que la région **EU868** apparaît dans "Network Server > Regions".
4.  Créez une Gateway en entrant son **Gateway ID** exact (EUI64).
5.  Vérifiez que le statut passe à "Online".
