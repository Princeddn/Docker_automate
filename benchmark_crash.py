"""
==========================================================
 BENCHMARK CRASH CONTRÔLÉ v3 — ESCALADE PROGRESSIVE
==========================================================
Nouveautés v3 :
  - Compteur msg/s temps réel corrigé (pas de wait_for_publish)
  - Serveur HTTP intégré pour recevoir les events ChirpStack
    (intégrateur HTTP de ChirpStack → ce script)
  - Rapport complet sauvegardé même en cas de Ctrl+C

Stratégie d'escalade :
  Phase 1  :  1 thread  → ~60-200 msg/s
  Phase 2  :  4 threads → ~400-800 msg/s
  Phase 3  :  8 threads → ~800-1600 msg/s
  Phase 4  : 16 threads → ~1600-3000 msg/s
  Phase 5  : 32 threads → ~3000-6000 msg/s
  Phase 6  : 64 threads → max possible

Usage : python benchmark_crash.py
"""

import paho.mqtt.client as mqtt
import threading
import time
import sys
import datetime
import socket
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque

# ============================================================
# CONFIGURATION
# ============================================================
BROKER_IP   = "192.168.3.100"
BROKER_PORT = 1883
USER        = "chirpstack"
PASSWORD    = "YOUR_PASSWORD"
TOPIC_PUB   = "eu868/gateway/mac_gw/event/up"

# Serveur HTTP pour recevoir les events de l'intégrateur ChirpStack
HTTP_LISTEN_PORT = 5050   # Configurez ChirpStack → Integrations → HTTP → http://<IP_VOTRE_PC>:5050

# Paliers : (nb_threads, durée_secondes, label)
PALIERS = [
    (1,  60,  "Phase 1 —  1 thread  (~free speed)"),
    (4,  60,  "Phase 2 —  4 threads (~×4)"),
    (8,  60,  "Phase 3 —  8 threads (~×8)"),
    (16, 60,  "Phase 4 — 16 threads (~×16)"),
    (32, 60,  "Phase 5 — 32 threads (~×32)"),
    (64, 60,  "Phase 6 — 64 threads (MAX)"),
]

# ============================================================
# PAYLOAD
# ============================================================
try:
    with open("valid_payload.bin", "rb") as f:
        payload_binaire = f.read()
    print(f"  ✅ Vraie trame LoRa chargée ({len(payload_binaire)} octets)")
except FileNotFoundError:
    print("  ⚠️  'valid_payload.bin' non trouvé → fausse trame 162 octets (zéros)")
    payload_binaire = b'\x00' * 162

# ============================================================
# ÉTAT GLOBAL (thread-safe)
# ============================================================
stop_event      = threading.Event()
compteur_lock   = threading.Lock()
compteur_global = 0          # Messages ENVOYÉS sur le réseau (total phase)
resultats_phases = []

# Compteurs HTTP (intégrateur ChirpStack)
http_lock           = threading.Lock()
http_events_recus   = 0      # Events reçus de ChirpStack via HTTP
http_dernier_event  = None   # Dernier JSON reçu
http_events_log     = deque(maxlen=100)  # Log des 100 derniers events

# ============================================================
# SERVEUR HTTP — RÉCEPTEUR D'EVENTS CHIRPSTACK
# ============================================================
class ChirpStackHTTPHandler(BaseHTTPRequestHandler):
    """Reçoit les events envoyés par l'intégrateur HTTP de ChirpStack."""

    def do_POST(self):
        global http_events_recus, http_dernier_event
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8", errors="replace"))

            with http_lock:
                http_events_recus += 1
                http_dernier_event = data
                event_type = self.path.strip("/")
                http_events_log.append({
                    "time":  datetime.datetime.now().strftime("%H:%M:%S"),
                    "type":  event_type,
                    "devEUI": data.get("deviceInfo", {}).get("devEui", "?"),
                    "fPort": data.get("fPort", "?"),
                })

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silence les logs HTTP inutiles dans le terminal


def demarrer_serveur_http():
    """Lance le serveur HTTP dans un thread daemon."""
    try:
        server = HTTPServer(("0.0.0.0", HTTP_LISTEN_PORT), ChirpStackHTTPHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"  🌐 Serveur HTTP démarré sur le port {HTTP_LISTEN_PORT}")
        print(f"     → Configurez ChirpStack : Integrations → HTTP → http://<IP_PC>:{HTTP_LISTEN_PORT}/up")
        return server
    except OSError as e:
        print(f"  ⚠️  Impossible d'ouvrir le port {HTTP_LISTEN_PORT} : {e}")
        print(f"     → L'intégration HTTP ne sera pas disponible, mais le benchmark continue.")
        return None

