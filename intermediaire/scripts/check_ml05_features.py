"""
Vérifie quelles variables du fichier master sont utilisées/non utilisées par ml_05

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("ANALYSE DES FEATURES UTILISEES PAR ML_05")
print("="*80)

# Charger le fichier
fichier = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")
df = pd.read_csv(fichier, nrows=1)  # Lire juste l'en-tête

all_columns = set(df.columns)
print(f"\nColonnes totales dans le fichier master: {len(all_columns)}")

# Reproduire la logique de sélection de ml_05
features_used = []

# 1. HUBS
hubs_features = [
    'nb_services_seniors', 'nb_sante_generale', 'nb_sante_specialisee',
    'nb_medecin', 'nb_medecins_equivalent', 'nb_ehpad', 'nb_hopital',
    'nb_laboratoire', 'nb_supermarche', 'nb_bus', 'nb_accessibilite',
    'taux_colocalisation', 'nb_hubs_brut', 'nb_hubs_deduplique'
]

for iso in ['walk_5min', 'drive_10min']:
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

for iso in ['drive_10min', 'walk_5min']:
    for pop in pop_features:
        col = f'{pop}_{iso}'
        if col in all_columns:
            features_used.append(col)

# 3. CONCURRENCE
concurrence_features = [
    'nb_pharmacies_concurrentes_drive_10min',
    'nb_pharmacies_concurrentes_walk_5min',
    'distance_pharmacie_plus_proche'
]
features_used.extend([f for f in concurrence_features if f in all_columns])

# 4. DERIVEES
derived_features = [
    'ratio_seniors_walk_5min', 'ratio_seniors_drive_10min',
    'ratio_femmes_hommes_65_walk_5min',
    'densite_hubs_sante_par_1000_seniors_walk',
    'concurrence_par_1000_seniors_drive',
    'zone_isolee'
]
features_used.extend([f for f in derived_features if f in all_columns])

# 5. TOURISME
tourisme_features = [
    'indice_touristique', 'categorie_touristique', 'affluence_estivale',
    'affluence_hivernale', 'capacite_accueil_totale'
]
features_used.extend([f for f in tourisme_features if f in all_columns])

# 6. CATEGORIQUES
categorical_features = ['type_zone', 'departement']
for cat_col in categorical_features:
    if cat_col in all_columns:
        features_used.append(f'{cat_col}_encoded')  # Sera créé par le script

features_used_set = set(features_used)

print(f"Features utilisees par ml_05: {len(features_used_set)}")

# Variables NON utilisées
features_not_used = all_columns - features_used_set

# Exclure les variables évidentes (ID, nom, CA, etc.)
exclude_patterns = ['id_', 'nom_', 'ca_', 'score_', 'latitude', 'longitude', 'code_postal', 'commune', 'adresse']
features_not_used_relevant = [
    col for col in features_not_used
    if not any(pattern in col.lower() for pattern in exclude_patterns)
]

print(f"\n" + "="*80)
print("VARIABLES NON UTILISEES (pertinentes)")
print("="*80)
print(f"Total: {len(features_not_used_relevant)} variables")

if len(features_not_used_relevant) > 0:
    print("\nVariables NON utilisees par categorie:")

    # Catégoriser
    categories = {
        'Population autres isochrones': [],
        'Hubs autres isochrones': [],
        'Concurrence autres isochrones': [],
        'Tourisme': [],
        'Features derivees manquantes': [],
        'Autres': []
    }

    for col in sorted(features_not_used_relevant):
        if 'pop_' in col and any(iso in col for iso in ['walk_10min', 'drive_5min', 'drive_15min', 'drive_20min']):
            categories['Population autres isochrones'].append(col)
        elif 'nb_' in col and any(iso in col for iso in ['walk_10min', 'drive_5min', 'drive_15min', 'drive_20min']):
            categories['Hubs autres isochrones'].append(col)
        elif 'pharmacies_concurrentes' in col and any(iso in col for iso in ['walk_10min', 'drive_5min', 'drive_15min', 'drive_20min']):
            categories['Concurrence autres isochrones'].append(col)
        elif any(x in col for x in ['hotel', 'camping', 'residence', 'capacite_accueil', 'flag_commune', 'densite_touristique']):
            categories['Tourisme'].append(col)
        elif any(x in col for x in ['ratio_', 'densite_', 'zone_']):
            categories['Features derivees manquantes'].append(col)
        else:
            categories['Autres'].append(col)

    for cat, cols in categories.items():
        if len(cols) > 0:
            print(f"\n{cat} ({len(cols)} variables):")
            for col in cols[:10]:  # Afficher max 10 par catégorie
                print(f"   - {col}")
            if len(cols) > 10:
                print(f"   ... et {len(cols)-10} autres")

print(f"\n" + "="*80)
print("RECOMMANDATIONS")
print("="*80)

# Vérifier les features touristiques manquantes
tourisme_vars_available = [col for col in all_columns if any(x in col for x in ['hotel', 'camping', 'residence', 'capacite_accueil', 'flag_commune'])]
tourisme_vars_used = [col for col in features_used if any(x in col for x in ['hotel', 'camping', 'residence', 'capacite_accueil', 'flag_commune'])]

print(f"\n1. VARIABLES TOURISTIQUES:")
print(f"   Disponibles dans le fichier: {len(tourisme_vars_available)}")
print(f"   Utilisees par ml_05: {len(tourisme_vars_used)}")

if len(tourisme_vars_available) > len(tourisme_vars_used):
    print(f"   RECOMMANDATION: Ajouter {len(tourisme_vars_available) - len(tourisme_vars_used)} variables touristiques a ml_05")
    print(f"   Variables touristiques non utilisees:")
    for var in sorted(set(tourisme_vars_available) - set(tourisme_vars_used))[:15]:
        print(f"      - {var}")

# Vérifier les features dérivées manquantes
derived_vars_available = [col for col in all_columns if any(x in col for x in ['ratio_', 'densite_']) and not any(x in col for x in ['pop_', 'nb_'])]
derived_vars_used = [col for col in features_used if any(x in col for x in ['ratio_', 'densite_'])]

print(f"\n2. FEATURES DERIVEES:")
print(f"   Disponibles dans le fichier: {len(derived_vars_available)}")
print(f"   Utilisees par ml_05: {len(derived_vars_used)}")

if len(derived_vars_available) > len(derived_vars_used):
    print(f"   RECOMMANDATION: Ajouter {len(derived_vars_available) - len(derived_vars_used)} features derivees a ml_05")
    print(f"   Features derivees non utilisees:")
    for var in sorted(set(derived_vars_available) - set(derived_vars_used))[:15]:
        print(f"      - {var}")

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

total_vars_available = len(all_columns)
total_vars_used = len(features_used_set)
coverage = (total_vars_used / total_vars_available) * 100

print(f"Coverage: {total_vars_used}/{total_vars_available} variables ({coverage:.1f}%)")

if coverage < 50:
    print(f"ATTENTION: Moins de 50% des variables sont utilisees")
    print(f"   -> Recommandation: Enrichir la selection de features dans ml_05")
elif coverage < 70:
    print(f"ATTENTION: Seulement {coverage:.1f}% des variables sont utilisees")
    print(f"   -> Recommandation: Verifier les variables touristiques et derivees")
else:
    print(f"OK: {coverage:.1f}% des variables sont utilisees")
