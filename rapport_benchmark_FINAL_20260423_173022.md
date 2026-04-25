# 📊 Rapport Professionnel de Benchmark WAGO CC100 (ChirpStack v4)

## 1. 🎯 Conclusion et Capacité d'Ingestion Automatique

> **Débit d'ingestion robuste validé sans erreur claire :** 0.5 messages / seconde.

### 📡 Fiabilité de Décodage de bout-en-bout (MQTT Application)
- **Trames radio brutes envoyées** : 1315
- **Trames décodées avec succès (JSON)** : 150
- **Taux de Perte global (Chute CPU)** : **88.6%**
> ⚠️ *Note: Une perte > 0% signifie que le processeur (ARM 600Mhz) a été incapable de suivre la cadence et a dû jeter les trames avant décodage.*

### Projection pour un déploiement GTB réel (Bâtiment) :
Si ce WAGO maintient 0.5 requêtes par seconde sans saturer, voici sa capacité théorique maximale :
- Si les capteurs émettent toutes les **1 minute** : 30 capteurs supportés.
- Si les capteurs émettent toutes les **5 minutes** : 150 capteurs supportés.
- Si les capteurs émettent toutes les **15 minutes** (Standard GTB) : **450 capteurs supportés.**

## 2. 📈 Localisation de la Rupture de Charge (Par Phases)

| Phase | Vitesse (Msg/s) | Injections (Gateway) | Décodages (App) | Taux de Perte |
|-------|-----------------|----------------------|-----------------|---------------|
| Phase 1 (0.5 msg/s) | 0.5 msg/s | 8 trames | 8 trames | 🟢 **0.0%** |
| Phase 2 (1.0 msg/s) | 1.0 msg/s | 15 trames | 14 trames | 🟠 **6.7%** |
| Phase 3 (1.5 msg/s) | 1.5 msg/s | 23 trames | 13 trames | 🟠 **43.5%** |
| Phase 4 (2.0 msg/s) | 2.0 msg/s | 30 trames | 18 trames | 🟠 **40.0%** |
| Phase 5 (2.5 msg/s) | 2.5 msg/s | 38 trames | 13 trames | 🛑 **65.8%** |
| Phase 6 (3.0 msg/s) | 3.0 msg/s | 45 trames | 16 trames | 🛑 **64.4%** |
| Phase 7 (3.5 msg/s) | 3.5 msg/s | 53 trames | 14 trames | 🛑 **73.6%** |
| Phase 8 (4.0 msg/s) | 4.0 msg/s | 60 trames | 14 trames | 🛑 **76.7%** |
| Phase 9 (4.5 msg/s) | 4.5 msg/s | 68 trames | 12 trames | 🛑 **82.4%** |
| Phase 10 (5.0 msg/s) | 5.0 msg/s | 75 trames | 15 trames | 🛑 **80.0%** |
| Phase 11 (10.0 msg/s - Torture) | 10.0 msg/s | 150 trames | 9 trames | 🛑 **94.0%** |
| Phase 12 (50.0 msg/s - Attaque DDoS) | 50.0 msg/s | 750 trames | 4 trames | 🛑 **99.5%** |

**Durée totale :** 265.0s | **Trames totales :** 1315

## 3. ⚠️ Analyse Interne ChirpStack (JavaScript Codec Errors)

Ceci indique si l'automate a manqué de temps CPU pour décoder les trames (Timeout 500ms).
❌ **941 erreurs détectées dans les logs Docker.** (CPU Probablement saturé)
```text
[2m2026-04-23T15:26:35.337049Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:26:35.418251Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:26:35.893723Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m450673577[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
[2m2026-04-23T15:26:35.971782Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:26:36.531121Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:26:36.607851Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:26:37.146143Z[0m [31mERROR[0m [2mchirpstack::uplink[0m[2m:[0m Deduplication error [3merror[0m[2m=[0mZero items in collect set
[2m2026-04-23T15:26:37.221845Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:26:37.224927Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:26:37.722113Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m1190437890[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
```

## 4. 💽 Télémétrie Système (Load Average & Mémoire)

