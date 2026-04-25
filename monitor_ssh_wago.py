import paramiko
import os
import datetime

# --- CONFIGURATION (À MODIFIER) ---
WAGO_IP = "192.168.3.100"  # Remplacez par l'IP de votre WAGO
WAGO_USER = "admin"
WAGO_PASS = "wago"

def test_ssh_monitoring(ip, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Tentative de connexion SSH sur {ip}...")
        client.connect(ip, username=user, password=password, timeout=10)
        print("Connexion réussie !\n")

        # Commande 1 : Infos système (Uptime et Charge)
        print("--- État du Système ---")
        stdin, stdout, stderr = client.exec_command("uptime")
        print(stdout.read().decode())

        # Commande 2 : Utilisation Mémoire
        print("--- Utilisation Mémoire ---")
        stdin, stdout, stderr = client.exec_command("free -m")
        print(stdout.read().decode())

        # Commande 3 : Snapshot des processus (TOP en batch)
        print("--- Top Processus ---")
        stdin, stdout, stderr = client.exec_command("top -b -n 1 | head -n 15")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Erreur de connexion : {e}")
    finally:
        client.close()
        print("\nConnexion fermée.")

if __name__ == "__main__":
    test_ssh_monitoring(WAGO_IP, WAGO_USER, WAGO_PASS)
