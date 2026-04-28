# Fichiers de Configuration de Référence

Ce document contient le contenu exact des fichiers de configuration nécessaires pour le fonctionnement de ChirpStack v4 sur Docker.

## 1. ChirpStack (`chirpstack.toml`)

**Chemin** : `/home/admin/lora-stack/chirpstack/config/chirpstack.toml`

Ce fichier configure les connexions aux bases de données et active les régions. Il a été adapté pour utiliser les noms d'hôtes Docker (`lora-postgres`, `lora-redis`, `lora-mosquitto`).

```toml
[logging]
  level="info"

[postgresql]
  # Connexion au conteneur lora-postgres
  dsn="postgresql://chirpstack:YOUR_PASSWORD@lora-postgres/chirpstack?sslmode=disable"

[redis]
  # Connexion au conteneur lora-redis
  servers=[
    "redis://lora-redis/",
  ]

[network]
  net_id="000000"

[api]
  bind="0.0.0.0:8080"

[integration]
  enabled=["mqtt"]

  [integration.mqtt]
    server="tcp://lora-mosquitto:1883"
    username="chirpstack"
    password="YOUR_PASSWORD"
    json=true

# Activation de la région externe
[regions]
  enabled=["eu868"]
```

## 2. Région EU868 (`region_eu868.toml`)

**Chemin** : `/home/admin/lora-stack/chirpstack/config/region_eu868.toml`

Définit les paramètres radio (fréquences) et la connexion spécifique du backend Gateway pour cette région.

*Points Clés* :
*   `server` pointe vers `lora-mosquitto`.
*   `topic_prefix` est défini sur `eu868`.

```toml
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
        username = "chirpstack"
        password = "YOUR_PASSWORD"
        qos = 0
        clean_session = false

    # Liste des canaux (Fréquences LoRaWAN EU868 standard)
    [[regions.gateway.channels]]
      frequency = 868100000
      bandwidth = 125000
      modulation = "LORA"
      spreading_factors = [7, 8, 9, 10, 11, 12]
    
    # ... (Autres canaux omis pour brièveté, voir fichier complet) ...

  # Paramètres réseau (RX Windows, Délais, ADR)
  [regions.network]
    installation_margin = 10
    rx_window = 0
    rx1_delay = 1
    rx2_frequency = 869525000
```

## 3. Gateway Bridge (`chirpstack-gateway-bridge.toml`)

**Chemin** : `/home/admin/lora-stack/gateway-bridge/config/chirpstack-gateway-bridge.toml`

Ce composant écoute les paquets UDP venant des Gateways et les transforme en messages MQTT pour ChirpStack.

```toml
[integration.mqtt]
event_topic_template="eu868/gateway/{{ .GatewayID }}/event/{{ .EventType }}"
command_topic_template="eu868/gateway/{{ .GatewayID }}/command/#"
marshaler="protobuf"

[integration.mqtt.auth.generic]
servers=["tcp://lora-mosquitto:1883"]
username="chirpstack"
password="YOUR_PASSWORD"

[backend.semtech_udp]
udp_bind="0.0.0.0:1700"
```

## 4. Stratégie de Stockage (WAGO)

Sur le contrôleur WAGO, la gestion de l'espace disque est critique.

*   **Docker Root (`/media/docker`)** :
    *   Configuré sur la **Carte SD**.
    *   Contient : Images Docker (lourdes), Conteneurs (temporaires).
    *   **Pourquoi ?** La mémoire interne du WAGO est trop petite pour stocker des images de plusieurs centaines de Mo.
*   **Données Persistantes (`/home/admin/lora-stack`)** :
    *   Configuré sur la **Flash Interne**.
    *   Contient : Bases de données Postgres/Redis et Fichiers de config TOML.
    *   **Risque** : Si la base de données PostgreSQL grossit trop (beaucoup de logs/métriques), elle peut saturer la mémoire interne et bloquer le contrôleur.
    *   **Recommandation** : Pour un déploiement, déplacez ce dossier sur la carte SD (ex: `/media/docker/lora-data`) et mettez à jour les chemins dans vos scripts de lancement Docker.
