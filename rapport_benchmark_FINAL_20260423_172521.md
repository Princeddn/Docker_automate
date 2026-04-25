# 📊 Rapport Professionnel de Benchmark WAGO CC100 (ChirpStack v4)

## 1. 🎯 Conclusion et Capacité d'Ingestion Automatique

> **Débit d'ingestion robuste validé sans erreur claire :** 0 messages / seconde.

### 📡 Fiabilité de Décodage de bout-en-bout (MQTT Application)
- **Trames radio brutes envoyées** : 1315
- **Trames décodées avec succès (JSON)** : 145
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
| Phase 1 (0.5 msg/s) | 0.5 msg/s | 8 trames | 6 trames | 🟠 **25.0%** |
| Phase 2 (1.0 msg/s) | 1.0 msg/s | 15 trames | 14 trames | 🟠 **6.7%** |
| Phase 3 (1.5 msg/s) | 1.5 msg/s | 23 trames | 15 trames | 🟠 **34.8%** |
| Phase 4 (2.0 msg/s) | 2.0 msg/s | 30 trames | 12 trames | 🛑 **60.0%** |
| Phase 5 (2.5 msg/s) | 2.5 msg/s | 38 trames | 16 trames | 🛑 **57.9%** |
| Phase 6 (3.0 msg/s) | 3.0 msg/s | 45 trames | 14 trames | 🛑 **68.9%** |
| Phase 7 (3.5 msg/s) | 3.5 msg/s | 53 trames | 15 trames | 🛑 **71.7%** |
| Phase 8 (4.0 msg/s) | 4.0 msg/s | 60 trames | 12 trames | 🛑 **80.0%** |
| Phase 9 (4.5 msg/s) | 4.5 msg/s | 68 trames | 14 trames | 🛑 **79.4%** |
| Phase 10 (5.0 msg/s) | 5.0 msg/s | 75 trames | 13 trames | 🛑 **82.7%** |
| Phase 11 (10.0 msg/s - Torture) | 10.0 msg/s | 150 trames | 12 trames | 🛑 **92.0%** |
| Phase 12 (50.0 msg/s - Attaque DDoS) | 50.0 msg/s | 750 trames | 2 trames | 🛑 **99.7%** |

**Durée totale :** 265.5s | **Trames totales :** 1315

## 3. ⚠️ Analyse Interne ChirpStack (JavaScript Codec Errors)

Ceci indique si l'automate a manqué de temps CPU pour décoder les trames (Timeout 500ms).
❌ **936 erreurs détectées dans les logs Docker.** (CPU Probablement saturé)
```text
[2m2026-04-23T15:21:21.945495Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:21:22.034766Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:21:22.590383Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m3876388745[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
[2m2026-04-23T15:21:22.710235Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:21:23.194773Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:21:23.218571Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:21:23.985082Z[0m [35mTRACE[0m [1mtx_ack[0m[1m{[0m[3mdownlink_id[0m[2m=[0m2806437982[1m}[0m[2m:[0m [2mchirpstack::downlink::tx_ack[0m[2m:[0m Logging tx ack error
[2m2026-04-23T15:21:24.372979Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
[2m2026-04-23T15:21:24.463702Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mup [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=up)
[2m2026-04-23T15:21:24.486840Z[0m [33m WARN[0m [2mchirpstack::integration::http[0m[2m:[0m Posting event failed [3mevent[0m[2m=[0mlog [3murl[0m[2m=[0mhttp://192.168.3.100:8081/api/uplink [3merror[0m[2m=[0mHTTP status client error (404 Not Found) for url (http://192.168.3.100:8081/api/uplink?event=log)
```

## 4. 💽 Télémétrie Système (Load Average & Mémoire)

