from dotenv import load_dotenv
load_dotenv()
"""
================================================================
  DIAGNOSTIC — Envoie UNE seule trame et écoute TOUT
================================================================
  Vérifie si ChirpStack traite la trame jusqu'au niveau application.
"""

import sys
import struct
import time
import random
import os
import hashlib
import paho.mqtt.client as mqtt

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import CMAC
except ImportError:
    print("[ERREUR] pip install pycryptodome"); sys.exit(1)

from chirpstack_api import gw

# ================================================================
# CONFIG
# ================================================================
BROKER_IP       = "192.168.3.100"
BROKER_PORT     = 1883
MQTT_USER       = "chirpstack"
MQTT_PASS = os.getenv("MQTT_PASS")
GATEWAY_ID      = os.getenv("GATEWAY_ID")

# Premier capteur simulé
DEV_EUI         = "aa00000000000001"
DEV_ADDR        = 0x01FF0001
FPORT           = 1

# Clés dérivées identiques à 01_creation_capteurs.py
seed = hashlib.sha256(DEV_EUI.encode()).digest()
NWK_S_KEY = seed[:16]
APP_S_KEY = seed[16:32]

# ================================================================
# COULEURS
# ================================================================
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ================================================================
# CRYPTO LORAWAN
# ================================================================
def lorawan_encrypt(key, dev_addr, fcnt, direction, payload):
    k = len(payload)
    if k == 0: return b''
    n_blocks = (k + 15) // 16
    s = b''
    for i in range(1, n_blocks + 1):
        a = bytes([0x01, 0x00, 0x00, 0x00, 0x00, direction])
        a += struct.pack('<I', dev_addr)
        a += struct.pack('<I', fcnt)
        a += bytes([0x00, i])
        s += AES.new(key, AES.MODE_ECB).encrypt(a)
    return bytes(a ^ b for a, b in zip(payload, s[:k]))

def lorawan_mic(key, dev_addr, fcnt, direction, msg):
    b0 = bytes([0x49, 0x00, 0x00, 0x00, 0x00, direction])
    b0 += struct.pack('<I', dev_addr)
    b0 += struct.pack('<I', fcnt)
    b0 += bytes([0x00, len(msg)])
    h = CMAC.new(key, ciphermod=AES)
    h.update(b0 + msg)
    return h.digest()[:4]

def build_phy_payload(dev_addr, nwk_s_key, app_s_key, fcnt, fport, frm_payload):
    mhdr = bytes([0x40])
    fhdr = struct.pack('<IBH', dev_addr, 0x00, fcnt & 0xFFFF)
    enc_payload = lorawan_encrypt(app_s_key, dev_addr, fcnt, 0, frm_payload)
    msg = mhdr + fhdr + bytes([fport]) + enc_payload
    mic = lorawan_mic(nwk_s_key, dev_addr, fcnt, 0, msg)
    return msg + mic

# ================================================================
# DIAGNOSTIC
# ================================================================
messages_recus = []

def on_connect(client, userdata, flags, rc, properties):
    print(f"{GREEN}[OK] Connecté au broker MQTT{RESET}")
    client.subscribe("#", qos=0)
    print(f"{CYAN}[RADIO] Souscrit à # (TOUS les topics){RESET}\n")

def on_message(client, userdata, msg):
    messages_recus.append({
        "topic": msg.topic,
        "size": len(msg.payload),
        "time": time.time()
    })
    # Coloriser selon le type
    if "application/" in msg.topic:
        color = GREEN + BOLD
        prefix = "🎯 APPLICATION"
    elif "gateway" in msg.topic:
        color = GREY
        prefix = "[RADIO] GATEWAY    "
    else:
        color = YELLOW
        prefix = "❓ AUTRE      "
    print(f"  {color}{prefix} │ {msg.topic} │ {len(msg.payload)} octets{RESET}")

