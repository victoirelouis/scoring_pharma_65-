# -*- coding: utf-8 -*-
"""
Script ml_04c_ajouter_ca_delta_norm.py

OBJECTIF:
Ajouter CA_delta et normaliser les 4 variables CA pour le modele PCA

VARIABLES AJOUTEES:
- ca_delta : CA total - CA_ethique - CA_conseil (CA residuel)
- ca_total_norm, ca_ethique_norm, ca_conseil_norm, ca_delta_norm (normalises [0-1])

ENTREES:
- pharmacies_features_complet.csv (ou pharmacies_features_complet_sig_enriched.csv)

SORTIE:
- pharmacies_features_complet_ca_enriched.csv (dataset avec CA_delta et versions normalisees)

AUTEUR: Pipeline ML Pharmacies 65+
DATE: 2025-01-20
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Ajouter le chemin du module de config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_ml import (
    INTERMEDIATE_FILES,
    DATA_INTERMEDIATE_DIR
)

print("="*80)
print("AJOUT CA_DELTA ET NORMALISATION DES VARIABLES CA")
print("="*80)

# ==============================================================================
# 1. CHARGEMENT DES DONNEES
# ==============================================================================

print("\n1. CHARGEMENT DES DONNEES")
print("-" * 80)

# Essayer le fichier enrichi SIG d'abord, sinon le fichier standard
enriched_sig_file = DATA_INTERMEDIATE_DIR / '1_etapes_pipeline' / 'pharmacies_features_complet_sig_enriched.csv'

if enriched_sig_file.exists():
    df_ml_path = enriched_sig_file
    print(f"   Utilisation fichier enrichi SIG : {df_ml_path.name}")
else:
    df_ml_path = INTERMEDIATE_FILES['pharmacies_features_complet']
    print(f"   Utilisation fichier standard : {df_ml_path.name}")

df_ml = pd.read_csv(df_ml_path)
print(f"   OK {len(df_ml):,} pharmacies chargees")
print(f"   OK {len(df_ml.columns):,} features actuelles")

# ==============================================================================
# 2. VERIFICATION COLONNES CA
# ==============================================================================

print("\n2. VERIFICATION COLONNES CA")
print("-" * 80)

colonnes_ca = ['ca_total', 'ca_ethique', 'ca_conseil']
colonnes_presentes = [col for col in colonnes_ca if col in df_ml.columns]
colonnes_manquantes = [col for col in colonnes_ca if col not in df_ml.columns]

print(f"   Colonnes presentes : {colonnes_presentes}")
if colonnes_manquantes:
    print(f"   ERREUR Colonnes manquantes : {colonnes_manquantes}")
    print(f"\n   Les colonnes CA doivent etre presentes dans le dataset")
    sys.exit(1)

# Verifier les valeurs non nulles
for col in colonnes_ca:
    n_non_null = df_ml[col].notna().sum()
    pct = 100 * n_non_null / len(df_ml)
    print(f"   {col:<15} : {n_non_null:>6,} / {len(df_ml):,} ({pct:>5.1f}%)")

# ==============================================================================
# 3. CALCUL CA_DELTA
# ==============================================================================

print("\n3. CALCUL CA_DELTA")
print("-" * 80)

df_ml['ca_delta'] = df_ml['ca_total'] - df_ml['ca_ethique'] - df_ml['ca_conseil']

print(f"   OK CA_delta calcule")
print(f"\n   Statistiques CA_delta:")
print(f"      Min    : {df_ml['ca_delta'].min():,.0f} euros")
print(f"      Max    : {df_ml['ca_delta'].max():,.0f} euros")
print(f"      Mean   : {df_ml['ca_delta'].mean():,.0f} euros")
print(f"      Median : {df_ml['ca_delta'].median():,.0f} euros")

# Verifier les valeurs negatives
n_negatifs = (df_ml['ca_delta'] < 0).sum()
if n_negatifs > 0:
    print(f"\n   ATTENTION: {n_negatifs} pharmacies avec CA_delta negatif")
    print(f"   Ces valeurs seront mises a 0 pour la normalisation")
    df_ml['ca_delta'] = df_ml['ca_delta'].clip(lower=0)

# ==============================================================================
# 4. NORMALISATION DES VARIABLES CA
# ==============================================================================

print("\n4. NORMALISATION DES VARIABLES CA")
print("-" * 80)

print("   Creation de versions normalisees [0-1] (suffixe _norm)")

variables_ca = ['ca_total', 'ca_ethique', 'ca_conseil', 'ca_delta']

for var in variables_ca:
    var_norm = f"{var}_norm"

    # Min-Max normalization
    min_val = df_ml[var].min()
    max_val = df_ml[var].max()

    if max_val > min_val:
        df_ml[var_norm] = (df_ml[var] - min_val) / (max_val - min_val)
        print(f"   OK {var_norm:<20} : [{min_val:,.0f}, {max_val:,.0f}] > [0, 1]")
    else:
        df_ml[var_norm] = 0
        print(f"   WARN {var_norm:<20} : Constante, mise a 0")

# ==============================================================================
# 5. SAUVEGARDE
# ==============================================================================

print("\n5. SAUVEGARDE")
print("-" * 80)

# Creer le repertoire de sortie si necessaire
output_dir = DATA_INTERMEDIATE_DIR / '1_etapes_pipeline'
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / 'pharmacies_features_complet_ca_enriched.csv'

df_ml.to_csv(output_path, index=False)

print(f"   OK Fichier sauvegarde : {output_path.name}")
print(f"   OK Taille : {output_path.stat().st_size / 1024 / 1024:.1f} MB")
print(f"   OK Lignes : {len(df_ml):,}")
print(f"   OK Colonnes : {len(df_ml.columns):,}")

# ==============================================================================
# 6. RAPPORT DETAILLE
# ==============================================================================

print("\n6. RAPPORT DETAILLE")
print("-" * 80)

print(f"\n   Variables CA ajoutees:")
for var in variables_ca:
    print(f"      - {var} (brute)")
    print(f"      - {var}_norm (normalisee)")

print(f"\n   Statistiques finales:")
print(f"      Features avant enrichissement : {len(pd.read_csv(df_ml_path).columns):,}")
print(f"      Features apres enrichissement : {len(df_ml.columns):,}")
print(f"      Nouvelles features            : {len(df_ml.columns) - len(pd.read_csv(df_ml_path).columns):,}")

print("\n" + "="*80)
print("ENRICHISSEMENT CA TERMINE")
print("="*80)
print(f"\nProchaine etape: Utiliser le fichier enrichi dans ml_05")
print(f"   Fichier: {output_path}")
print(f"\n   Commande: python 1_pipeline_ml/ml_05_score_attractivite_pca.py")