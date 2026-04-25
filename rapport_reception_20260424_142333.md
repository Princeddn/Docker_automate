# 📊 Rapport d'Analyse du Taux de Réception LoRaWAN

**Date** : 2026-04-24 14:23:33  
**Cible** : WAGO CC100 (`192.168.3.100`)  
**Gateway** : `YOUR_GATEWAY_ID`  

## 1. Résumé

> **Débit max fiable (≥95% réception)** : **0.5 msg/s**  
> **Ratio global IN/OUT** : 1838 envoyés → 378 reçus (**20.6%**)  

## 2. Résultats par Palier

| Palier | Cible (msg/s) | Réel (msg/s) | Durée | IN | OUT | Ratio | Perte | Status |
|--------|---------------|--------------|-------|----|-----|-------|-------|--------|
| 1 | 0.5 msg/s | 0.5 msg/s | 30s | 15 | 16 | **106.7%** | -6.7% | ✅ OK |
| 2 | 1.0 msg/s | 1.0 msg/s | 30s | 30 | 27 | **90.0%** | 10.0% | ⚠️ WARN |
| 3 | 1.5 msg/s | 1.5 msg/s | 30s | 45 | 29 | **64.4%** | 35.6% | 🛑 FAIL |
| 4 | 2.0 msg/s | 2.0 msg/s | 30s | 60 | 29 | **48.3%** | 51.7% | 🛑 FAIL |
| 5 | 2.5 msg/s | 2.52 msg/s | 25s | 63 | 26 | **41.3%** | 58.7% | 🛑 FAIL |
| 6 | 3.0 msg/s | 3.0 msg/s | 25s | 75 | 23 | **30.7%** | 69.3% | 🛑 FAIL |
| 7 | 3.5 msg/s | 3.52 msg/s | 25s | 88 | 24 | **27.3%** | 72.7% | 🛑 FAIL |
| 8 | 4.0 msg/s | 4.0 msg/s | 20s | 80 | 21 | **26.2%** | 73.8% | 🛑 FAIL |
| 9 | 4.5 msg/s | 4.5 msg/s | 20s | 90 | 21 | **23.3%** | 76.7% | 🛑 FAIL |
| 10 | 5.0 msg/s | 5.0 msg/s | 20s | 100 | 19 | **19.0%** | 81.0% | 🛑 FAIL |
| 11 | 5.5 msg/s | 5.5 msg/s | 20s | 110 | 18 | **16.4%** | 83.6% | 🛑 FAIL |
| 12 | 6.0 msg/s | 6.0 msg/s | 15s | 90 | 16 | **17.8%** | 82.2% | 🛑 FAIL |
| 13 | 6.5 msg/s | 6.53 msg/s | 15s | 98 | 13 | **13.3%** | 86.7% | 🛑 FAIL |
| 14 | 7.0 msg/s | 7.0 msg/s | 15s | 105 | 14 | **13.3%** | 86.7% | 🛑 FAIL |
| 15 | 7.5 msg/s | 7.53 msg/s | 15s | 113 | 18 | **15.9%** | 84.1% | 🛑 FAIL |
| 16 | 8.0 msg/s | 8.0 msg/s | 15s | 120 | 14 | **11.7%** | 88.3% | 🛑 FAIL |
| 17 | 8.5 msg/s | 8.53 msg/s | 15s | 128 | 16 | **12.5%** | 87.5% | 🛑 FAIL |
| 18 | 9.0 msg/s | 9.0 msg/s | 15s | 135 | 11 | **8.1%** | 91.9% | 🛑 FAIL |
| 19 | 9.5 msg/s | 9.53 msg/s | 15s | 143 | 12 | **8.4%** | 91.6% | 🛑 FAIL |
| 20 | 10.0 msg/s | 10.0 msg/s | 15s | 150 | 11 | **7.3%** | 92.7% | 🛑 FAIL |

**Total** : 1838 trames injectées → 378 trames décodées (**20.6%**)  

## 3. Projection Déploiement

En se basant sur un débit fiable de **0.5 msg/s** :

| Intervalle d'émission | Capteurs supportés |
|----------------------|--------------------|
| Toutes les 1 minute  | **30** capteurs |
| Toutes les 5 minutes | **150** capteurs |
| Toutes les 15 minutes (Standard GTB) | **450** capteurs |

## 4. Interprétation

- **Ratio ≥ 98%** : Le système absorbe la charge sans perte significative.
- **Ratio 80-98%** : Zone de dégradation. Le CPU ARM 600MHz commence à saturer.
- **Ratio < 80%** : Effondrement. Le codec JavaScript timeout (>500ms) et les trames sont jetées.
