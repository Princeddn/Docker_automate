# 🐳 Docker Automate — LoRaWAN Stack on WAGO CC100

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

> **Déploiement automatisé d'une stack LoRaWAN (ChirpStack v4) via Docker sur un automate industriel WAGO CC100.**
>
> Ce projet fournit des scripts d'installation, de simulation de capteurs, de benchmark de performance et un dashboard de monitoring temps réel.

---

## 📋 Table des matières

- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation rapide](#-installation-rapide)
- [Structure du projet](#-structure-du-projet)
- [Scripts principaux](#-scripts-principaux)
- [Benchmark & Stress Test](#-benchmark--stress-test)
- [Dashboard](#-dashboard)
- [Documentation](#-documentation)
- [Licence](#-licence)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  WAGO CC100 (armv7)                 │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Redis 7  │  │ Postgres │  │   Mosquitto 2    │  │
│  │  (cache)  │  │   15     │  │  (MQTT broker)   │  │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘  │
│       │              │                │              │
│       └──────────────┼────────────────┘              │
│                      │                               │
│              ┌───────┴───────┐                       │
│              │  ChirpStack 4 │                       │
│              │  (LoRaWAN NS) │                       │
│              └───────────────┘                       │
└─────────────────────────────────────────────────────┘
          ▲                          ▲
          │  MQTT                    │  API gRPC
          │                          │
   ┌──────┴──────┐          ┌───────┴────────┐
   │  Simulateur  │          │   Dashboard    │
   │  Radio       │          │   Node.js      │
   └─────────────┘          └────────────────┘
```

---

## ⚙ Prérequis

| Composant       | Version minimale |
|-----------------|-----------------|
| Python          | 3.10+           |
| Docker          | 20.10+          |
| Docker Compose  | v2+             |
| Node.js         | 18+ (dashboard) |

---

## 🚀 Installation rapide

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
# Copier et adapter la configuration
cp lorainstall.yaml lorainstall.local.yaml
# Éditer les mots de passe et ports...

# Lancer l'installation automatisée
bash install_lora.sh
```

---

## 📁 Structure du projet

```
Docker_automate/
├── 00_suppression_capteurs.py      # Suppression des capteurs ChirpStack
├── 01_creation_capteurs.py         # Création automatique de capteurs
├── 02_simulateur_radio.py          # Simulateur de trames LoRaWAN (MQTT)
├── 02_simulateur_radio_http.py     # Simulateur via API HTTP
├── 02_simulateur_radio_verif.py    # Simulateur avec vérification de réception
├── benchmark_crash.py              # Test de crash / saturation
├── benchmark_pc.py                 # Benchmark depuis le PC
├── master_benchmark.py             # Orchestrateur de benchmark progressif
├── mqtt_monitor.py                 # Monitoring MQTT temps réel
├── enregistreur_csv.py             # Enregistrement des données en CSV
├── simulateur_capteurs.py          # Simulateur multi-capteurs
├── diag_single_frame.py            # Diagnostic mono-trame
├── monitor_ssh_wago.py             # Monitoring SSH du WAGO
├── test_monitor_psutil.py          # Test monitoring via psutil
├── test_monitor_top.py             # Test monitoring via top
│
├── install_lora.sh                 # Script d'installation de la stack
├── benchmark_lora.sh               # Script benchmark shell
├── lorainstall.yaml                # Configuration d'installation
│
├── chirpstack_*.toml               # Configs ChirpStack
├── region_eu868*.toml              # Configs régionales LoRaWAN
│
├── dashboard/                      # Dashboard Node.js temps réel
│   ├── sensor_dashboard.js
│   ├── Dockerfile
│   └── package.json
│
├── docs/                           # Documentation technique
│   ├── installation.md
│   ├── configuration.md
│   ├── benchmark.md
│   └── ...
│
├── rapport/                        # Rapport de projet complet
│   ├── 00_page_de_garde.md
│   ├── ...
│   └── annexes/
│
├── scratch/                        # Scripts utilitaires
├── requirements.txt                # Dépendances Python
└── .gitignore
```

---

## 🔧 Scripts principaux

### Gestion des capteurs

| Script | Description |
|--------|-------------|
| `01_creation_capteurs.py` | Crée automatiquement des devices LoRaWAN dans ChirpStack via l'API gRPC |
| `00_suppression_capteurs.py` | Supprime les capteurs de test de ChirpStack |

### Simulation radio

| Script | Description |
|--------|-------------|
| `02_simulateur_radio.py` | Envoie des trames LoRaWAN simulées via MQTT |
| `02_simulateur_radio_http.py` | Variante utilisant l'API HTTP |
| `02_simulateur_radio_verif.py` | Version avec vérification stricte de la réception |
| `simulateur_capteurs.py` | Simulation multi-capteurs complète |

### Monitoring

| Script | Description |
|--------|-------------|
| `mqtt_monitor.py` | Écoute et analyse le trafic MQTT en temps réel |
| `enregistreur_csv.py` | Enregistre les données reçues en CSV |
| `monitor_ssh_wago.py` | Surveillance du WAGO via SSH |

---

## 📊 Benchmark & Stress Test

Le projet inclut un système complet de benchmark progressif :

```bash
# Lancer le benchmark complet (ramp-up de 1 à N capteurs)
python master_benchmark.py

# Test de crash / saturation
python benchmark_crash.py
```

Les rapports générés se trouvent dans `rapport_benchmark_FINAL*.md`.

---

## 📺 Dashboard

Un dashboard Node.js temps réel pour visualiser les capteurs :

```bash
cd dashboard
npm install
node sensor_dashboard.js
```

Ou via Docker :

```bash
cd dashboard
docker build -t lora-dashboard .
docker run -p 3000:3000 lora-dashboard
```

---

## 📖 Documentation

La documentation complète est disponible dans le dossier [`docs/`](docs/) :

- [Guide d'installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Guide de benchmark](docs/benchmark.md)
- [Intégration HTTP](docs/HTTP_INTEGRATION_GUIDE.md)
- [Déploiement Cloud](docs/CLOUD_DEPLOYMENT.md)
- [Configuration Gateway](docs/gateway_configuration.md)

Le rapport de projet complet est dans [`rapport/`](rapport/).

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

<p align="center">
  <strong>Projet réalisé dans le cadre d'un déploiement Docker sur automate industriel WAGO CC100</strong>
</p>
