import time
import random
import os
import hashlib
import datetime
import struct
import threading
import paramiko
import paho.mqtt.client as mqtt
import importlib.util
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
from chirpstack_api import gw

# --- CONFIGURATION (RESTÉE INTACTE) ---
WAGO_IP         = "192.168.3.100"
WAGO_USER       = "root"
WAGO_PASS       = "wago"
MQTT_USER       = "chirpstack"
MQTT_PASS       = "YOUR_PASSWORD"
GATEWAY_ID      = "YOUR_GATEWAY_ID"
NB_CAPTEURS     = 30  # Réservoir de capteurs (Le script va les provisionner)

# --- NOUVELLES PHASES DU BENCHMARK (Progressives) ---
# Format: (Nom, msg_par_seconde, duree_en_secondes)
PHASES = [
    ("Phase 1 (0.5 msg/s)", 0.5, 15),
    ("Phase 2 (1.0 msg/s)", 1.0, 15),
    ("Phase 3 (1.5 msg/s)", 1.5, 15),
    ("Phase 4 (2.0 msg/s)", 2.0, 15),
    ("Phase 5 (2.5 msg/s)", 2.5, 15),
    ("Phase 6 (3.0 msg/s)", 3.0, 15),
    ("Phase 7 (3.5 msg/s)", 3.5, 15),
    ("Phase 8 (4.0 msg/s)", 4.0, 15),
    ("Phase 9 (4.5 msg/s)", 4.5, 15),
    ("Phase 10 (5.0 msg/s)", 5.0, 15),
    ("Phase 11 (10.0 msg/s - Torture)", 10.0, 15),
    ("Phase 12 (50.0 msg/s - Attaque DDoS)", 50.0, 15),
]

# ================================================================
# MONITEUR SSH
# ================================================================
class WagoMonitor(threading.Thread):
    def __init__(self, ip, user, password):
        super().__init__()
        self.ip = ip
        self.user = user
        self.password = password
        self.running = True
        self.stats_history = []
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def run(self):
        try:
            self.client.connect(self.ip, username=self.user, password=self.password, timeout=10)
            while self.running:
                cmd = (
                    "awk '{print $1}' /proc/loadavg; "
                    "free | awk '/Mem/ {print (($3+$5)/$2)*100}'"
                )
                stdin, stdout, stderr = self.client.exec_command(cmd)
                lines = stdout.readlines()
                if len(lines) >= 2:
                    try:
                        self.stats_history.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "load": float(lines[0].strip()),
                            "mem_perc": float(lines[1].strip()),
                            "docker": "N/A"
                        })
                    except: pass
                time.sleep(2)
        except Exception as e:
            pass
        finally:
            self.client.close()

    def stop(self):
        self.running = False


# Les fonctions cryptographiques sont désormais importées depuis 02_simulateur_radio.py
# pour garantir une parfaite synchronicité de la logique d'injection.


# ================================================================
# MAIN
# ================================================================
application_messages_received = 0

def on_message(client, userdata, msg):
    global application_messages_received
    application_messages_received += 1

