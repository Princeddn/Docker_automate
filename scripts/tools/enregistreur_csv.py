"""
==========================================================
 📊 ENREGISTREUR DE DONNÉES MQTT → CSV (EXCEL)
==========================================================
Ce script se connecte au WAGO, écoute les données des capteurs 
décodées par ChirpStack, et les enregistre automatiquement
dans un fichier CSV que vous pouvez ouvrir dans Excel.

Laissez-le tourner en tâche de fond pour accumuler la data !

Usage : python enregistreur_csv.py
"""

import paho.mqtt.client as mqtt
import json
import csv
import os
import datetime

# ============================================================
# CONFIGURATION
# ============================================================
BROKER_IP   = "192.168.3.100"
BROKER_PORT = 1883
USER        = "chirpstack"
PASSWORD    = "YOUR_PASSWORD"

# On a besoin uniquement des données capteurs
TOPIC_SUB   = "application/+/device/+/event/up"

FICHIER_CSV = "historique_capteurs.csv"

# ============================================================
# INITIALISATION DU FICHIER CSV
# ============================================================
def init_csv():
    # Créer le fichier avec l'en-tête s'il n'existe pas
    if not os.path.exists(FICHIER_CSV):
        with open(FICHIER_CSV, mode='w', newline='', encoding='utf-8') as fichier:
            writer = csv.writer(fichier, delimiter=';') # Point-virgule idéal pour l'Excel Français
            writer.writerow([
                "Date_Heure", 
                "DevEUI", 
                "Nom_Capteur", 
                "Temperature_C", 
                "Humidite_%", 
                "CO2_ppm", 
                "RSSI_dBm", 
                "SNR_dB"
            ])
        print(f"📁 Fichier {FICHIER_CSV} créé avec succès.")

# ============================================================
# CALLBACKS MQTT
# ============================================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ Connecté à Mosquitto sur le WAGO ({BROKER_IP}).")
        print(f"📡 Écoute attentive des capteurs...")
        print(f"💾 Les données sont écrites en direct dans '{FICHIER_CSV}'.")
        print(f"Appuyez sur Ctrl+C pour arrêter.")
        client.subscribe(TOPIC_SUB, qos=1)
    else:
        print(f"❌ Erreur connexion : code {reason_code}")

def on_message(client, userdata, msg):
    try:
        # Tenter de convertir le texte brut en dictionnaire JSON
        payload = json.loads(msg.payload.decode("utf-8"))
        
        # Ce champ confirme qu'il y a des données décodées
        if "deviceInfo" in payload and "object" in payload:
            
            # --- Extraction des données ---
            heure = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dev_eui = payload["deviceInfo"].get("devEui", "Inconnu")
            nom_capteur = payload["deviceInfo"].get("deviceName", "Inconnu")
            
            # Les données décodées par le code Javascript (si le codec est mis !)
            data = payload.get("object", {})
            temp = data.get("temperature", "")
            hum = data.get("humidity", "")
            co2 = data.get("co2", "")
            
            # La qualité du signal radio (très utile en debug)
            rssi = ""
            snr = ""
            if "rxInfo" in payload and len(payload["rxInfo"]) > 0:
                rssi = payload["rxInfo"][0].get("rssi", "")
                snr = payload["rxInfo"][0].get("snr", "")
            
            # --- Écriture dans le fichier CSV ---
            with open(FICHIER_CSV, mode='a', newline='', encoding='utf-8') as fichier:
                writer = csv.writer(fichier, delimiter=';')
                writer.writerow([heure, dev_eui, nom_capteur, temp, hum, co2, rssi, snr])
            
            print(f"[{heure}] 📝 Donnée enregistrée pour {nom_capteur} ({dev_eui})")
            
    except Exception as e:
        # Erreur silencieuse si un message n'est pas bon ou JSON cassé
        pass

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("   💾 ENREGISTREUR DE DATA - LORAWAN TO EXCEL")
    print("=" * 60)
    
    init_csv()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="enregistreur_csv_pc")
    client.username_pw_set(USER, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Enregistrement arrêté. Vous pouvez ouvrir le fichier CSV !")
        client.disconnect()
