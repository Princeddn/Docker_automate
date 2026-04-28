"""
==========================================================
 MQTT MONITOR — Souscrire à TOUT sur Mosquitto WAGO
==========================================================
Souscrit au topic "#" (wildcard universel) et affiche
chaque message reçu avec son topic, horodatage et payload.

Usage : python mqtt_monitor.py
"""

import paho.mqtt.client as mqtt
import datetime
import json
import sys

# ============================================================
# CONFIGURATION
# ============================================================
BROKER_IP   = "192.168.3.100"
BROKER_PORT = 1883
USER        = "chirpstack"
PASSWORD    = "YOUR_PASSWORD"
TOPIC_SUB   = "#"   # Tout écouter

# Topics à mettre en valeur (couleur dans le terminal)
TOPICS_IMPORTANTS = [
    "application/",   # Données décodées des capteurs
    "event/up",       # Trames uplink
    "event/join",     # Jonction d'un nouveau capteur
    "event/ack",      # Accusé de réception downlink
    "event/txack",    # Confirmation d'envoi downlink
    "event/log",      # Logs d'erreurs ChirpStack
]

compteur = 0

# ============================================================
# CODES COULEUR ANSI
# ============================================================
RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
GREY    = "\033[90m"
MAGENTA = "\033[95m"

def coloriser_topic(topic):
    if "application/" in topic and "event/up" in topic:
        return f"{GREEN}{BOLD}{topic}{RESET}"
    if "event/join" in topic:
        return f"{MAGENTA}{BOLD}{topic}{RESET}"
    if "event/log" in topic or "error" in topic.lower():
        return f"{RED}{topic}{RESET}"
    if "eu868/" in topic or "gateway" in topic:
        return f"{GREY}{topic}{RESET}"
    if "application/" in topic:
        return f"{CYAN}{topic}{RESET}"
    return f"{YELLOW}{topic}{RESET}"

def decoder_payload(topic, payload_bytes):
    """Tente de décoder le payload : JSON > texte > hex."""
    try:
        text = payload_bytes.decode("utf-8")
        # Tentative d'indentation JSON
        data = json.loads(text)
        # Afficher seulement les champs utiles pour les events capteurs
        if "deviceInfo" in data:
            info = data["deviceInfo"]
            output = []
            output.append(f"  DevEUI    : {info.get('devEui', '?')}")
            output.append(f"  Device    : {info.get('deviceName', '?')}")
            output.append(f"  App       : {info.get('applicationName', '?')}")
            if "object" in data:
                output.append(f"  Data      : {json.dumps(data['object'], ensure_ascii=False)}")
            if "data" in data:
                output.append(f"  Data (b64): {data['data']}")
            if "fPort" in data:
                output.append(f"  fPort     : {data['fPort']}")
            if "dr" in data:
                output.append(f"  DR        : {data['dr']}")
            if "rxInfo" in data and data["rxInfo"]:
                rx = data["rxInfo"][0]
                output.append(f"  RSSI      : {rx.get('rssi', '?')} dBm")
                output.append(f"  SNR       : {rx.get('snr', '?')} dB")
            return "\n".join(output)
        # JSON générique abrégé
        preview = json.dumps(data, ensure_ascii=False)
        if len(preview) > 300:
            preview = preview[:300] + "…"
        return f"  JSON: {preview}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    # Tentative texte brut
    try:
        text = payload_bytes.decode("utf-8")
        if len(text) > 200:
            text = text[:200] + "…"
        return f"  TEXT: {text}"
    except UnicodeDecodeError:
        pass
    # Fallback hex
    hex_str = payload_bytes.hex()
    if len(hex_str) > 120:
        hex_str = hex_str[:120] + "…"
    return f"  HEX : {hex_str} ({len(payload_bytes)} octets)"

# ============================================================
# CALLBACKS MQTT
# ============================================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"{GREEN}✅ Connecté à Mosquitto @ {BROKER_IP}:{BROKER_PORT}{RESET}")
        print(f"{CYAN}📡 Souscrit à : {TOPIC_SUB} (TOUT){RESET}")
        print(f"{GREY}─── En attente de messages... (Ctrl+C pour quitter) ───{RESET}\n")
        client.subscribe(TOPIC_SUB, qos=0)
    else:
        print(f"{RED}❌ Erreur connexion : code {reason_code}{RESET}")
        sys.exit(1)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if reason_code != 0:
        print(f"{RED}⚠️  Déconnecté : code {reason_code} — Reconnexion automatique...{RESET}")

def on_message(client, userdata, msg):
    global compteur
    compteur += 1

    heure     = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    topic_col = coloriser_topic(msg.topic)
    payload   = decoder_payload(msg.topic, msg.payload)

    # Séparateur visuel selon le type de topic
    est_important = any(k in msg.topic for k in TOPICS_IMPORTANTS)
    sep = f"{BOLD}{'━'*60}{RESET}" if est_important else f"{GREY}{'─'*60}{RESET}"

    print(sep)
    print(f"  {GREY}#{compteur:<6}{RESET} [{heure}]  {topic_col}")
    print(payload)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("   📡 MQTT MONITOR — WAGO CC100")
    print("=" * 60)
    print(f"   Broker  : {BROKER_IP}:{BROKER_PORT}")
    print(f"   Topic   : {TOPIC_SUB}  (tout écouter)")
    print()
    print(f"   {GREEN}Vert  = Données décodées capteur (application/... /up){RESET}")
    print(f"   {MAGENTA}Violet = Jonction nouveau capteur (event/join){RESET}")
    print(f"   {CYAN}Cyan  = Autres topics application/{RESET}")
    print(f"   {GREY}Gris  = Trames brutes gateway (eu868/...){RESET}")
    print(f"   {RED}Rouge = Logs / erreurs{RESET}")
    print()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="mqtt_monitor_pc"
    )
    client.username_pw_set(USER, PASSWORD)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    try:
        client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}🛑 Arrêt manuel. {compteur} messages reçus au total.{RESET}")
        client.disconnect()
    except ConnectionRefusedError:
        print(f"{RED}❌ Impossible de se connecter à {BROKER_IP}:{BROKER_PORT}{RESET}")
        sys.exit(1)
