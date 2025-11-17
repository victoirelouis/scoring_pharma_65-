"""
Configuration centralisée pour le pipeline ML de prédiction CA pharmacies

Ce fichier contient tous les paramètres configurables du projet.
Modifier ici pour ajuster le comportement de tous les scripts.

Auteur: Pipeline ML Pharmacies
Date: 2025-01-10
"""

import os
from pathlib import Path

# ============================================================================
# CHEMINS DES FICHIERS
# ============================================================================

# Répertoire racine du projet (chemin Windows)
PROJECT_ROOT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")

# Répertoire des données d'entrée (data)
DATA_INPUT_DIR = PROJECT_ROOT / "data"

# Répertoire intermédiaire
INTERMEDIATE_ROOT = PROJECT_ROOT / "intermediaire"

# Répertoire des scripts (dans intermediaire)
SCRIPTS_DIR = INTERMEDIATE_ROOT / "scripts"

# Répertoire des données intermédiaires (dans intermediaire/output)
DATA_INTERMEDIATE_DIR = INTERMEDIATE_ROOT / "output"

# Répertoire des résultats finaux (dans data/output)
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

# Répertoire des modèles entraînés
MODELS_DIR = DATA_INTERMEDIATE_DIR / "models"

# Répertoire des rapports et graphiques
REPORTS_DIR = DATA_INTERMEDIATE_DIR / "reports"

