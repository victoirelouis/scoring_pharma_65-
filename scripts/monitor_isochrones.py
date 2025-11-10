#!/usr/bin/env python3
"""
Moniteur de progression en temps réel pour la génération d'isochrones

Script de surveillance qui affiche la progression en temps réel,
les statistiques de performance et l'état des sauvegardes.

Usage:
    python monitor_isochrones.py          # Surveillance en continu
    python monitor_isochrones.py --once   # Affichage unique
    python monitor_isochrones.py --watch  # Mode watch (rafraîchissement auto)
"""

import pandas as pd
import json
import time
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import os
import sys

# Configuration des chemins
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "isochrones"
CACHE_DIR = BASE_DIR / "data" / "cache" / "isochrones"

# Configuration des isochrones (pour calculs)
ISOCHRONE_TYPES = ['walk_5min', 'walk_10min', 'drive_15min', 'drive_20min']


def clear_screen():
    """Efface l'écran selon l'OS"""
    os.system('cls' if os.name == 'nt' else 'clear')


def load_progress_status():
    """Charge le statut de progression"""
    status_file = OUTPUT_DIR / "progress_status.json"
    
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None


def load_results_summary():
    """Charge le résumé des résultats"""
    summary_file = OUTPUT_DIR / "isochrones_summary.csv"
    
    if summary_file.exists():
        try:
            return pd.read_csv(summary_file)
        except:
            return pd.DataFrame()
    return pd.DataFrame()


def get_backup_info():
    """Récupère les informations sur les backups"""
    backup_dir = OUTPUT_DIR / "backups"
    
    if not backup_dir.exists():
        return {'count': 0, 'latest': None, 'total_size': 0}
    
    backup_files = list(backup_dir.glob("isochrones_summary_backup_*.csv"))
    
    if not backup_files:
        return {'count': 0, 'latest': None, 'total_size': 0}
    
    # Trier par date de modification
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_backup = backup_files[0]
    
    # Calculer la taille totale
    total_size = sum(f.stat().st_size for f in backup_files)
    
    return {
        'count': len(backup_files),
        'latest': datetime.fromtimestamp(latest_backup.stat().st_mtime),
        'total_size': total_size / (1024 * 1024)  # En MB
    }


def get_output_files_info():
    """Compte les fichiers de sortie créés"""
    counts = {}
    total_size = 0
    
    for iso_type in ISOCHRONE_TYPES:
        iso_dir = OUTPUT_DIR / iso_type
        if iso_dir.exists():
            files = list(iso_dir.glob("*.geojson"))
            counts[iso_type] = len(files)
            total_size += sum(f.stat().st_size for f in files)
        else:
            counts[iso_type] = 0
    
    return counts, total_size / (1024 * 1024)  # En MB


