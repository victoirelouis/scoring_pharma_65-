"""
Script de monitoring pour suivre la progression du traitement
"""
import pandas as pd
from pathlib import Path
import time
from datetime import datetime, timedelta

checkpoint_file = Path("intermediaire/output/checkpoint_hubs.csv")
total_pharmacies = 19307

print("=" * 80)
print("MONITORING PROGRESSION - ml_01_prepare_hubs_par_isochrone.py")
print("=" * 80)
print()

while True:
    if checkpoint_file.exists():
        try:
            df = pd.read_csv(checkpoint_file)
            n_done = len(df)
            pct = (n_done / total_pharmacies) * 100
            remaining = total_pharmacies - n_done
            
            # ETA basé sur la vitesse
            if n_done > 10:
                # Estimer temps par pharmacie (environ 1.5 sec)
                time_per_pharma = 1.5  # secondes
                eta_seconds = remaining * time_per_pharma
                eta = timedelta(seconds=int(eta_seconds))
                
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Progression: {n_done:,}/{total_pharmacies:,} ({pct:.1f}%) | Restant: {remaining:,} | ETA: {eta}", end="", flush=True)
            else:
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Progression: {n_done:,}/{total_pharmacies:,} ({pct:.1f}%) | Calcul ETA...", end="", flush=True)
        
        except Exception as e:
            print(f"\rErreur lecture checkpoint: {e}", end="", flush=True)
    else:
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Checkpoint non trouvé, traitement en cours...", end="", flush=True)
    
    time.sleep(5)  # Mise à jour toutes les 5 secondes
