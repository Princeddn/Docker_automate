"""
================================================================
  2b. ANALYSE DU TAUX DE RÉCEPTION — RAMPE PROGRESSIVE
================================================================
  Variante de 02_simulateur_radio.py qui fait varier le débit
  d'injection (msg/s) par paliers et mesure pour chacun :
    - Nombre de paquets envoyés (IN)
    - Nombre de paquets reçus par ChirpStack (OUT)
    - Ratio OUT/IN (taux de décodage)

  Objectif : trouver le point de rupture du WAGO CC100.
"""

import sys
import struct
import time
import random
import os
import hashlib
import json
import datetime
import threading
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
MQTT_PASS       = "YOUR_PASSWORD"

GATEWAY_ID      = "YOUR_GATEWAY_ID"
APPLICATION_ID  = "YOUR_APPLICATION_ID"

NB_CAPTEURS     = 30
FPORT           = 1

# ================================================================
# PALIERS DE TEST (msg/s, durée en secondes)
# ================================================================
PALIERS = [
    (0.5,  30),
    (1.0,  30),
    (1.5,  30),
    (2.0,  30),
    (2.5,  25),
    (3.0,  25),
    (3.5,  25),
    (4.0,  20),
    (4.5,  20),
    (5.0,  20),
    (5.5,  20),
    (6.0,  15),
    (6.5,  15),
    (7.0,  15),
    (7.5,  15),
    (8.0,  15),
    (8.5,  15),
    (9.0,  15),
    (9.5,  15),
    (10.0, 15),
]

# Temps de purge après chaque palier (laisser ChirpStack finir)
PURGE_SEC = 5

# ================================================================
# COULEURS TERMINAL
# ================================================================
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

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

def build_uplink_frame_protobuf(phy_payload, rssi, snr, frequency, sf):
    frame = gw.UplinkFrame()
    frame.phy_payload = phy_payload
    frame.tx_info.frequency = frequency
    frame.tx_info.modulation.lora.bandwidth = 125000
    frame.tx_info.modulation.lora.spreading_factor = sf
    frame.tx_info.modulation.lora.code_rate = gw.CodeRate.CR_4_5
    frame.rx_info.gateway_id = GATEWAY_ID
    frame.rx_info.uplink_id = random.randint(1, 65535)
    frame.rx_info.rssi = rssi
    frame.rx_info.snr = snr
    frame.rx_info.context = os.urandom(4)
    frame.rx_info.crc_status = gw.CRCStatus.CRC_OK
    return frame.SerializeToString()


# ================================================================
# COMPTEUR THREAD-SAFE
# ================================================================
class ReceptionCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    def get(self):
        with self._lock:
            return self._count

    def reset(self):
        with self._lock:
            self._count = 0


