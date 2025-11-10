#!/usr/bin/env python3
"""
Fusionner les pharmacies sources et le résumé nettoyé des isochrones.
Produit :
 - data/processed/isochrones/isochrones_master_with_missing.csv (tout)
 - data/processed/isochrones/isochrones_missing_enriched.csv (seulement missing)
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PHARM_FILE = BASE / 'data' / 'input' / 'data_cleaning' / 'pharmacies_final.csv'
PROCESSED_FILE = BASE / 'data' / 'processed' / 'isochrones' / 'isochrones_summary_clean.csv'
OUT_DIR = BASE / 'data' / 'processed' / 'isochrones'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def norm_id(x):
    if pd.isna(x):
        return x
    s = str(x)
    if s.endswith('.0'):
        s = s[:-2]
    return s

def main():
    print('Lecture des fichiers...')
    df_pharm = pd.read_csv(PHARM_FILE, sep=';', dtype=str)
    df_proc = pd.read_csv(PROCESSED_FILE, dtype=str)

    # Normaliser id columns
    df_pharm['id_pharmacie'] = df_pharm['id_pharmacie'].astype(str)
    df_proc['id_pharmacie'] = df_proc['id_pharmacie'].astype(str).apply(lambda x: x.rstrip('.0'))

    # Merge left (toutes les pharmacies sources)
    # Pour éviter collision de colonnes, prefixer les colonnes du processed
    proc_prefix = 'proc_'
    df_proc_pref = df_proc.add_prefix(proc_prefix)
    df_proc_pref = df_proc_pref.rename(columns={proc_prefix + 'id_pharmacie': 'id_pharmacie'})

    df_master = df_pharm.merge(df_proc_pref, on='id_pharmacie', how='left')

    # Status
    def status_row(r):
        # If any proc walk_5min_file not null or success True -> processed
        if pd.notna(r.get('proc_walk_5min_file')) and r.get('proc_walk_5min_file') != '':
            return 'processed'
        # or if any success flag True
        for col in ['proc_walk_5min_success','proc_walk_10min_success','proc_drive_15min_success','proc_drive_20min_success']:
            if col in r and str(r.get(col)).lower() == 'true':
                return 'processed'
        return 'missing'

    df_master['processing_status'] = df_master.apply(status_row, axis=1)

    # Export master CSV using semicolon (consistent with source)
    out_master = OUT_DIR / 'isochrones_master_with_missing.csv'
    df_master.to_csv(out_master, index=False, sep=';')

    # Export only missing enriched
    df_missing = df_master[df_master['processing_status'] == 'missing'].copy()
    out_missing = OUT_DIR / 'isochrones_missing_enriched.csv'
    df_missing.to_csv(out_missing, index=False, sep=';')

    # Print summary
    total = len(df_master)
    processed = (df_master['processing_status'] == 'processed').sum()
    missing = (df_master['processing_status'] == 'missing').sum()
    print(f'Total pharmacies source: {total}')
    print(f'Processed: {processed}')
    print(f'Missing: {missing}')
    print('Fichiers écrits:')
    print(str(out_master))
    print(str(out_missing))

if __name__ == '__main__':
    main()