| Heure | Load CPU | Utilisation RAM (%) | Consommation Docker |
|-------|----------|---------------------|---------------------|
| 17:25:59 | 7.44 | 41.1% | `N/A` |
| 17:26:01 | 7.33 | 41.1% | `N/A` |
| 17:26:03 | 7.33 | 41.1% | `N/A` |
| 17:26:05 | 6.82 | 41.1% | `N/A` |
| 17:26:08 | 6.82 | 41.1% | `N/A` |
| 17:26:10 | 6.82 | 41.3% | `N/A` |
| 17:26:12 | 7.48 | 42.1% | `N/A` |
| 17:26:15 | 7.48 | 41.2% | `N/A` |
| 17:26:17 | 7.12 | 41.1% | `N/A` |
| 17:26:19 | 7.12 | 41.1% | `N/A` |
| 17:26:21 | 7.19 | 41.1% | `N/A` |
| 17:26:24 | 7.19 | 41.1% | `N/A` |
| 17:26:26 | 7.09 | 41.0% | `N/A` |
| 17:26:28 | 7.09 | 41.0% | `N/A` |
| 17:26:30 | 6.84 | 41.0% | `N/A` |
| 17:26:33 | 6.84 | 41.0% | `N/A` |
| 17:26:35 | 6.84 | 41.1% | `N/A` |
| 17:26:37 | 7.18 | 41.1% | `N/A` |
| 17:26:39 | 7.18 | 41.2% | `N/A` |
| 17:26:42 | 6.84 | 41.1% | `N/A` |
| 17:26:44 | 6.84 | 41.3% | `N/A` |
| 17:26:46 | 7.02 | 42.4% | `N/A` |
| 17:26:49 | 7.02 | 41.0% | `N/A` |
| 17:26:51 | 7.41 | 41.0% | `N/A` |
| 17:26:53 | 7.41 | 41.0% | `N/A` |
| 17:26:56 | 7.46 | 40.9% | `N/A` |
| 17:26:58 | 7.46 | 40.9% | `N/A` |
| 17:27:00 | 7.46 | 40.9% | `N/A` |
| 17:27:02 | 7.83 | 40.9% | `N/A` |
| 17:27:05 | 7.83 | 40.8% | `N/A` |
| 17:27:07 | 7.76 | 40.8% | `N/A` |
| 17:27:09 | 7.76 | 40.8% | `N/A` |
| 17:27:11 | 7.62 | 41.1% | `N/A` |
| 17:27:14 | 7.62 | 41.1% | `N/A` |
| 17:27:16 | 7.81 | 41.1% | `N/A` |
| 17:27:18 | 7.81 | 41.3% | `N/A` |
| 17:27:21 | 7.98 | 42.3% | `N/A` |
| 17:27:23 | 7.98 | 41.9% | `N/A` |
| 17:27:25 | 7.98 | 41.2% | `N/A` |
| 17:27:27 | 8.39 | 41.1% | `N/A` |
| 17:27:30 | 8.39 | 41.1% | `N/A` |
| 17:27:32 | 8.36 | 41.1% | `N/A` |
| 17:27:34 | 8.36 | 41.1% | `N/A` |
| 17:27:36 | 8.57 | 41.0% | `N/A` |
| 17:27:39 | 8.57 | 41.0% | `N/A` |
| 17:27:41 | 8.2 | 41.0% | `N/A` |
| 17:27:43 | 8.2 | 40.4% | `N/A` |
| 17:27:45 | 8.27 | 40.3% | `N/A` |
| 17:27:48 | 8.27 | 40.3% | `N/A` |
| 17:27:50 | 8.27 | 40.2% | `N/A` |
| 17:27:52 | 8.32 | 40.6% | `N/A` |
| 17:27:55 | 8.32 | 41.3% | `N/A` |
| 17:27:57 | 9.18 | 40.4% | `N/A` |
| 17:27:59 | 9.18 | 40.4% | `N/A` |
| 17:28:01 | 9.25 | 40.4% | `N/A` |
| 17:28:04 | 9.25 | 40.4% | `N/A` |
| 17:28:06 | 9.15 | 40.4% | `N/A` |
| 17:28:08 | 9.15 | 40.3% | `N/A` |
| 17:28:11 | 8.65 | 40.3% | `N/A` |
| 17:28:13 | 8.65 | 40.2% | `N/A` |
| 17:28:15 | 8.65 | 40.2% | `N/A` |
| 17:28:17 | 8.36 | 40.3% | `N/A` |
| 17:28:20 | 8.36 | 40.3% | `N/A` |
| 17:28:22 | 8.57 | 40.1% | `N/A` |
| 17:28:24 | 8.57 | 40.3% | `N/A` |
| 17:28:27 | 8.21 | 40.3% | `N/A` |
| 17:28:29 | 8.21 | 41.6% | `N/A` |
| 17:28:31 | 8.43 | 40.6% | `N/A` |
| 17:28:34 | 8.43 | 40.4% | `N/A` |
| 17:28:36 | 8.64 | 40.4% | `N/A` |
| 17:28:38 | 8.64 | 40.4% | `N/A` |
| 17:28:40 | 8.64 | 40.3% | `N/A` |
| 17:28:43 | 8.34 | 40.4% | `N/A` |
| 17:28:45 | 8.34 | 40.3% | `N/A` |
| 17:28:47 | 8.0 | 40.3% | `N/A` |
| 17:28:49 | 8.0 | 40.5% | `N/A` |
| 17:28:52 | 7.6 | 40.5% | `N/A` |
| 17:28:54 | 7.6 | 40.4% | `N/A` |
| 17:28:56 | 7.47 | 40.4% | `N/A` |
| 17:28:59 | 7.47 | 40.3% | `N/A` |
| 17:29:01 | 7.27 | 40.3% | `N/A` |
| 17:29:03 | 7.27 | 41.5% | `N/A` |
| 17:29:05 | 7.27 | 41.6% | `N/A` |
| 17:29:08 | 7.73 | 40.8% | `N/A` |
| 17:29:10 | 7.73 | 40.6% | `N/A` |
| 17:29:12 | 7.43 | 40.5% | `N/A` |
| 17:29:15 | 7.43 | 40.5% | `N/A` |
| 17:29:17 | 7.08 | 40.4% | `N/A` |
| 17:29:19 | 7.08 | 40.5% | `N/A` |
| 17:29:21 | 6.75 | 40.9% | `N/A` |
| 17:29:24 | 6.75 | 41.6% | `N/A` |
| 17:29:26 | 7.17 | 42.6% | `N/A` |
| 17:29:28 | 7.17 | 43.5% | `N/A` |
| 17:29:31 | 7.08 | 44.1% | `N/A` |
| 17:29:33 | 7.08 | 44.6% | `N/A` |
