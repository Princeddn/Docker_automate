# 📊 Rapport Professionnel de Benchmark WAGO CC100 (ChirpStack v4)

## 1. 🎯 Conclusion et Capacité d'Ingestion Automatique

> **Débit d'ingestion robuste validé sans erreur claire :** 0 messages / seconde.

### 📡 Fiabilité de Décodage de bout-en-bout (MQTT Application)
- **Trames radio brutes envoyées** : 1315
- **Trames décodées avec succès (JSON)** : 144
- **Taux de Perte global (Chute CPU)** : **89.0%**
> ⚠️ *Note: Une perte > 0% signifie que le processeur (ARM 600Mhz) a été incapable de suivre la cadence et a dû jeter les trames avant décodage.*

### Projection pour un déploiement GTB réel (Bâtiment) :
Si ce WAGO maintient 0 requêtes par seconde sans saturer, voici sa capacité théorique maximale :
- Si les capteurs émettent toutes les **1 minute** : 0 capteurs supportés.
- Si les capteurs émettent toutes les **5 minutes** : 0 capteurs supportés.
- Si les capteurs émettent toutes les **15 minutes** (Standard GTB) : **0 capteurs supportés.**

## 2. 📈 Localisation de la Rupture de Charge (Par Phases)

| Phase | Vitesse (Msg/s) | Injections (Gateway) | Décodages (App) | Taux de Perte |
|-------|-----------------|----------------------|-----------------|---------------|
| Phase 1 (0.5 msg/s) | 0.5 msg/s | 8 trames | 7 trames | 🟠 **12.5%** |
| Phase 2 (1.0 msg/s) | 1.0 msg/s | 15 trames | 12 trames | 🟠 **20.0%** |
| Phase 3 (1.5 msg/s) | 1.5 msg/s | 23 trames | 17 trames | 🟠 **26.1%** |
| Phase 4 (2.0 msg/s) | 2.0 msg/s | 30 trames | 12 trames | 🛑 **60.0%** |
| Phase 5 (2.5 msg/s) | 2.5 msg/s | 38 trames | 15 trames | 🛑 **60.5%** |
| Phase 6 (3.0 msg/s) | 3.0 msg/s | 45 trames | 13 trames | 🛑 **71.1%** |
| Phase 7 (3.5 msg/s) | 3.5 msg/s | 53 trames | 12 trames | 🛑 **77.4%** |
| Phase 8 (4.0 msg/s) | 4.0 msg/s | 60 trames | 15 trames | 🛑 **75.0%** |
| Phase 9 (4.5 msg/s) | 4.5 msg/s | 68 trames | 13 trames | 🛑 **80.9%** |
| Phase 10 (5.0 msg/s) | 5.0 msg/s | 75 trames | 14 trames | 🛑 **81.3%** |
| Phase 11 (10.0 msg/s - Torture) | 10.0 msg/s | 150 trames | 10 trames | 🛑 **93.3%** |
| Phase 12 (50.0 msg/s - Attaque DDoS) | 50.0 msg/s | 750 trames | 4 trames | 🛑 **99.5%** |

**Durée totale :** 266.5s | **Trames totales :** 1315

## 3. ⚠️ Analyse Interne ChirpStack (JavaScript Codec Errors)

Ceci indique si l'automate a manqué de temps CPU pour décoder les trames (Timeout 500ms).
❌ **887 erreurs détectées dans les logs Docker.** (CPU Probablement saturé)
```text
[2m2026-04-24T11:24:45.089504Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m2674764962[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
[2m2026-04-24T11:24:45.326264Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-24T11:24:45.524306Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-24T11:24:45.552902Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-24T11:24:46.426902Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m2968371292[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
[2m2026-04-24T11:24:46.603754Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-24T11:24:46.667634Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-24T11:24:46.691384Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-24T11:24:47.492307Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-24T11:24:47.554649Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
```

## 4. 💽 Télémétrie Système (Load Average & Mémoire)