def main():
    print("=" * 64)
    print(f"  {BOLD}🔬 DIAGNOSTIC — UNE TRAME, TOUS LES TOPICS{RESET}")
    print("=" * 64)

    # Afficher les clés pour vérification
    print(f"\n{CYAN}--- Paramètres du device ---{RESET}")
    print(f"  DevEUI    : {DEV_EUI}")
    print(f"  DevAddr   : {DEV_ADDR:08x}")
    print(f"  NwkSKey   : {NWK_S_KEY.hex()}")
    print(f"  AppSKey   : {APP_S_KEY.hex()}")
    print(f"  Gateway   : {GATEWAY_ID}")

    # Connexion
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="diag_single")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"{RED}[ERREUR] Connexion impossible: {e}{RESET}")
        return

    client.loop_start()
    time.sleep(2)  # Laisser le temps de souscrire

    # Construire la trame
    payload_clair = struct.pack('>hHH', int(22.5 * 10), int(55.0 * 10), 650)
    fcnt = 0  # Frame counter à 0 (frais)
    phy = build_phy_payload(DEV_ADDR, NWK_S_KEY, APP_S_KEY, fcnt, FPORT, payload_clair)

    print(f"\n{CYAN}--- Trame construite ---{RESET}")
    print(f"  Payload clair : temp=22.5°C, hum=55.0%, co2=650ppm")
    print(f"  PHY (hex)     : {phy.hex()}")
    print(f"  Taille        : {len(phy)} octets")
    print(f"  MIC (4 derniers octets) : {phy[-4:].hex()}")

    # Construire le protobuf
    frame = gw.UplinkFrame()
    frame.phy_payload = phy
    frame.tx_info.frequency = 868100000
    frame.tx_info.modulation.lora.bandwidth = 125000
    frame.tx_info.modulation.lora.spreading_factor = 7
    frame.tx_info.modulation.lora.code_rate = gw.CodeRate.CR_4_5
    frame.rx_info.gateway_id = GATEWAY_ID
    frame.rx_info.uplink_id = random.randint(1, 65535)
    frame.rx_info.rssi = -60
    frame.rx_info.snr = 8.0
    frame.rx_info.context = os.urandom(4)
    frame.rx_info.crc_status = gw.CRCStatus.CRC_OK

    proto_bytes = frame.SerializeToString()
    gw_topic = f"eu868/gateway/{GATEWAY_ID}/event/up"

    print(f"\n{CYAN}--- Envoi ---{RESET}")
    print(f"  Topic  : {gw_topic}")
    print(f"  Proto  : {len(proto_bytes)} octets")

    # Envoyer
    messages_recus.clear()
    result = client.publish(gw_topic, proto_bytes, qos=0)
    print(f"  Status : rc={result.rc} (0=OK)")

    # Attendre la réponse de ChirpStack
    print(f"\n{YELLOW}⏳ Attente de 8 secondes pour la réponse de ChirpStack...{RESET}\n")
    time.sleep(8)

    client.loop_stop()
    client.disconnect()

    # Bilan
    print(f"\n{'=' * 64}")
    print(f"  {BOLD}[STATS] BILAN{RESET}")
    print(f"{'=' * 64}")

    gw_msgs = [m for m in messages_recus if "gateway" in m["topic"]]
    app_msgs = [m for m in messages_recus if "application/" in m["topic"]]
    other_msgs = [m for m in messages_recus if "gateway" not in m["topic"] and "application/" not in m["topic"]]

    print(f"\n  [RADIO] Messages GATEWAY  : {len(gw_msgs)}")
    print(f"  🎯 Messages APPLICATION : {len(app_msgs)}")
    print(f"  ❓ Messages AUTRES   : {len(other_msgs)}")

    if app_msgs:
        print(f"\n  {GREEN}{BOLD}[OK] SUCCÈS ! ChirpStack traite la trame correctement.{RESET}")
        print(f"  Topics application reçus :")
        for m in app_msgs:
            print(f"    → {m['topic']}")
    else:
        print(f"\n  {RED}{BOLD}[ERREUR] ÉCHEC ! Aucune trame remontée au niveau application.{RESET}")
        print(f"\n  {YELLOW}Causes probables :{RESET}")
        print(f"  1. MIC invalide (clés désynchronisées)")
        print(f"  2. DevAddr inconnu dans ChirpStack")
        print(f"  3. Problème de configuration ChirpStack")
        print(f"\n  {YELLOW}→ Vérifiez les logs : ssh root@192.168.3.100 \"docker logs --tail 20 chirpstack\"{RESET}")

if __name__ == "__main__":
    main()
