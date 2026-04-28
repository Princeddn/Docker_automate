import paho.mqtt.client as mqtt
import time
import sys
import datetime
import math

BROKER_IP = "192.168.3.100"
BROKER_PORT = 1883
USER = "chirpstack"
PASSWORD = "YOUR_PASSWORD"

TOPIC_SUB = "eu868/gateway/+/event/up"
TOPIC_PUB = "eu868/gateway/mac_gw/event/up"

TOTAL_MESSAGES = 150000

payload_binaire = None

# Tentative de charger une vraie trame sauvegardée, sinon on crée une fausse trame de 162 octets
try:
    with open("valid_payload.bin", "rb") as f:
        payload_binaire = f.read()
    print(f" Vraie trame chargée depuis 'valid_payload.bin' ({len(payload_binaire)} octets)")
except FileNotFoundError:
    print(" 'valid_payload.bin' non trouvé. Utilisation d'une fausse trame (162 octets remplis de zéros).")
    print("   Note : ChirpStack la rejettera très vite, mais ça testera quand même le réseau MQTT.")
    payload_binaire = b'\x00' * 162

# On n'écoute plus les messages entrants
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(" Connecté au broker Mosquitto du WAGO")
    else:
        print(" Erreur de connexion au broker")

print("==========================================================")
print("   BENCHMARK LORAWAN EXTREME - DEPUIS LE PC")
print("==========================================================")
print(f" Connexion au WAGO sur {BROKER_IP}...")

client = mqtt.Client()
client.username_pw_set(USER, PASSWORD)
client.on_connect = on_connect

try:
    client.connect(BROKER_IP, BROKER_PORT, 60)
except Exception as e:
    print(f"Impossible de se connecter : {e}")
    sys.exit(1)

# Lancement de la boucle réseau en tâche de fond
client.loop_start()

# PUS DE PHASE 1 D'INTERCEPTION : On a déjà la trame

# ÉTAPE 2 : Préparation de l'envoi
input("\n[PRÊT] Appuyez sur [ENTRÉE] pour lancer le bombardement immédiat...")

# ÉTAPE 3 : Injection à haute vitesse
print(f"\n[3/3]  INJECTION DE {TOTAL_MESSAGES} TRAMES EN COURS...")

# On garde la boucle de fond active pendant le tir
client.loop_start() 

start_time = time.time()
heure_debut = datetime.datetime.now().strftime("%H:%M:%S")

# On définit un palier d'affichage tous les 5000 messages (ou moins si on fait un petit test)
BATCH_SIZE = 5000 if TOTAL_MESSAGES >= 5000 else math.ceil(TOTAL_MESSAGES / 5)

print(f"   -> Envoi en cours... Des checkpoints de contrôle auront lieu tous les {BATCH_SIZE} msgs.")

for i in range(TOTAL_MESSAGES):
    is_last = (i == TOTAL_MESSAGES - 1)
    is_checkpoint = ((i + 1) % BATCH_SIZE == 0)

    # Si c'est la fin d'un palier ou le TOUT dernier message, on exige l'accusé de réception (QoS 1)
    if is_checkpoint or is_last:
        msg = client.publish(TOPIC_PUB, payload_binaire, qos=1)
        # On bloque mathématiquement l'ordinateur tant que le WAGO n'a pas digéré CE palier
        msg.wait_for_publish()
        
        heure_checkpoint = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"   [{heure_checkpoint}]  Palier validé : {i + 1} / {TOTAL_MESSAGES} trames absorbées par l'automate")
    else:
        # Sinon, on balance à pleine vitesse (QoS 0)
        client.publish(TOPIC_PUB, payload_binaire, qos=0)

client.loop_stop()

end_time = time.time()
heure_fin = datetime.datetime.now().strftime("%H:%M:%S")
duree = end_time - start_time
duree = max(duree, 0.001) # Éviter division par 0
mps = TOTAL_MESSAGES / duree

print("\n==========================================================")
print("         RAPPORT FINAL D'INJECTION (Côté PC)")
print("==========================================================")
print(f" │ Heure de début         : {heure_debut}")
print(f" │ Heure de fin           : {heure_fin}")
print(f" │ Durée totale d'envoi   : {duree:.2f} secondes")
print(f" │ Messages injectés      : {TOTAL_MESSAGES}")
print(f" │ Débit moyen VRAI       : ~{int(mps)} msg/s")
print("==========================================================")
print("\n L'envoi est terminé ! Regardez maintenant l'outil 'top' sur votre")
print("WAGO pour observer comment ChirpStack digère cette arrivée massive.")