# ================================================================
# MAIN
# ================================================================
def main():
    print("=" * 70)
    print(f"  {BOLD}📡  ANALYSE DU TAUX DE RÉCEPTION — RAMPE PROGRESSIVE{RESET}")
    print("=" * 70)
    print(f"  Capteurs : {NB_CAPTEURS}")
    print(f"  Paliers  : {len(PALIERS)} niveaux de débit")
    print(f"  Purge    : {PURGE_SEC}s entre chaque palier")
    print(f"  Cible    : {BROKER_IP}")
    print("=" * 70)

    CHANNELS = [868100000, 868300000, 868500000]

    # 1. Génération des devices (identique à 02_simulateur_radio)
    devices = []
    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        seed = hashlib.sha256(dev_eui.encode()).digest()
        sf = random.choices([7, 8, 9, 10, 11, 12], weights=[40, 25, 15, 10, 5, 5])[0]
        base_rssi = -60 - ((sf - 7) * 10) - random.randint(0, 15)
        base_snr = 10.0 - ((sf - 7) * 4.0) - random.uniform(0, 3.0)

        devices.append({
            "dev_addr": dev_addr,
            "nwk_s_key": seed[:16],
            "app_s_key": seed[16:32],
            "name": f"Sim-Capteur-{i:04d}",
            "fcnt": 0,
            "temp_base": round(random.uniform(18.0, 24.0), 1),
            "hum_base": round(random.uniform(40.0, 60.0), 1),
            "co2_base": random.randint(400, 800),
            "sf": sf,
            "rssi_base": max(-120, base_rssi),
            "snr_base": max(-20.0, base_snr)
        })

    # 2. Connexion MQTT
    counter = ReceptionCounter()

    def on_msg(client, userdata, msg):
        counter.increment()

    print(f"\n{CYAN}Connexion au broker MQTT...{RESET}")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lorawan_rampe_verif")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_msg
    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"{RED}❌ Impossible de se connecter : {e}{RESET}")
        return

    client.loop_start()
    client.subscribe(f"application/{APPLICATION_ID}/device/+/event/up")

    gw_topic = f"eu868/gateway/{GATEWAY_ID}/event/up"

    # 3. Exécution des paliers
    resultats = []
    total_in = 0
    total_out = 0
    max_safe_rate = 0

    print(f"\n{GREEN}{BOLD}🚀 Démarrage de la rampe de charge...{RESET}\n")

    try:
        for idx, (msg_per_sec, duree) in enumerate(PALIERS):
            interval = 1.0 / msg_per_sec
            palier_label = f"Palier {idx+1}/{len(PALIERS)}"

            print(f"  {BOLD}{'─' * 60}{RESET}")
            print(f"  {BOLD}{palier_label} : {msg_per_sec} msg/s pendant {duree}s{RESET}")
            print(f"  {BOLD}{'─' * 60}{RESET}")

            # Reset du compteur de réception pour ce palier
            counter.reset()
            sent = 0
            errors = 0
            start = time.time()

            while (time.time() - start) < duree:
                dev = random.choice(devices)

                # Drift naturel
                dev["temp_base"] += random.uniform(-0.2, 0.2)
                dev["hum_base"] += random.uniform(-0.5, 0.5)
                dev["co2_base"] += random.randint(-15, 15)

                temp = round(max(-10, min(50, dev["temp_base"])), 1)
                hum  = round(max(10, min(90, dev["hum_base"])), 1)
                co2  = int(max(400, min(3000, dev["co2_base"])))
                rssi = int(max(-125, min(-40, dev["rssi_base"])))
                snr  = round(max(-20.0, min(15.0, dev["snr_base"])), 1)
                freq = random.choice(CHANNELS)
                sf   = dev["sf"]

                payload = encode_sensor_payload(temp, hum, co2)
                phy = build_phy_payload(dev["dev_addr"], dev["nwk_s_key"],
                                        dev["app_s_key"], dev["fcnt"], FPORT, payload)
                dev["fcnt"] += 1

                frame = build_uplink_frame_protobuf(phy, rssi, snr, freq, sf)
                try:
                    info = client.publish(gw_topic, frame, qos=0)
                    if info.rc != mqtt.MQTT_ERR_SUCCESS:
                        errors += 1
                except:
                    errors += 1

                sent += 1

                # Régulation du débit
                elapsed = time.time() - start
                expected_time = sent * interval
                sleep_time = expected_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # Purge : laisser le temps à ChirpStack de traiter
            print(f"    ⏳ Purge de {PURGE_SEC}s (attente décodage ChirpStack)...")
            time.sleep(PURGE_SEC)

            received = counter.get()
            ratio = (received / sent * 100) if sent > 0 else 0
            perte = 100 - ratio

            # Icône
            if ratio >= 98:
                icone = f"{GREEN}✅"
            elif ratio >= 80:
                icone = f"{YELLOW}⚠️"
            else:
                icone = f"{RED}🛑"

            actual_rate = sent / duree

            print(f"    {icone} IN={sent}  OUT={received}  "
                  f"Ratio={ratio:.1f}%  Perte={perte:.1f}%  "
                  f"(débit réel: {actual_rate:.1f} msg/s){RESET}")

            if errors > 0:
                print(f"    {RED}⚡ Erreurs MQTT: {errors}{RESET}")

            resultats.append({
                "palier": idx + 1,
                "cible_msg_s": msg_per_sec,
                "reel_msg_s": round(actual_rate, 2),
                "duree_s": duree,
                "sent": sent,
                "received": received,
                "ratio_pct": round(ratio, 1),
                "perte_pct": round(perte, 1),
                "errors": errors,
            })

            total_in += sent
            total_out += received

            if ratio >= 95:
                max_safe_rate = msg_per_sec

    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Interruption manuelle.{RESET}")

    # 4. Déconnexion
    client.loop_stop()
    client.disconnect()

    # ============================================================
    # RAPPORT FINAL EN CONSOLE
    # ============================================================
    print(f"\n{'=' * 70}")
    print(f"  {BOLD}📊  RAPPORT — TAUX DE RÉCEPTION PAR PALIER{RESET}")
    print(f"{'=' * 70}\n")

    # En-tête du tableau
    header = (f"  {'Palier':>7} │ {'Cible':>8} │ {'Réel':>8} │ "
              f"{'IN':>6} │ {'OUT':>6} │ {'Ratio':>7} │ {'Perte':>7} │ {'Status'}")
    sep    = f"  {'─'*7}─┼─{'─'*8}─┼─{'─'*8}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*7}─┼─{'─'*7}─┼─{'─'*8}"

    print(header)
    print(sep)

    for r in resultats:
        if r["ratio_pct"] >= 98:
            status = f"{GREEN}  OK  {RESET}"
        elif r["ratio_pct"] >= 80:
            status = f"{YELLOW} WARN {RESET}"
        else:
            status = f"{RED} FAIL {RESET}"

        print(f"  {r['palier']:>7} │ {r['cible_msg_s']:>6.1f}/s │ {r['reel_msg_s']:>6.1f}/s │ "
              f"{r['sent']:>6} │ {r['received']:>6} │ {r['ratio_pct']:>6.1f}% │ "
              f"{r['perte_pct']:>6.1f}% │ {status}")

    print(sep)
    ratio_global = (total_out / total_in * 100) if total_in > 0 else 0
    print(f"  {'TOTAL':>7} │ {'':>8} │ {'':>8} │ "
          f"{total_in:>6} │ {total_out:>6} │ {ratio_global:>6.1f}% │ "
          f"{100-ratio_global:>6.1f}% │")

    # Verdict
    print(f"\n  {CYAN}── Verdict ──{RESET}")
    print(f"  Débit max fiable (≥95% réception) : {BOLD}{max_safe_rate} msg/s{RESET}")

    if max_safe_rate > 0:
        print(f"\n  {CYAN}── Projection Déploiement GTB ──{RESET}")
        print(f"  Capteurs à 1 trame / 1 min  : {int(max_safe_rate * 60)} capteurs")
        print(f"  Capteurs à 1 trame / 5 min  : {int(max_safe_rate * 300)} capteurs")
        print(f"  Capteurs à 1 trame / 15 min : {BOLD}{int(max_safe_rate * 900)} capteurs{RESET}")

    # ============================================================
    # EXPORT RAPPORT MARKDOWN
    # ============================================================
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rapport_reception_{ts}.md"
    _generate_report(filename, resultats, total_in, total_out, max_safe_rate)

    print(f"\n  {GREEN}📄 Rapport exporté : {filename}{RESET}")
    print(f"{'=' * 70}\n")