| Heure | Load CPU | Utilisation RAM (%) | Consommation Docker |
|-------|----------|---------------------|---------------------|
| 17:20:57 | 10.34 | 39.9% | `N/A` |
| 17:21:00 | 10.71 | 38.8% | `N/A` |
| 17:21:02 | 10.71 | 38.8% | `N/A` |
| 17:21:04 | 10.57 | 38.8% | `N/A` |
| 17:21:06 | 10.57 | 38.9% | `N/A` |
| 17:21:09 | 9.73 | 39.0% | `N/A` |
| 17:21:11 | 9.73 | 39.5% | `N/A` |
| 17:21:13 | 9.03 | 39.5% | `N/A` |
| 17:21:15 | 9.03 | 39.5% | `N/A` |
| 17:21:17 | 9.03 | 39.4% | `N/A` |
| 17:21:20 | 8.95 | 39.7% | `N/A` |
| 17:21:22 | 8.95 | 39.7% | `N/A` |
| 17:21:24 | 9.03 | 39.7% | `N/A` |
| 17:21:27 | 9.03 | 39.6% | `N/A` |
| 17:21:29 | 9.03 | 39.6% | `N/A` |
| 17:21:31 | 9.03 | 40.3% | `N/A` |
| 17:21:34 | 9.11 | 39.9% | `N/A` |
| 17:21:36 | 9.11 | 39.9% | `N/A` |
| 17:21:38 | 8.62 | 39.8% | `N/A` |
| 17:21:41 | 8.62 | 39.8% | `N/A` |
| 17:21:43 | 8.33 | 40.0% | `N/A` |
| 17:21:45 | 8.33 | 40.0% | `N/A` |
| 17:21:47 | 8.33 | 40.0% | `N/A` |
| 17:21:50 | 9.02 | 40.0% | `N/A` |
| 17:21:52 | 9.02 | 40.0% | `N/A` |
| 17:21:54 | 8.7 | 40.0% | `N/A` |
| 17:21:56 | 8.7 | 39.9% | `N/A` |
| 17:21:59 | 8.8 | 39.9% | `N/A` |
| 17:22:01 | 8.8 | 39.9% | `N/A` |
| 17:22:03 | 8.9 | 41.0% | `N/A` |
| 17:22:06 | 8.9 | 40.7% | `N/A` |
| 17:22:08 | 9.23 | 40.2% | `N/A` |
| 17:22:10 | 9.23 | 40.2% | `N/A` |
| 17:22:12 | 9.23 | 40.2% | `N/A` |
| 17:22:15 | 9.21 | 40.3% | `N/A` |
| 17:22:17 | 9.21 | 40.3% | `N/A` |
| 17:22:19 | 8.79 | 40.2% | `N/A` |
| 17:22:22 | 8.79 | 40.2% | `N/A` |
| 17:22:24 | 8.49 | 40.2% | `N/A` |
| 17:22:26 | 8.49 | 40.1% | `N/A` |
| 17:22:28 | 8.29 | 40.1% | `N/A` |
| 17:22:31 | 8.29 | 40.1% | `N/A` |
| 17:22:33 | 8.43 | 40.0% | `N/A` |
| 17:22:35 | 8.43 | 40.0% | `N/A` |
| 17:22:38 | 8.43 | 41.5% | `N/A` |
| 17:22:40 | 7.99 | 41.0% | `N/A` |
| 17:22:42 | 7.99 | 40.4% | `N/A` |
| 17:22:44 | 7.83 | 40.3% | `N/A` |
| 17:22:47 | 7.83 | 40.3% | `N/A` |
| 17:22:49 | 7.77 | 40.6% | `N/A` |
| 17:22:52 | 7.77 | 40.6% | `N/A` |
| 17:22:54 | 7.94 | 40.5% | `N/A` |
| 17:22:56 | 7.94 | 40.5% | `N/A` |
| 17:22:58 | 7.79 | 40.0% | `N/A` |
| 17:23:01 | 7.79 | 40.0% | `N/A` |
| 17:23:03 | 7.4 | 40.0% | `N/A` |
| 17:23:07 | 7.4 | 39.9% | `N/A` |
| 17:23:09 | 7.4 | 39.9% | `N/A` |
| 17:23:12 | 7.13 | 40.1% | `N/A` |
| 17:23:14 | 7.13 | 40.7% | `N/A` |
| 17:23:16 | 6.72 | 39.8% | `N/A` |
| 17:23:18 | 6.72 | 39.8% | `N/A` |
| 17:23:21 | 6.66 | 40.0% | `N/A` |
| 17:23:23 | 6.66 | 40.0% | `N/A` |
| 17:23:25 | 6.61 | 40.0% | `N/A` |
| 17:23:28 | 6.61 | 40.0% | `N/A` |
| 17:23:30 | 6.56 | 40.0% | `N/A` |
| 17:23:32 | 6.56 | 40.0% | `N/A` |
| 17:23:34 | 6.56 | 40.0% | `N/A` |
| 17:23:37 | 6.6 | 39.9% | `N/A` |
| 17:23:39 | 6.6 | 39.9% | `N/A` |
| 17:23:41 | 6.71 | 39.9% | `N/A` |
| 17:23:43 | 6.71 | 39.9% | `N/A` |
| 17:23:46 | 7.29 | 40.3% | `N/A` |
| 17:23:48 | 7.29 | 41.1% | `N/A` |
| 17:23:50 | 7.59 | 40.2% | `N/A` |
| 17:23:53 | 7.59 | 40.2% | `N/A` |
| 17:23:55 | 7.59 | 40.2% | `N/A` |
| 17:23:57 | 7.54 | 40.1% | `N/A` |
| 17:23:59 | 7.54 | 40.1% | `N/A` |
| 17:24:02 | 7.82 | 40.1% | `N/A` |
| 17:24:04 | 7.82 | 40.1% | `N/A` |
| 17:24:06 | 7.67 | 40.0% | `N/A` |
| 17:24:08 | 7.67 | 40.0% | `N/A` |
| 17:24:11 | 7.78 | 40.3% | `N/A` |
| 17:24:13 | 7.78 | 40.2% | `N/A` |
| 17:24:15 | 7.8 | 40.2% | `N/A` |
| 17:24:18 | 7.8 | 40.2% | `N/A` |
| 17:24:20 | 7.8 | 41.1% | `N/A` |
| 17:24:22 | 8.06 | 42.5% | `N/A` |
| 17:24:25 | 8.06 | 43.9% | `N/A` |
| 17:24:27 | 8.61 | 44.0% | `N/A` |
| 17:24:30 | 8.61 | 43.9% | `N/A` |
| 17:24:32 | 8.56 | 44.8% | `N/A` |
