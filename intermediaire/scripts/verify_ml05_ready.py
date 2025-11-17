"""
Script de vérification avant lancement du ml_05
Vérifie que toutes les données sont prêtes

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("VERIFICATION AVANT LANCEMENT ML_05")
print("="*80)

# Chemin du fichier
fichier = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")

print(f"\n1. Verification existence fichier...")
if fichier.exists():
    print(f"   OK Fichier existe: {fichier}")
else:
    print(f"   ERREUR Fichier introuvable: {fichier}")
    exit(1)

# Charger le fichier
print(f"\n2. Chargement des donnees...")
df = pd.read_csv(fichier)
print(f"   OK {len(df):,} pharmacies x {len(df.columns)} colonnes")

# Vérifier les colonnes CA
print(f"\n3. Verification colonnes CA...")
ca_cols = ['ca_total', 'ca_ethique', 'ca_conseil']
for col in ca_cols:
    if col in df.columns:
        non_null = df[col].notna().sum()
        print(f"   OK {col:15s} : {non_null:,} valeurs non-nulles ({non_null/len(df)*100:.1f}%)")
    else:
        print(f"   ERREUR {col:15s} : MANQUANT")

# Vérifier quelques features clés
print(f"\n4. Verification features cles...")
key_features = [
    'pop_65_plus_drive_10min',
    'nb_sante_generale_drive_10min',
    'nb_pharmacies_concurrentes_drive_10min',
    'latitude',
    'longitude'
]

for feat in key_features:
    if feat in df.columns:
        print(f"   OK {feat}")
    else:
        print(f"   ERREUR {feat} MANQUANT")

# Vérifier les valeurs manquantes
print(f"\n5. Verification data quality...")
nan_count = df.isnull().sum().sum()
print(f"   Valeurs manquantes totales: {nan_count}")
if nan_count == 0:
    print(f"   OK Aucune valeur manquante")
else:
    print(f"   ATTENTION {nan_count} valeurs manquantes detectees")

# Statistiques CA
print(f"\n6. Statistiques CA...")
for col in ca_cols:
    if col in df.columns and df[col].notna().sum() > 0:
        ca_data = df[col].dropna()
        print(f"   {col:15s}:")
        print(f"      - Moyenne : {ca_data.mean():,.0f} €")
        print(f"      - Médiane : {ca_data.median():,.0f} €")
        print(f"      - Min     : {ca_data.min():,.0f} €")
        print(f"      - Max     : {ca_data.max():,.0f} €")

print(f"\n" + "="*80)
print("VERIFICATION TERMINEE")
print("="*80)
print("\nOK Le fichier est pret pour ml_05 !")
print(f"\nPour lancer ml_05, utilisez:")
print(f"   cd \"N:\\Commun_GERS\\Victoire LOUIS\\PyScore\\PROFILS DE PATIENTELE\\Git\\scoring_pharma_65-\\intermediaire\\scripts\"")
print(f"   python ml_05_score_attractivite_lightgbm.py")
