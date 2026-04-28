# Configuration du Protocole LoRaWAN

Avant de détailler les fichiers de configuration, il est essentiel de bien comprendre **où se trouve chaque composant**, **comment ils communiquent entre eux**, et surtout **le double rôle du broker MQTT** dans cette architecture.

### Vue d'ensemble : Qui est où ?

Le schéma ci-dessous montre l'emplacement physique de chaque élément. Tous les logiciels (du Gateway Bridge jusqu'aux bases de données) tournent **à l'intérieur de l'automate WAGO**, dans un réseau Docker isolé. Seule la passerelle radio RAK est un équipement externe.

```mermaid
graph TD
    subgraph "ZONE TERRAIN — Dans le bâtiment (Air)"
        C1["Capteur LoRaWAN<br/>(ex: Sonde CO₂ Nexelec)"]
    end

    subgraph "ARMOIRE TECHNIQUE — Passerelle Radio"
        RAK["Passerelle RAK7268<br/>Rôle : Recevoir les ondes radio<br/>et les transmettre par câble Ethernet"]
    end

    subgraph "AUTOMATE WAGO CC100 — Réseau Docker interne 'lora_net'"
        GB["Gateway Bridge<br/>Écoute sur le port 1700 (UDP)<br/>Rôle : Convertir UDP → message MQTT"]
        
        MQ["Broker Mosquitto<br/>Port 1883 (TCP)<br/>Rôle : DISTRIBUER les messages<br/>entre tous les services"]
        
        CS["ChirpStack v4<br/>Port interne 8080<br/>Rôle : DÉCHIFFRER et DÉCODER<br/>les données capteurs"]
        
        RD[("Redis — Port 6379<br/>Rôle : Stocker les sessions<br/>actives des capteurs")]
        
        PG[("PostgreSQL — Port 5432<br/>Rôle : Stocker la configuration<br/>et l'historique des trames")]
    end

    subgraph "POSTE OPÉRATEUR — Navigateur Web"
        APP["Interface ChirpStack<br/>Accessible sur le port 8081<br/>+ API REST pour intégrations"]
    end

    C1 -->|"Onde radio LoRa<br/>868 MHz, chiffrée AES-128"| RAK
    RAK -->|"Câble Ethernet<br/>Protocole UDP (port 1700)"| GB
    GB -->|"Publie sur Mosquitto"| MQ
    MQ -->|"Transmet à ChirpStack"| CS
    CS <-->|"Sessions"| RD
    CS <-->|"Archivage"| PG
    CS -->|"HTTP (port 8081)"| APP
```

### Point clé : Le double rôle de Mosquitto (Broker MQTT)

C'est le point qui peut prêter à confusion. **Mosquitto est un composant totalement indépendant de ChirpStack.** C'est un service séparé, dans son propre conteneur Docker. Il ne sait rien du LoRaWAN : son seul travail est de **recevoir des messages et de les redistribuer** à ceux qui les demandent.

Or, ChirpStack utilise Mosquitto **deux fois**, pour deux choses très différentes :

```mermaid
graph TD
    subgraph "Broker Mosquitto — Le facteur central"
        BOITE_A[" Boîte aux lettres A<br/>Topic : eu868/gateway/.../event/up<br/>(Contenu : trame radio CHIFFRÉE)"]
        BOITE_B[" Boîte aux lettres B<br/>Topic : application/.../event/up<br/>(Contenu : donnée LISIBLE en JSON)"]
    end

    GB["Gateway Bridge"] -->|"1. Dépose la trame<br/>radio brute (Protobuf)"| BOITE_A

    BOITE_A -->|"2. ChirpStack RÉCUPÈRE<br/>la trame chiffrée"| CS["ChirpStack v4"]

    CS -->|"3. Après déchiffrement,<br/>ChirpStack DÉPOSE la donnée<br/>lisible (ex: temp = 22.5°C)"| BOITE_B

    BOITE_B -->|"4. N'importe quel client<br/>peut RÉCUPÉRER la donnée"| APP["Application tierce<br/>(Jeedom, Node-RED,<br/>Dashboard custom...)"]

    style BOITE_A fill:#fff3e0,stroke:#ff9800,color:#000
    style BOITE_B fill:#e8f5e9,stroke:#4caf50,color:#000
    style CS fill:#e3f2fd,stroke:#2196f3,color:#000
```

**Explication pas à pas :**

