# Docker Automate — LoRaWAN Stack on WAGO CC100


> **Déploiement automatisé d'une stack LoRaWAN (ChirpStack v4) via Docker sur un automate industriel WAGO CC100.**
>
> Ce projet fournit des scripts d'installation, de simulation de capteurs et de benchmark de performance.

---

## Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation rapide](#installation-rapide)
- [Structure du projet](#structure-du-projet)
- [Scripts principaux](#scripts-principaux)
- [Benchmark & Stress Test](#benchmark--stress-test)
- [Documentation](#documentation)
- [Licence](#licence)

---

## Architecture

```mermaid
flowchart TD
    subgraph W ["Automate WAGO CC100 (armv7)"]
        direction TB
        R[("Redis 7<br/>(Cache)")]
        P[("PostgreSQL 15<br/>(DB)")]
        M{{"Mosquitto 2<br/>(Broker MQTT)"}}
        
        C["ChirpStack 4<br/>(LoRaWAN Network Server)"]
        
        R <--> C
        P <--> C
        M <--> C
    end

    SIM["Simulateur Radio<br/>(Python)"]

    SIM -->|MQTT| M

    style W fill:#eceff1,stroke:#607d8b,stroke-width:2px,color:#000
    style C fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    style M fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    style R fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
    style P fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000
    style SIM fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
```

---

## Prérequis

| Composant       | Version minimale |
|-----------------|-----------------|
| Python          | 3.10+           |
| Docker          | 20.10+          |
| Docker Compose  | v2+             |

---

## Installation rapide

### 1. Cloner le dépôt

```bash
git clone https://github.com/Princeddn/Docker_automate.git
cd Docker_automate
```

### 2. Installer les dépendances Python

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 3. Déployer la stack sur le WAGO

```bash
# Lancer l'installation automatisée (le script est dans config/)
bash config/install_lora.sh
```

---

## Structure du projet

```
Docker_automate/
├── .env                            # Fichier de configuration (Clés API, identifiants MQTT)
├── scripts/
│   ├── simulators/                 # Générateurs de trames et capteurs virtuels
│   ├── benchmark/                  # Orchestrateurs de tests de charge (Ramp-Up, DDoS)
│   └── tools/                      # Diagnostics, écoute MQTT et scripts de monitoring
├── config/                         # Fichiers TOML, YAML et shell (Install WAGO)
├── docs/                           # Documentation
│   └── DOCUMENTATION.md            # Rapport global et manuel technique unifié
├── requirements.txt                # Dépendances Python
└── Readme.md                       # Ce fichier
```

---

## Scripts principaux

### Gestion des capteurs

| Script | Description |
|--------|-------------|
| `scripts/simulators/01_creation_capteurs.py` | Crée automatiquement des devices LoRaWAN dans ChirpStack via l'API gRPC |
| `scripts/simulators/00_suppression_capteurs.py` | Supprime les capteurs de test de ChirpStack |

### Simulation radio

| Script | Description |
|--------|-------------|
| `scripts/simulators/02_simulateur_radio.py` | Envoie des trames LoRaWAN simulées via MQTT |
| `scripts/simulators/02_simulateur_radio_http.py` | Variante utilisant l'API HTTP |
| `scripts/simulators/02_simulateur_radio_verif.py` | Version avec vérification stricte de la réception |
| `scripts/simulators/simulateur_capteurs.py` | Simulation multi-capteurs complète |

### Monitoring

| Script | Description |
|--------|-------------|
| `scripts/tools/mqtt_monitor.py` | Écoute et analyse le trafic MQTT en temps réel |
| `scripts/tools/enregistreur_csv.py` | Enregistre les données reçues en CSV |
| `scripts/tools/monitor_ssh_wago.py` | Surveillance du WAGO via SSH |

---

## Benchmark & Stress Test

Le projet inclut un système complet de benchmark progressif :

```bash
# Lancer le benchmark complet (ramp-up de 1 à N capteurs)
python scripts/benchmark/master_benchmark.py

# Test de crash / saturation
python scripts/benchmark/benchmark_crash.py
```

Les conclusions de ces tests sont documentées et consolidées dans le manuel technique complet.

---


## Documentation

La documentation unifiée et mise à jour est disponible dans le dossier [`docs/`](docs/) :

- **[Manuel Technique Complet (DOCUMENTATION.md)](docs/DOCUMENTATION.md)** : C'est le grand rapport global qui détaille l'ensemble du projet (architecture, analyse matérielle, déploiement, configuration, incidents, et résultats des benchmarks).
- [Guide d'installation rapide](docs/installation.md)
- [Guide de configuration ChirpStack](docs/configuration.md)
- [Guide de configuration Gateway RAK](docs/gateway_configuration.md)

*(Note : Le manuel PDF du capteur physique se trouve également dans ce dossier).*

---

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

<p align="center">
  <strong>Projet réalisé dans le cadre d'un déploiement Docker sur automate industriel WAGO CC100</strong>
</p>
