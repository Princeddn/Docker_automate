# Configuration de la Passerelle RAK7268 (WisGateOS)

Ce document détaille la configuration spécifique nécessaire pour connecter une passerelle RAK7268 (ou tout modèle sous WisGateOS 2.x) à votre serveur ChirpStack hébergé sur le WAGO.

## Pourquoi cette configuration manuelle ?

Les passerelles RAK modernes embarquent leur propre serveur LoRa (WisGateOS). Par défaut, elles essaient de traiter les données en interne. Pour utiliser votre serveur WAGO externe, nous devons :
1.  Désactiver l'intelligence embarquée (`lorasrv`).
2.  Forcer le mode "Packet Forwarder" pur en UDP.
3.  **Contourner un bug connu** où l'interface web force l'adresse du serveur à `127.0.0.1`.

---

## Méthode 1 : Via l'Interface Web (WisGateOS)

C'est la méthode la plus simple, à tenter en premier.

1.  **Accès** : Ouvrez votre navigateur sur l'IP de la Gateway (ex: `https://192.168.x.x`).
2.  **Login** : Par défaut `root` / `root` (vous serez invité à changer le mot de passe).
3.  **Désactiver le Serveur Interne** :
    *   Allez dans **LoRa®** > **Configuration** > **General Setup**.
    *   Assurez-vous que le mode est sur **Packet Forwarder** (et non "Built-in LoRa Server" ou "Basics Station").
4.  **Configurer la Destination** :
    *   Allez dans **LoRa®** > **Configuration** > **Packet Forwarder**.
    *   **Protocol** : Sélectionnez **Semtech UDP** (anciennement "Legacy Semtech").
    *   **Server Address** : Entrez l'IP du WAGO (`192.168.3.100`).
    *   **Port Up/Down** : `1700`.
    *   Cliquez sur **Save & Apply**.

> **⚠️ Important** : Si après redémarrage, l'adresse revient sur `127.0.0.1`, c'est que le firmware force la configuration locale. Dans ce cas, **vous DEVEZ utiliser la méthode SSH ci-dessous**.

---

## Méthode 2 : Via SSH (Force Brute - Recommandé)

C'est la méthode la plus fiable si l'interface web ne sauvegarde pas vos changements ou si le paramètre "Protocol" est bloqué sur `protobuf`.
Connectez-vous avec un terminal (PuTTY ou PowerShell) :
```bash
ssh root@<IP_GATEWAAY>
# Mot de passe par défaut : root
```

### 2. Désactiver le Serveur Interne (Indispensable)
Le service `lorasrv` tourne sur le port 1700 par défaut et intercepte vos messages. Il faut le "tuer".

```bash
/etc/init.d/lorasrv stop
/etc/init.d/lorasrv disable
```
*Note : Si vous voyez un service `loragwbridge`, désactivez-le aussi.*

### 3. Modifier les Paramètres (UCI)

Nous utilisons l'outil `uci` (Unified Configuration Interface) pour modifier la configuration persistante.

#### A. Définir l'adresse du Serveur WAGO
Remplacez `192.168.3.100` par l'IP réelle de votre automate WAGO.

```bash
uci set lora_pkt_fwd.gateway_conf.server_address='192.168.3.100'
```

#### B. Définir les Ports
Le standard Semtech UDP utilise le port 1700.

```bash
uci set lora_pkt_fwd.gateway_conf.serv_port_up=1700
uci set lora_pkt_fwd.gateway_conf.serv_port_down=1700
```

#### C. LE PARAMÈTRE CRITIQUE : Protocole
C'est ici que se joue la différence entre "ça marche" et "ça ne marche pas".
Par défaut, WisGateOS peut être sur `protobuf` ou `protobuf-v4`. Dans ce mode, le système **ignore** votre adresse `192.168.3.100` et remet `127.0.0.1` à chaque redémarrage.

**Il faut forcer le mode UDP classique :**

```bash
uci set lora_pkt_fwd.gateway_conf.proto='udp'
```

### 4. Appliquer et Redémarrer
Sauvegardez les changements et relancez le service Packet Forwarder.

```bash
uci commit lora_pkt_fwd
/etc/init.d/sx130x_lora_pkt_fwd restart
```

---

## Vérification

Pour vérifier que vos paramètres sont bien pris en compte, affichez le fichier généré :

```bash
cat /var/etc/global_conf.json | grep server_address
```
> **Succès** : `"server_address": "192.168.3.100"`
>
> **Échec** : `"server_address": "127.0.0.1"` (Relisez l'étape 3-C).

Une fois validé, votre Gateway transmettra tous les paquets LoRa reçus directement à votre WAGO sur le port 1700.