| Étape | Qui agit ? | Que se passe-t-il ? | Où dans Mosquitto ? |
|:---:|:---|:---|:---|
| **1** | **Gateway Bridge** | Reçoit le paquet UDP brut de la passerelle radio et le **dépose** dans Mosquitto | Topic `eu868/gateway/.../event/up` ( Boîte A — données chiffrées) |
| **2** | **ChirpStack** (lecture) | **Récupère** le message chiffré depuis Mosquitto, vérifie les clés AES-128 dans Redis, et décode la payload | ChirpStack **lit** la Boîte A |
| **3** | **ChirpStack** (écriture) | Une fois la donnée déchiffrée (ex: `température = 22.5°C`), ChirpStack la **republie** dans Mosquitto sous un format JSON lisible | Topic `application/.../event/up` ( Boîte B — données lisibles) |
| **4** | **Application tierce** | N'importe quel logiciel (Jeedom, Node-RED, script Python...) peut s'abonner à la Boîte B pour récupérer les données capteurs déjà décodées | Lecture de la Boîte B |

> **En résumé :** Mosquitto ne déchiffre rien, ne comprend rien. Il fait juste transiter des boîtes. ChirpStack est le seul à savoir ouvrir la boîte chiffrée (Boîte A) et à en produire une version lisible (Boîte B). C'est cette deuxième publication (étape 3) qui correspond à la section `[integration.mqtt]` dans le fichier de configuration `chirpstack.toml`.

Les fichiers de configuration TOML présentés ci-dessous ont pour but de paramétrer chacun de ces liens, ports, et topics de communication.

## Configuration ChirpStack v4 (TOML)

ChirpStack v4 impose une architecture de configuration stricte en **deux fichiers TOML séparés**. Cette séparation, source d'un incident documenté au chapitre VIII, est désormais automatisée par le script d'installation.

### Fichier principal : `chirpstack.toml`

Ce fichier gère les connexions aux services internes (bases de données, broker MQTT) et déclare les régions activées :

```toml
[logging]
  level = "info"

[postgresql]
  dsn = "postgresql://chirpstack:YOUR_PASSWORD@lora-postgres/chirpstack?sslmode=disable"

[redis]
  servers = ["redis://lora-redis/"]

[network]
  net_id = "000000"
  enabled_regions = ["eu868"]

[api]
  bind = "0.0.0.0:8080"

[integration]
  enabled = ["mqtt"]

  [integration.mqtt]
    server   = "tcp://lora-mosquitto:1883"
    username = "chirpstack"
    password = "YOUR_PASSWORD"
    json     = true
```

**Points techniques notables :**
- Les noms d'hôtes (`lora-postgres`, `lora-redis`, `lora-mosquitto`) sont résolus automatiquement par le DNS Docker interne du réseau `lora_net`
- L'API écoute sur `0.0.0.0:8080` (port interne), mappé vers `8081` sur l'hôte pour éviter le conflit avec Jeedom
- L'intégration MQTT est activée en mode JSON pour permettre le décodage des payloads par des services tiers

> **Lien avec le graphe d'architecture :** Le bloc `[integration.mqtt]` ci-dessus correspond exactement à la ** Boîte B** (topic `application/.../event/up`) décrite dans le schéma du double rôle de Mosquitto en début de chapitre. C'est par cette section que ChirpStack **republie** les données décodées (ex: `température = 22.5°C`) dans Mosquitto, les rendant accessibles à n'importe quelle application tierce.

### Fichier régional : `region_eu868.toml`

Ce fichier définit les paramètres radio spécifiques à la bande EU868 (Europe, 863–870 MHz). Il utilise la syntaxe **Array of Tables** TOML (`[[regions]]` avec double crochet) :

```toml
[[regions]]
  id          = "eu868"
  description = "EU868"
  common_name = "EU868"

  [regions.gateway.backend]
    enabled = "mqtt"

    [regions.gateway.backend.mqtt]
      topic_prefix = "eu868"
      server       = "tcp://lora-mosquitto:1883"
      username     = "chirpstack"
      password     = "YOUR_PASSWORD"
      qos          = 0
      clean_session = false

  # 8 canaux LoRa + 1 canal FSK — Standard LoRa Alliance EU868
  [[regions.gateway.channels]]
    frequency         = 868100000    # 868.1 MHz
    bandwidth         = 125000
    modulation        = "LORA"
    spreading_factors = [7, 8, 9, 10, 11, 12]

  [[regions.gateway.channels]]
    frequency         = 868300000    # 868.3 MHz — (identique structure)
    # ... (7 canaux LoRa supplémentaires + 1 canal FSK)

  [regions.network]
    installation_margin = 10
    rx_window           = 0          # RX1 puis RX2
    rx1_delay           = 1          # 1 seconde après uplink
    rx2_frequency       = 869525000  # 869.525 MHz (standard EU)
    adr_disabled        = false
    min_dr              = 0
    max_dr              = 5
```

