"""
================================================================
  2. STRESS-TEST RADIO - INJECTION AES-128
================================================================
  Ce script tire des trames simulées chiffrées sur le réseau.
  Il ne communique pas avec l'API, il se contente de générer 
  des ondes radio virtuelles via MQTT.
"""

import sys
import struct
import time
import random
import os
import hashlib
import json
import datetime
import paho.mqtt.client as mqtt

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import CMAC
except ImportError:
    print("❌ Module 'pycryptodome' manquant ! (pip install pycryptodome)")
    sys.exit(1)

from chirpstack_api import gw

# ================================================================
# CONFIGURATION
# ================================================================
BROKER_IP       = "192.168.3.100"
BROKER_PORT     = 1883
MQTT_USER       = "chirpstack"
MQTT_PASS = os.getenv("MQTT_PASS")

GATEWAY_ID      = "YOUR_GATEWAY_ID"
APPLICATION_ID  = "YOUR_APPLICATION_ID"

NB_CAPTEURS     = 30        
INTERVAL_SEC    = 2       
FPORT           = 1         

# ================================================================
# CRYPTOGRAPHIE LORAWAN (AES-128)
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

def encode_sensor_payload(t, h, c):
    """Encode nos fausses métriques sur 6 octets, lues par le Codec JS"""
    return struct.pack('>hHH', int(t * 10), int(h * 10), int(c))

# ================================================================
# ENCODAGE PROTOBUF PASSERELLE
# ================================================================
def build_uplink_frame_protobuf(phy_payload, rssi, snr, frequency, sf):
    """Construit un UplinkFrame parfait en utilisant la librairie officielle gw"""
    frame = gw.UplinkFrame()
    frame.phy_payload = phy_payload
    # tx_info
    frame.tx_info.frequency = frequency
    frame.tx_info.modulation.lora.bandwidth = 125000
    frame.tx_info.modulation.lora.spreading_factor = sf
    frame.tx_info.modulation.lora.code_rate = gw.CodeRate.CR_4_5
    # rx_info (Objet unique dans ChirpStack v4)
    frame.rx_info.gateway_id = GATEWAY_ID  # Chaine de caractères en V4
    frame.rx_info.uplink_id = random.randint(1, 65535)
    frame.rx_info.rssi = rssi
    frame.rx_info.snr = snr
    frame.rx_info.context = os.urandom(4)
    frame.rx_info.crc_status = gw.CRCStatus.CRC_OK
    return frame.SerializeToString()

# ================================================================
# VÉRIFICATION EN DIRECT
# ================================================================
trames_recues = 0
def on_verification_msg(client, userdata, msg):
    global trames_recues
    trames_recues += 1

# ================================================================
# GÉNÉRATION DE L'INJECTION
# ================================================================
def main():
    global trames_recues
    print("=" * 64)
    print("  📡  TIR DE BARRAGE LORAWAN - SANS API (RÉALISTE)")
    print("=" * 64)

    # Canaux EU868 de base
    CHANNELS = [868100000, 868300000, 868500000]

    # 1. On regénère les clés et on assigne des propriétés physiques réalistes
    devices = []
    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        seed = hashlib.sha256(dev_eui.encode()).digest()
        
        # Attribution de la distance du capteur (SF et puissance associée)
        sf = random.choices([7, 8, 9, 10, 11, 12], weights=[40, 25, 15, 10, 5, 5])[0]
        base_rssi = -60 - ((sf - 7) * 10) - random.randint(0, 15)  # Plus le SF est grand (loin), plus le RSSI s'écroule
        base_snr = 10.0 - ((sf - 7) * 4.0) - random.uniform(0, 3.0)

        devices.append({
            "dev_addr": dev_addr,
            "nwk_s_key": seed[:16],
            "app_s_key": seed[16:32],
            "name": f"Sim-Capteur-{i:04d}",
            "fcnt": 0,
            
            # Valeurs environnementales (Modèles)
            "temp_base": round(random.uniform(18.0, 24.0), 1),
            "hum_base": round(random.uniform(40.0, 60.0), 1),
            "co2_base": random.randint(400, 800),
            
            # Paramètres Radio (Modèles)
            "sf": sf,
            "rssi_base": max(-120, base_rssi),
            "snr_base": max(-20.0, base_snr)
        })

    # 2. Branchement sur le MQTT du WAGO
    print("\nConnexion au réseau local...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lorawan_sim_guns")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_verification_msg
    try: client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"❌ Impossible de se connecter à la passerelle : {e}"); return
    
    client.loop_start()
    client.subscribe(f"application/{APPLICATION_ID}/device/+/event/up")
    
    gw_topic = f"eu868/gateway/{GATEWAY_ID}/event/up"
    compteur = 0
    debut = time.time()
    
    print(f"\n🔥 Feu à volonté ! ({NB_CAPTEURS} capteurs avec météo et radio dynamiques)")
    print("Ctrl+C pour arrêter le test.\n")
    
    try:
        while True:
            dev = random.choice(devices)
            
            # DÉRANGEMENT NATUREL (Marche Aléatoire / Random Drift)
            dev["temp_base"] += random.uniform(-0.2, 0.2)
            dev["hum_base"] += random.uniform(-0.5, 0.5)
            dev["co2_base"] += random.randint(-15, 15)
            dev["rssi_base"] += random.uniform(-1.5, 1.5)
            dev["snr_base"] += random.uniform(-0.5, 0.5)
            
            # Limitation réaliste des dérives
            temp = round(max(-10, min(50, dev["temp_base"])), 1)
            hum = round(max(10, min(90, dev["hum_base"])), 1)
            co2 = int(max(400, min(3000, dev["co2_base"])))
            rssi = int(max(-125, min(-40, dev["rssi_base"])))
            snr = round(max(-20.0, min(15.0, dev["snr_base"])), 1)
            freq = random.choice(CHANNELS)
            sf = dev["sf"]

            # Assemblage et Chiffrement
            payload = encode_sensor_payload(temp, hum, co2)
            phy = build_phy_payload(dev["dev_addr"], dev["nwk_s_key"], dev["app_s_key"], dev["fcnt"], FPORT, payload)
            dev["fcnt"] += 1

            # Injection dans l'antenne virtuelle avec Radio Réaliste
            frame = build_uplink_frame_protobuf(phy, rssi, snr, freq, sf)
            client.publish(gw_topic, frame, qos=0)
            compteur += 1

            # Affichage périodique
            if compteur % 5 == 0:
                elapsed = time.time() - debut
                rate = compteur / elapsed if elapsed > 0 else 0
                print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] "
                      f"Envoyés: {compteur} | Reçus (JSON): {trames_recues} | {rate:.1f} msg/s | "
                      f"{dev['name']} -> T={temp}°C | SF{sf} | RSSI {rssi}")
            
            time.sleep(INTERVAL_SEC)
            
    except KeyboardInterrupt:
        print("\n🛑 ARRÊT DE L'INJECTION.")
        print("📊 Bilan du Simulateur Radio :")
        print(f"   - Trames simulées et envoyées : {compteur}")
        print(f"   - Trames reçues décodées (JSON) : {trames_recues}")
        if compteur > 0:
            taux = (trames_recues / compteur) * 100
            print(f"   - Taux de réussite de décodage : {taux:.1f}%")
            if taux < 100:
                print("   ⚠️ Attention : Certaines trames ont été perdues ou rejetées par le WAGO !")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
