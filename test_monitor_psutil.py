import psutil
import datetime
import os

def generate_report(filename="rapport_psutil.txt"):
    print(f"Extraction des données système via psutil...")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write(f"RAPPORT DE PERFORMANCE PSUTIL\n")
        f.write(f"Date/Heure : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n\n")

        # CPU
        f.write("[1] CHARGE CPU\n")
        cpu_usage = psutil.cpu_percent(interval=1)
        f.write(f"Utilisation globale : {cpu_usage}%\n")
        f.write(f"Nombre de cœurs logiques : {psutil.cpu_count()}\n")
        f.write(f"Fréquence CPU : {psutil.cpu_freq().current:.2f} MHz\n\n")

        # RAM
        f.write("[2] MÉMOIRE VIVE\n")
        mem = psutil.virtual_memory()
        f.write(f"Total : {mem.total / (1024**3):.2f} GB\n")
        f.write(f"Utilisé : {mem.used / (1024**3):.2f} GB ({mem.percent}%)\n")
        f.write(f"Libre : {mem.available / (1024**3):.2f} GB\n\n")

        # PROCESSUS
        f.write("[3] TOP 15 PROCESSUS (Trié par CPU %)\n")
        f.write(f"{'PID':<8} {'Nom':<25} {'CPU%':<10} {'MEM%':<10}\n")
        f.write("-" * 55 + "\n")
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # On trie par CPU
        processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:15]
        
        for p in processes:
            f.write(f"{p['pid']:<8} {p['name'][:25]:<25} {p['cpu_percent']:<10} {p['memory_percent']:0.2f}\n")

    print(f"Terminé. Rapport enregistré dans : {os.path.abspath(filename)}")

if __name__ == "__main__":
    generate_report()
