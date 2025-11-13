"""
Script de calibration COMPLET des paniers moyens
=================================================

Version COMPLÈTE utilisant TOUTES les variables disponibles :
- Population par âge détaillée (65-74, 75-84, 85+)
- Population par genre ET âge (hommes/femmes séparés)
- DEUX périmètres : drive_10min ET walk_5min
- 6 catégories touristiques détaillées
- Variables contextuelles riches (zone, tourisme, montagne/littoral)

Auteur : Victoire LOUIS
Date : Novembre 2025
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_PATH = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
OUTPUT_PATH = BASE_PATH / "data" / "intermediaire" / "output"

# Fichier d'entrée
INPUT_FILE = BASE_PATH / "intermediaire" / "output" / "pharmacies_features_complet.csv"

# Fichiers de sortie
OUTPUT_COEF = BASE_PATH / "intermediaire" / "output" / "coefficients_paniers_complets.json"
OUTPUT_REPORT = BASE_PATH / "intermediaire" / "output" / "rapport_calibration_complet.txt"

# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

print("="*80)
print("CALIBRATION COMPLETE - PANIERS MOYENS PAR AGE ET GENRE")
print("="*80)

df = pd.read_csv(INPUT_FILE)

# Filtrer pharmacies avec CA complet
df_calib = df[
    df['ca_total'].notna() & 
    df['ca_ethique'].notna() & 
    df['ca_conseil'].notna()
].copy()

print(f"\nPharmacies total : {len(df):,}")
print(f"Pharmacies pour calibration : {len(df_calib):,}")

# Calculer CA_delta
df_calib['ca_delta'] = (
    df_calib['ca_total'] - 
    df_calib['ca_ethique'] - 
    df_calib['ca_conseil']
)

print(f"\nStatistiques CA_delta :")
print(f"  Min : {df_calib['ca_delta'].min():,.0f}EUR")
print(f"  Mediane : {df_calib['ca_delta'].median():,.0f}EUR")
print(f"  Moyenne : {df_calib['ca_delta'].mean():,.0f}EUR")
print(f"  Max : {df_calib['ca_delta'].max():,.0f}EUR")

# =============================================================================
# SEGMENTATION CONTEXTUELLE ENRICHIE
# =============================================================================

print("\n" + "="*80)
print("SEGMENTATION CONTEXTUELLE")
print("="*80)

# Segment 1 : Type de zone (5 catégories)
df_calib['segment_zone'] = df_calib['type_zone'].fillna('rural')

# Segment 2 : Zone touristique (6 catégories détaillées)
if 'type_zone_touristique' in df_calib.columns:
    df_calib['segment_tourisme'] = df_calib['type_zone_touristique'].fillna('non_touristique')
else:
    df_calib['segment_tourisme'] = 'non_touristique'

# Segment 3 : Montagne/Littoral
df_calib['segment_geo_specifique'] = 'standard'
if 'flag_commune_montagne' in df_calib.columns:
    df_calib.loc[df_calib['flag_commune_montagne'] == 1, 'segment_geo_specifique'] = 'montagne'
if 'flag_commune_littoral' in df_calib.columns:
    df_calib.loc[df_calib['flag_commune_littoral'] == 1, 'segment_geo_specifique'] = 'littoral'

# Segment 4 : Zone isolée
if 'zone_isolee' in df_calib.columns:
    df_calib['segment_isolement'] = df_calib['zone_isolee'].fillna(0).astype(int).astype(str)
else:
    df_calib['segment_isolement'] = '0'

# Segment 5 : Densité de seniors
df_calib['segment_densite_seniors'] = pd.qcut(
    df_calib['pop_65_plus_drive_10min'],
    q=3,
    labels=['densite_faible', 'densite_moyenne', 'densite_forte'],
    duplicates='drop'
)

print(f"\nRepartition des segments :")
print(f"\n  Type de zone ({df_calib['segment_zone'].nunique()} categories) :")
for val, count in df_calib['segment_zone'].value_counts().items():
    print(f"    {val:20s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Tourisme ({df_calib['segment_tourisme'].nunique()} categories) :")
for val, count in df_calib['segment_tourisme'].value_counts().items():
    print(f"    {val:25s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Geographie specifique ({df_calib['segment_geo_specifique'].nunique()} categories) :")
for val, count in df_calib['segment_geo_specifique'].value_counts().items():
    print(f"    {val:20s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Isolement ({df_calib['segment_isolement'].nunique()} categories) :")
for val, count in df_calib['segment_isolement'].value_counts().items():
    status = 'Non isole' if val == '0' else 'Isole'
    print(f"    {status:20s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Densite seniors ({df_calib['segment_densite_seniors'].nunique()} categories) :")
for val, count in df_calib['segment_densite_seniors'].value_counts().items():
    print(f"    {val:20s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

# =============================================================================
# FONCTION CALIBRATION
# =============================================================================

def calibrer_modele(df, perimetre='drive_10min'):
    """Calibre les modèles par âge et par genre×âge pour un périmètre donné"""
    
    print(f"\n{'='*80}")
    print(f"CALIBRATION PERIMETRE : {perimetre.upper()}")
    print("="*80)
    
    resultats_perimetre = {'modele_age': {}, 'modele_genre_age': {}}
    
    # =========================================================================
    # MODÈLE 1 : PAR ÂGE (sans distinction genre)
    # =========================================================================
    
    print(f"\n--- MODELE 1 : CALIBRATION PAR TRANCHE D'AGE ({perimetre}) ---")
    
    # Variables de population
    X_age = df[[
        f'pop_totale_{perimetre}',
        f'pop_65_74_{perimetre}',
        f'pop_75_84_{perimetre}',
        f'pop_85_plus_{perimetre}'
    ]].copy()
    
    # Calculer pop_0_64
    X_age[f'pop_0_64_{perimetre}'] = (
        X_age[f'pop_totale_{perimetre}'] - 
        X_age[f'pop_65_74_{perimetre}'] -
        X_age[f'pop_75_84_{perimetre}'] -
        X_age[f'pop_85_plus_{perimetre}']
    )
    
    X_age_final = X_age[[
        f'pop_0_64_{perimetre}',
        f'pop_65_74_{perimetre}',
        f'pop_75_84_{perimetre}',
        f'pop_85_plus_{perimetre}'
    ]]
    
    # --- CA_ETHIQUE ---
    print(f"\n1. CA_ETHIQUE (Medicaments prescrits)")
    
    y_ethique = df['ca_ethique']
    model_ethique = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_ethique.fit(X_age_final, y_ethique)
    
    panier_age_ethique = {
        'intercept': float(model_ethique.intercept_),
        '0-64': float(model_ethique.coef_[0]),
        '65-74': float(model_ethique.coef_[1]),
        '75-84': float(model_ethique.coef_[2]),
        '85+': float(model_ethique.coef_[3])
    }
    
    y_pred = model_ethique.predict(X_age_final)
    r2 = r2_score(y_ethique, y_pred)
    mae = mean_absolute_error(y_ethique, y_pred)
    
    print(f"  Paniers annuels (EUR/pers/an) :")
    for age, panier in panier_age_ethique.items():
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an  ({panier/12:>8,.2f}EUR/mois)")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_age']['ca_ethique'] = {
        'paniers_annuels': panier_age_ethique,
        'paniers_mensuels': {k: v/12 for k, v in panier_age_ethique.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    # --- CA_CONSEIL ---
    print(f"\n2. CA_CONSEIL (Parapharmacie)")
    
    y_conseil = df['ca_conseil']
    model_conseil = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_conseil.fit(X_age_final, y_conseil)
    
    panier_age_conseil = {
        'intercept': float(model_conseil.intercept_),
        '0-64': float(model_conseil.coef_[0]),
        '65-74': float(model_conseil.coef_[1]),
        '75-84': float(model_conseil.coef_[2]),
        '85+': float(model_conseil.coef_[3])
    }
    
    y_pred = model_conseil.predict(X_age_final)
    r2 = r2_score(y_conseil, y_pred)
    mae = mean_absolute_error(y_conseil, y_pred)
    
    print(f"  Paniers annuels (EUR/pers/an) :")
    for age, panier in panier_age_conseil.items():
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an  ({panier/12:>8,.2f}EUR/mois)")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_age']['ca_conseil'] = {
        'paniers_annuels': panier_age_conseil,
        'paniers_mensuels': {k: v/12 for k, v in panier_age_conseil.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    # --- CA_DELTA ---
    print(f"\n3. CA_DELTA (Materiel medical, orthopédie, etc.)")
    
    y_delta = df['ca_delta']
    model_delta = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_delta.fit(X_age_final, y_delta)
    
    panier_age_delta = {
        'intercept': float(model_delta.intercept_),
        '0-64': float(model_delta.coef_[0]),
        '65-74': float(model_delta.coef_[1]),
        '75-84': float(model_delta.coef_[2]),
        '85+': float(model_delta.coef_[3])
    }
    
    y_pred = model_delta.predict(X_age_final)
    r2 = r2_score(y_delta, y_pred)
    mae = mean_absolute_error(y_delta, y_pred)
    
    print(f"  Paniers annuels (EUR/pers/an) :")
    for age, panier in panier_age_delta.items():
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an  ({panier/12:>8,.2f}EUR/mois)")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_age']['ca_delta'] = {
        'paniers_annuels': panier_age_delta,
        'paniers_mensuels': {k: v/12 for k, v in panier_age_delta.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    # =========================================================================
    # MODÈLE 2 : PAR GENRE ET ÂGE
    # =========================================================================
    
    print(f"\n--- MODELE 2 : CALIBRATION PAR GENRE ET TRANCHE D'AGE ({perimetre}) ---")
    
    # Variables hommes/femmes par âge
    X_genre_age = df[[
        f'pop_hommes_65_74_{perimetre}',
        f'pop_hommes_75_84_{perimetre}',
        f'pop_hommes_85_plus_{perimetre}',
        f'pop_femmes_65_74_{perimetre}',
        f'pop_femmes_75_84_{perimetre}',
        f'pop_femmes_85_plus_{perimetre}'
    ]].copy()
    
    # Ajouter pop 0-64 total
    X_genre_age[f'pop_0_64_{perimetre}'] = X_age[f'pop_0_64_{perimetre}']
    
    # --- CA_ETHIQUE par genre ---
    print(f"\n1. CA_ETHIQUE par genre et age")
    
    y_ethique = df['ca_ethique']
    model_genre_ethique = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_genre_ethique.fit(X_genre_age, y_ethique)
    
    panier_genre_ethique = {
        'intercept': float(model_genre_ethique.intercept_),
        '0-64': float(model_genre_ethique.coef_[6]),
        'homme_65-74': float(model_genre_ethique.coef_[0]),
        'homme_75-84': float(model_genre_ethique.coef_[1]),
        'homme_85+': float(model_genre_ethique.coef_[2]),
        'femme_65-74': float(model_genre_ethique.coef_[3]),
        'femme_75-84': float(model_genre_ethique.coef_[4]),
        'femme_85+': float(model_genre_ethique.coef_[5])
    }
    
    y_pred = model_genre_ethique.predict(X_genre_age)
    r2 = r2_score(y_ethique, y_pred)
    mae = mean_absolute_error(y_ethique, y_pred)
    
    print(f"  0-64 ans : {panier_genre_ethique['0-64']:>10,.2f}EUR/an")
    print(f"  HOMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'homme_{age}'
        panier = panier_genre_ethique[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  FEMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'femme_{age}'
        panier = panier_genre_ethique[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_genre_age']['ca_ethique'] = {
        'paniers_annuels': panier_genre_ethique,
        'paniers_mensuels': {k: v/12 for k, v in panier_genre_ethique.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    # --- CA_CONSEIL par genre ---
    print(f"\n2. CA_CONSEIL par genre et age")
    
    y_conseil = df['ca_conseil']
    model_genre_conseil = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_genre_conseil.fit(X_genre_age, y_conseil)
    
    panier_genre_conseil = {
        'intercept': float(model_genre_conseil.intercept_),
        '0-64': float(model_genre_conseil.coef_[6]),
        'homme_65-74': float(model_genre_conseil.coef_[0]),
        'homme_75-84': float(model_genre_conseil.coef_[1]),
        'homme_85+': float(model_genre_conseil.coef_[2]),
        'femme_65-74': float(model_genre_conseil.coef_[3]),
        'femme_75-84': float(model_genre_conseil.coef_[4]),
        'femme_85+': float(model_genre_conseil.coef_[5])
    }
    
    y_pred = model_genre_conseil.predict(X_genre_age)
    r2 = r2_score(y_conseil, y_pred)
    mae = mean_absolute_error(y_conseil, y_pred)
    
    print(f"  0-64 ans : {panier_genre_conseil['0-64']:>10,.2f}EUR/an")
    print(f"  HOMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'homme_{age}'
        panier = panier_genre_conseil[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  FEMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'femme_{age}'
        panier = panier_genre_conseil[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_genre_age']['ca_conseil'] = {
        'paniers_annuels': panier_genre_conseil,
        'paniers_mensuels': {k: v/12 for k, v in panier_genre_conseil.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    # --- CA_DELTA par genre ---
    print(f"\n3. CA_DELTA (ETHIQUE - CONSEIL) par genre et age")
    
    y_delta = df['ca_delta']
    model_genre_delta = LinearRegression(fit_intercept=True)  # AVEC intercept
    model_genre_delta.fit(X_genre_age, y_delta)
    
    panier_genre_delta = {
        'intercept': float(model_genre_delta.intercept_),
        '0-64': float(model_genre_delta.coef_[6]),
        'homme_65-74': float(model_genre_delta.coef_[0]),
        'homme_75-84': float(model_genre_delta.coef_[1]),
        'homme_85+': float(model_genre_delta.coef_[2]),
        'femme_65-74': float(model_genre_delta.coef_[3]),
        'femme_75-84': float(model_genre_delta.coef_[4]),
        'femme_85+': float(model_genre_delta.coef_[5])
    }
    
    y_pred = model_genre_delta.predict(X_genre_age)
    r2 = r2_score(y_delta, y_pred)
    mae = mean_absolute_error(y_delta, y_pred)
    
    print(f"  0-64 ans : {panier_genre_delta['0-64']:>10,.2f}EUR/an")
    print(f"  HOMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'homme_{age}'
        panier = panier_genre_delta[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  FEMMES :")
    for age in ['65-74', '75-84', '85+']:
        key = f'femme_{age}'
        panier = panier_genre_delta[key]
        print(f"    {age:8s} : {panier:>10,.2f}EUR/an")
    print(f"  R2 = {r2:.3f}  |  MAE = {mae:,.0f}EUR")
    
    resultats_perimetre['modele_genre_age']['ca_delta'] = {
        'paniers_annuels': panier_genre_delta,
        'paniers_mensuels': {k: v/12 for k, v in panier_genre_delta.items()},
        'r2': float(r2),
        'mae': float(mae)
    }
    
    return resultats_perimetre, panier_age_ethique, panier_age_conseil, panier_age_delta, panier_genre_ethique, panier_genre_conseil, panier_genre_delta

# =============================================================================
# CALIBRATION DRIVE 10MIN
# =============================================================================

(resultats_drive, panier_ethique_drive, panier_conseil_drive, panier_delta_drive,
 panier_genre_ethique_drive, panier_genre_conseil_drive, panier_genre_delta_drive) = calibrer_modele(
    df_calib, 
    'drive_10min'
)

# =============================================================================
# CALIBRATION WALK 5MIN
# =============================================================================

(resultats_walk, panier_ethique_walk, panier_conseil_walk, panier_delta_walk,
 panier_genre_ethique_walk, panier_genre_conseil_walk, panier_genre_delta_walk) = calibrer_modele(
    df_calib,
    'walk_5min'
)

# =============================================================================
# COEFFICIENTS MULTIPLICATEURS PAR SEGMENT (drive_10min)
# =============================================================================

print("\n" + "="*80)
print("COEFFICIENTS MULTIPLICATEURS PAR SEGMENT (drive_10min)")
print("="*80)

def calculer_coef_segment(df, segment_col, panier_base, y_col):
    """Calcule les coefficients multiplicateurs par segment"""
    coefficients = {}
    
    for segment in df[segment_col].unique():
        if pd.isna(segment):
            continue
            
        mask = df[segment_col] == segment
        df_seg = df[mask]
        
        if len(df_seg) < 50:
            coefficients[str(segment)] = 1.0
            continue
        
        # Prédiction avec modèle de référence
        X_seg = df_seg[[
            'pop_totale_drive_10min',
            'pop_65_74_drive_10min',
            'pop_75_84_drive_10min',
            'pop_85_plus_drive_10min'
        ]].copy()
        
        X_seg['pop_0_64_drive_10min'] = (
            X_seg['pop_totale_drive_10min'] -
            X_seg['pop_65_74_drive_10min'] -
            X_seg['pop_75_84_drive_10min'] -
            X_seg['pop_85_plus_drive_10min']
        )
        
        y_pred_ref = (
            panier_base.get('intercept', 0) +
            X_seg['pop_0_64_drive_10min'] * panier_base['0-64'] +
            X_seg['pop_65_74_drive_10min'] * panier_base['65-74'] +
            X_seg['pop_75_84_drive_10min'] * panier_base['75-84'] +
            X_seg['pop_85_plus_drive_10min'] * panier_base['85+']
        )
        
        y_reel = df_seg[y_col]
        coef = (y_reel.sum() / y_pred_ref.sum()) if y_pred_ref.sum() > 0 else 1.0
        
        coefficients[str(segment)] = float(coef)
    
    return coefficients

coefficients_segmentes = {}

# Type de zone
print("\n--- Type de zone ---")
coef_zone = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_zone', panier_ethique_drive, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_zone', panier_conseil_drive, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_zone', panier_delta_drive, 'ca_delta')
}
for ca_type, coefs in coef_zone.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:20s} : {coef:.3f}x")

coefficients_segmentes['type_zone'] = coef_zone

# Tourisme (6 catégories détaillées)
print("\n--- Tourisme (6 categories) ---")
coef_tourisme = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_tourisme', panier_ethique_drive, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_tourisme', panier_conseil_drive, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_tourisme', panier_delta_drive, 'ca_delta')
}
for ca_type, coefs in coef_tourisme.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:30s} : {coef:.3f}x")

coefficients_segmentes['tourisme'] = coef_tourisme

# Géographie spécifique
print("\n--- Montagne / Littoral ---")
coef_geo = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_ethique_drive, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_conseil_drive, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_delta_drive, 'ca_delta')
}
for ca_type, coefs in coef_geo.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:20s} : {coef:.3f}x")

coefficients_segmentes['geographie'] = coef_geo

# Isolement
print("\n--- Isolement ---")
coef_isolement = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_isolement', panier_ethique_drive, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_isolement', panier_conseil_drive, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_isolement', panier_delta_drive, 'ca_delta')
}
for ca_type, coefs in coef_isolement.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        status = 'Non isole' if zone == '0' else 'Isole'
        print(f"  {status:20s} : {coef:.3f}x")

coefficients_segmentes['isolement'] = coef_isolement

# =============================================================================
# SAUVEGARDE
# =============================================================================

print("\n" + "="*80)
print("SAUVEGARDE DES RESULTATS")
print("="*80)

resultats = {
    'drive_10min': resultats_drive,
    'walk_5min': resultats_walk,
    'coefficients_segmentes': coefficients_segmentes,
    'metadata': {
        'n_pharmacies_calibration': len(df_calib),
        'n_pharmacies_total': len(df),
        'date_calibration': pd.Timestamp.now().isoformat(),
        'perimetres': ['drive_10min', 'walk_5min'],
        'modeles': ['modele_age', 'modele_genre_age'],
        'segmentations': {
            'type_zone': df_calib['segment_zone'].nunique(),
            'tourisme': df_calib['segment_tourisme'].nunique(),
            'geographie': df_calib['segment_geo_specifique'].nunique(),
            'isolement': df_calib['segment_isolement'].nunique(),
            'densite_seniors': df_calib['segment_densite_seniors'].nunique()
        },
        'r2_moyen_drive_age': float(np.mean([
            resultats_drive['modele_age']['ca_ethique']['r2'],
            resultats_drive['modele_age']['ca_conseil']['r2'],
            resultats_drive['modele_age']['ca_delta']['r2']
        ])),
        'r2_moyen_drive_genre': float(np.mean([
            resultats_drive['modele_genre_age']['ca_ethique']['r2'],
            resultats_drive['modele_genre_age']['ca_conseil']['r2']
        ])),
        'r2_moyen_walk_age': float(np.mean([
            resultats_walk['modele_age']['ca_ethique']['r2'],
            resultats_walk['modele_age']['ca_conseil']['r2'],
            resultats_walk['modele_age']['ca_delta']['r2']
        ])),
        'r2_moyen_walk_genre': float(np.mean([
            resultats_walk['modele_genre_age']['ca_ethique']['r2'],
            resultats_walk['modele_genre_age']['ca_conseil']['r2']
        ]))
    }
}

with open(OUTPUT_COEF, 'w', encoding='utf-8') as f:
    json.dump(resultats, f, indent=2, ensure_ascii=False)

print(f"\nOK Coefficients sauvegardes : {OUTPUT_COEF}")

# Rapport texte
with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("RAPPORT DE CALIBRATION COMPLETE\n")
    f.write("="*80 + "\n\n")
    f.write(f"Date : {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Pharmacies calibration : {len(df_calib):,}\n\n")
    
    f.write("PERIMETRES :\n")
    f.write(f"  - drive_10min : R2 moyen age={resultats['metadata']['r2_moyen_drive_age']:.3f}, genre={resultats['metadata']['r2_moyen_drive_genre']:.3f}\n")
    f.write(f"  - walk_5min   : R2 moyen age={resultats['metadata']['r2_moyen_walk_age']:.3f}, genre={resultats['metadata']['r2_moyen_walk_genre']:.3f}\n\n")
    
    f.write("SEGMENTATIONS :\n")
    for seg, n_cat in resultats['metadata']['segmentations'].items():
        f.write(f"  - {seg:20s} : {n_cat} categories\n")

print(f"OK Rapport sauvegarde : {OUTPUT_REPORT}")

print("\n" + "="*80)
print("CALIBRATION TERMINEE AVEC SUCCES !")
print("="*80)
print(f"\n4 MODELES DISPONIBLES :")
print(f"   1. drive_10min par age         (R2 = {resultats['metadata']['r2_moyen_drive_age']:.3f})")
print(f"   2. drive_10min par genre+age   (R2 = {resultats['metadata']['r2_moyen_drive_genre']:.3f})")
print(f"   3. walk_5min par age           (R2 = {resultats['metadata']['r2_moyen_walk_age']:.3f})")
print(f"   4. walk_5min par genre+age     (R2 = {resultats['metadata']['r2_moyen_walk_genre']:.3f})")
print(f"\n{df_calib['segment_tourisme'].nunique()} categories touristiques utilisees")
print(f"{df_calib['segment_zone'].nunique()} categories de zones")
print("="*80 + "\n")
