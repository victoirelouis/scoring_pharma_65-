"""
Analyse des variables NON utilisees par ml_05 enrichi
Identifie les 9% de variables non exploitees

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("ANALYSE DES VARIABLES NON UTILISEES (9%)")
print("="*80)

# Charger le fichier
fichier = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")
df = pd.read_csv(fichier, nrows=1)  # Juste l'en-tete

all_columns = set(df.columns)
print(f"\nColonnes totales: {len(all_columns)}")

# Reproduire la logique de selection enrichie
features_used = []

# 1. HUBS
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

# 2. POPULATION
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

# 3. CONCURRENCE
for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
    col_conc = f'nb_pharmacies_concurrentes_{iso}'
    if col_conc in all_columns:
        features_used.append(col_conc)

if 'distance_pharmacie_plus_proche' in all_columns:
    features_used.append('distance_pharmacie_plus_proche')

# 4. DERIVEES
derived_patterns = ['ratio_', 'densite_', 'zone_']
for col in df.columns:
    if any(pattern in col for pattern in derived_patterns):
        if not any(x in col for x in ['pop_', 'nb_']) or any(x in col for x in ['ratio_', 'densite_']):
            if col not in features_used:
                features_used.append(col)

# 5. TOURISME
tourisme_patterns = ['nb_hotels_', 'nb_campings_', 'nb_residences_', 'capacite_accueil_', 'flag_commune_']
for col in df.columns:
    if any(pattern in col for pattern in tourisme_patterns):
        if col not in features_used:
            features_used.append(col)

# 6. CATEGORIELLES
categorical_features = ['type_zone', 'departement']
for cat_col in categorical_features:
    if cat_col in all_columns:
        features_used.append(f'{cat_col}_encoded')

features_used_set = set(features_used)

# Variables NON utilisees
features_not_used = all_columns - features_used_set

print(f"Features utilisees: {len(features_used_set)} (91.2%)")
print(f"Features NON utilisees: {len(features_not_used)} (8.8%)")

print(f"\n" + "="*80)
print("LISTE COMPLETE DES VARIABLES NON UTILISEES")
print("="*80)

# Categoriser
categories = {
    'ID et Identifiants': [],
    'Adresse et Geolocalisation': [],
    'CA (cibles)': [],
    'Scores (sorties du modele)': [],
    'Variables brutes (avant encoding)': [],
    'Autres': []
}

for col in sorted(features_not_used):
    if any(x in col.lower() for x in ['id_', 'id']):
        categories['ID et Identifiants'].append(col)
    elif any(x in col.lower() for x in ['latitude', 'longitude', 'adresse', 'commune', 'code_postal', 'departement']):
        categories['Adresse et Geolocalisation'].append(col)
    elif any(x in col.lower() for x in ['ca_total', 'ca_ethique', 'ca_conseil']):
        categories['CA (cibles)'].append(col)
    elif any(x in col.lower() for x in ['score_']):
        categories['Scores (sorties du modele)'].append(col)
    elif col in ['type_zone', 'departement']:
        categories['Variables brutes (avant encoding)'].append(col)
    else:
        categories['Autres'].append(col)

for cat, cols in categories.items():
    if len(cols) > 0:
        print(f"\n{cat} ({len(cols)} variables):")
        for col in sorted(cols):
            print(f"   - {col}")

print(f"\n" + "="*80)
print("ANALYSE")
print("="*80)

# Compter les vraies features perdues
vraies_features_perdues = [
    col for col in features_not_used
    if not any(x in col.lower() for x in [
        'id_', 'id', 'latitude', 'longitude', 'adresse', 'commune', 'code_postal',
        'ca_', 'score_', 'nom_'
    ])
    and col not in ['type_zone', 'departement']
]

print(f"\nVariables d'identification/geo: {len([c for c in features_not_used if any(x in c.lower() for x in ['id_', 'latitude', 'longitude', 'adresse', 'commune', 'code_postal', 'nom_'])])}")
print(f"Variables cibles (CA): {len([c for c in features_not_used if 'ca_' in c.lower()])}")
print(f"Variables categorielles brutes: {len([c for c in features_not_used if c in ['type_zone', 'departement']])}")
print(f"Scores (sorties): {len([c for c in features_not_used if 'score_' in c.lower()])}")
print(f"Vraies features perdues: {len(vraies_features_perdues)}")

if len(vraies_features_perdues) > 0:
    print(f"\n   ATTENTION Variables pertinentes non utilisees:")
    for col in sorted(vraies_features_perdues):
        print(f"      - {col}")

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

if len(vraies_features_perdues) == 0:
    print(f"\nOK Les 9% non utilises sont des variables META (ID, adresses, CA cibles, variables brutes)")
    print(f"   -> 100% des features PERTINENTES sont utilisees")
    print(f"   -> Coverage reel: 100%")
else:
    print(f"\nATTENTION {len(vraies_features_perdues)} features pertinentes non utilisees")
    print(f"   -> A ajouter au script ml_05")
