"""
Script de calibration OPTIMISÉ des paniers moyens
==================================================

Version optimisée utilisant TOUTES vos variables disponibles :
- Population par âge détaillée (65-74, 75-84, 85+)
- Population par genre ET âge (hommes/femmes séparés)
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
INPUT_FILE = OUTPUT_PATH / "pharmacies_features_complet.csv"

# Fichiers de sortie
OUTPUT_COEF = OUTPUT_PATH / "coefficients_paniers_optimises.json"
OUTPUT_REPORT = OUTPUT_PATH / "rapport_calibration_optimise.txt"

# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

print("="*80)
print("CALIBRATION OPTIMISÉE - PANIERS MOYENS PAR ÂGE ET GENRE")
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
print(f"  Min : {df_calib['ca_delta'].min():,.0f}€")
print(f"  Médiane : {df_calib['ca_delta'].median():,.0f}€")
print(f"  Moyenne : {df_calib['ca_delta'].mean():,.0f}€")
print(f"  Max : {df_calib['ca_delta'].max():,.0f}€")

# =============================================================================
# SEGMENTATION CONTEXTUELLE ENRICHIE
# =============================================================================

print("\n" + "="*80)
print("SEGMENTATION CONTEXTUELLE")
print("="*80)

# Segment 1 : Type de zone (utilise votre variable existante)
df_calib['segment_zone'] = df_calib['type_zone'].fillna('rural')

# Segment 2 : Zone touristique (utilise les 6 catégories détaillées)
if 'type_zone_touristique' in df_calib.columns:
    df_calib['segment_tourisme'] = df_calib['type_zone_touristique'].fillna('non_touristique')
else:
    df_calib['segment_tourisme'] = 'non_touristique'

# Segment 3 : Montagne/Littoral (utilise vos flags)
df_calib['segment_geo_specifique'] = 'standard'
if 'flag_commune_montagne' in df_calib.columns:
    df_calib.loc[df_calib['flag_commune_montagne'] == 1, 'segment_geo_specifique'] = 'montagne'
if 'flag_commune_littoral' in df_calib.columns:
    df_calib.loc[df_calib['flag_commune_littoral'] == 1, 'segment_geo_specifique'] = 'littoral'

# Segment 4 : Zone isolée
if 'zone_isolee' in df_calib.columns:
    df_calib['segment_isolement'] = df_calib['zone_isolee'].fillna('non_isole')
else:
    df_calib['segment_isolement'] = 'non_isole'

# Segment 5 : Densité de seniors
df_calib['segment_densite_seniors'] = pd.qcut(
    df_calib['pop_65_plus_drive_10min'],
    q=3,
    labels=['densite_faible', 'densite_moyenne', 'densite_forte'],
    duplicates='drop'
)

print(f"\nRépartition des segments :")
print(f"\n  Type de zone :")
for val, count in df_calib['segment_zone'].value_counts().items():
    print(f"    {val:15s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Tourisme :")
for val, count in df_calib['segment_tourisme'].value_counts().items():
    print(f"    {val:15s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Géographie spécifique :")
for val, count in df_calib['segment_geo_specifique'].value_counts().items():
    print(f"    {val:15s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Isolement :")
for val, count in df_calib['segment_isolement'].value_counts().items():
    print(f"    {val:15s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

print(f"\n  Densité seniors :")
for val, count in df_calib['segment_densite_seniors'].value_counts().items():
    print(f"    {val:15s} : {count:5,} ({count/len(df_calib)*100:5.1f}%)")

# =============================================================================
# CALIBRATION MODÈLE 1 : PAR ÂGE (sans distinction genre)
# =============================================================================

print("\n" + "="*80)
print("MODÈLE 1 : CALIBRATION PAR TRANCHE D'ÂGE - DRIVE 10MIN")
print("="*80)

# Variables de population DRIVE 10MIN
X_age_drive = df_calib[[
    'pop_totale_drive_10min',
    'pop_65_74_drive_10min',
    'pop_75_84_drive_10min',
    'pop_85_plus_drive_10min'
]]

# Calculer pop_0_64
X_age_drive['pop_0_64_drive_10min'] = (
    X_age_drive['pop_totale_drive_10min'] - 
    X_age_drive['pop_65_74_drive_10min'] -
    X_age_drive['pop_75_84_drive_10min'] -
    X_age_drive['pop_85_plus_drive_10min']
)

X_age_drive_final = X_age_drive[[
    'pop_0_64_drive_10min',
    'pop_65_74_drive_10min',
    'pop_75_84_drive_10min',
    'pop_85_plus_drive_10min'
]]

resultats = {
    'modele_age_drive': {}, 
    'modele_genre_age_drive': {}, 
    'modele_age_walk': {},
    'modele_genre_age_walk': {},
    'coefficients_segmentes': {}
}

# --- CA_ETHIQUE ---
print("\n--- CA_ETHIQUE (Médicaments prescrits) ---")

y_ethique = df_calib['ca_ethique']
model_ethique = LinearRegression(fit_intercept=False)
model_ethique.fit(X_age_final, y_ethique)

panier_age_ethique = {
    '0-64': float(model_ethique.coef_[0]),
    '65-74': float(model_ethique.coef_[1]),
    '75-84': float(model_ethique.coef_[2]),
    '85+': float(model_ethique.coef_[3])
}

y_pred = model_ethique.predict(X_age_final)
r2 = r2_score(y_ethique, y_pred)
mae = mean_absolute_error(y_ethique, y_pred)

print(f"\nPaniers annuels (€/pers/an) :")
for age, panier in panier_age_ethique.items():
    print(f"  {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")

print(f"\nRatios vs 0-64 ans :")
ref = panier_age_ethique['0-64']
for age, panier in panier_age_ethique.items():
    print(f"  {age:8s} : {panier/ref if ref > 0 else 0:>5.2f}x")

print(f"\nR² = {r2:.3f}  |  MAE = {mae:,.0f}€")

resultats['modele_age']['ca_ethique'] = {
    'paniers_annuels': panier_age_ethique,
    'paniers_mensuels': {k: v/12 for k, v in panier_age_ethique.items()},
    'r2': float(r2),
    'mae': float(mae)
}

# --- CA_CONSEIL ---
print("\n--- CA_CONSEIL (Parapharmacie) ---")

y_conseil = df_calib['ca_conseil']
model_conseil = LinearRegression(fit_intercept=False)
model_conseil.fit(X_age_final, y_conseil)

panier_age_conseil = {
    '0-64': float(model_conseil.coef_[0]),
    '65-74': float(model_conseil.coef_[1]),
    '75-84': float(model_conseil.coef_[2]),
    '85+': float(model_conseil.coef_[3])
}

y_pred = model_conseil.predict(X_age_final)
r2 = r2_score(y_conseil, y_pred)
mae = mean_absolute_error(y_conseil, y_pred)

print(f"\nPaniers annuels (€/pers/an) :")
for age, panier in panier_age_conseil.items():
    print(f"  {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")

print(f"\nRatios vs 0-64 ans :")
ref = panier_age_conseil['0-64']
for age, panier in panier_age_conseil.items():
    print(f"  {age:8s} : {panier/ref if ref > 0 else 0:>5.2f}x")

print(f"\nR² = {r2:.3f}  |  MAE = {mae:,.0f}€")

resultats['modele_age']['ca_conseil'] = {
    'paniers_annuels': panier_age_conseil,
    'paniers_mensuels': {k: v/12 for k, v in panier_age_conseil.items()},
    'r2': float(r2),
    'mae': float(mae)
}

# --- CA_DELTA ---
print("\n--- CA_DELTA (Matériel médical, orthopédie, etc.) ---")

y_delta = df_calib['ca_delta']
model_delta = LinearRegression(fit_intercept=False)
model_delta.fit(X_age_final, y_delta)

panier_age_delta = {
    '0-64': float(model_delta.coef_[0]),
    '65-74': float(model_delta.coef_[1]),
    '75-84': float(model_delta.coef_[2]),
    '85+': float(model_delta.coef_[3])
}

y_pred = model_delta.predict(X_age_final)
r2 = r2_score(y_delta, y_pred)
mae = mean_absolute_error(y_delta, y_pred)

print(f"\nPaniers annuels (€/pers/an) :")
for age, panier in panier_age_delta.items():
    print(f"  {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")

print(f"\nRatios vs 0-64 ans :")
ref = panier_age_delta['0-64']
for age, panier in panier_age_delta.items():
    print(f"  {age:8s} : {panier/ref if ref > 0 else 0:>5.2f}x")

print(f"\nR² = {r2:.3f}  |  MAE = {mae:,.0f}€")

resultats['modele_age']['ca_delta'] = {
    'paniers_annuels': panier_age_delta,
    'paniers_mensuels': {k: v/12 for k, v in panier_age_delta.items()},
    'r2': float(r2),
    'mae': float(mae)
}

# =============================================================================
# CALIBRATION MODÈLE 2 : PAR GENRE ET ÂGE (encore plus précis !)
# =============================================================================

print("\n" + "="*80)
print("MODÈLE 2 : CALIBRATION PAR GENRE ET TRANCHE D'ÂGE")
print("="*80)

# Variables hommes/femmes par âge (vous les avez !)
X_genre_age = df_calib[[
    'pop_hommes_65_74_drive_10min',
    'pop_hommes_75_84_drive_10min',
    'pop_hommes_85_plus_drive_10min',
    'pop_femmes_65_74_drive_10min',
    'pop_femmes_75_84_drive_10min',
    'pop_femmes_85_plus_drive_10min'
]]

# Calculer pop 0-64 (on suppose équilibre hommes/femmes)
pop_0_64_total = X_age['pop_0_64_drive_10min']
X_genre_age['pop_0_64_drive_10min'] = pop_0_64_total

# --- CA_ETHIQUE par genre ---
print("\n--- CA_ETHIQUE par genre et âge ---")

y_ethique = df_calib['ca_ethique']
model_genre_ethique = LinearRegression(fit_intercept=False)
model_genre_ethique.fit(X_genre_age, y_ethique)

panier_genre_ethique = {
    '0-64': float(model_genre_ethique.coef_[6]),  # pop_0_64
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

print(f"\nPaniers annuels (€/pers/an) :")
print(f"  0-64 ans       : {panier_genre_ethique['0-64']:>10,.2f}€/an")
print(f"\n  HOMMES :")
for age in ['65-74', '75-84', '85+']:
    key = f'homme_{age}'
    panier = panier_genre_ethique[key]
    print(f"    {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")
print(f"  FEMMES :")
for age in ['65-74', '75-84', '85+']:
    key = f'femme_{age}'
    panier = panier_genre_ethique[key]
    print(f"    {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")

print(f"\nDifférence Femmes vs Hommes (même âge) :")
for age in ['65-74', '75-84', '85+']:
    homme = panier_genre_ethique[f'homme_{age}']
    femme = panier_genre_ethique[f'femme_{age}']
    diff_pct = ((femme - homme) / homme * 100) if homme > 0 else 0
    print(f"  {age:8s} : {diff_pct:>+6.1f}%  (Femme {femme:,.0f}€ vs Homme {homme:,.0f}€)")

print(f"\nR² = {r2:.3f}  |  MAE = {mae:,.0f}€")

resultats['modele_genre_age']['ca_ethique'] = {
    'paniers_annuels': panier_genre_ethique,
    'paniers_mensuels': {k: v/12 for k, v in panier_genre_ethique.items()},
    'r2': float(r2),
    'mae': float(mae)
}

# --- CA_CONSEIL par genre ---
print("\n--- CA_CONSEIL par genre et âge ---")

y_conseil = df_calib['ca_conseil']
model_genre_conseil = LinearRegression(fit_intercept=False)
model_genre_conseil.fit(X_genre_age, y_conseil)

panier_genre_conseil = {
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

print(f"\nPaniers annuels (€/pers/an) :")
print(f"  0-64 ans       : {panier_genre_conseil['0-64']:>10,.2f}€/an")
print(f"\n  HOMMES :")
for age in ['65-74', '75-84', '85+']:
    key = f'homme_{age}'
    panier = panier_genre_conseil[key]
    print(f"    {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")
print(f"  FEMMES :")
for age in ['65-74', '75-84', '85+']:
    key = f'femme_{age}'
    panier = panier_genre_conseil[key]
    print(f"    {age:8s} : {panier:>10,.2f}€/an  ({panier/12:>8,.2f}€/mois)")

print(f"\nDifférence Femmes vs Hommes (parapharmacie) :")
for age in ['65-74', '75-84', '85+']:
    homme = panier_genre_conseil[f'homme_{age}']
    femme = panier_genre_conseil[f'femme_{age}']
    diff_pct = ((femme - homme) / homme * 100) if homme > 0 else 0
    print(f"  {age:8s} : {diff_pct:>+6.1f}%  (Femme {femme:,.0f}€ vs Homme {homme:,.0f}€)")

print(f"\nR² = {r2:.3f}  |  MAE = {mae:,.0f}€")

resultats['modele_genre_age']['ca_conseil'] = {
    'paniers_annuels': panier_genre_conseil,
    'paniers_mensuels': {k: v/12 for k, v in panier_genre_conseil.items()},
    'r2': float(r2),
    'mae': float(mae)
}

# =============================================================================
# COEFFICIENTS MULTIPLICATEURS PAR SEGMENT
# =============================================================================

print("\n" + "="*80)
print("COEFFICIENTS MULTIPLICATEURS PAR SEGMENT")
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
            'pop_0_64_drive_10min',
            'pop_65_74_drive_10min',
            'pop_75_84_drive_10min',
            'pop_85_plus_drive_10min'
        ]]
        
        # Ajouter pop_0_64 si pas présent
        if 'pop_0_64_drive_10min' not in X_seg.columns:
            X_seg['pop_0_64_drive_10min'] = (
                df_seg['pop_totale_drive_10min'] -
                df_seg['pop_65_74_drive_10min'] -
                df_seg['pop_75_84_drive_10min'] -
                df_seg['pop_85_plus_drive_10min']
            )
        
        y_pred_ref = (
            X_seg['pop_0_64_drive_10min'] * panier_base['0-64'] +
            X_seg['pop_65_74_drive_10min'] * panier_base['65-74'] +
            X_seg['pop_75_84_drive_10min'] * panier_base['75-84'] +
            X_seg['pop_85_plus_drive_10min'] * panier_base['85+']
        )
        
        y_reel = df_seg[y_col]
        coef = (y_reel.sum() / y_pred_ref.sum()) if y_pred_ref.sum() > 0 else 1.0
        
        coefficients[str(segment)] = float(coef)
    
    return coefficients

# Calculer pour chaque segment et type de CA

# Type de zone
print("\n--- Type de zone ---")
coef_zone = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_zone', panier_age_ethique, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_zone', panier_age_conseil, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_zone', panier_age_delta, 'ca_delta')
}
for ca_type, coefs in coef_zone.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:15s} : {coef:.3f}x")

resultats['coefficients_segmentes']['type_zone'] = coef_zone

# Tourisme
print("\n--- Tourisme ---")
coef_tourisme = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_tourisme', panier_age_ethique, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_tourisme', panier_age_conseil, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_tourisme', panier_age_delta, 'ca_delta')
}
for ca_type, coefs in coef_tourisme.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:20s} : {coef:.3f}x")

resultats['coefficients_segmentes']['tourisme'] = coef_tourisme

# Géographie spécifique
print("\n--- Montagne / Littoral ---")
coef_geo = {
    'ca_ethique': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_age_ethique, 'ca_ethique'),
    'ca_conseil': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_age_conseil, 'ca_conseil'),
    'ca_delta': calculer_coef_segment(df_calib, 'segment_geo_specifique', panier_age_delta, 'ca_delta')
}
for ca_type, coefs in coef_geo.items():
    print(f"\n{ca_type} :")
    for zone, coef in coefs.items():
        print(f"  {zone:15s} : {coef:.3f}x")

resultats['coefficients_segmentes']['geographie'] = coef_geo

# =============================================================================
# SAUVEGARDE
# =============================================================================

print("\n" + "="*80)
print("SAUVEGARDE DES RÉSULTATS")
print("="*80)

resultats['metadata'] = {
    'n_pharmacies_calibration': len(df_calib),
    'n_pharmacies_total': len(df),
    'date_calibration': pd.Timestamp.now().isoformat(),
    'utilise_donnees_reelles_par_age': True,
    'utilise_donnees_par_genre': True,
    'r2_moyen_modele_age': float(np.mean([
        resultats['modele_age']['ca_ethique']['r2'],
        resultats['modele_age']['ca_conseil']['r2'],
        resultats['modele_age']['ca_delta']['r2']
    ])),
    'r2_moyen_modele_genre': float(np.mean([
        resultats['modele_genre_age']['ca_ethique']['r2'],
        resultats['modele_genre_age']['ca_conseil']['r2']
    ]))
}

with open(OUTPUT_COEF, 'w', encoding='utf-8') as f:
    json.dump(resultats, f, indent=2, ensure_ascii=False)

print(f"\n✅ Coefficients sauvegardés : {OUTPUT_COEF}")

# Rapport texte
with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("RAPPORT DE CALIBRATION OPTIMISÉE\n")
    f.write("="*80 + "\n\n")
    f.write(f"Date : {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Pharmacies calibration : {len(df_calib):,}\n\n")
    f.write(f"R² moyen modèle âge : {resultats['metadata']['r2_moyen_modele_age']:.3f}\n")
    f.write(f"R² moyen modèle genre+âge : {resultats['metadata']['r2_moyen_modele_genre']:.3f}\n")

print(f"✅ Rapport sauvegardé : {OUTPUT_REPORT}")

print("\n" + "="*80)
print("CALIBRATION TERMINÉE AVEC SUCCÈS !")
print("="*80)
print(f"\n📊 Deux modèles disponibles :")
print(f"   1. Modèle par âge (R² = {resultats['metadata']['r2_moyen_modele_age']:.3f})")
print(f"   2. Modèle par genre+âge (R² = {resultats['metadata']['r2_moyen_modele_genre']:.3f})")
print(f"\n🚀 Prochaine étape : ml_09_modele_huff_distribution.py")
print("="*80 + "\n")
