#!/bin/sh

LOG_FILE="/root/resultats_benchmark.txt"

echo "=========================================================="
echo " 📊 MONITEUR DE RESSOURCES (Mode Analyse / Historique)"
echo "=========================================================="
echo "-> Les résultats s'affichent en direct ET sont sauvegardés dans le fichier :"
echo "   $LOG_FILE"
echo "-> Appuyez sur Ctrl+C pour arrêter l'enregistrement."
echo ""

# Écriture de l'en-tête dans le fichier de log uniquement (pour Excel/Rapport)
echo "HEURE      | CPU(Load) | REPOS_CPU | RAM_SYS           | BD_MAX  | CHIRPSTACK | DB_POSTGRES | MOSQUITTO | REDIS" > $LOG_FILE

while true; do
    TIME=$(date '+%H:%M:%S')
    
    # 1. CPU (Load + Extrait de l'Inactivité)
    CUR_LOAD=$(awk '{print $1}' /proc/loadavg)
    IDLE_CPU=$(top -bn1 | grep -E -m1 -i "cpu.*id" | awk '{print $8}')
    [ -z "$IDLE_CPU" ] && IDLE_CPU=$(top -bn1 | grep -i "cpu" | grep -o "[0-9]*% idle" | awk '{print $1}')
    [ -z "$IDLE_CPU" ] && IDLE_CPU="??%"
    
    # 2. RAM Système Globale (Correction Busybox KB -> MB)
    MEM_FREE_KB=$(free | awk '/Mem/ {print $4}')
    MEM_USED_KB=$(free | awk '/Mem/ {print $3}')
    MEM_TOTAL_KB=$(free | awk '/Mem/ {print $2}')
    MEM_FREE=$((MEM_FREE_KB / 1024))
    MEM_USED=$((MEM_USED_KB / 1024))
    MEM_TOTAL=$((MEM_TOTAL_KB / 1024))
    
    # 3. Taille Disque Postgres
    DB_SIZE=$(du -sk /media/docker/lora-stack/postgres 2>/dev/null | awk '{print $1}')
    [ -z "$DB_SIZE" ] && DB_SIZE=0
    DB_MB=$((DB_SIZE / 1024))
    
    # 4. RAM détaillée par Docker et Stats complètes
    DSTATS_RAW=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}")
    DSTATS_MEM=$(docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" 2>/dev/null)
    
    CS_MEM=$(echo "$DSTATS_MEM" | awk '/lora-chirpstack/ {print $2}')
    PG_MEM=$(echo "$DSTATS_MEM" | awk '/lora-postgres/ {print $2}')
    MQ_MEM=$(echo "$DSTATS_MEM" | awk '/lora-mosquitto/ {print $2}')
    RD_MEM=$(echo "$DSTATS_MEM" | awk '/lora-redis/ {print $2}')
    
    # Valeurs par défaut
    [ -z "$CS_MEM" ] && CS_MEM="??"
    [ -z "$PG_MEM" ] && PG_MEM="??"
    [ -z "$MQ_MEM" ] && MQ_MEM="??"
    [ -z "$RD_MEM" ] && RD_MEM="??"

    # Écriture invisible de l'historique horizontal dans le fichier 
    LINE="[$TIME] | L = $CUR_LOAD | id: $IDLE_CPU | $MEM_USED / $MEM_TOTAL Mo | ${DB_MB}Mo | CS:$CS_MEM | PG:$PG_MEM | MQ:$MQ_MEM | RE:$RD_MEM"
    echo "$LINE" >> $LOG_FILE
    
    # AFFICHAGE INTERACTIF FAÇON DOCKER STATS
    clear
    echo "========================================================================="
    echo " 🚀 MONITEUR DE RESSOURCES WAGO — ACTUALISÉ À $TIME"
    echo "========================================================================="
    echo " 💾 SYSTEME:"
    echo "    Charge CPU (Load)    : $CUR_LOAD"
    echo "    Repos libre CPU (Id) : $IDLE_CPU"
    echo "    RAM Utilisée         : $MEM_USED Mo / $MEM_TOTAL Mo (Libre: $MEM_FREE Mo)"
    echo "    BDD Postgres Disque  : $DB_MB Mo"
    echo "-------------------------------------------------------------------------"
    echo "$DSTATS_RAW"
    echo "========================================================================="
    echo " (Les données sont également sauvées dans $LOG_FILE. Ctrl+C pour quitter)"
    
    sleep 2
done
