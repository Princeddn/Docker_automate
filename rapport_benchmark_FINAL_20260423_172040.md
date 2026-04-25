# 📊 Rapport Professionnel de Benchmark WAGO CC100 (ChirpStack v4)

## 1. 🎯 Conclusion et Capacité d'Ingestion Automatique

> **Débit d'ingestion robuste validé sans erreur claire :** 0 messages / seconde.

### 📡 Fiabilité de Décodage de bout-en-bout (MQTT Application)
- **Trames radio brutes envoyées** : 272
- **Trames décodées avec succès (JSON)** : 88
- **Taux de Perte global (Chute CPU)** : **67.6%**
> ⚠️ *Note: Une perte > 0% signifie que le processeur (ARM 600Mhz) a été incapable de suivre la cadence et a dû jeter les trames avant décodage.*

### Projection pour un déploiement GTB réel (Bâtiment) :
Si ce WAGO maintient 0 requêtes par seconde sans saturer, voici sa capacité théorique maximale :
- Si les capteurs émettent toutes les **1 minute** : 0 capteurs supportés.
- Si les capteurs émettent toutes les **5 minutes** : 0 capteurs supportés.
- Si les capteurs émettent toutes les **15 minutes** (Standard GTB) : **0 capteurs supportés.**

## 2. 📈 Localisation de la Rupture de Charge (Par Phases)

| Phase | Vitesse (Msg/s) | Injections (Gateway) | Décodages (App) | Taux de Perte |
|-------|-----------------|----------------------|-----------------|---------------|
| Phase 1 (0.5 msg/s) | 0.5 msg/s | 8 trames | 0 trames | 🛑 **100.0%** |
| Phase 2 (1.0 msg/s) | 1.0 msg/s | 15 trames | 2 trames | 🛑 **86.7%** |
| Phase 3 (1.5 msg/s) | 1.5 msg/s | 23 trames | 17 trames | 🟠 **26.1%** |
| Phase 4 (2.0 msg/s) | 2.0 msg/s | 30 trames | 13 trames | 🛑 **56.7%** |
| Phase 5 (2.5 msg/s) | 2.5 msg/s | 38 trames | 16 trames | 🛑 **57.9%** |
| Phase 6 (3.0 msg/s) | 3.0 msg/s | 45 trames | 13 trames | 🛑 **71.1%** |
| Phase 7 (3.5 msg/s) | 3.5 msg/s | 53 trames | 13 trames | 🛑 **75.5%** |
| Phase 8 (4.0 msg/s) | 4.0 msg/s | 60 trames | 14 trames | 🛑 **76.7%** |

**Durée totale :** 219.0s | **Trames totales :** 272

## 3. ⚠️ Analyse Interne ChirpStack (JavaScript Codec Errors)

Ceci indique si l'automate a manqué de temps CPU pour décoder les trames (Timeout 500ms).
❌ **3525 erreurs détectées dans les logs Docker.** (CPU Probablement saturé)
```text
[2m2026-04-23T15:15:41.763339Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:46.851807Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.147292Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.169338Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.177915Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.206382Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.224002Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:47.690208Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:48.575898Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:15:48.812025Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
```

## 4. 💽 Télémétrie Système (Load Average & Mémoire)

