#!/usr/bin/env python3
"""
Gestionnaire de batchs pour la génération d'isochrones

Utilitaire pour analyser, nettoyer et gérer les batchs d'isochrones.
Permet de voir l'état des batchs, nettoyer le cache, reprendre des batchs spécifiques.

Usage:
    python manage_isochrone_batches.py --status        # Voir l'état
    python manage_isochrone_batches.py --clean-cache   # Nettoyer le cache
    python manage_isochrone_batches.py --reset-batch 5 # Reset batch 5
    python manage_isochrone_batches.py --stats         # Statistiques détaillées
"""

import pandas as pd
import json
import time
from pathlib import Path
import argparse
import shutil
from datetime import datetime, timedelta
import sys

# Configuration des chemins
BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "data" / "cache" / "isochrones"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "isochrones"


def load_batch_metadata():
    """Charge les métadonnées des batchs"""
    metadata_file = CACHE_DIR / "batches" / "batch_metadata.csv"
    if metadata_file.exists():
        return pd.read_csv(metadata_file)
    return pd.DataFrame()


def load_batch_progress():
    """Charge le progrès des batchs"""
    progress_file = CACHE_DIR / "batches" / "batch_progress.jsonl"
    progress = {}
    
    if progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    batch_id = entry['batch_id']
                    progress[batch_id] = {
                        'completed': entry['completed'],
                        'error': entry.get('error'),
                        'timestamp': entry['timestamp']
                    }
        except Exception as e:
            print(f"⚠️  Erreur lecture progrès: {e}")
    
    return progress


def show_batch_status():
    """Affiche l'état des batchs"""
    print("📊 ÉTAT DES BATCHS D'ISOCHRONES")
    print("=" * 50)
    
    # Charger les métadonnées et progrès
    metadata = load_batch_metadata()
    progress = load_batch_progress()
    
    if metadata.empty:
        print("❌ Aucune métadonnée de batch trouvée")
        print("   Lancez d'abord: python generate_isochrones.py")
        return
    
    total_batches = len(metadata)
    completed_batches = sum(1 for p in progress.values() if p['completed'])
    failed_batches = sum(1 for p in progress.values() if not p['completed'] and p.get('error'))
    pending_batches = total_batches - completed_batches - failed_batches
    
    print(f"📦 Total batchs        : {total_batches:,}")
    print(f"✅ Complétés          : {completed_batches:,} ({completed_batches/total_batches*100:.1f}%)")
    print(f"❌ Échecs             : {failed_batches:,} ({failed_batches/total_batches*100:.1f}%)")
    print(f"⏳ En attente         : {pending_batches:,} ({pending_batches/total_batches*100:.1f}%)")
    
    print(f"\n📍 DÉTAIL PAR BATCH:")
    print("-" * 80)
    print(f"{'ID':>3} | {'Taille':>6} | {'Cluster':>7} | {'État':>10} | {'Dernière activité'}")
    print("-" * 80)
    
    for idx, batch in metadata.iterrows():
        batch_id = int(batch['batch_id'])
        size = int(batch['size'])
        cluster_id = int(batch['cluster_id'])
        
        if batch_id in progress:
            status = progress[batch_id]
            if status['completed']:
                state = "✅ Terminé"
                color = ""
            elif status.get('error'):
                state = "❌ Échec"
                color = ""
            else:
                state = "🔄 En cours"
                color = ""
            
            last_activity = datetime.fromtimestamp(status['timestamp']).strftime("%d/%m %H:%M")
        else:
            state = "⏳ Attente"
            color = ""
            last_activity = "N/A"
        
        print(f"{batch_id:3d} | {size:6d} | {cluster_id:7d} | {state:>10} | {last_activity}")
    
    print("-" * 80)
    
    # Statistiques des clusters
    if not metadata.empty:
        print(f"\n🗺️  RÉPARTITION GÉOGRAPHIQUE:")
        cluster_stats = metadata.groupby('cluster_id').agg({
            'size': ['sum', 'count'],
            'lat_center': 'mean',
            'lon_center': 'mean'
        }).round(3)
        
        cluster_stats.columns = ['total_pharmacies', 'nb_batches', 'lat_center', 'lon_center']
        print(cluster_stats.head(10))