| Heure | Load CPU | Utilisation RAM (%) | Consommation Docker |
|-------|----------|---------------------|---------------------|
| 13:24:05 | 2.56 | 34.8% | `N/A` |
| 13:24:07 | 2.56 | 35.5% | `N/A` |
| 13:24:09 | 3.07 | 35.2% | `N/A` |
| 13:24:12 | 3.07 | 35.3% | `N/A` |
| 13:24:14 | 3.47 | 35.8% | `N/A` |
| 13:24:16 | 3.47 | 35.9% | `N/A` |
| 13:24:18 | 3.59 | 36.0% | `N/A` |
| 13:24:21 | 3.59 | 36.0% | `N/A` |
| 13:24:23 | 3.59 | 36.1% | `N/A` |
| 13:24:25 | 3.62 | 36.2% | `N/A` |
| 13:24:28 | 3.62 | 36.3% | `N/A` |
| 13:24:30 | 3.97 | 37.0% | `N/A` |
| 13:24:32 | 3.97 | 36.9% | `N/A` |
| 13:24:35 | 4.3 | 36.9% | `N/A` |
| 13:24:37 | 4.3 | 36.8% | `N/A` |
| 13:24:39 | 4.35 | 36.8% | `N/A` |
| 13:24:41 | 4.35 | 37.0% | `N/A` |
| 13:24:44 | 4.25 | 37.0% | `N/A` |
| 13:24:46 | 4.25 | 36.9% | `N/A` |
| 13:24:48 | 4.25 | 36.9% | `N/A` |
| 13:24:50 | 4.39 | 36.9% | `N/A` |
| 13:24:53 | 4.39 | 36.9% | `N/A` |
| 13:24:55 | 4.68 | 36.8% | `N/A` |
| 13:24:58 | 4.68 | 36.8% | `N/A` |
| 13:25:00 | 5.34 | 36.8% | `N/A` |
| 13:25:02 | 5.34 | 37.5% | `N/A` |
| 13:25:04 | 5.64 | 37.5% | `N/A` |
| 13:25:07 | 5.64 | 37.2% | `N/A` |
| 13:25:09 | 5.5 | 37.2% | `N/A` |
| 13:25:11 | 5.5 | 37.7% | `N/A` |
| 13:25:14 | 6.18 | 37.7% | `N/A` |
| 13:25:16 | 6.18 | 37.7% | `N/A` |
| 13:25:18 | 6.18 | 37.7% | `N/A` |
| 13:25:20 | 6.65 | 37.7% | `N/A` |
| 13:25:23 | 6.65 | 37.7% | `N/A` |
| 13:25:25 | 7.16 | 37.6% | `N/A` |
| 13:25:27 | 7.16 | 37.7% | `N/A` |
| 13:25:30 | 7.15 | 37.7% | `N/A` |
| 13:25:32 | 7.15 | 37.7% | `N/A` |
| 13:25:34 | 6.89 | 37.8% | `N/A` |
| 13:25:37 | 6.89 | 38.6% | `N/A` |
| 13:25:39 | 6.9 | 38.2% | `N/A` |
| 13:25:41 | 6.9 | 38.2% | `N/A` |
| 13:25:44 | 7.23 | 38.2% | `N/A` |
| 13:25:46 | 7.23 | 38.7% | `N/A` |
| 13:25:48 | 7.23 | 38.1% | `N/A` |
| 13:25:51 | 7.37 | 38.1% | `N/A` |
| 13:25:53 | 7.37 | 38.0% | `N/A` |
| 13:25:55 | 7.02 | 38.0% | `N/A` |
| 13:25:57 | 7.02 | 38.0% | `N/A` |
| 13:26:00 | 7.18 | 38.2% | `N/A` |
| 13:26:02 | 7.18 | 38.4% | `N/A` |
| 13:26:04 | 7.09 | 38.5% | `N/A` |
| 13:26:06 | 7.09 | 38.4% | `N/A` |
| 13:26:09 | 7.4 | 38.6% | `N/A` |
| 13:26:11 | 7.4 | 38.4% | `N/A` |
| 13:26:13 | 7.4 | 38.4% | `N/A` |
| 13:26:16 | 7.45 | 38.4% | `N/A` |
| 13:26:18 | 7.45 | 38.4% | `N/A` |
| 13:26:20 | 7.65 | 39.2% | `N/A` |
| 13:26:22 | 7.65 | 38.6% | `N/A` |
| 13:26:25 | 7.52 | 38.6% | `N/A` |
| 13:26:27 | 7.52 | 38.5% | `N/A` |
| 13:26:29 | 7.48 | 38.5% | `N/A` |
| 13:26:32 | 7.48 | 38.5% | `N/A` |
| 13:26:34 | 7.28 | 38.5% | `N/A` |
| 13:26:36 | 7.28 | 38.5% | `N/A` |
| 13:26:38 | 7.28 | 38.5% | `N/A` |
| 13:26:41 | 7.26 | 38.4% | `N/A` |
| 13:26:43 | 7.26 | 39.0% | `N/A` |
| 13:26:45 | 7.16 | 38.7% | `N/A` |
| 13:26:48 | 7.16 | 38.7% | `N/A` |
| 13:26:50 | 6.66 | 38.6% | `N/A` |
| 13:26:52 | 6.66 | 38.6% | `N/A` |
| 13:26:55 | 6.61 | 39.2% | `N/A` |
| 13:26:57 | 6.61 | 38.5% | `N/A` |
| 13:26:59 | 6.56 | 38.4% | `N/A` |
| 13:27:01 | 6.56 | 38.4% | `N/A` |
| 13:27:03 | 6.56 | 38.5% | `N/A` |
| 13:27:06 | 7.08 | 38.5% | `N/A` |
| 13:27:08 | 7.08 | 38.4% | `N/A` |
| 13:27:11 | 6.99 | 38.4% | `N/A` |
| 13:27:13 | 6.99 | 38.4% | `N/A` |
| 13:27:15 | 6.99 | 38.5% | `N/A` |
| 13:27:18 | 6.99 | 39.5% | `N/A` |
| 13:27:20 | 7.23 | 38.8% | `N/A` |
| 13:27:22 | 7.23 | 38.8% | `N/A` |
| 13:27:25 | 7.05 | 38.7% | `N/A` |
| 13:27:27 | 7.05 | 39.7% | `N/A` |
| 13:27:30 | 7.61 | 39.7% | `N/A` |
| 13:27:32 | 7.61 | 40.7% | `N/A` |
| 13:27:34 | 7.64 | 41.4% | `N/A` |
| 13:27:37 | 7.64 | 42.1% | `N/A` |
| 13:27:39 | 7.51 | 43.2% | `N/A` |
| 13:27:41 | 7.51 | 43.7% | `N/A` |
