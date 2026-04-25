# 📊 Rapport d'Analyse du Taux de Réception LoRaWAN

**Date** : 2026-04-24 13:55:00  
**Cible** : WAGO CC100 (`192.168.3.100`)  
**Gateway** : `YOUR_GATEWAY_ID`  

## 1. Résumé

> **Débit max fiable (≥95% réception)** : **0.5 msg/s**  
> **Ratio global IN/OUT** : 1215 envoyés → 132 reçus (**10.9%**)  

## 2. Résultats par Palier

| Palier | Cible (msg/s) | Réel (msg/s) | Durée | IN | OUT | Ratio | Perte | Status |
|--------|---------------|--------------|-------|----|-----|-------|-------|--------|
| 1 | 0.5 msg/s | 0.5 msg/s | 30s | 15 | 15 | **100.0%** | 0.0% | ✅ OK |
| 2 | 1.0 msg/s | 1.0 msg/s | 30s | 30 | 28 | **93.3%** | 6.7% | ⚠️ WARN |
| 3 | 2.0 msg/s | 2.0 msg/s | 30s | 60 | 30 | **50.0%** | 50.0% | 🛑 FAIL |
| 4 | 3.0 msg/s | 3.0 msg/s | 20s | 60 | 20 | **33.3%** | 66.7% | 🛑 FAIL |
| 5 | 5.0 msg/s | 5.0 msg/s | 20s | 100 | 21 | **21.0%** | 79.0% | 🛑 FAIL |
| 6 | 10.0 msg/s | 10.0 msg/s | 15s | 150 | 15 | **10.0%** | 90.0% | 🛑 FAIL |
| 7 | 20.0 msg/s | 20.0 msg/s | 15s | 300 | 3 | **1.0%** | 99.0% | 🛑 FAIL |
| 8 | 50.0 msg/s | 50.0 msg/s | 10s | 500 | 0 | **0.0%** | 100.0% | 🛑 FAIL |

**Total** : 1215 trames injectées → 132 trames décodées (**10.9%**)  

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