def show_detailed_stats():
    """Affiche des statistiques détaillées"""
    print("📊 STATISTIQUES DÉTAILLÉES")
    print("=" * 50)
    
    # Taille du cache
    if CACHE_DIR.exists():
        cache_size = sum(f.stat().st_size for f in CACHE_DIR.rglob('*') if f.is_file())
        cache_size_mb = cache_size / (1024 * 1024)
        print(f"💾 Taille du cache    : {cache_size_mb:.1f} MB")
        
        # Nombre de graphes en cache
        graphs_dir = CACHE_DIR / "graphs"
        if graphs_dir.exists():
            nb_graphs = len(list(graphs_dir.glob("*.pkl")))
            print(f"🗺️  Graphes en cache   : {nb_graphs:,}")
    
    # Taille des isochrones
    if OUTPUT_DIR.exists():
        total_files = 0
        total_size = 0
        
        for iso_type in ['walk_5min', 'walk_10min', 'drive_15min', 'drive_20min']:
            iso_dir = OUTPUT_DIR / iso_type
            if iso_dir.exists():
                files = list(iso_dir.glob("*.geojson"))
                size = sum(f.stat().st_size for f in files)
                total_files += len(files)
                total_size += size
                
                print(f"📄 {iso_type:<12} : {len(files):,} fichiers, {size/(1024*1024):.1f} MB")
        
        print(f"📁 Total isochrones  : {total_files:,} fichiers, {total_size/(1024*1024):.1f} MB")
    
    # Analyse temporelle
    progress = load_batch_progress()
    if progress:
        timestamps = [p['timestamp'] for p in progress.values()]
        if timestamps:
            first_time = min(timestamps)
            last_time = max(timestamps)
            duration = last_time - first_time
            
            print(f"\n⏱️  CHRONOLOGIE:")
            print(f"   Premier batch    : {datetime.fromtimestamp(first_time).strftime('%d/%m/%Y %H:%M')}")
            print(f"   Dernier batch    : {datetime.fromtimestamp(last_time).strftime('%d/%m/%Y %H:%M')}")
            print(f"   Durée totale     : {str(timedelta(seconds=int(duration)))}")


def clean_cache():
    """Nettoie le cache des graphes"""
    print("🧹 NETTOYAGE DU CACHE")
    print("=" * 30)
    
    if not CACHE_DIR.exists():
        print("❌ Aucun cache trouvé")
        return
    
    # Compter les fichiers avant
    graphs_dir = CACHE_DIR / "graphs"
    if graphs_dir.exists():
        files_before = list(graphs_dir.glob("*.pkl"))
        print(f"📁 Graphes en cache : {len(files_before):,}")
        
        if files_before:
            # Supprimer les fichiers
            for file in files_before:
                file.unlink()
            
            print(f"✅ {len(files_before):,} fichiers de cache supprimés")
        else:
            print("ℹ️  Cache déjà vide")
    else:
        print("ℹ️  Dossier de cache inexistant")


def reset_batch(batch_id):
    """Reset un batch spécifique pour le retraiter"""
    print(f"🔄 RESET DU BATCH {batch_id}")
    print("=" * 30)
    
    # Charger les progrès
    progress = load_batch_progress()
    
    if batch_id not in progress:
        print(f"❌ Batch {batch_id} introuvable")
        return
    
    # Marquer comme non complété
    progress_file = CACHE_DIR / "batches" / "batch_progress.jsonl"
    
    # Ajouter une entrée de reset
    reset_entry = {
        'batch_id': batch_id,
        'timestamp': time.time(),
        'completed': False,
        'error': None,
        'reset': True
    }
    
    with open(progress_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(reset_entry) + '\n')
    
    print(f"✅ Batch {batch_id} marqué pour retraitement")
    print(f"   Lancez: python generate_isochrones.py --resume-batch {batch_id}")


def clean_failed_outputs():
    """Nettoie les fichiers de sortie des batchs échoués"""
    print("🧹 NETTOYAGE DES FICHIERS ÉCHOUÉS")
    print("=" * 40)
    
    progress = load_batch_progress()
    failed_batches = [bid for bid, status in progress.items() 
                     if not status['completed'] and status.get('error')]
    
    if not failed_batches:
        print("ℹ️  Aucun batch échoué trouvé")
        return
    
    print(f"🔍 {len(failed_batches)} batchs échoués détectés")
    
    # Cette fonctionnalité nécessiterait de connaître quelles pharmacies
    # appartiennent à quels batchs, ce qui nécessite plus de métadonnées
    print("⚠️  Fonctionnalité à implémenter : mapping batch -> pharmacies")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Gestionnaire de batchs d\'isochrones')
    parser.add_argument('--status', action='store_true', help='Afficher l\'état des batchs')
    parser.add_argument('--stats', action='store_true', help='Statistiques détaillées')
    parser.add_argument('--clean-cache', action='store_true', help='Nettoyer le cache des graphes')
    parser.add_argument('--reset-batch', type=int, help='Reset un batch spécifique')
    parser.add_argument('--clean-failed', action='store_true', help='Nettoyer les fichiers des batchs échoués')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        # Aucun argument, afficher l'aide
        parser.print_help()
        return
    
    print("🔧 GESTIONNAIRE DE BATCHS D'ISOCHRONES")
    print("=" * 50)
    print()
    
    if args.status:
        show_batch_status()
        print()
    
    if args.stats:
        show_detailed_stats()
        print()
    
    if args.clean_cache:
        clean_cache()
        print()
    
    if args.reset_batch is not None:
        reset_batch(args.reset_batch)
        print()
    
    if args.clean_failed:
        clean_failed_outputs()
        print()


if __name__ == "__main__":
    main()