# ============================================================
# VÉRIFICATION WAGO
# ============================================================
def verifier_wago_vivant():
    try:
        s = socket.create_connection((BROKER_IP, BROKER_PORT), timeout=5)
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# ============================================================
# THREAD PUBLISHER MQTT
# ============================================================
def publisher_thread(thread_id, duree_sec):
    """Publie à pleine vitesse pendant duree_sec secondes.
    Compte localement et reverse dans le global par batch de 200."""
    global compteur_global

    try:
        client_id = f"crash_{thread_id}_{int(time.time()*1000) % 100000}"
        cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        cli.username_pw_set(USER, PASSWORD)
        cli.connect(BROKER_IP, BROKER_PORT, keepalive=60)
        cli.loop_start()
    except Exception as e:
        return  # Connexion impossible, on abandonne ce thread

    fin         = time.time() + duree_sec
    local_count = 0
    BATCH       = 200

    while time.time() < fin and not stop_event.is_set():
        try:
            cli.publish(TOPIC_PUB, payload_binaire, qos=0)
            local_count += 1
            if local_count >= BATCH:
                with compteur_lock:
                    compteur_global += local_count
                local_count = 0
        except Exception:
            break

    # Reverser le reliquat
    if local_count > 0:
        with compteur_lock:
            compteur_global += local_count

    try:
        cli.loop_stop()
        cli.disconnect()
    except Exception:
        pass

# ============================================================
# LANCEMENT D'UNE PHASE
# ============================================================
def lancer_phase(nb_threads, duree_sec, nom_phase):
    global compteur_global

    # Reset compteur de phase
    with compteur_lock:
        compteur_global = 0

    print(f"\n{'='*62}")
    print(f"  {nom_phase}")
    print(f"{'='*62}")

    if not verifier_wago_vivant():
        print("  🔴 WAGO NE RÉPOND PLUS — phase annulée.")
        return False

    heure_debut = datetime.datetime.now().strftime("%H:%M:%S")
    start       = time.time()

    # Reset HTTP counter for this phase
    with http_lock:
        http_start_count = http_events_recus

    print(f"  ✅ WAGO vivant — lancement de {nb_threads} thread(s) pendant {duree_sec}s")
    print(f"  {'HEURE':^10} | {'T+':^5} | {'MSGS ENVOYÉS':^16} | {'MSG/S':^9} | {'HTTP EVENTS':^12} | WAGO")
    print(f"  {'-'*77}")

    # Démarrer tous les threads
    threads = []
    for i in range(nb_threads):
        t = threading.Thread(target=publisher_thread, args=(i, duree_sec), daemon=True)
        t.start()
        threads.append(t)

    # Monitoring toutes les 5s
    dernier_check     = time.time()
    dernier_count     = 0
    dernier_http      = http_start_count
    wago_mort         = False
    temps_mort        = None
    CHECK_INTERVAL    = 5  # secondes entre chaque ligne d'affichage

    while any(t.is_alive() for t in threads):
        time.sleep(CHECK_INTERVAL)
        now      = time.time()
        elapsed  = now - start
        dt       = now - dernier_check  # durée exacte depuis le dernier check

        with compteur_lock:
            current_count = compteur_global
        with http_lock:
            current_http = http_events_recus

        # Calcul du débit sur l'intervalle exact
        msgs_intervalle = current_count - dernier_count
        debit_instantane = msgs_intervalle / dt if dt > 0 else 0

        http_intervalle  = current_http - dernier_http
        dernier_count    = current_count
        dernier_http     = current_http
        dernier_check    = now

        alive = verifier_wago_vivant()
        heure_now = datetime.datetime.now().strftime("%H:%M:%S")

        statut = "✅ VIVANT" if alive else "🔴 MORT !"
        print(
            f"  [{heure_now}]"
            f" | T+{int(elapsed):>4}s"
            f" | {current_count:>14,} msgs"
            f" | {int(debit_instantane):>7} m/s"
            f" | +{http_intervalle:>4} ev ({current_http - http_start_count} tot)"
            f" | {statut}"
        )

        if not alive and not wago_mort:
            wago_mort  = True
            temps_mort = elapsed
            print(f"\n  ⚠️  CRASH DÉTECTÉ à T+{int(elapsed)}s !")
            stop_event.set()

    for t in threads:
        t.join(timeout=5)

    duree_reelle  = time.time() - start
    heure_fin     = datetime.datetime.now().strftime("%H:%M:%S")
    with compteur_lock:
        total_msgs = compteur_global
    with http_lock:
        total_http = http_events_recus - http_start_count

    debit_moyen = total_msgs / max(duree_reelle, 0.001)

    resultat = {
        "phase":       nom_phase,
        "threads":     nb_threads,
        "messages":    total_msgs,
        "duree":       duree_reelle,
        "debit":       debit_moyen,
        "http_events": total_http,
        "wago_crash":  wago_mort,
        "temps_crash": temps_mort,
        "heure_debut": heure_debut,
        "heure_fin":   heure_fin,
    }
    resultats_phases.append(resultat)

    print(f"\n  ── Résultat ──────────────────────────────────────────")
    print(f"  │ Période          : {heure_debut} → {heure_fin}")
    print(f"  │ Msgs MQTT envoyés: {total_msgs:,}")
    print(f"  │ Débit moyen      : ~{int(debit_moyen):,} msg/s")
    print(f"  │ Events HTTP reçus: {total_http}")
    print(f"  │ WAGO status      : {'🔴 CRASH à T+' + str(int(temps_mort)) + 's' if wago_mort else '✅ SURVIVANT'}")

    if wago_mort:
        return False

    # Pause de récupération entre phases
    print(f"\n  ⏸  Pause de récupération 20s...")
    time.sleep(20)

    if not verifier_wago_vivant():
        print("  🔴 WAGO mort pendant la récupération (crash différé) !")
        resultat["wago_crash"]  = True
        resultat["temps_crash"] = duree_reelle + 20
        return False

    print("  ✅ WAGO vivant après récupération.")
    return True