### Fichier passerelle : `chirpstack-gateway-bridge.toml`

Le Gateway Bridge fait le lien entre le monde physique (UDP Semtech) et le monde logiciel (MQTT Protobuf) :

```toml
[integration.mqtt]
  event_topic_template   = "eu868/gateway/{{ .GatewayID }}/event/{{ .EventType }}"
  command_topic_template = "eu868/gateway/{{ .GatewayID }}/command/#"
  marshaler              = "protobuf"

[integration.mqtt.auth.generic]
  servers  = ["tcp://lora-mosquitto:1883"]
  username = "chirpstack"
  password = "YOUR_PASSWORD"

[backend.semtech_udp]
  udp_bind = "0.0.0.0:1700"
```

> **Règle critique :** Le `topic_prefix` doit être **identique** dans les trois fichiers de configuration (`eu868`). Toute divergence crée un « silence radio » total — la stack fonctionne sans erreur apparente mais aucun paquet n'est traité. Cet incident a été rencontré et documenté au chapitre VIII.

```mermaid
graph LR
    GBT["chirpstack-gateway-bridge.toml<br/>topic_prefix = eu868"] --> MQ{"Mosquitto<br/>Topic : eu868/gateway/..."}
    CSR["region_eu868.toml<br/>topic_prefix = eu868"] --> MQ
    CSM["chirpstack.toml<br/>enabled_regions = eu868"] --> MQ
    
    MQ -->|"Les 3 sont identiques"| OK["Trames reçues"]
    MQ -->|"Un seul différent"| KO["Silence radio total"]
```

## Configuration de la Passerelle RAK7268

La configuration de la passerelle RAK requiert une intervention SSH directe, l'interface web étant sujette à un bug de réinitialisation des paramètres :

```bash
# Connexion SSH à la passerelle
ssh root@<IP_RAK7268>

# 1. Désactiver le serveur LoRa embarqué (libère le port 1700)
/etc/init.d/lorasrv stop
/etc/init.d/lorasrv disable

# 2. Configurer la destination UDP vers le WAGO
uci set lora_pkt_fwd.gateway_conf.server_address='192.168.3.100'
uci set lora_pkt_fwd.gateway_conf.serv_port_up=1700
uci set lora_pkt_fwd.gateway_conf.serv_port_down=1700

# 3. PARAMÈTRE CRITIQUE : Forcer le protocole UDP classique
uci set lora_pkt_fwd.gateway_conf.proto='udp'

# 4. Appliquer et redémarrer
uci commit lora_pkt_fwd
/etc/init.d/sx130x_lora_pkt_fwd restart

# 5. Vérifier
cat /var/etc/global_conf.json | grep server_address
# Attendu : "server_address": "192.168.3.100"
```

## Vérification End-to-End

La validation de la chaîne complète (capteur → gateway → WAGO → ChirpStack) se fait en deux étapes :

**Étape 1 — Vérifier la réception des trames MQTT :**
```bash
docker exec -it lora-mosquitto sh -lc \
  'mosquitto_sub -v -u chirpstack -P YOUR_PASSWORD -t "eu868/gateway/#"'
```
Si une trame apparaît contenant `event/up`, la chaîne radio → MQTT est fonctionnelle.

**Étape 2 — Vérifier le traitement par ChirpStack :**
```bash
docker logs -n 50 lora-chirpstack | grep "Setting up"
# Attendu : "Setting up gateway backends"
```
Si ce message est absent, la région EU868 n'est pas activée (voir incident C, chapitre VIII).

---

# Journal des Interventions et Troubleshooting

Ce chapitre documente les quatre incidents majeurs rencontrés au cours du projet, leurs analyses techniques et leurs résolutions. Ce retour d'expérience terrain constitue une base de connaissances précieuse pour tout futur déploiement Docker sur automate embarqué.

## Incident A — Conflit de Port 8080 avec Jeedom

| Champ | Détail |
|:---|:---|
| **Date** | 5 février 2026 |
| **Symptôme** | Conteneur `lora-chirpstack` en boucle de redémarrage (`Restarting (1) X seconds ago`) |
| **Log d'erreur** | `bind: address already in use (0.0.0.0:8080)` |
| **Cause racine** | Un conteneur Jeedom pré-installé sur l'automate occupait le port 8080 |
| **Impact** | Interface ChirpStack inaccessible, stack inopérante |

