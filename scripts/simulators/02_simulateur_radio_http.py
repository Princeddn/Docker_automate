from dotenv import load_dotenv
load_dotenv()
"""
================================================================
  3. STRESS-TEST RADIO - INJECTION AES-128 via HTTP POST
================================================================
  Ce script tire des trames simulées chiffrées sur le réseau.
  Il ne communique pas via MQTT, il envoie les trames radio virtuelles
  directement via des requêtes HTTP POST.
"""

import sys
import struct
import time
import random
import os
import hashlib
import datetime

try:
    import requests
except ImportError:
    print("[ERREUR] Module 'requests' manquant ! (pip install requests)")
    sys.exit(1)

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import CMAC
except ImportError:
    print("[ERREUR] Module 'pycryptodome' manquant ! (pip install pycryptodome)")
    sys.exit(1)

from chirpstack_api import gw

# ================================================================
# CONFIGURATION
# ================================================================
# URL HTTP de destination (par exemple un endpoint custom ou un bridge HTTP)
HTTP_ENDPOINT   = "http://192.168.3.100:8081/api/uplink"
GATEWAY_ID      = os.getenv("GATEWAY_ID")
APPLICATION_ID  = os.getenv("APPLICATION_ID")

NB_CAPTEURS     = 10        
INTERVAL_SEC    = 1.0       
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
def build_uplink_frame_protobuf(phy_payload, rssi=-80, snr=8.5):
    """Construit un UplinkFrame parfait en utilisant la librairie officielle gw"""
    frame = gw.UplinkFrame()
    frame.phy_payload = phy_payload
    # tx_info
    frame.tx_info.frequency = 868100000
    frame.tx_info.modulation.lora.bandwidth = 125000
    frame.tx_info.modulation.lora.spreading_factor = 7
    frame.tx_info.modulation.lora.code_rate = gw.CodeRate.CR_4_5
    # rx_info
    frame.rx_info.gateway_id = GATEWAY_ID 
    frame.rx_info.uplink_id = random.randint(1, 65535)
    frame.rx_info.rssi = rssi
    frame.rx_info.snr = snr
    frame.rx_info.context = os.urandom(4)
    frame.rx_info.crc_status = gw.CRCStatus.CRC_OK
    return frame.SerializeToString()


# ================================================================
# GÉNÉRATION DE L'INJECTION
# ================================================================
def main():
    print("=" * 64)
    print("  [RADIO]  TIR DE BARRAGE LORAWAN - HTTP POST")
    print("=" * 64)

    devices = []
    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        seed = hashlib.sha256(dev_eui.encode()).digest()
        devices.append({
            "dev_addr": dev_addr,
            "nwk_s_key": seed[:16],
            "app_s_key": seed[16:32],
            "name": f"Sim-Capteur-{i:04d}",
            "fcnt": 0,
            "temp_base": round(random.uniform(18.0, 24.0), 1),
            "hum_base": round(random.uniform(40.0, 60.0), 1),
        })

    compteur = 0
    debut = time.time()
    
    print(f"\n[FIRE] Feu à volonté ! ({NB_CAPTEURS} capteurs, 1 tir toutes les {INTERVAL_SEC}s)")
    print(f"URL de destination HTTP : {HTTP_ENDPOINT}")
    print("Ctrl+C pour arrêter le test.\n")
    
    # Session requests pour optimiser la connexion HTTP (Keep-Alive)
    session = requests.Session()
    # Headers génériques, vous pouvez les adapter selon les besoins de votre API
    headers = {"Content-Type": "application/x-protobuf"}

    try:
        while True:
            # Choix d'un capteur au hasard
            dev = random.choice(devices)
            temp = round(dev["temp_base"] + random.uniform(-1.5, 1.5), 1)
            hum  = round(dev["hum_base"]  + random.uniform(-3.0, 3.0), 1)
            co2  = random.randint(400, 1200)

            # Assemblage et Chiffrement militaire
            payload = encode_sensor_payload(temp, hum, co2)
            phy = build_phy_payload(dev["dev_addr"], dev["nwk_s_key"], dev["app_s_key"], dev["fcnt"], FPORT, payload)
            dev["fcnt"] += 1

            # Injection dans l'antenne virtuelle via HTTP POST
            frame = build_uplink_frame_protobuf(phy, -80, 8.5)
            
            try:
                # Envoi asynchrone / synchrone de la requête
                resp = session.post(HTTP_ENDPOINT, data=frame, headers=headers, timeout=2)
                status = resp.status_code
            except requests.exceptions.RequestException as e:
                status = "Erreur de connexion"

            compteur += 1

            # Affichage périodique
            if compteur % 5 == 0:
                elapsed = time.time() - debut
                rate = compteur / elapsed if elapsed > 0 else 0
                print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] {compteur} requêtes POST envoyées ({rate:.1f}/s) | HTTP Status: {status} | {dev['name']} T={temp}°C")
            
            time.sleep(INTERVAL_SEC)
            
    except KeyboardInterrupt:
        print("\n[STOP] ARRÊT DE L'INJECTION.")
        session.close()

if __name__ == "__main__":
    main()