def _generate_report(filename, resultats, total_in, total_out, max_safe_rate):
    """Génère un rapport Markdown du test de réception"""
    ratio_global = (total_out / total_in * 100) if total_in > 0 else 0

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 📊 Rapport d'Analyse du Taux de Réception LoRaWAN\n\n")
        f.write(f"**Date** : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Cible** : WAGO CC100 (`{BROKER_IP}`)  \n")
        f.write(f"**Gateway** : `{GATEWAY_ID}`  \n\n")

        f.write("## 1. Résumé\n\n")
        f.write(f"> **Débit max fiable (≥95% réception)** : **{max_safe_rate} msg/s**  \n")
        f.write(f"> **Ratio global IN/OUT** : {total_in} envoyés → {total_out} reçus "
                f"(**{ratio_global:.1f}%**)  \n\n")

        f.write("## 2. Résultats par Palier\n\n")
        f.write("| Palier | Cible (msg/s) | Réel (msg/s) | Durée | IN | OUT | Ratio | Perte | Status |\n")
        f.write("|--------|---------------|--------------|-------|----|-----|-------|-------|--------|\n")

        for r in resultats:
            if r["ratio_pct"] >= 98:
                status = "✅ OK"
            elif r["ratio_pct"] >= 80:
                status = "⚠️ WARN"
            else:
                status = "🛑 FAIL"

            f.write(f"| {r['palier']} | {r['cible_msg_s']} msg/s | {r['reel_msg_s']} msg/s | "
                    f"{r['duree_s']}s | {r['sent']} | {r['received']} | "
                    f"**{r['ratio_pct']}%** | {r['perte_pct']}% | {status} |\n")

        f.write(f"\n**Total** : {total_in} trames injectées → {total_out} trames décodées "
                f"(**{ratio_global:.1f}%**)  \n\n")

        f.write("## 3. Projection Déploiement\n\n")
        if max_safe_rate > 0:
            f.write(f"En se basant sur un débit fiable de **{max_safe_rate} msg/s** :\n\n")
            f.write(f"| Intervalle d'émission | Capteurs supportés |\n")
            f.write(f"|----------------------|--------------------|\n")
            f.write(f"| Toutes les 1 minute  | **{int(max_safe_rate * 60)}** capteurs |\n")
            f.write(f"| Toutes les 5 minutes | **{int(max_safe_rate * 300)}** capteurs |\n")
            f.write(f"| Toutes les 15 minutes (Standard GTB) | **{int(max_safe_rate * 900)}** capteurs |\n\n")
        else:
            f.write("⚠️ Aucun palier n'a atteint 95% de réception.\n\n")

        f.write("## 4. Interprétation\n\n")
        f.write("- **Ratio ≥ 98%** : Le système absorbe la charge sans perte significative.\n")
        f.write("- **Ratio 80-98%** : Zone de dégradation. Le CPU ARM 600MHz commence à saturer.\n")
        f.write("- **Ratio < 80%** : Effondrement. Le codec JavaScript timeout (>500ms) et les trames sont jetées.\n")


if __name__ == "__main__":
    main()