**Méthode de diagnostic :**
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
# Révèle : jeedom → 0.0.0.0:8080->80/tcp
```

**Résolution :**
1. Arrêt du conteneur interférant : `docker stop jeedom && docker rm jeedom`
2. Remappage du port ChirpStack : `8081:8080` dans le script d'installation

**Prévention :** Le script `install_lora.sh` utilise désormais systématiquement le port 8081 pour éviter tout conflit futur avec des applications tierces.

**Leçon GTB :** Sur un automate de bâtiment, plusieurs applications coexistent. Docker ne suffit pas à lui seul à éviter les conflits de ports entre conteneurs et l'hôte. Le script d'installation doit intégrer cette réalité terrain dès la conception.

## Incident B — Erreur de Syntaxe TOML (Rupture v3 → v4)

| Champ | Détail |
|:---|:---|
| **Date** | 5 février 2026 |
| **Symptôme** | ChirpStack refuse de démarrer immédiatement après lancement |
| **Log d'erreur** | `Error: TOML parse error at line 77, column 2 ... duplicate key [regions]` |
| **Cause racine** | Incompatibilité de syntaxe TOML entre ChirpStack v3 et v4 |
| **Impact** | Stack entièrement inopérante |

**Analyse technique détaillée :**

ChirpStack v4 a introduit un changement de format de configuration :
- **v3** : `[regions]` — définition d'une **Table** TOML simple
- **v4** : `[[regions]]` — définition d'un **Array of Tables** TOML (double crochet)

Le parser Rust de ChirpStack v4 détecte la coexistence des deux syntaxes comme une duplication de clé et rejette la configuration.

**Résolution :**
1. Séparation stricte en deux fichiers (`chirpstack.toml` et `region_eu868.toml`)
2. Le fichier principal ne conserve que `enabled_regions=["eu868"]`
3. Transfert des fichiers par **SCP** (Secure Copy) et non par copier-coller terminal, qui corrompait les retours à la ligne

**Prévention :** Le script génère automatiquement les deux fichiers avec la syntaxe correcte pour v4.

## Incident C — Silence Radio (Topic MQTT Divergent)

| Champ | Détail |
|:---|:---|
| **Date** | 5 février 2026 |
| **Symptôme** | Stack entièrement opérationnelle, gateway « Online » dans l'interface, **aucun paquet capteur reçu** |
| **Cause racine** | La région EU868 avait été commentée/désactivée lors du débogage de l'incident B |
| **Impact** | Système en apparence fonctionnel mais sourd — le pire type de panne |

**Diagnostic :** Absence du message `Setting up gateway backends` dans les logs ChirpStack. Ce message confirme qu'au moins une région radio est active et que ChirpStack écoute effectivement les topics MQTT correspondants.

**Résolution :** Réactivation de `enabled_regions=["eu868"]` dans `chirpstack.toml` et vérification de la cohérence du `topic_prefix = "eu868"` dans les trois fichiers de configuration.

**Règle d'or — Diagnostic du silence radio :**
1. Vérifier que le `topic_prefix` est **identique** dans les 3 fichiers de configuration
2. Écouter manuellement le bus MQTT : `mosquitto_sub -t "eu868/gateway/#"`
3. Vérifier l'IP destination dans la passerelle RAK : `cat /var/etc/global_conf.json | grep server_address`
4. Contrôler les logs du Gateway Bridge : `docker logs lora-gateway-bridge`

## Incident D — Crash DNS et Résolution Redis

| Champ | Détail |
|:---|:---|
| **Date** | 5 février 2026 (après redémarrage de l'automate) |
| **Symptôme** | ChirpStack ne peut plus communiquer avec Redis |
| **Log d'erreur** | `failed to lookup address information: Name does not resolve` |
| **Cause racine** | Le conteneur `lora-redis` a crashé (Exit Code 255) et n'a pas redémarré |
| **Impact** | Stack LoRaWAN inopérante (Redis requis pour les sessions) |

**Analyse technique :** Lorsqu'un conteneur Docker est arrêté, Docker retire son nom du serveur DNS interne. ChirpStack, essayant de résoudre le nom d'hôte `lora-redis`, échoue sur une erreur DNS. Le crash de Redis est lié au paramètre `vm.overcommit_memory` du noyau Linux, qui provoque des échecs de fork sur les systèmes à mémoire contrainte.

**Résolution immédiate :**
```bash
docker start lora-redis
docker restart lora-chirpstack
```

**Résolution préventive :**
1. Application de `sysctl -w vm.overcommit_memory=1` dans le script d'installation
2. Passage de la politique de redémarrage de `unless-stopped` à `always`
3. Ajout de healthchecks sur Redis (`redis-cli ping`) et PostgreSQL (`pg_isready`)

---

# Industrialisation et Sécurisation

Pour passer du prototype expérimental à un déploiement adapté à un bâtiment en exploitation, quatre mesures de durcissement ont été appliquées.

## Persistance Durcie : Redis AOF

**Problème :** Un automate de bâtiment peut subir des coupures de courant inopinées. Redis en mode snapshot par défaut (RDB) sauvegarde les données périodiquement mais peut perdre **jusqu'à 5 minutes** de sessions actives. Les capteurs LoRaWAN doivent alors re-joindre le réseau (procédure **OTAA Join**), ce qui génère un temps mort de 30 secondes à plusieurs minutes par capteur.

> **Qu'est-ce que l'OTAA Join ?** OTAA (Over-The-Air Activation) est la procédure par laquelle un capteur LoRaWAN s'identifie auprès du serveur réseau. Le capteur envoie une requête d'association (JoinRequest) contenant son identité chiffrée. Le serveur vérifie les clés racines, puis renvoie une réponse (JoinAccept) avec des **clés de session temporaires** (NwkSKey, AppSKey). Ce n'est qu'après cet échange que le capteur peut émettre des données. Si les sessions Redis sont perdues, ChirpStack ne reconnaît plus les capteurs, qui doivent tous refaire cette procédure.

**Solution :** Activation du mode AOF (Append Only File) avec synchronisation à la seconde :

```bash
redis-server --appendonly yes --appendfsync everysec
```

**Résultat :** Perte maximale d'**une seconde** de données en cas de coupure totale. Les capteurs conservent leur session active et reprennent immédiatement l'émission de données.

| Mode Redis | Perte de données (coupure brutale) | Impact LoRaWAN |
|:---|:---|:---|
| **RDB** (défaut) | Jusqu'à 5 minutes | Re-join nécessaire → temps mort |
| **AOF everysec** (appliqué) | ≤ 1 seconde | Sessions préservées → reprise instantanée |
| **AOF always** | 0 seconde |  Écriture excessive → usure carte SD |

## Healthchecks et Auto-Guérison

Docker est configuré pour surveiller activement la santé des services critiques :

| Service | Commande de vérification | Intervalle | Timeout | Comportement si échec |
|:---|:---|:---:|:---:|:---|
| **PostgreSQL** | `pg_isready -U chirpstack` | 30s | 10s | Marqué `unhealthy` après 5 échecs → redémarrage automatique |
| **Redis** | `redis-cli ping \| grep PONG` | 30s | 10s | Marqué `unhealthy` après 5 échecs → redémarrage automatique |

Couplés à la politique `restart: always`, ces healthchecks créent un système d'**auto-guérison** : si un service tombe, Docker le redétecte en moins de 30 secondes et le relance automatiquement, sans intervention humaine.

```mermaid
graph LR
    A["Service actif"] -->|"Healthcheck toutes les 30s"| B{"Réponse ?"}
    B -->|"OK (healthy)"| A
    B -->|"5 échecs consécutifs"| C["Marqué unhealthy"]
    C --> D["Docker redémarre<br/>le conteneur"]
    D --> A
