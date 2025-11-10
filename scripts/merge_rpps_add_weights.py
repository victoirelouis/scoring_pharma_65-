#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge RPPS CSV files from a folder into a single CSV and add speciality weights (bonus).
Saves result to data/processed/RPPS_merged_with_weights.csv

Usage:
    python scripts/merge_rpps_add_weights.py

This script will:
- Look for files in data/input/RPPS/ (CSV/TXT) or files matching *RPPS*.csv in data/input/
- Read and concatenate them (robust to different separators/encodings)
- Map 'NomSpecialiteGers' to a bonus value and add column 'bonus_attractivite'
- Save a single merged CSV
"""

import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
RPPS_SUBDIR = INPUT_DIR / "RPPS"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# RPPS specialty -> bonus mapping (keep in sync with other scripts)
RPPS_SPECIALITES = {
    'Médecine Générale': 0.18,
    'Gériatrie Gérontologie': 0.18,
    'Cardiologie': 0.16,
    'Rhumatologie': 0.16,
    'Ophtalmologie': 0.15,
    'Néphrologie': 0.15,
    'Endocrinologie Diabétologie': 0.15,
    'Neurologie': 0.14,
    'Gastro Entérologie': 0.14,
    'Dermatologie': 0.13,
    'Pneumologie': 0.13,
    'Urologie': 0.13,
    'Oncologie Cancérologie': 0.13,
    'Phlébologie Angeiologie': 0.12,
    'Hématologie': 0.12,
    'Médecine Interne': 0.12,
    'Rééducation Fonctionnelle': 0.11,
    'Allergologie': 0.11,
    'Psychiatrie': 0.10,
    'Oto Rhino Laryngologie': 0.10,
    'Chirurgie Orthopédique': 0.10,
    'Radiothérapie': 0.10,
    'Anesthésiologie Réanimation': 0.08,
    'Chirurgie Générale': 0.08,
    'Stomatologie': 0.08,
    'Gynécologie': 0.05,
    'Médecine Esthétique': 0.03,
    'Chirurgie Dentaire': 0.05
}


def find_rpps_files():
    files = []
    if RPPS_SUBDIR.exists() and RPPS_SUBDIR.is_dir():
        files = list(RPPS_SUBDIR.glob("*.csv")) + list(RPPS_SUBDIR.glob("*.txt"))
    if not files:
        # fallback to input dir
        patterns = ["RPPS.csv", "*RPPS*.csv", "*rpps*.csv", "*RPPS*.txt"]
        for p in patterns:
            files.extend(list(INPUT_DIR.glob(p)))
    # unique and sorted
    unique = []
    seen = set()
    for f in files:
        if f.exists() and f not in seen:
            unique.append(f)
            seen.add(f)
    return unique


def try_read_csv(path, nrows=None):
    # Try different encodings/separators
    encodings = ["utf-8", "latin-1", "cp1252"]
    seps = [",", ";", "|", "\t"]
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, nrows=nrows, low_memory=False)
                # require at least columns 'Rue' or 'CodePostal' or 'NomSpecialiteGers'
                if any(c in df.columns for c in ['Rue', 'CodePostal', 'NomSpecialiteGers', 'Nom']):
                    return df
            except Exception:
                continue
    # last resort
    try:
        return pd.read_csv(path, low_memory=False, nrows=nrows)
    except Exception as e:
        print(f"Impossible de lire {path}: {e}")
        return None


def main(dry=False):
    files = find_rpps_files()
    if not files:
        print("Aucun fichier RPPS trouvé dans:")
        print(f"  - {RPPS_SUBDIR}")
        print(f"  - {INPUT_DIR}")
        return 1

    print(f"Fichiers trouvés ({len(files)}):")
    for f in files:
        print(f"  - {f}")

    dfs = []
    for f in files:
        print(f"Lecture: {f.name} ...", end=" ")
        df = try_read_csv(f)
        if df is None:
            print("ÉCHEC")
            continue
        print(f"OK ({len(df):,} lignes)")
        dfs.append(df)

    if not dfs:
        print("Aucune table lue correctement.")
        return 1

    # Concatenate
    merged = pd.concat(dfs, ignore_index=True, sort=False)
    print(f"Total concaténé: {len(merged):,} lignes (avant dédoublonnage)")

    # Drop exact duplicates
    merged = merged.drop_duplicates()
    print(f"Après drop_duplicates: {len(merged):,} lignes")

    # Normalize specialty column name
    if 'NomSpecialiteGers' not in merged.columns and 'Specialite' in merged.columns:
        merged['NomSpecialiteGers'] = merged['Specialite']

    # Add bonus column
    def map_bonus(spec):
        if pd.isna(spec):
            return 0.0
        s = str(spec).strip()
        return RPPS_SPECIALITES.get(s, 0.0)

    merged['bonus_attractivite'] = merged['NomSpecialiteGers'].apply(map_bonus)

    # Sélectionner uniquement les colonnes essentielles
    colonnes_essentielles = [
        'CodeRPPS', 'Nom', 'Prenom', 'NomSpecialiteGers',
        'Rue', 'CodePostal', 'Ville', 
        'latitude', 'longitude', 'bonus_attractivite'
    ]
    
    # Ne garder que les colonnes qui existent
    colonnes_a_garder = [c for c in colonnes_essentielles if c in merged.columns]
    merged = merged[colonnes_a_garder]
    
    print(f"\nColonnes conservées: {', '.join(colonnes_a_garder)}")

    # Save
    out_file = OUTPUT_DIR / 'RPPS_merged_with_weights.csv'
    if dry:
        print(f"Dry-run: ne sauvegarde pas. would save to {out_file}")
    else:
        merged.to_csv(out_file, index=False, encoding='utf-8')
        print(f"Sauvegardé: {out_file} ({len(merged):,} lignes)")

    # Summary
    counts = merged['bonus_attractivite'].value_counts().sort_index()
    print("\nRépartition des poids (bonus_attractivite):")
    print(counts.to_string())
    return 0


if __name__ == '__main__':
    dry = False
    if len(sys.argv) > 1 and sys.argv[1] in ('--dry', '-n'):
        dry = True
    sys.exit(main(dry=dry))