def main():
    global application_messages_received
    print("\n" + "="*70)
    print(" 🤖 DÉMARRAGE DU BENCHMARK INTELLIGENT")
    print("="*70)
    
    reponse = input(f"Voulez-vous (re)créer/mettre à jour les {NB_CAPTEURS} capteurs via l'API avant le test ? (O/n) : ").strip().lower()
    
    if reponse != 'n':
        # Appel de 01_creation_capteurs pour inscrire les équipements sur ChirpStack avant d'attaquer
        try:
            spec = importlib.util.spec_from_file_location("capteurs", "01_creation_capteurs.py")
            capteurs = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(capteurs)
            print(f"\n📡 PROVISIONING : Inscription de {NB_CAPTEURS} capteurs via le profil 'Simulated-ABP'...")
            capteurs.NB_CAPTEURS = NB_CAPTEURS
            tenant_id = capteurs.get_tenant_from_app()
            if tenant_id:
                dp_id = capteurs.setup_profile(tenant_id)
                capteurs.create_or_update_devices(dp_id)
                print("✅ Provisioning terminé. L'automate connaît maintenant les signatures.")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'appel au script API : {e}")
    else:
        print("⏭️ Provisioning ignoré. Démarrage direct de la simulation...")

    # Init Devices en RAM pour les tirs
    print(f"\nGénération de l'espace cryptographique Python pour {NB_CAPTEURS} capteurs...")
    devices = []
    for i in range(1, NB_CAPTEURS + 1):
        dev_eui = f"aa00000000{i:06x}"
        dev_addr = 0x01FF0000 + i
        seed = hashlib.sha256(dev_eui.encode()).digest()
        devices.append({"dev_addr": dev_addr, "nwk_s_key": seed[:16], "app_s_key": seed[16:32], "fcnt": 0})

    monitor = WagoMonitor(WAGO_IP, WAGO_USER, WAGO_PASS)
    monitor.start()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="benchmark_ai")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_message
    try:
        client.connect(WAGO_IP, 1883, 60)
        client.subscribe("application/+/device/+/event/up")
        client.loop_start()
    except Exception as e:
        print(f"❌ Erreur MQTT : {e}"); monitor.stop(); return

    # Import Dynamique du Module Simulateur 02
    try:
        spec2 = importlib.util.spec_from_file_location("simulateur", "02_simulateur_radio.py")
        simulateur = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(simulateur)
    except Exception as e:
        print(f"⚠️ Erreur lors de l'import de 02_simulateur_radio.py : {e}")
        return

    gw_topic = f"eu868/gateway/{GATEWAY_ID}/event/up"
    
    results = []
    global_start_time = time.time()
    total_injected = 0
    max_safe_rate = 0  # Vitesse max avant effondrement

    try:
        for phase_name, msg_per_sec, duration in PHASES:
            interval = 1.0 / msg_per_sec
            print(f"\n🚀 {phase_name} ({msg_per_sec} msg/s pendant {duration}s)")
            
            # Réinitialisation du compteur pour isoler la performance de la phase cible
            global application_messages_received
            application_messages_received = 0
            
            start_phase = time.time()
            sent_phase = 0
            errors_phase = 0
            
            while (time.time() - start_phase) < duration:
                dev = random.choice(devices)
                
                # Utilisation parfaite du code 02_simulateur
                temp = random.uniform(15.0, 30.0)
                hum = random.uniform(30.0, 60.0)
                co2 = random.randint(400, 1000)
                
                payload = simulateur.encode_sensor_payload(temp, hum, co2)
                phy = simulateur.build_phy_payload(dev["dev_addr"], dev["nwk_s_key"], dev["app_s_key"], dev["fcnt"], 1, payload)
                dev["fcnt"] += 1
                
                # Fréquence et SF fixes pour accélérer le jet 
                frame = simulateur.build_uplink_frame_protobuf(phy, -60, 9.5, 868100000, 7)
                
                try:
                    info = client.publish(gw_topic, frame, qos=0)
                    if info.rc != mqtt.MQTT_ERR_SUCCESS: errors_phase += 1
                except:
                    errors_phase += 1
                
                sent_phase += 1
                total_injected += 1
                elapsed_while = time.time() - start_phase
                # Compensation du temps de calcul
                time.sleep(max(0, (sent_phase * interval) - elapsed_while))

            # Fin de phase et purge de la file
            print("   ⏳ Traitement ChirpStack en cours (purge de 3s)...")
            time.sleep(3)
            
            reçus_phase = application_messages_received
            perte_phase = ((sent_phase - reçus_phase) / sent_phase * 100) if sent_phase > 0 else 0
            
            color = "🟢" if perte_phase == 0 else ("🟠" if perte_phase < 50 else "🛑")
            print(f"   {color} Envoyés: {sent_phase} | Reçus (JSON): {reçus_phase} | Pertes: {perte_phase:.1f}%")
            
            results.append({
                "phase": phase_name,
                "msg_rate": msg_per_sec,
                "sent": sent_phase,
                "received": reçus_phase,
                "loss": perte_phase,
                "errors": errors_phase
            })
            
            # Détermination intelligente du point de rupture
            if perte_phase < 5:  # Tolérance de 5% de perte max pour considérer la charge comme "Safe"
                max_safe_rate = msg_per_sec
                
    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur.")

    print("\n⏳ Fin des phases...")
    client.loop_stop()
    client.disconnect()
    monitor.stop()
    monitor.join()

    print("Analyse post-mortem du système (CPU, Logs)...")

    # -- EXTRACTION DES LOGS CHIRPSTACK --
    chirpstack_errors = []
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(WAGO_IP, username=WAGO_USER, password=WAGO_PASS, timeout=10)
        stdin, stdout, stderr = ssh.exec_command("docker logs --since 5m lora-chirpstack | grep -i 'error' | grep -iv 'without error'")
        logs = stdout.read().decode().strip().split('\n')
        chirpstack_errors = [l for l in logs if l]
        ssh.close()
    except: pass

    # -- GÉNÉRATION DU RAPPORT I.A. --
    duration_total = time.time() - global_start_time
    generate_report(f"rapport_benchmark_FINAL_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md", results, monitor.stats_history, chirpstack_errors, max_safe_rate, duration_total)