```

## Tuning Noyau Linux

Un réglage critique du noyau Linux est nécessaire pour la stabilité de Redis sur les systèmes ARM à mémoire contrainte :

```bash
sysctl -w vm.overcommit_memory=1
echo "vm.overcommit_memory=1" >> /etc/sysctl.conf
```

**Explication :** Redis utilise l'appel système `fork()` pour ses sauvegardes de fond. Sur un système avec peu de mémoire libre, le noyau Linux peut refuser le `fork()` si `overcommit_memory=0` (comportement par défaut restrictif). Avec la valeur `1`, le noyau autorise l'allocation mémoire optimiste, évitant les crashs de Redis lors des sauvegardes AOF.

## Isolation Réseau par Défaut

La politique de sécurité réseau suit le principe du **moindre privilège** :

| Port | Service | Exposé à l'hôte | Justification |
|:---:|:---|:---:|:---|
| 1700/UDP | Gateway Bridge |  Oui | Nécessaire pour la réception des paquets de la passerelle RAK |
| 1883/TCP | Mosquitto MQTT |  Oui | Accès diagnostic et intégrations tierces |
| 8081/TCP | ChirpStack |  Oui | Interface web d'administration |
| 5432/TCP | PostgreSQL |  Non | Accessible uniquement via le réseau Docker interne |
| 6379/TCP | Redis |  Non | Accessible uniquement via le réseau Docker interne |

Les bases de données ne sont **jamais** exposées directement à l'extérieur. Toute communication avec PostgreSQL ou Redis passe obligatoirement par ChirpStack, qui agit comme couche d'abstraction sécurisée.
# Validation et Benchmarking

Ce chapitre présente les deux campagnes de stress test réalisées sur l'automate WAGO CC100. Elles constituent la **validation quantitative** du projet, établissant les limites physiques mesurables de l'architecture Docker déployée.

## Méthodologie : La Simulation Radio Dynamique (Python)

### Pourquoi cette méthode ?

Contrairement à une simple "Replay Attack" (qui renvoie toujours la même trame pré-calculée), nous avons développé un **générateur de trafic LoRaWAN dynamique** en Python (`master_benchmark.py`).

L'espace disque pour stocker 10, 100 ou 1000 capteurs dans PostgreSQL ne coûte aucune ressource CPU. Le véritable goulot d'étranglement matériel de l'automate se situe au millième de seconde exact où la trame radio frappe la passerelle réseau. Pour mesurer la capacité de calcul réelle, le script Python génère en cours de route de fausses données (Température, Humidité, CO2), les chiffre mathématiquement avec une clé `AES-128`, calcule un *Message Integrity Code* (MIC) conforme, puis bombarde l'automate à des cadences progressives.

Voici l'enchaînement exact des opérations (et la charge CPU en cascade) que l'automate WAGO doit subir lorsqu'il réceptionne chaque trame :

```mermaid
---
title: Traitement interne d'une trame LoRaWAN (WAGO CC100)
---
flowchart LR
    A[Flux Radio Entrant<br>MQTT: eu868/gateway/...] -->|1. Réception| B(ChirpStack Core<br>Orchestrateur)
    
    B -->|2. Requête Identité| C[(PostgreSQL / Redis<br>Accès Disque/RAM)]
    C -.->|3. Fourniture Clés| B
    
    B -->|4. Opération Cryptographique| D{Déchiffrement AES-128<br>Charge CPU très forte}
    
    D -->|5. Transmission Finale| E[Données JSON Brutes<br>MQTT: application/.../up]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style B fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style C fill:#eceff1,stroke:#455a64,stroke-width:2px
    style D fill:#ffebee,stroke:#c62828,stroke-width:3px
    style E fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