| Heure | Load CPU | Utilisation RAM (%) | Consommation Docker |
|-------|----------|---------------------|---------------------|
| 17:17:03 | 9.93 | 59.5% | `N/A` |
| 17:17:05 | 9.93 | 59.0% | `N/A` |
| 17:17:07 | 9.85 | 57.5% | `N/A` |
| 17:17:09 | 9.85 | 56.2% | `N/A` |
| 17:17:12 | 9.85 | 54.6% | `N/A` |
| 17:17:14 | 9.38 | 52.9% | `N/A` |
| 17:17:17 | 9.38 | 51.6% | `N/A` |
| 17:17:19 | 9.03 | 50.0% | `N/A` |
| 17:17:21 | 9.03 | 48.8% | `N/A` |
| 17:17:23 | 8.55 | 47.5% | `N/A` |
| 17:17:26 | 8.55 | 47.4% | `N/A` |
| 17:17:28 | 8.43 | 46.0% | `N/A` |
| 17:17:30 | 8.43 | 44.6% | `N/A` |
| 17:17:32 | 8.47 | 42.8% | `N/A` |
| 17:17:35 | 8.47 | 41.8% | `N/A` |
| 17:17:37 | 8.47 | 41.7% | `N/A` |
| 17:17:39 | 8.11 | 41.6% | `N/A` |
| 17:17:41 | 8.11 | 41.6% | `N/A` |
| 17:17:44 | 7.7 | 41.6% | `N/A` |
| 17:17:46 | 7.7 | 41.6% | `N/A` |
| 17:17:48 | 8.13 | 42.2% | `N/A` |
| 17:17:50 | 8.13 | 41.7% | `N/A` |
| 17:17:53 | 8.04 | 41.7% | `N/A` |
| 17:17:55 | 8.04 | 41.6% | `N/A` |
| 17:17:57 | 8.35 | 41.9% | `N/A` |
| 17:18:00 | 8.35 | 42.8% | `N/A` |
| 17:18:02 | 8.35 | 41.7% | `N/A` |
| 17:18:04 | 8.33 | 41.7% | `N/A` |
| 17:18:06 | 8.33 | 41.6% | `N/A` |
| 17:18:09 | 8.06 | 41.6% | `N/A` |
| 17:18:11 | 8.06 | 41.6% | `N/A` |
| 17:18:13 | 7.97 | 41.4% | `N/A` |
| 17:18:16 | 7.97 | 41.6% | `N/A` |
| 17:18:18 | 7.82 | 41.7% | `N/A` |
| 17:18:20 | 7.82 | 41.7% | `N/A` |
| 17:18:22 | 7.83 | 40.8% | `N/A` |
| 17:18:25 | 7.83 | 40.7% | `N/A` |
| 17:18:27 | 7.83 | 40.7% | `N/A` |
| 17:18:29 | 7.76 | 40.7% | `N/A` |
| 17:18:32 | 7.76 | 41.3% | `N/A` |
| 17:18:34 | 7.46 | 41.3% | `N/A` |
| 17:18:36 | 7.46 | 40.8% | `N/A` |
| 17:18:39 | 7.35 | 40.7% | `N/A` |
| 17:18:41 | 7.35 | 40.7% | `N/A` |
| 17:18:43 | 7.56 | 40.6% | `N/A` |
| 17:18:45 | 7.56 | 40.5% | `N/A` |
| 17:18:48 | 7.75 | 40.5% | `N/A` |
| 17:18:50 | 7.75 | 40.5% | `N/A` |
| 17:18:52 | 7.75 | 40.5% | `N/A` |
| 17:18:54 | 7.61 | 40.4% | `N/A` |
| 17:18:57 | 7.61 | 40.5% | `N/A` |
| 17:18:59 | 7.4 | 40.8% | `N/A` |
| 17:19:01 | 7.4 | 40.8% | `N/A` |
| 17:19:04 | 7.45 | 40.7% | `N/A` |
| 17:19:06 | 7.45 | 41.5% | `N/A` |
| 17:19:08 | 7.5 | 41.7% | `N/A` |
| 17:19:11 | 7.5 | 40.9% | `N/A` |
| 17:19:13 | 7.3 | 40.8% | `N/A` |
| 17:19:15 | 7.3 | 40.8% | `N/A` |
| 17:19:18 | 7.27 | 40.5% | `N/A` |
| 17:19:20 | 7.27 | 40.5% | `N/A` |
| 17:19:22 | 7.27 | 40.5% | `N/A` |
| 17:19:25 | 7.17 | 40.9% | `N/A` |
| 17:19:27 | 7.17 | 38.9% | `N/A` |