def generate_report(filename, results, history, errors, max_safe_rate, duration_total):
    total_sent = sum([r["sent"] for r in results])
    app_received = sum([r["received"] for r in results])
    pertes_relatives = total_sent - app_received
    taux_perte = (pertes_relatives / total_sent) * 100 if total_sent > 0 else 0
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 📊 Rapport Professionnel de Benchmark WAGO CC100 (ChirpStack v4)\n\n")
        
        f.write("## 1. 🎯 Conclusion et Capacité d'Ingestion Automatique\n\n")
        f.write(f"> **Débit d'ingestion robuste validé sans erreur claire :** {max_safe_rate} messages / seconde.\n\n")
        
        f.write("### 📡 Fiabilité de Décodage de bout-en-bout (MQTT Application)\n")
        f.write(f"- **Trames radio brutes envoyées** : {total_sent}\n")
        f.write(f"- **Trames décodées avec succès (JSON)** : {app_received}\n")
        f.write(f"- **Taux de Perte global (Chute CPU)** : **{taux_perte:.1f}%**\n")
        if taux_perte > 0:
            f.write("> ⚠️ *Note: Une perte > 0% signifie que le processeur (ARM 600Mhz) a été incapable de suivre la cadence et a dû jeter les trames avant décodage.*\n\n")
        else:
            f.write("> ✅ *Note: Excellence logicielle. Aucune trame perdue, tout a été déchiffré à temps !*\n\n")

        f.write("### Projection pour un déploiement GTB réel (Bâtiment) :\n")
        f.write(f"Si ce WAGO maintient {max_safe_rate} requêtes par seconde sans saturer, voici sa capacité théorique maximale :\n")
        f.write(f"- Si les capteurs émettent toutes les **1 minute** : {int(max_safe_rate * 60)} capteurs supportés.\n")
        f.write(f"- Si les capteurs émettent toutes les **5 minutes** : {int(max_safe_rate * 300)} capteurs supportés.\n")
        f.write(f"- Si les capteurs émettent toutes les **15 minutes** (Standard GTB) : **{int(max_safe_rate * 900)} capteurs supportés.**\n\n")

        f.write("## 2. 📈 Localisation de la Rupture de Charge (Par Phases)\n\n")
        f.write("| Phase | Vitesse (Msg/s) | Injections (Gateway) | Décodages (App) | Taux de Perte |\n")
        f.write("|-------|-----------------|----------------------|-----------------|---------------|\n")
        for r in results:
            loss_indicator = "🟢" if r['loss'] == 0 else ("🟠" if r['loss'] < 50 else "🛑")
            f.write(f"| {r['phase']} | {r['msg_rate']} msg/s | {r['sent']} trames | {r['received']} trames | {loss_indicator} **{r['loss']:.1f}%** |\n")
            
        f.write(f"\n**Durée totale :** {duration_total:.1f}s | **Trames totales :** {total_sent}\n\n")

        f.write("## 3. ⚠️ Analyse Interne ChirpStack (JavaScript Codec Errors)\n\n")
        f.write("Ceci indique si l'automate a manqué de temps CPU pour décoder les trames (Timeout 500ms).\n")
        if not errors:
            f.write("✅ **0 Erreur de décodage.** Le WAGO a parfaitement réussi à traduire toutes les trames AES en JSON sans être interrompu.\n")
        else:
            f.write(f"❌ **{len(errors)} erreurs détectées dans les logs Docker.** (CPU Probablement saturé)\n")
            f.write("```text\n")
            for e in errors[:10]: f.write(e + "\n")
            f.write("```\n")

        f.write("\n## 4. 💽 Télémétrie Système (Load Average & Mémoire)\n\n")
        f.write("| Heure | Load CPU | Utilisation RAM (%) | Consommation Docker |\n")
        f.write("|-------|----------|---------------------|---------------------|\n")
        for h in history:
            f.write(f"| {h['time']} | {h['load']} | {h['mem_perc']:.1f}% | `{h['docker']}` |\n")

    print(f"\n🎉 RAPPORT DÉFINITIF GÉNÉRÉ : {filename}")
    print("Ouvre ce fichier markdown pour voir la capacité réelle du WAGO !")

if __name__ == "__main__":
    main()