Comme le montre ce diagramme, chaque message entrant force le processeur embarque monocoeur a effectuer des allers-retours continus entre la base de donnees et les fonctions de cryptographie lourde. Le stress-test a pour objectif de pousser le WAGO a ses limites et d'identifier sa capacite maximale de calcul cryptographique simultane.

### Un script automatisé (Ramp-Up)
Le script orchestre l'escalade automatiquement, découpant l'attaque de 0.5 msg/s (Nominal) à 50 msg/s (DDoS). Au terme de chaque phase, l'algorithme "pose les crayons" et vérifie dans le flux applicatif de sortie (`application/...`) combien de trames ont franchi avec succès le barrage par rapport au nombre d'ondes radio générées.

```mermaid
---
title: Architecture du banc de test de charge radio (Ramp-Up)
---
graph LR
    subgraph SIM ["1. Simulateur Python (Faux Capteurs)"]
        direction TB
        A[Génération données<br/>Temp, Hum, CO2] -->|struct.pack| B(Payload<br/>Binaire)
        B -->|AppSKey + NwkSKey| C{Chiffrement<br/>AES-128 & MIC}
        C --> D[Enrobage Protobuf<br/>Faux RSSI / SNR / SF]
        D --> E((Client<br/>MQTT Tx))
    end
    
    %% Liaison entre les blocs (injection dans le réseau)
    E == "Publish: eu868/gateway/..." ===> F

    subgraph SRV ["2. Serveur WAGO / ChirpStack"]
        direction TB
        F[(Broker MQTT<br/>Mosquitto)] -->|Transmission| G[ChirpStack NS<br/>Déchiffrement & Décodage]
        G -->|JSON Valide| I[Publication<br/>Événement Up]
        I -.->|Boucle interne| F
    end

    %% Sortie latérale pour le monitoring (Le listener s'abonne au Broker)
    F -. "Topic: application/...<br/>(Vérification)" .-> J([Listener Simulateur<br/>Calcul Taux de Réussite])
    
    %% Styles enrichis pour tous les blocs
    style A fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style B fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style C fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style D fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style E fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    style F fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style G fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style I fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    
    style J fill:#eceff1,stroke:#37474f,stroke-width:2px
```

---

### Comprendre le « Load Average » sur un automate industriel

Pour interpréter correctement les résultats qui suivent, il est essentiel de comprendre ce que mesure le **Load Average** (charge moyenne du processeur) et pourquoi sa signification change radicalement selon le matériel utilisé.

#### Qu'est-ce que le Load Average ?

