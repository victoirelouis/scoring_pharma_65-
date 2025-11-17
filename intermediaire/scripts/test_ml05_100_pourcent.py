"""
Test FINAL du select_features enrichi avec TOUTES les corrections
Verifie si on atteint 100% de coverage des features pertinentes

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("TEST FINAL - COVERAGE 100% DES FEATURES PERTINENTES")
print("="*80)

# Chemins
FICHIER_CLEAN = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")

print(f"\n[LOAD] Chargement du fichier...")
df = pd.read_csv(FICHIER_CLEAN, nrows=1)  # Juste l'en-tete
print(f"   OK {len(df.columns)} colonnes")

all_columns = set(df.columns)
features_used = []

# ===================================================================
# REPRODUIRE LA NOUVELLE LOGIQUE AVEC TOUTES LES CORRECTIONS
# ===================================================================

print(f"\n" + "="*80)
print("SIMULATION AVEC CORRECTIONS")
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

# Distance (avec variantes _x et _y)
for dist_col in ['distance_pharmacie_plus_proche', 'distance_pharmacie_plus_proche_x', 'distance_pharmacie_plus_proche_y']:
    if dist_col in all_columns and dist_col not in features_used:
        features_used.append(dist_col)

nb_conc = len([f for f in features_used if 'pharmacies_concurrentes' in f or 'distance_pharmacie' in f])
print(f"3. CONCURRENCE: {nb_conc} features")

# 4. FEATURES DERIVEES - TOUTES avec corrections
derived_patterns = ['ratio_', 'densite_', 'zone_', 'concurrence_par_', 'delta', 'voisins_']
for col in df.columns:
    if any(pattern in col for pattern in derived_patterns):
        if not any(x in col for x in ['pop_', 'nb_']) or any(x in col for x in ['ratio_', 'densite_', 'concurrence_par_']):
            if col not in features_used:
                features_used.append(col)

nb_derived = len([f for f in features_used if any(x in f for x in ['ratio_', 'densite_', 'zone_', 'concurrence_par_', 'delta', 'voisins_']) and not f.startswith('pop_')])
print(f"4. DERIVEES: {nb_derived} features")

# 5. TOURISME - TOUTES avec nb_total_hebergements
tourisme_patterns = ['nb_hotels_', 'nb_campings_', 'nb_residences_', 'capacite_accueil_', 'flag_commune_', 'nb_total_hebergements_']
for col in df.columns:
    if any(pattern in col for pattern in tourisme_patterns):
        if col not in features_used:
            features_used.append(col)

nb_tourisme = len([f for f in features_used if any(x in f for x in ['hotels_', 'campings_', 'residences_', 'capacite_accueil_', 'flag_commune_', 'hebergements_'])])
print(f"5. TOURISME: {nb_tourisme} features")

# 6. CATEGORIELLES
categorical_features = ['type_zone', 'departement']
for cat_col in categorical_features:
    if cat_col in all_columns:
        features_used.append(f'{cat_col}_encoded')

nb_cat = 2
print(f"6. CATEGORIELLES: {nb_cat} features")

# ===================================================================
# STATISTIQUES FINALES
# ===================================================================

print(f"\n" + "="*80)
print("ANALYSE DES VARIABLES NON UTILISEES")
print("="*80)

features_used_set = set(features_used)
features_not_used = all_columns - features_used_set

total_vars_available = len(all_columns)
total_vars_used = len(features_used_set)
coverage = (total_vars_used / total_vars_available) * 100

print(f"\nVariables totales: {total_vars_available}")
print(f"Variables utilisees: {total_vars_used} ({coverage:.1f}%)")
print(f"Variables NON utilisees: {len(features_not_used)} ({100-coverage:.1f}%)")

# Analyser les variables non utilisees
non_utilisees_meta = []
non_utilisees_pertinentes = []

meta_patterns = ['id_', 'nom_', 'adresse', 'commune', 'code_postal', 'latitude', 'longitude', 'ca_', 'score_']

for col in features_not_used:
    if any(x in col.lower() for x in meta_patterns) or col in ['type_zone', 'departement']:
        non_utilisees_meta.append(col)
    else:
        non_utilisees_pertinentes.append(col)

print(f"\nVariables META non utilisees (normales): {len(non_utilisees_meta)}")
for col in sorted(non_utilisees_meta):
    print(f"   - {col}")

if len(non_utilisees_pertinentes) > 0:
    print(f"\nVariables PERTINENTES non utilisees: {len(non_utilisees_pertinentes)}")
    for col in sorted(non_utilisees_pertinentes):
        print(f"   - {col}")
else:
    print(f"\nVariables PERTINENTES non utilisees: 0")

# ===================================================================
# CONCLUSION
# ===================================================================

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

coverage_features_pertinentes = (total_vars_used / (total_vars_available - len(non_utilisees_meta))) * 100

print(f"\nCoverage brut: {coverage:.1f}%")
print(f"Coverage features pertinentes: {coverage_features_pertinentes:.1f}%")

if len(non_utilisees_pertinentes) == 0:
    print(f"\nEXCELLENT 100% des features PERTINENTES sont utilisees!")
    print(f"   -> Les {len(non_utilisees_meta)} variables non utilisees sont des variables META")
    print(f"   -> (ID, adresses, CA cibles, variables brutes avant encoding)")
else:
    print(f"\nATTENTION {len(non_utilisees_pertinentes)} features pertinentes manquent encore")

print(f"\n" + "="*80)
print("RESUME")
print("="*80)
print(f"   - HUBS              : {nb_hubs:3d} features")
print(f"   - POPULATION        : {nb_pop:3d} features")
print(f"   - CONCURRENCE       : {nb_conc:3d} features")
print(f"   - DERIVEES          : {nb_derived:3d} features")
print(f"   - TOURISME          : {nb_tourisme:3d} features")
print(f"   - CATEGORIELLES     : {nb_cat:3d} features")
print(f"   - TOTAL             : {total_vars_used:3d} features")
