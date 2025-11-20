# -*- coding: utf-8 -*-
"""
Script ml_04b_enrichir_sig_p20.py

OBJECTIF:
Enrichir le dataset ML avec les variables du SIG_P20 pour ameliorer le modele

VARIABLES AJOUTEES:
- UN : Unites vendues (volume d'activite)
- CAHT : Chiffre d'affaires total

NOTE: Le SIG_P20 contient des donnees mensuelles qu'il faut agreger par pharmacie
      Les colonnes CA_conseil et CA_ethique ne sont pas disponibles dans SIG_P20

ENTREES:
- pharmacies_features_complet.csv (dataset ML actuel, 300+ features)
- SIG_P20.CSV (donnees d'activite reelles mensuelles)

SORTIE:
- pharmacies_features_complet_sig_enriched.csv (dataset enrichi)

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
    INPUT_FILES,
    INTERMEDIATE_FILES,
    DATA_INTERMEDIATE_DIR
)

print("="*80)
print("ENRICHISSEMENT DATASET ML AVEC VARIABLES SIG_P20")
print("="*80)

# ==============================================================================
# 1. CHARGEMENT DES DONNEES
# ==============================================================================

print("\n1. CHARGEMENT DES DONNEES")
print("-" * 80)

# Dataset ML complet (sorti du ml_04)
df_ml_path = INTERMEDIATE_FILES['pharmacies_features_complet']
print(f"   Chargement : {df_ml_path.name}")

if not df_ml_path.exists():
    print(f"   ERREUR: Fichier non trouve")
    print(f"   Chemin: {df_ml_path}")
    print(f"\n   Veuillez d'abord executer ml_04_integration_complete.py")
    sys.exit(1)

df_ml = pd.read_csv(df_ml_path, sep=';' if ';' in open(df_ml_path, encoding='utf-8').readline() else ',')
print(f"   OK {len(df_ml):,} pharmacies chargees")
print(f"   OK {len(df_ml.columns):,} features actuelles")

# SIG_P20
sig_p20_path = INPUT_FILES['sig_p20']
print(f"\n   Chargement : {sig_p20_path.name}")

if not sig_p20_path.exists():
    print(f"   ERREUR: Fichier SIG_P20 non trouve")
    print(f"   Chemin: {sig_p20_path}")
    sys.exit(1)

# Tester le separateur
with open(sig_p20_path, 'r', encoding='utf-8-sig') as f:
    first_line = f.readline()
    sep = ';' if ';' in first_line else ','

df_sig = pd.read_csv(sig_p20_path, sep=sep, encoding='utf-8-sig', decimal=',')
print(f"   OK {len(df_sig):,} lignes dans SIG_P20")
print(f"   OK Colonnes: {list(df_sig.columns)}")

# ==============================================================================
# 2. ANALYSE STRUCTURE SIG_P20
# ==============================================================================

print("\n2. ANALYSE STRUCTURE SIG_P20")
print("-" * 80)

# Verifier colonnes attendues
colonnes_attendues = ['Pvactif', 'CleMoisAnnee', 'UN', 'CAHT']
colonnes_presentes = [col for col in colonnes_attendues if col in df_sig.columns]
colonnes_manquantes = [col for col in colonnes_attendues if col not in df_sig.columns]

print(f"   Colonnes presentes : {colonnes_presentes}")
if colonnes_manquantes:
    print(f"   WARN Colonnes manquantes : {colonnes_manquantes}")

# Analyser la structure temporelle
if 'CleMoisAnnee' in df_sig.columns:
    n_mois = df_sig['CleMoisAnnee'].nunique()
    mois_min = df_sig['CleMoisAnnee'].min()
    mois_max = df_sig['CleMoisAnnee'].max()
    print(f"\n   Donnees temporelles :")
    print(f"      Nombre de mois : {n_mois}")
    print(f"      Periode        : {mois_min} -> {mois_max}")

    # Pharmacies uniques
    n_pharma_sig = df_sig['Pvactif'].nunique()
    print(f"      Pharmacies SIG : {n_pharma_sig:,}")

# ==============================================================================
# 3. SELECTION ANNEE DE REFERENCE
# ==============================================================================

print("\n3. SELECTION ANNEE DE REFERENCE")
print("-" * 80)

# Prendre l'annee la plus recente complete (12 mois)
if 'CleMoisAnnee' in df_sig.columns:
    # Extraire l'annee
    df_sig['annee'] = df_sig['CleMoisAnnee'] // 100

    # Compter mois par annee
    mois_par_annee = df_sig.groupby('annee')['CleMoisAnnee'].nunique()
    print(f"   Mois par annee :")
    for annee, nb_mois in mois_par_annee.items():
        print(f"      {annee} : {nb_mois} mois")

    # Prendre la derniere annee complete (12 mois) ou la plus recente
    annees_completes = mois_par_annee[mois_par_annee >= 12].index
    if len(annees_completes) > 0:
        annee_ref = annees_completes.max()
        print(f"\n   Annee de reference : {annee_ref} (12 mois complets)")
    else:
        annee_ref = mois_par_annee.index.max()
        print(f"\n   Annee de reference : {annee_ref} (annee la plus recente, {mois_par_annee[annee_ref]} mois)")

    # Filtrer sur l'annee de reference
    df_sig_annee = df_sig[df_sig['annee'] == annee_ref].copy()
    print(f"   OK {len(df_sig_annee):,} lignes pour {annee_ref}")

# ==============================================================================
# 4. AGREGATION PAR PHARMACIE
# ==============================================================================

print("\n4. AGREGATION PAR PHARMACIE")
print("-" * 80)

# Agreger par pharmacie (somme sur tous les mois de l'annee)
agg_dict = {}
if 'UN' in df_sig_annee.columns:
    agg_dict['UN'] = 'sum'
if 'CAHT' in df_sig_annee.columns:
    agg_dict['CAHT'] = 'sum'

if len(agg_dict) == 0:
    print("   ERREUR: Aucune variable UN ou CAHT trouvee")
    sys.exit(1)

df_sig_agg = df_sig_annee.groupby('Pvactif').agg(agg_dict).reset_index()

print(f"   OK {len(df_sig_agg):,} pharmacies agregeees")
print(f"   OK Variables : {list(agg_dict.keys())}")

# Renommer Pvactif -> id_pharmacie
df_sig_agg = df_sig_agg.rename(columns={'Pvactif': 'id_pharmacie'})

# Ajouter suffixe _sig pour eviter conflits
for col in agg_dict.keys():
    df_sig_agg = df_sig_agg.rename(columns={col: f"{col}_sig"})

print(f"\n   Statistiques variables agregeees :")
for col in [f"{k}_sig" for k in agg_dict.keys()]:
    if col in df_sig_agg.columns:
        print(f"\n   {col}:")
        print(f"      Min    : {df_sig_agg[col].min():,.0f}")
        print(f"      Max    : {df_sig_agg[col].max():,.0f}")
        print(f"      Mean   : {df_sig_agg[col].mean():,.0f}")
        print(f"      Median : {df_sig_agg[col].median():,.0f}")

# ==============================================================================
# 5. FUSION AVEC DATASET ML
# ==============================================================================

print("\n5. FUSION AVEC DATASET ML")
print("-" * 80)

# Identifier la colonne ID dans df_ml
id_cols_candidates = ['id_pharmacie', 'ID_PHARMACIE', 'pharmacie_id', 'id']
id_col_ml = None

for col in id_cols_candidates:
    if col in df_ml.columns:
        id_col_ml = col
        break

if id_col_ml is None:
    print(f"   ERREUR: Colonne ID pharmacie non trouvee dans dataset ML")
    print(f"   Colonnes disponibles: {list(df_ml.columns[:20])}")
    sys.exit(1)

print(f"   Colonne ID dataset ML : {id_col_ml}")
print(f"   Colonne ID SIG_P20    : id_pharmacie")

# Fusion left join (garder toutes les pharmacies du ML)
df_enriched = df_ml.merge(
    df_sig_agg,
    left_on=id_col_ml,
    right_on='id_pharmacie',
    how='left',
    suffixes=('', '_dup')
)

print(f"\n   OK Fusion effectuee")
print(f"   OK Pharmacies totales  : {len(df_enriched):,}")
print(f"   OK Features totales    : {len(df_enriched.columns):,}")

# Supprimer colonne id_pharmacie dupliquee si necessaire
if 'id_pharmacie_dup' in df_enriched.columns:
    df_enriched = df_enriched.drop(columns=['id_pharmacie_dup'])

# ==============================================================================
# 6. ANALYSE DU MATCHING
# ==============================================================================

print("\n6. ANALYSE DU MATCHING")
print("-" * 80)

variables_sig = [f"{k}_sig" for k in agg_dict.keys()]

for var in variables_sig:
    if var in df_enriched.columns:
        n_non_null = df_enriched[var].notna().sum()
        pct = 100 * n_non_null / len(df_enriched)
        print(f"   {var:<15} : {n_non_null:>6,} / {len(df_enriched):,} ({pct:>5.1f}%)")

if len(variables_sig) > 1:
    n_complete = df_enriched[variables_sig].notna().all(axis=1).sum()
    pct_complete = 100 * n_complete / len(df_enriched)
    print(f"\n   Pharmacies avec TOUTES les variables SIG : {n_complete:,} ({pct_complete:.1f}%)")

# ==============================================================================
# 7. GESTION DES VALEURS MANQUANTES
# ==============================================================================

print("\n7. GESTION DES VALEURS MANQUANTES")
print("-" * 80)

# Imputation par mediane (approche conservative)
print("   Strategie: Imputation par mediane (approche conservative)")

for var in variables_sig:
    if var in df_enriched.columns:
        n_missing = df_enriched[var].isna().sum()
        if n_missing > 0:
            median_val = df_enriched[var].median()
            df_enriched[var] = df_enriched[var].fillna(median_val)
            print(f"   OK {var:<15} : {n_missing:>5,} valeurs imputees (mediane = {median_val:,.0f})")
        else:
            print(f"   OK {var:<15} : Aucune valeur manquante")

# ==============================================================================
# 8. NORMALISATION DES VARIABLES SIG_P20
# ==============================================================================

print("\n8. NORMALISATION DES VARIABLES SIG_P20")
print("-" * 80)

# Les variables SIG_P20 ont des echelles tres differentes des autres features
# On va creer des versions normalisees [0-1] pour la PCA

print("   Creation de versions normalisees (suffixe _norm)")

for var in variables_sig:
    if var in df_enriched.columns:
        var_norm = f"{var}_norm"

        # Min-Max normalization
        min_val = df_enriched[var].min()
        max_val = df_enriched[var].max()

        if max_val > min_val:
            df_enriched[var_norm] = (df_enriched[var] - min_val) / (max_val - min_val)
            print(f"   OK {var_norm:<20} : [{min_val:,.0f}, {max_val:,.0f}] > [0, 1]")
        else:
            df_enriched[var_norm] = 0
            print(f"   WARN {var_norm:<20} : Constante, mise a 0")

# ==============================================================================
# 9. SAUVEGARDE
# ==============================================================================

print("\n9. SAUVEGARDE")
print("-" * 80)

# Creer le repertoire de sortie si necessaire
output_dir = DATA_INTERMEDIATE_DIR / '1_etapes_pipeline'
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / 'pharmacies_features_complet_sig_enriched.csv'

df_enriched.to_csv(output_path, index=False)

print(f"   OK Fichier sauvegarde : {output_path.name}")
print(f"   OK Taille : {output_path.stat().st_size / 1024 / 1024:.1f} MB")
print(f"   OK Lignes : {len(df_enriched):,}")
print(f"   OK Colonnes : {len(df_enriched.columns):,}")

# ==============================================================================
# 10. RAPPORT DETAILLE
# ==============================================================================

print("\n10. RAPPORT DETAILLE")
print("-" * 80)

print(f"\n   Variables SIG_P20 ajoutees (annee {annee_ref}):")
for var in variables_sig:
    if var in df_enriched.columns:
        print(f"      - {var} (brute)")
        print(f"      - {var}_norm (normalisee)")

print(f"\n   Statistiques finales:")
print(f"      Features avant enrichissement : {len(df_ml.columns):,}")
print(f"      Features apres enrichissement : {len(df_enriched.columns):,}")
print(f"      Nouvelles features            : {len(df_enriched.columns) - len(df_ml.columns):,}")

print("\n" + "="*80)
print("ENRICHISSEMENT SIG_P20 TERMINE")
print("="*80)
print(f"\nProchaine etape: Utiliser le fichier enrichi dans ml_05")
print(f"   Fichier: {output_path}")
print(f"\n   Commande: python 1_pipeline_ml/ml_05_score_attractivite_pca.py")
print(f"\n   NOTE: Les variables CA_conseil et CA_ethique ne sont pas disponibles dans SIG_P20")
print(f"         Seules UN_sig et CAHT_sig ont ete ajoutees au modele")