Le Load Average est un indicateur fourni par le système d'exploitation Linux. Il représente le **nombre moyen de processus (programmes) qui sont en train de travailler ou qui attendent leur tour** pour accéder au processeur, mesuré sur un intervalle glissant de 1 minute, 5 minutes et 15 minutes.

**Analogie simple :** Imaginons un guichet unique dans une administration. Le Load Average correspond au nombre de personnes **en train d'être servies + celles qui font la queue**. Si la valeur est de 1.00, exactement une personne est servie et personne n'attend : le guichet est utilisé à 100% mais sans file d'attente. Si la valeur monte à 5.00, cela signifie qu'une personne est servie et que 4 autres attendent dans la file : le guichet est débordé.

#### Le cas particulier du WAGO CC100 : un processeur monocœur

Le WAGO CC100 embarque un processeur **ARM Cortex-A8 cadencé à 600 MHz avec un seul cœur de calcul**. C'est un processeur de classe industrielle embarquée, conçu pour la fiabilité et la faible consommation énergétique, et non pour la puissance de calcul brute.

Cette architecture monocœur a une conséquence directe sur l'interprétation du Load Average :

| Load Average | Signification sur le WAGO CC100 (1 cœur) | Signification sur un serveur classique (8 cœurs) |
|:---:|:---|:---|
| **0.50** | Le CPU travaille à 50% — tout va bien | Le serveur est presque au repos (6% par cœur) |
| **1.00** | Le CPU est utilisé à **100%** — aucune marge | Le serveur est à 12.5% — très confortable |
| **2.00** | **1 processus travaille + 1 attend** — début de saturation | Le serveur est à 25% — aucun souci |
| **4.00** | **3 processus en file** — ralentissements perceptibles | Le serveur est à 50% — charge modérée |
| **9.00** | **8 processus en file** — le système est submergé | Le serveur est un peu chargé (112%) |
| **13.00** | **12 processus en file** — surcharge critique | Le serveur gère encore (162%) |

> **Règle fondamentale :** Sur un processeur à **N cœurs**, le seuil critique est un Load Average de **N**. Au-delà, les processus commencent à faire la queue.
>
> Le WAGO CC100 ayant **1 seul cœur**, son seuil critique est donc **1.00**. Toute valeur supérieure à 1 signifie que des programmes attendent leur tour pour être exécutés. En pratique, on considère qu'un Load inférieur à **2.00** reste acceptable (le kernel Linux gère la file efficacement), mais qu'au-delà, les performances se dégradent visiblement.

#### Pourquoi le Load monte si haut pendant nos tests ?

Lorsque l'on injecte des milliers de trames, voici les programmes qui se battent simultanément pour accéder à cet unique processeur :

| Processus | Rôle |
|:---|:---|
| `mosquitto` | Réceptionner et distribuer les messages MQTT |
| `chirpstack` | Décoder le format Protobuf et tenter le déchiffrement AES-128 |
| `postgres` | Gérer les requêtes de base de données |
| `redis-server` | Gérer le cache et les files de messages internes |
| `containerd` / `runc` | Orchestrer les conteneurs Docker |
| `codesys3` | Le runtime PLC de l'automate WAGO (toujours actif) |
| `ksoftirqd` | Traiter les interruptions réseau (paquets TCP/IP entrants) |

Tous ces programmes se partagent **un seul cœur à 600 MHz**. Quand le Load atteint 13, cela signifie concrètement que le processeur exécute un programme à la fois pendant quelques millisecondes, puis bascule sur le suivant (*context switching*), créant un embouteillage permanent.

> **En résumé :** Un Load de 13 sur le WAGO CC100 ne signifie pas du tout la même chose qu'un Load de 13 sur un serveur de datacenter. Sur notre automate monocœur, c'est l'équivalent d'un embouteillage monstre sur une route à voie unique. Sur un serveur à 16 cœurs, ce serait à peine un ralentissement sur une autoroute.

---

## Résultats du Benchmark Progressif (Ramp-Up)

Le script `master_benchmark.py` a été exécuté sur l'automate WAGO en paramétrant un saut d'injection en 12 étapes (de `0.5` à `50.0 msg/s`) réparties sur un banc de test de 1000 compteurs provisionnés.

### Identification du point de rupture de charge

L'expérience prouve sans équivoque la relation entre la charge CPU (Load Average monocœur) et la survie des paquets réseaux au-delà de sa limite de traitement.