# ============================================================
# RAPPORT FINAL
# ============================================================
def afficher_rapport_final():
    now_str  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lignes   = []
    total    = 0

    lignes.append("=" * 62)
    lignes.append("     RAPPORT FINAL — BENCHMARK CRASH CONTRÔLÉ v3")
    lignes.append("=" * 62)
    lignes.append(f"  Date    : {now_str}")
    lignes.append(f"  Cible   : WAGO CC100 @ {BROKER_IP}:{BROKER_PORT}")
    lignes.append("-" * 62)

    crashed  = []
    survived = []
    for r in resultats_phases:
        st = "🔴 CRASH" if r["wago_crash"] else "✅ OK"
        ligne = (
            f"  {r['phase']}\n"
            f"    Msgs envoyés : {r['messages']:>12,}  |  Débit moyen : ~{int(r['debit']):>7,} msg/s\n"
            f"    HTTP events  : {r['http_events']:>12}  |  Durée réelle: {r['duree']:.1f}s\n"
            f"    Status : {st}"
            + (f"  — crash à T+{int(r['temps_crash'])}s" if r["wago_crash"] and r["temps_crash"] else "")
        )
        lignes.append(ligne)
        lignes.append("")
        total += r["messages"]
        if r["wago_crash"]:
            crashed.append(r)
        else:
            survived.append(r)

    lignes.append("-" * 62)
    lignes.append(f"  Total messages MQTT injectés : {total:,}")
    lignes.append(f"  Phases complétées            : {len(survived)}/{len(resultats_phases)}")

    if crashed:
        seuil_survie = int(survived[-1]["debit"]) if survived else 0
        seuil_crash  = int(crashed[0]["debit"])
        lignes.append("")
        lignes.append("  🎯 SEUIL DE CRASH IDENTIFIÉ :")
        lignes.append(f"    Dernier débit survivant : ~{seuil_survie:,} msg/s")
        lignes.append(f"    Débit au crash          : ~{seuil_crash:,} msg/s")
    elif resultats_phases:
        lignes.append("")
        lignes.append(f"  ⚡ LE WAGO A TOUT SURVÉCU — débit max atteint : ~{int(resultats_phases[-1]['debit']):,} msg/s")

    lignes.append("=" * 62)

    rapport = "\n".join(lignes)
    print("\n\n" + rapport)

    # Sauvegarde fichier
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"rapport_crash_{ts}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(rapport + "\n")
    print(f"\n  📄 Rapport sauvegardé → {path}")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 62)
    print("   🔥 BENCHMARK CRASH CONTRÔLÉ v3 — ESCALADE PROGRESSIVE")
    print("=" * 62)
    print(f"   Cible      : WAGO CC100 @ {BROKER_IP}")
    print(f"   Phases     : {len(PALIERS)}")
    print(f"   Max threads: {PALIERS[-1][0]}")
    print()

    # Démarrer le serveur HTTP pour l'intégrateur ChirpStack
    http_server = demarrer_serveur_http()
    print()

    print("   ⚠️  CE TEST VA TENTER DE CRASHER L'AUTOMATE !")
    print("   Assurez-vous que le monitoring SSH est actif sur le WAGO.")
    print()
    input("   Appuyez sur [ENTRÉE] pour commencer l'escalade...")

    try:
        for nb_threads, duree, nom in PALIERS:
            if stop_event.is_set():
                break
            ok = lancer_phase(nb_threads, duree, nom)
            if not ok:
                print(f"\n  🔴 CRASH CONFIRMÉ — Arrêt de l'escalade.")
                break
    except KeyboardInterrupt:
        print(f"\n  🛑 ARRÊT MANUEL (Ctrl+C)")
        stop_event.set()
    finally:
        afficher_rapport_final()
        if http_server:
            http_server.shutdown()