# Créer les répertoires s'ils n'existent pas
for directory in [DATA_INTERMEDIATE_DIR, DATA_OUTPUT_DIR, MODELS_DIR, REPORTS_DIR, SCRIPTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Fichiers d'entrée (vos vrais noms de fichiers)
# ----------------------------------------------------------------------------

INPUT_FILES = {
    'pharmacies': DATA_INPUT_DIR / 'input' / 'data_cleaning' / 'pharmacies_final.csv',
    'hubs': DATA_INPUT_DIR / 'output' / 'HUBS_unified_corriges.csv',
    'enrichi_insee': DATA_INPUT_DIR / 'output' / 'pharmacies_enrichies_insee.csv',
    'variables_touristiques': DATA_INPUT_DIR / 'output' / 'pharmacies_final_avec_variables_touristiques.csv',
    'population_age_csv': DATA_INPUT_DIR / 'input' / 'age_profession.CSV',  # Donnees population + profession par IRIS
    'zones_iris_gpkg': DATA_INPUT_DIR / 'input' / 'geo' / 'contours_iris.gpkg',  # Zones IRIS
    'zones_iris_geojson': DATA_INPUT_DIR / 'zones_iris.geojson',  # Si disponible
    
    # Répertoires des isochrones (dans data/processed/isochrones)
    'isochrones_walk_5min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'walk_5min',
    'isochrones_walk_10min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'walk_10min',
    'isochrones_drive_5min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'drive_5min',
    'isochrones_drive_10min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'drive_10min',
    'isochrones_drive_15min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'drive_15min',
    'isochrones_drive_20min': DATA_INPUT_DIR / 'processed' / 'isochrones' / 'drive_20min',
}

# ----------------------------------------------------------------------------
# Fichiers intermédiaires
# ----------------------------------------------------------------------------

INTERMEDIATE_FILES = {
    'pharmacies_avec_hubs': DATA_INTERMEDIATE_DIR / 'pharmacies_avec_hubs.csv',
    'pharmacies_avec_concurrence': DATA_INTERMEDIATE_DIR / 'pharmacies_avec_concurrence.csv',
    'pharmacies_avec_population_isochrones': DATA_INTERMEDIATE_DIR / 'pharmacies_avec_population_isochrones.csv',
    'pharmacies_features_complet': DATA_INTERMEDIATE_DIR / 'pharmacies_features_complet_clean.csv',  # Version nettoyée
    'pharmacies_features_engineered': DATA_INTERMEDIATE_DIR / 'pharmacies_features_engineered.csv',
    'pharmacies_features_selected': DATA_INTERMEDIATE_DIR / 'pharmacies_features_selected.csv',
    'pharmacies_avec_scores_attractivite': DATA_INTERMEDIATE_DIR / 'pharmacies_avec_scores_attractivite.csv',  # Ajouté pour script 5
    'data_ml_complete': DATA_INTERMEDIATE_DIR / 'data_ml_complete.csv',
    'data_ml_features': DATA_INTERMEDIATE_DIR / 'data_ml_features.csv',
}

# ----------------------------------------------------------------------------
# Fichiers de sortie
# ----------------------------------------------------------------------------

OUTPUT_FILES = {
    'predictions_ca_potentiel': DATA_OUTPUT_DIR / 'predictions_ca_potentiel.csv',
    'opportunites_pharmacies': DATA_OUTPUT_DIR / 'opportunites_pharmacies.csv',
    'leviers_action': DATA_OUTPUT_DIR / 'leviers_action.csv',
    'decomposition_ca_par_segment': DATA_OUTPUT_DIR / 'decomposition_ca_par_segment.csv',
    'feature_importance': DATA_OUTPUT_DIR / 'feature_importance.csv',
    'dashboard': DATA_OUTPUT_DIR / 'dashboard_opportunites.html',
}


# ============================================================================
# CONFIGURATION HUBS - DÉDUPLICATION
# ============================================================================

HUBS_DEDUPLICATION_CONFIG = {
    # Activer la déduplication spatiale ?
    'activer': True,  # False = compte tous les hubs naïvement
    
    # Distance de regroupement (mètres)
    # Hubs à moins de cette distance = même cluster
    'epsilon_metres': 50,
    
    # Nom de la colonne contenant le type de hub
    'colonne_type': 'hub_type_detail',
    
    # Colonnes géographiques
    'colonne_latitude': 'latitude',
    'colonne_longitude': 'longitude',
    
    # Hiérarchie d'importance (pour identifier hub dominant dans un cluster)
    # Plus le nombre est élevé, plus le hub est prioritaire
    'hierarchie': {
        # Niveau 1 : Infrastructures majeures
        'hopital': 10,
        'centre_sante': 9,
        
        # Niveau 2 : Services seniors
        'ehpad': 8,
        'service_senior': 7,
        
        # Niveau 3 : Services spécialisés
        'thermalisme': 6,
        'soin_specialise': 6,
        'dialyse': 5,
        'laboratoire': 5,
        'sante_mentale': 5,
        'addictologie': 5,
        'handicap_adulte': 6,
        
        # Niveau 4 : Professionnels libéraux
        'medecin': 4,
        'prevention': 4,
        
        # Niveau 5 : Services à domicile
        'service_domicile': 3,
        'tutelle': 3,
        'coordination': 3,
        'social': 3,
        
        # Niveau 6 : Commerces
        'supermarche': 2,
        'marche': 2,
        
        # Niveau 7 : Transports
        'gare': 1,
        'metro': 1,
        'bus': 0.5,
    },
    
    # Pondération pour hubs colocalisés
    # Format : 'categorie_avec_categorie_dominante': coefficient
    'ponderations_colocalisation': {
        # ===== MÉDECINS =====
        'medecin_avec_hopital': 0.2,
        'medecin_avec_centre_sante': 0.4,
        'medecin_avec_medecin': 0.7,
        'medecin_standalone': 1.0,
        
        # ===== LABORATOIRES =====
        'laboratoire_avec_hopital': 0.3,
        'laboratoire_standalone': 1.0,
        
        # ===== SOINS SPÉCIALISÉS =====
        'soin_specialise_avec_hopital': 0.3,
        'dialyse_avec_hopital': 0.4,
        'dialyse_standalone': 1.0,
        
        # ===== SERVICES SENIORS (toujours pleine valeur) =====
        'ehpad_avec_hopital': 1.0,
        'ehpad_avec_centre_sante': 1.0,
        'ehpad_standalone': 1.0,
        'service_senior_standalone': 1.0,
        'service_domicile_standalone': 1.0,
        
        # ===== COMMERCES ET TRANSPORTS =====
        'supermarche_standalone': 1.0,
        'bus_avec_bus': 0.8,
        'bus_standalone': 1.0,
        'gare_standalone': 1.0,
        'metro_standalone': 1.0,
        
        # ===== HUBS STRUCTURANTS (toujours pleine valeur) =====
        'hopital_standalone': 1.0,
        'centre_sante_standalone': 1.0,
        
        # ===== DÉFAUTS =====
        'default_colocalise': 0.5,
        'default_standalone': 1.0,
    }
}


# ============================================================================
# CONFIGURATION HUBS - AGRÉGATIONS PAR FAMILLE
# ============================================================================

HUBS_AGREGATIONS_CONFIG = {
    # Regroupement par grandes familles (TOUJOURS créées)
    'familles': {
        'sante_generale': [
            'medecin',
            'hopital',
            'centre_sante',
            'laboratoire'
        ],
        'sante_specialisee': [
            'soin_specialise',
            'sante_mentale',
            'addictologie',
            'prevention',
            'thermalisme',
            'dialyse'
        ],
        'services_seniors': [
            'ehpad',
            'service_senior',
            'service_domicile',
            'handicap_adulte'
        ],
        'accessibilite': [
            'bus',
            'gare',
            'metro',
            'supermarche',
            'marche'
        ]
    },
    
    # Catégories à détailler séparément (en plus des agrégations)
    # Ces catégories auront leurs propres variables nb_X_walk_5min, nb_X_drive_10min
    'categories_detaillees': [
        'medecin',
        'ehpad',
        'hopital',
        'laboratoire',
        'supermarche',
        'bus'
    ],
    
    # Activer les variables détaillées ?
    'inclure_details': True,  # False pour n'avoir que les familles agrégées
}


# ============================================================================
# CONFIGURATION ISOCHRONES
# ============================================================================

ISOCHRONES_CONFIG = {
    # Types d'isochrones à utiliser
    # MODIFIE : Ajout des 4 isochrones manquants pour calcul population complète
    'types_isochrones': ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min'],

    # Nom des colonnes ID pharmacie dans les différents fichiers
    'colonne_id_pharmacie': 'id_pharmacie',

    # Format des fichiers isochrones
    'format_fichiers': 'geojson',  # ou 'json'

    # Pattern des noms de fichiers isochrones
    # {id_pharmacie} sera remplacé par l'ID réel
    'pattern_nom_fichier': '{id_pharmacie}.geojson',
}


# ============================================================================
# CONFIGURATION POPULATION
# ============================================================================

POPULATION_CONFIG = {
    # Variables population à agréger par isochrone
    # Note: Les colonnes exactes dans votre fichier sont les codes INSEE P22_XXX
    # Le script 3 va les transformer en pop_65_74, pop_75_84, pop_85_plus
    'variables_age': [
        'pop_totale',
        'pop_65_74',
        'pop_75_84',
        'pop_85_plus',
    ],
    
    'variables_sexe_age': [
        'pop_femmes_65_74',
        'pop_femmes_75_84',
        'pop_femmes_85_plus',
        'pop_hommes_65_74',
        'pop_hommes_75_84',
        'pop_hommes_85_plus',
    ],
    
    # Variables socio-économiques (au niveau IRIS/commune)
    'variables_socio_eco': [
        'revenu_median',
        'taux_pauvrete',
        'taux_proprietaires',
        'taux_diplomes_superieurs',
    ],
    
    # Les données population sont-elles déjà par isochrone ?
    'deja_par_isochrone': False,  # ❌ NON - Vos données sont par IRIS avec codes INSEE P22_XXX
    # → Le Script 3 est NÉCESSAIRE pour calculer les populations par isochrone
    
    # Nom de la colonne zone IRIS dans votre fichier
    'colonne_zone': 'code_iris',  # Ou 'IRIS' selon votre fichier population_age.csv
    
    # Utiliser le fichier population_age.csv séparé ?
    'utiliser_fichier_population_separe': True,
    'fichier_population_separe': 'population_age.csv',  # Dans DATA_INPUT_DIR
}


# ============================================================================
# CONFIGURATION CONCURRENCE
# ============================================================================

CONCURRENCE_CONFIG = {
    # Distance maximale pour considérer une pharmacie comme "la plus proche"
    'distance_max_plus_proche_km': 20,
}


# ============================================================================
# CONFIGURATION FEATURE ENGINEERING
# ============================================================================

FEATURE_ENGINEERING_CONFIG = {
    # Interactions à créer
    'interactions': [
        ('capacite_accueil_drive_10min', 'pop_65_plus_drive_10min', 'tourisme_x_pop_65_plus'),
        ('nb_sante_generale_drive_10min', 'pop_65_plus_drive_10min', 'hubs_x_pop_65_plus'),
        ('nb_pharmacies_concurrentes_drive_10min', 'pop_65_plus_drive_10min', 'concurrence_x_pop'),
        ('capacite_accueil_drive_10min', 'revenu_median', 'tourisme_x_revenus'),
        ('nb_ehpad_drive_10min', 'pop_85_plus_drive_10min', 'ehpad_x_pop_85_plus'),
    ],
    
    # Ratios à créer
    'ratios': [
        ('pop_65_plus_drive_10min', 'pop_totale_drive_10min', 'taux_seniors'),
        ('pop_85_plus_drive_10min', 'pop_65_plus_drive_10min', 'taux_tres_ages'),
        ('pop_femmes_65_plus_drive_10min', 'pop_65_plus_drive_10min', 'taux_femmes_seniors'),
        ('nb_pharmacies_concurrentes_drive_10min', 'pop_65_plus_drive_10min', 'pression_concurrence'),
        ('pop_65_plus_walk_5min', 'pop_65_plus_drive_10min', 'ratio_pop_walk_drive'),
    ],
    
    # Variables à one-hot encoder
    'variables_categoriques': [
        'departement',
        'type_zone_touristique',
        'type_zone_urbain_rural',
    ],
    
    # Gestion valeurs manquantes
    'imputation_strategy': 'median',  # ou 'mean', 'mode'
    
    # Seuil VIF pour détecter multicolinéarité
    'vif_threshold': 10,
}


# ============================================================================
# CONFIGURATION SÉLECTION DE FEATURES
# ============================================================================

FEATURE_SELECTION_CONFIG = {
    # Seuil de variance minimale
    'seuil_variance': 0.01,
    
    # Seuil de corrélation pour éliminer features redondantes
    'seuil_correlation': 0.95,
    
    # Nombre maximum de features à conserver
    'max_features': 80,
    
    # Méthode de sélection
    'methode': 'importance',  # 'importance', 'correlation', 'variance'
    
    # Seuil d'importance (percentile)
    'importance_threshold': 0.001,
}


# ============================================================================
# CONFIGURATION MODÈLES ML
# ============================================================================

ML_CONFIG = {
    # Variables target (CA à prédire)
    'targets': [
        'ca_total',
        'ca_ethique',
        'ca_conseil',
        'ca_delta'
    ],
    
    # Split des données
    'train_size': 0.70,
    'val_size': 0.15,
    'test_size': 0.15,
    'random_state': 42,
    'stratify_by': 'type_zone_touristique',  # Variable pour stratification
    
    # Hyperparamètres LightGBM (par défaut)
    'lightgbm_params': {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 50,
        'max_depth': 10,
        'learning_rate': 0.05,
        'n_estimators': 200,
        'min_child_samples': 20,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'n_jobs': -1,
        'verbose': -1,
    },
    
    # Hyperparameter tuning
    'hyperparameter_tuning': {
        'activer': True,  # False pour utiliser params par défaut
        'methode': 'optuna',  # ou 'grid_search', 'random_search'
        'n_trials': 50,  # Pour Optuna
        'cv_folds': 5,
        
        # Espace de recherche
        'param_space': {
            'num_leaves': [31, 50, 70, 100],
            'max_depth': [7, 10, 15, 20],
            'learning_rate': [0.01, 0.05, 0.1],
            'n_estimators': [100, 200, 500],
            'min_child_samples': [20, 50, 100],
            'subsample': [0.7, 0.8, 1.0],
            'colsample_bytree': [0.7, 0.8, 1.0],
        }
    },
    
    # Early stopping
    'early_stopping_rounds': 50,
}


# ============================================================================
# CONFIGURATION ÉVALUATION
# ============================================================================

EVALUATION_CONFIG = {
    # Métriques à calculer
    'metriques': ['r2', 'mae', 'rmse', 'mape'],
    
    # Segments pour analyse de performance
    'segments_analyse': [
        'type_zone_touristique',
        'departement',
        'type_zone_urbain_rural',
    ],
}


# ============================================================================
# CONFIGURATION OPPORTUNITÉS
# ============================================================================

OPPORTUNITES_CONFIG = {
    # Seuils de catégorisation
    'seuil_sous_performance_forte': 0.80,  # ratio < 0.80
    'seuil_sous_performance_moderee': 0.90,  # 0.80 <= ratio < 0.90
    'seuil_normal_min': 0.90,  # 0.90 <= ratio <= 1.10
    'seuil_normal_max': 1.10,
    'seuil_sur_performance_moderee': 1.20,  # 1.10 < ratio <= 1.20
    # ratio > 1.20 = sur-performance forte
    
    # Montant minimum d'opportunité pour être inclus dans le rapport
    'montant_min_opportunite': 50000,  # 50 000 €
    
    # Nombre de pharmacies similaires à comparer pour identifier leviers
    'n_pharmacies_similaires': 10,
}


# ============================================================================
# CONFIGURATION DÉCOMPOSITION CA PAR SEGMENT
# ============================================================================

DECOMPOSITION_CONFIG = {
    # Activer la décomposition CA 65+ vs autres
    'activer': True,
    
    # Méthode de décomposition
    'methode': 'regression_interactions',  # ou 'regression_simple', 'bayesian'
    
    # Priors (si méthode bayesian)
    'priors': {
        'panier_moyen_65_plus_national': 450,  # €/an (depuis littérature)
        'ratio_65_plus_vs_autres': 2.5,  # Les 65+ dépensent 2.5x plus
    },
}


# ============================================================================
# CONFIGURATION SHAP
# ============================================================================

SHAP_CONFIG = {
    # Nombre de pharmacies pour calcul SHAP (coûteux en calcul)
    'n_echantillon': 1000,
    
    # Features principales à analyser en détail
    'top_features': 10,
}


# ============================================================================
# CONFIGURATION DASHBOARD
# ============================================================================

DASHBOARD_CONFIG = {
    # Titre du dashboard
    'titre': 'Dashboard Opportunités Pharmacies - Scoring CA 65+',
    
    # Nombre de top opportunités à afficher
    'n_top_opportunites': 50,
    
    # Carte interactive
    'carte': {
        'center_lat': 46.603354,  # Centre France
        'center_lon': 1.888334,
        'zoom_start': 6,
    }
}


# ============================================================================
# CONFIGURATION LOGS
# ============================================================================

LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': DATA_INTERMEDIATE_DIR / 'pipeline_ml.log',
}


# ============================================================================
# AFFICHAGE DE LA CONFIGURATION (pour vérification)
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CONFIGURATION DU PIPELINE ML - PRÉDICTION CA PHARMACIES")
    print("=" * 80)
    print(f"\nRépertoire projet : {PROJECT_ROOT}")
    print(f"\nRépertoire données entrée : {DATA_INPUT_DIR}")
    print(f"Répertoire données sortie : {DATA_OUTPUT_DIR}")
    print(f"Répertoire modèles : {MODELS_DIR}")
    print(f"Répertoire rapports : {REPORTS_DIR}")
    print("\n" + "=" * 80)
    print("Configuration chargée avec succès !")
    print("=" * 80)