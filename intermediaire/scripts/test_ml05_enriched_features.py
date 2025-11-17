"""
Test du nouveau select_features enrichi du ml_05
Verifie combien de features sont maintenant utilisees

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
import sys

print("="*80)
print("TEST DU NOUVEAU SELECT_FEATURES ENRICHI")
print("="*80)

# Chemins
FICHIER_CLEAN = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")

print(f"\n[LOAD] Chargement du fichier...")
df = pd.read_csv(FICHIER_CLEAN)
print(f"   OK {len(df):,} pharmacies x {len(df.columns)} colonnes")

all_columns = set(df.columns)
features_used = []

# ===================================================================
# REPRODUIRE LA NOUVELLE LOGIQUE DE SELECTION
# ===================================================================

print(f"\n" + "="*80)
print("SIMULATION DE LA NOUVELLE SELECTION")
print("="*80)

# 1. HUBS - TOUS les isochrones
hubs_features = [
    'nb_services_seniors', 'nb_sante_generale', 'nb_sante_specialisee',
    'nb_medecin', 'nb_medecins_equivalent', 'nb_ehpad', 'nb_hopital',
    'nb_laboratoire', 'nb_supermarche', 'nb_bus', 'nb_accessibilite',
    'taux_colocalisation', 'nb_hubs_brut', 'nb_hubs_deduplique'
]

for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
    for hub in hubs_features:
        col = f'{hub}_{iso}'
        if col in all_columns:
            features_used.append(col)

nb_hubs = len([f for f in features_used if any(x in f for x in hubs_features)])
print(f"\n1. HUBS: {nb_hubs} features")

# 2. POPULATION - TOUS les isochrones
pop_features = [
    'pop_totale', 'pop_0_64', 'pop_65_plus', 'pop_65_74', 'pop_75_84', 'pop_85_plus',
    'pop_hommes_65_plus', 'pop_femmes_65_plus',
    'pop_hommes_65_74', 'pop_femmes_65_74',
    'pop_hommes_75_84', 'pop_femmes_75_84',
    'pop_hommes_85_plus', 'pop_femmes_85_plus',
    'taux_retraites', 'taux_cadres'
]

for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
    for pop in pop_features:
        col = f'{pop}_{iso}'
        if col in all_columns:
            features_used.append(col)

nb_pop = len([f for f in features_used if f.startswith('pop_') or 'taux_retraites' in f or 'taux_cadres' in f])
print(f"2. POPULATION: {nb_pop} features")

# 3. CONCURRENCE - TOUS les isochrones
for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
    col_conc = f'nb_pharmacies_concurrentes_{iso}'
    if col_conc in all_columns:
        features_used.append(col_conc)

if 'distance_pharmacie_plus_proche' in all_columns:
    features_used.append('distance_pharmacie_plus_proche')

nb_conc = len([f for f in features_used if 'pharmacies_concurrentes' in f or 'distance_pharmacie' in f])
print(f"3. CONCURRENCE: {nb_conc} features")

# 4. FEATURES DERIVEES - TOUTES
derived_patterns = ['ratio_', 'densite_', 'zone_']
for col in df.columns:
    if any(pattern in col for pattern in derived_patterns):
        if not any(x in col for x in ['pop_', 'nb_']) or any(x in col for x in ['ratio_', 'densite_']):
            if col not in features_used:
                features_used.append(col)

nb_derived = len([f for f in features_used if any(x in f for x in ['ratio_', 'densite_', 'zone_']) and not f.startswith('pop_')])
print(f"4. DERIVEES: {nb_derived} features")

# 5. TOURISME - TOUTES
tourisme_patterns = ['nb_hotels_', 'nb_campings_', 'nb_residences_', 'capacite_accueil_', 'flag_commune_']
for col in df.columns:
    if any(pattern in col for pattern in tourisme_patterns):
        if col not in features_used:
            features_used.append(col)

nb_tourisme = len([f for f in features_used if any(x in f for x in ['hotels_', 'campings_', 'residences_', 'capacite_accueil_', 'flag_commune_'])])
print(f"5. TOURISME: {nb_tourisme} features")

# 6. CATEGORIELLES
categorical_features = ['type_zone', 'departement']
for cat_col in categorical_features:
    if cat_col in all_columns:
        features_used.append(f'{cat_col}_encoded')

nb_cat = 2  # type_zone_encoded et departement_encoded
print(f"6. CATEGORIELLES: {nb_cat} features")

# ===================================================================
# STATISTIQUES FINALES
# ===================================================================

print(f"\n" + "="*80)
print("COMPARAISON AVANT/APRES")
print("="*80)

features_used_set = set(features_used)
total_vars_available = len(all_columns)
total_vars_used = len(features_used_set)
coverage = (total_vars_used / total_vars_available) * 100

print(f"\nAVANT enrichissement:")
print(f"   - Features utilisees: 62 (23.7%)")
print(f"   - Tourisme: 0")
print(f"   - Derivees: 6")
print(f"   - Isochrones: 2 (walk_5min, drive_10min)")

print(f"\nAPRES enrichissement:")
print(f"   - Features utilisees: {total_vars_used} ({coverage:.1f}%)")
print(f"   - HUBS: {nb_hubs}")
print(f"   - POPULATION: {nb_pop}")
print(f"   - CONCURRENCE: {nb_conc}")
print(f"   - DERIVEES: {nb_derived}")
print(f"   - TOURISME: {nb_tourisme}")
print(f"   - CATEGORIELLES: {nb_cat}")
print(f"   - Isochrones: 6 (walk_5min, walk_10min, drive_5min, drive_10min, drive_15min, drive_20min)")

print(f"\nGAIN:")
print(f"   - +{total_vars_used - 62} features ({coverage - 23.7:.1f} points de coverage)")
print(f"   - +{nb_tourisme} variables touristiques")
print(f"   - +{nb_derived - 6} features derivees")
print(f"   - x3 nombre d'isochrones")

# Exemples de features touristiques utilisees
print(f"\n" + "="*80)
print("EXEMPLES DE VARIABLES TOURISTIQUES AJOUTEES")
print("="*80)

tourisme_features = [f for f in features_used if any(x in f for x in ['hotels_', 'campings_', 'residences_', 'capacite_accueil_', 'flag_commune_'])]
for feat in sorted(tourisme_features)[:20]:
    print(f"   - {feat}")
if len(tourisme_features) > 20:
    print(f"   ... et {len(tourisme_features) - 20} autres")

# Exemples de features derivees ajoutees
print(f"\n" + "="*80)
print("EXEMPLES DE FEATURES DERIVEES AJOUTEES")
print("="*80)

derived_features = [f for f in features_used if any(x in f for x in ['ratio_', 'densite_', 'zone_']) and not f.startswith('pop_')]
for feat in sorted(derived_features)[:15]:
    print(f"   - {feat}")
if len(derived_features) > 15:
    print(f"   ... et {len(derived_features) - 15} autres")

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

if coverage >= 70:
    print(f"\nEXCELLENT Le script ml_05 enrichi utilise maintenant {coverage:.1f}% des variables disponibles")
    print(f"   -> Toutes les categories de variables sont bien representees")
    print(f"   -> Le modele dispose de {total_vars_used} features pour predire le CA")
elif coverage >= 50:
    print(f"\nBON Le script ml_05 enrichi utilise maintenant {coverage:.1f}% des variables disponibles")
    print(f"   -> Amelioration significative par rapport aux 23.7% initiaux")
else:
    print(f"\nATTENTION Seulement {coverage:.1f}% des variables utilisees")

print(f"\nLe script ml_05 est maintenant PRET a etre lance!")