| Qualification | Vitesse Testee | Comportement Automate | Taux de Perte |
|---------------|----------------|-----------------------|---------------|
| **Regime Nominal** | 0.5 msg/s a 2.0 msg/s | **Parfait**. Le processeur traite le decryptage dans les temps. | **0.0%** |
| **Zone d'Alerte** | 2.5 msg/s a 4.0 msg/s | **Degrade**. File d'attente systeme, premieres destructions de trames par securite (Time-out). | **15% a 50%** |
| **Zone Rouge** | 4.5 msg/s a 10.0 msg/s | **Saturation critique**. Delai de traitement (Load Average > 8). Rejet massif. | **70% a 95%** |
| **Attaque DDoS** | 50.0 msg/s | **Asphyxie Total**. Deni de service preemptif. | **100.0%** |

### Interprétation Physique (Déni de Service)

Il est vital de comprendre que ce taux de chute n'est **pas une erreur ou un bogue de plateforme**. Au contraire, il démontre l'excellente isolation du système conteneurisé. Confronté à un afflux radio (DDoS) 20 fois supérieur à sa fréquence d'horloge tolérée, le processus `ChirpStack` (aidé par les limites d'accès I/O) détruit les événements à l'entrée avec des erreurs d'asphyxie (timeout). 

**Cette stratégie permet de préserver l'intégrité du système principal `CODESYS` de l'automate industriel** : au lieu de crasher entièrement l'appareil, ChirpStack sert de fusible applicatif. Le WAGO écarte les trames qu'il n'aura mathématiquement jamais le temps de déchiffrer en `AES` en temps utile.

---

## Cartographie des Limites Opérationnelles

### Synthèse des limites identifiées

| Ressource | Limite mesurée | Risque en production réelle |
|:---|:---|:---|
| **CPU** | Saturation à 9 msg/s (Load > 13) |  **Aucun** — débit réel < 1 msg/s |
| **RAM** | Marge de 4 Mo avant OOM sous stress extrême |  **Faible** si ajout de services |
| **Carte SD** | Non sollicitée en écriture (anti-replay) |  **Aucun** |
| **Réseau MQTT** | 0 message perdu sur 6 000 trames (deux tests) |  **Aucun** |
| **Stabilité Docker** | 0 crash conteneur sur 2 campagnes de stress |  **Excellente** |

### Capacité maximale validée en production

| Scénario GTB | Capteurs | Intervalle | Débit | Charge CPU | RAM | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Bureau (petit) | 20 | 10 min | 0.03 msg/s | < 2 |  |  **Confort** |
| Bâtiment (moyen) | 50 | 5 min | 0.17 msg/s | < 2.5 |  |  **OK** |
| **Bâtiment (grand)** | **100** | **5 min** | **0.33 msg/s** | **< 3** |  |  **Limite** |
| Campus | 200 | 5 min | 0.67 msg/s | ~4 |  |  **Non recommandé** |
| Smart City | 500+ | 1 min | 8+ msg/s |  |  |  **Impossible** |

**Marge de sécurité en conditions réelles :**

En régime nominal (100 capteurs, émission toutes les 5 minutes, soit 0.33 msg/s), l'automate fonctionne à **3.7% de sa capacité maximale de traitement** (0.33 / 9 msg/s). Cette marge de **×27** garantit la stabilité même en cas de pics d'émission simultanée de plusieurs capteurs.

```mermaid
pie title Utilisation CPU en production (100 capteurs)
    "Capacité utilisée (0.33 msg/s)" : 3.7
    "Marge de sécurité disponible" : 96.3
```

### Points forts validés

-  L'architecture Docker tient la charge sans crasher — même à Load 13+, aucun conteneur n'est tombé
-  ChirpStack déchiffre et analyse 6 000 trames (sur deux campagnes) sans erreur fatale
-  Le mécanisme de sécurité anti-replay LoRaWAN (Frame Counter) fonctionne parfaitement
-  Mosquitto bufferise correctement les files d'attente sous pression extrême
-  L'empreinte mémoire des conteneurs reste stable (pas de fuite mémoire détectée)

### Points de vigilance

-  **La RAM est le facteur limitant principal.** Avec 4 Mo de marge sous stress extrême, l'ajout de services supplémentaires (Grafana, Node-RED, dashboards) est **fortement déconseillé** sur cet automate.
-  **Le swap n'est pas activé.** En l'absence de swap, une saturation RAM déclenche l'OOM Killer sans filet de sécurité. L'ajout d'un swap de 256 Mo sur la carte SD est recommandé comme mesure de protection.
-  **Le Load Average ne redescend pas immédiatement.** Après la fin de l'injection (T+230s), le load était encore à 11.84. Le kernel Linux n'avait pas fini d'éponger la file d'attente CPU 3 secondes après la fin du test. Sur un processeur plus puissant, cette récupération serait instantanée.