def display_status(clear=True):
    """Affiche le statut complet"""
    if clear:
        clear_screen()
    
    print("🔍 MONITEUR ISOCHRONES - STATUT EN TEMPS RÉEL")
    print("=" * 70)
    print(f"🕒 Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Charger les données
    status = load_progress_status()
    results_df = load_results_summary()
    backup_info = get_backup_info()
    file_counts, total_size_mb = get_output_files_info()
    
    # État du traitement
    if status:
        print("📊 ÉTAT DU TRAITEMENT:")
        
        total_processed = status.get('total_processed', 0)
        total_successes = status.get('total_successes', 0)
        total_failures = status.get('total_failures', 0)
        current_batch = status.get('current_batch', 0)
        
        success_rate = (total_successes / (total_successes + total_failures)) * 100 if (total_successes + total_failures) > 0 else 0
        
        print(f"   Pharmacies traitées   : {total_processed:,}")
        print(f"   Succès total          : {total_successes:,}")
        print(f"   Échecs total          : {total_failures:,}")
        print(f"   Taux de succès        : {success_rate:.1f}%")
        print(f"   Batch actuel          : {current_batch}")
        
        # Performance
        print(f"\n⚡ PERFORMANCE:")
        pharmacies_per_min = status.get('pharmacies_per_minute', 0)
        elapsed_seconds = status.get('elapsed_seconds', 0)
        
        if elapsed_seconds > 0:
            elapsed_str = str(timedelta(seconds=int(elapsed_seconds)))
            print(f"   Vitesse actuelle      : {pharmacies_per_min:.1f} pharmacies/min")
            print(f"   Temps écoulé          : {elapsed_str}")
            
            # ETA
            estimated_completion = status.get('estimated_completion')
            if estimated_completion:
                eta = estimated_completion - time.time()
                if eta > 0:
                    eta_str = str(timedelta(seconds=int(eta)))
                    completion_time = datetime.fromtimestamp(estimated_completion)
                    print(f"   Temps restant estimé  : {eta_str}")
                    print(f"   Fin estimée           : {completion_time.strftime('%d/%m %H:%M')}")
                else:
                    print(f"   Statut                : Presque terminé !")
        
        print(f"   Dernière activité     : {datetime.fromtimestamp(status['timestamp']).strftime('%d/%m %H:%M:%S')}")
    
    else:
        print("📊 ÉTAT DU TRAITEMENT:")
        print("   ⚠️  Aucun fichier de statut trouvé")
        print("   Le traitement n'est peut-être pas démarré ou terminé")
    
    # Résumé des fichiers
    if not results_df.empty:
        print(f"\n📋 RÉSUMÉ DES DONNÉES:")
        print(f"   Entrées dans le résumé: {len(results_df):,}")
        
        # Compter les succès par type
        for iso_type in ISOCHRONE_TYPES:
            success_col = f'{iso_type}_success'
            if success_col in results_df.columns:
                successes = results_df[success_col].sum()
                total_entries = len(results_df)
                success_pct = (successes / total_entries) * 100 if total_entries > 0 else 0
                print(f"   {iso_type:<12}    : {successes:,}/{total_entries:,} ({success_pct:.1f}%)")
    
    # Fichiers de sortie
    print(f"\n📁 FICHIERS CRÉÉS:")
    total_files = sum(file_counts.values())
    print(f"   Total fichiers        : {total_files:,}")
    for iso_type, count in file_counts.items():
        print(f"   {iso_type:<12}    : {count:,} fichiers")
    print(f"   Taille totale         : {total_size_mb:.1f} MB")
    
    # Informations de sauvegarde
    print(f"\n💾 SAUVEGARDES:")
    if backup_info['count'] > 0:
        print(f"   Fichiers de backup    : {backup_info['count']}")
        print(f"   Dernier backup        : {backup_info['latest'].strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"   Taille des backups    : {backup_info['total_size']:.1f} MB")
        
        # Ancienneté du dernier backup
        time_since_backup = datetime.now() - backup_info['latest']
        if time_since_backup.total_seconds() < 300:  # < 5 min
            print(f"   État                  : ✅ Récent ({int(time_since_backup.total_seconds())}s)")
        elif time_since_backup.total_seconds() < 1800:  # < 30 min
            print(f"   État                  : ⚠️  Moyennement récent ({int(time_since_backup.total_seconds()/60)}min)")
        else:
            print(f"   État                  : ❌ Ancien ({int(time_since_backup.total_seconds()/3600)}h)")
    else:
        print(f"   Aucun backup trouvé   : ⚠️  Risque de perte de données")
    
    # Vérification de la cohérence
    print(f"\n🔍 VÉRIFICATIONS:")
    
    # Cohérence entre statut et fichiers
    if status and not results_df.empty:
        status_processed = status.get('total_processed', 0)
        file_processed = len(results_df)
        
        if abs(status_processed - file_processed) <= 50:  # Tolérance de 50
            print(f"   Cohérence données     : ✅ OK ({status_processed} vs {file_processed})")
        else:
            print(f"   Cohérence données     : ⚠️  Écart détecté ({status_processed} vs {file_processed})")
    
    # Vérification des dossiers
    missing_dirs = []
    for iso_type in ISOCHRONE_TYPES:
        if not (OUTPUT_DIR / iso_type).exists():
            missing_dirs.append(iso_type)
    
    if missing_dirs:
        print(f"   Dossiers manquants    : ⚠️  {', '.join(missing_dirs)}")
    else:
        print(f"   Structure dossiers    : ✅ OK")
    
    print("=" * 70)
    
    # Conseils
    if status:
        current_time = time.time()
        last_update = status.get('timestamp', 0)
        time_since_update = current_time - last_update
        
        if time_since_update > 600:  # > 10 minutes
            print("💡 Le traitement semble inactif depuis plus de 10 minutes")
            print("   Vérifiez si le processus est toujours en cours")
        elif total_processed == 0:
            print("💡 Le traitement n'a pas encore commencé")
            print("   Lancez: python scripts\\generate_isochrones.py")
        elif success_rate < 50:
            print("💡 Taux de succès faible détecté")
            print("   Vérifiez les logs pour identifier les problèmes")


def monitor_continuous(interval=30):
    """Surveillance continue avec rafraîchissement"""
    print("🔍 Démarrage du moniteur en temps réel...")
    print(f"Rafraîchissement toutes les {interval} secondes")
    print("Appuyez sur Ctrl+C pour arrêter")
    print()
    
    try:
        while True:
            display_status(clear=True)
            print(f"\n⏱️  Prochain rafraîchissement dans {interval}s (Ctrl+C pour arrêter)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 Moniteur arrêté par l'utilisateur")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Moniteur de progression des isochrones')
    parser.add_argument('--once', action='store_true', help='Affichage unique (pas de rafraîchissement)')
    parser.add_argument('--watch', action='store_true', help='Mode surveillance continue')
    parser.add_argument('--interval', type=int, default=30, help='Intervalle de rafraîchissement en secondes (défaut: 30)')
    parser.add_argument('--no-clear', action='store_true', help='Ne pas effacer l\'écran')
    
    args = parser.parse_args()
    
    if args.once:
        display_status(clear=not args.no_clear)
    elif args.watch:
        monitor_continuous(args.interval)
    else:
        # Mode par défaut : affichage unique
        display_status(clear=not args.no_clear)


if __name__ == "__main__":
    main()