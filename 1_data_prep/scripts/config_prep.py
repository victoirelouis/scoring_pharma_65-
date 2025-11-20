"""
Configuration centralisée pour la préparation des données (Phase 1)

Ce fichier contient tous les chemins et paramètres pour les scripts de préparation :
- Pharmacies
- Hubs médicaux
- Isochrones
- Enrichissement INSEE
- Validation

Auteur: Pipeline Data Prep
Date: 2025-11-20
"""

from pathlib import Path

# ============================================================================
# CHEMINS DES FICHIERS
# ============================================================================

# Répertoire racine du projet
PROJECT_ROOT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")

# Répertoires Phase 1
DATA_PREP_ROOT = PROJECT_ROOT / "1_data_prep"
INPUT_DIR = DATA_PREP_ROOT / "input"
OUTPUT_DIR = DATA_PREP_ROOT / "output"
CACHE_DIR = DATA_PREP_ROOT / "cache"
SCRIPTS_DIR = DATA_PREP_ROOT / "scripts"

# Créer les répertoires s'ils n'existent pas
for directory in [INPUT_DIR, OUTPUT_DIR, CACHE_DIR, SCRIPTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Sous-répertoires OUTPUT
# ----------------------------------------------------------------------------

# Isochrones (répertoires détaillés)
ISOCHRONES_WALK_5MIN = OUTPUT_DIR / 'isochrones' / 'walk_5min'
ISOCHRONES_WALK_10MIN = OUTPUT_DIR / 'isochrones' / 'walk_10min'
ISOCHRONES_DRIVE_5MIN = OUTPUT_DIR / 'isochrones' / 'drive_5min'
ISOCHRONES_DRIVE_10MIN = OUTPUT_DIR / 'isochrones' / 'drive_10min'
ISOCHRONES_DRIVE_15MIN = OUTPUT_DIR / 'isochrones' / 'drive_15min'
ISOCHRONES_DRIVE_20MIN = OUTPUT_DIR / 'isochrones' / 'drive_20min'

# RPPS geocodés
RPPS_GEOCODE_DIR = OUTPUT_DIR / 'rpps_geocode'

# Créer les sous-répertoires output
for directory in [
    ISOCHRONES_WALK_5MIN,
    ISOCHRONES_WALK_10MIN,
    ISOCHRONES_DRIVE_5MIN,
    ISOCHRONES_DRIVE_10MIN,
    ISOCHRONES_DRIVE_15MIN,
    ISOCHRONES_DRIVE_20MIN,
    RPPS_GEOCODE_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Fichiers d'entrée (sources brutes)
# ----------------------------------------------------------------------------

INPUT_FILES = {
    # Sources brutes
    'contours_iris_gpkg': INPUT_DIR / '1_sources_brutes' / 'contours_iris.gpkg',
    'contours_iris': INPUT_DIR / '1_sources_brutes' / 'contours_iris.gpkg',  # Alias
    'finess_csv': INPUT_DIR / '1_sources_brutes' / 'finess_complet.csv',
    'finess': INPUT_DIR / 'FINESS.csv',  # Ancien chemin
    'rpps_medecins': INPUT_DIR / '1_sources_brutes' / 'rpps_medecins.csv',
    'osm_france': INPUT_DIR / '1_sources_brutes' / 'france-latest.osm.pbf',

    # Données INSEE
    'population_age_csv': INPUT_DIR / '2_insee_brutes' / 'age_profession.CSV',
    'age_profession': INPUT_DIR / '2_insee_brutes' / 'age_profession.CSV',  # Alias
    'diplome_formation_csv': INPUT_DIR / '2_insee_brutes' / 'diplome_formation.CSV',
    'diplome_formation': INPUT_DIR / '2_insee_brutes' / 'diplome_formation.CSV',  # Alias
    'logement_csv': INPUT_DIR / '2_insee_brutes' / 'logement.CSV',
    'logement': INPUT_DIR / '2_insee_brutes' / 'logement.CSV',  # Alias
    'revenus_csv': INPUT_DIR / '2_insee_brutes' / 'revenus.csv',
    'revenus': INPUT_DIR / '2_insee_brutes' / 'revenus.csv',  # Alias
    'hebergements_classes': INPUT_DIR / '2_insee_brutes' / 'INSEE_hebergements_classes.csv',
    'hebergements_hotels': INPUT_DIR / '2_insee_brutes' / 'hebergements_hotels.csv',
    'hebergements_campings': INPUT_DIR / '2_insee_brutes' / 'hebergements_campings.csv',
    'hebergements_autres': INPUT_DIR / '2_insee_brutes' / 'hebergements_autres.csv',

    # Pharmacies
    'pharmacies_brutes': INPUT_DIR / '3_pharmacies' / 'pharmacies_raw.csv',
    'pharmacies_source': INPUT_DIR / 'points_ventes_202509.geocoded.csv',  # UGA source
    'pharmacies': INPUT_DIR / '3_pharmacies' / 'pharmacies_raw.csv',  # Alias

    # Références
    'correspondance_iris_cp': INPUT_DIR / '4_references' / 'correspondance_iris_code_postal.csv',
    'correspondance_iris_postal': INPUT_DIR / '4_references' / 'correspondance_iris_code_postal.csv',  # Alias
    'correspondance_insee_postal': INPUT_DIR / '4_references' / 'correspondance-code-insee-code-postal.csv',

    # Validation
    'sig_p20': INPUT_DIR / '5_validation' / 'SIG_P20.CSV',
    'df_bas_annee': INPUT_DIR / '5_validation' / 'df_bas_annee.csv',
}

# Fichiers RPPS (multiples professions)
RPPS_FILES = {
    'medecins': INPUT_DIR / 'PS_LibreAcces_Personne_activite_01.txt',
    'dentistes': INPUT_DIR / 'PS_LibreAcces_Personne_activite_02.txt',
    'pharmaciens': INPUT_DIR / 'PS_LibreAcces_Personne_activite_03.txt',
    'sages_femmes': INPUT_DIR / 'PS_LibreAcces_Personne_activite_04.txt',
    'infirmiers': INPUT_DIR / 'PS_LibreAcces_Personne_activite_05.txt',
    'kines': INPUT_DIR / 'PS_LibreAcces_Personne_activite_06.txt',
}

# ----------------------------------------------------------------------------
# Fichiers de sortie Phase 1
# ----------------------------------------------------------------------------

OUTPUT_FILES = {
    # 1. Pharmacies
    'pharmacies_final': OUTPUT_DIR / 'pharmacies_final.csv',

    # 2. Hubs médicaux
    'hubs_unified_final': OUTPUT_DIR / 'HUBS_unified_final.csv',
    'hubs_unified': OUTPUT_DIR / 'HUBS_unified.csv',
    'hubs': OUTPUT_DIR / 'hubs.csv',
    'hubs_gpkg': OUTPUT_DIR / 'hubs.gpkg',
    'hubs_rpps_geocoded': OUTPUT_DIR / 'hubs_rpps_geocoded.csv',
    'hubs_finess_processed': OUTPUT_DIR / 'hubs_finess_processed.csv',
    'finess_merged': OUTPUT_DIR / 'FINESS_merged.csv',
    'rpps_merged': RPPS_GEOCODE_DIR / 'RPPS_merged.csv',

    # 3. Isochrones
    'isochrones_dir': OUTPUT_DIR / 'isochrones',
    'isochrones_walk_5min': ISOCHRONES_WALK_5MIN,
    'isochrones_walk_10min': ISOCHRONES_WALK_10MIN,
    'isochrones_drive_5min': ISOCHRONES_DRIVE_5MIN,
    'isochrones_drive_10min': ISOCHRONES_DRIVE_10MIN,
    'isochrones_drive_15min': ISOCHRONES_DRIVE_15MIN,
    'isochrones_drive_20min': ISOCHRONES_DRIVE_20MIN,

    # Matrice pharmacie-IRIS (avec w_IRIS)
    'matrice_w_iris': OUTPUT_DIR / 'matrice_w_iris.csv',
    'matrice_w_iris_enriched': OUTPUT_DIR / 'matrice_w_iris_enriched.csv',
    'matrice_w_iris_100pct': OUTPUT_DIR / 'matrice_w_iris_100pct.csv',

    # 4. Enrichissement
    'pharmacies_variables_touristiques': OUTPUT_DIR / 'pharmacies_final_avec_variables_touristiques.csv',
    'pharmacies_avec_tourisme': OUTPUT_DIR / 'pharmacies_final_avec_variables_touristiques.csv',  # Alias
    'pharmacies_enrichies_insee': OUTPUT_DIR / 'pharmacies_enrichies_insee.csv',

    # Checkpoints
    'checkpoint_tourisme': OUTPUT_DIR / 'checkpoint_variables_touristiques.csv',
}

# ============================================================================
# CONFIGURATION ISOCHRONES
# ============================================================================

ISOCHRONES_CONFIG = {
    # Types d'isochrones à générer
    'types': [
        ('walk', 5),    # Marche 5min
        ('walk', 10),   # Marche 10min
        ('drive', 5),   # Voiture 5min
        ('drive', 10),  # Voiture 10min
        ('drive', 15),  # Voiture 15min
        ('drive', 20),  # Voiture 20min
    ],

    # API configuration
    'api_provider': 'valhalla',  # ou 'osrm', 'graphhopper'
    'api_url': 'http://localhost:8002',  # Valhalla local

    # Format de sortie
    'output_format': 'geojson',
    'filename_pattern': '{id_pharmacie}.geojson',

    # Paramètres de calcul
    'batch_size': 100,
    'retry_attempts': 3,
    'timeout_seconds': 30,
}

# ============================================================================
# CONFIGURATION HUBS
# ============================================================================

HUBS_CONFIG = {
    # Types de hubs à inclure
    'types_hubs': [
        'medecin',
        'hopital',
        'centre_sante',
        'ehpad',
        'laboratoire',
        'pharmacie',
        'infirmier',
        'kine',
        'dentiste',
    ],

    # Distance de déduplication (mètres)
    'deduplication_distance': 50,

    # Géocodage
    'geocoding_provider': 'nominatim',  # ou 'google', 'ban'
    'geocoding_batch_size': 100,
}

# ============================================================================
# CONFIGURATION ENRICHISSEMENT
# ============================================================================

ENRICHISSEMENT_CONFIG = {
    # Variables touristiques à calculer
    'variables_touristiques': [
        'nb_hotels',
        'nb_campings',
        'nb_residences_tourisme',
        'capacite_accueil_totale',
        'flag_commune_touristique',
    ],

    # Variables INSEE à inclure
    'variables_insee': [
        'pop_totale',
        'pop_65_plus',
        'taux_retraites',
        'taux_cadres',
        'revenu_median',
        'taux_pauvrete',
    ],

    # Rayons d'analyse (mètres)
    'rayons_analyse': [500, 1000, 2000],
}

# ============================================================================
# PARAMÈTRES DE TRAITEMENT
# ============================================================================

# Géocodage
GEOCODING_WORKERS = 10  # Nombre de workers parallèles pour géocodage
GEOCODING_TIMEOUT = 10  # Timeout en secondes par requête

# Isochrones
ISOCHRONE_TYPES = {
    'walk_5min': {'mode': 'walking', 'time': 5},
    'walk_10min': {'mode': 'walking', 'time': 10},
    'drive_5min': {'mode': 'driving', 'time': 5},
    'drive_10min': {'mode': 'driving', 'time': 10},
    'drive_15min': {'mode': 'driving', 'time': 15},
    'drive_20min': {'mode': 'driving', 'time': 20},
}

ISOCHRONE_WORKERS = 4  # Nombre de workers parallèles pour génération isochrones
ISOCHRONE_TIMEOUT = 30  # Timeout en secondes par isochrone

# Dédoublonnage HUBS
DEDUP_DISTANCE_THRESHOLD = 50  # Distance en mètres pour dédoublonnage spatial

# Enrichissement
ENRICHISSEMENT_WORKERS = 4  # Nombre de workers pour enrichissement INSEE

# ============================================================================
# CONFIGURATION LOGGING
# ============================================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

VALIDATION_CONFIG = {
    # Seuils de qualité
    'seuil_valeurs_manquantes': 0.10,  # Max 10% de valeurs manquantes
    'seuil_outliers': 0.05,  # Max 5% d'outliers

    # Variables obligatoires
    'colonnes_obligatoires': [
        'id_pharmacie',
        'nom_pharmacie',
        'latitude',
        'longitude',
        'code_postal',
        'commune',
    ],
}

# ============================================================================
# AFFICHAGE DE LA CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CONFIGURATION DATA PREP - PHASE 1")
    print("=" * 80)
    print(f"\nRépertoire projet : {PROJECT_ROOT}")
    print(f"Répertoire input  : {INPUT_DIR}")
    print(f"Répertoire output : {OUTPUT_DIR}")
    print(f"Répertoire scripts: {SCRIPTS_DIR}")
    print("\n" + "=" * 80)
    print("Configuration chargée avec succès !")
    print("=" * 80)