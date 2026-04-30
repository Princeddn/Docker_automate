from dotenv import load_dotenv
import subprocess
import os
import platform
load_dotenv()

def capture_top_snapshot(filename="rapport_top_batch.txt"):
    print(f"Tentative de capture via la commande 'top'...")
    
    # Vérification de l'OS (top n'existe pas nativement sur Windows)
    if platform.system() == "Windows":
        print("ERREUR : La commande 'top' n'est pas disponible sur Windows.")
        print("Si vous testez sur Windows, utilisez le script 'test_monitor_psutil.py'.")
        print("Ce script est conçu pour être exécuté sur le WAGO (Linux) ou via WSL.")
        return

    try:
        # -b : Batch mode (permet l'export vers un fichier)
        # -n 1 : capture un seul instantané
        resultat = subprocess.check_output(['top', '-b', '-n', '1']).decode('utf-8')
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- SNAPSHOT 'TOP' (MODE BATCH) ---\n")
            f.write(resultat)
        
        print(f"Terminé. Rapport enregistré dans : {os.path.abspath(filename)}")
    
    except Exception as e:
        print(f"Erreur lors de l'exécution de top : {e}")

if __name__ == "__main__":
    capture_top_snapshot()
