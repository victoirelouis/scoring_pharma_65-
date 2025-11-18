"""
Script 5 : CALCUL DU SCORE D'ATTRACTIVITÉ avec LightGBM + GridSearch

Ce script entraîne un modèle LightGBM pour prédire le CA des pharmacies,
puis utilise les prédictions comme score d'attractivité.

Les hyperparamètres sont optimisés via GridSearchCV pour maximiser la performance.

APPROCHE :
    1. Charger pharmacies_features_complet.csv
    2. Sélectionner les features d'attractivité
    3. GridSearch pour optimiser les hyperparamètres LightGBM
    4. Entraîner 3 modèles (ca_total, ca_ethique, ca_conseil)
    5. Calculer les scores d'attractivité (prédictions normalisées)
    6. Sauvegarder avec les meilleurs paramètres

Inputs:
    - pharmacies_features_complet.csv (Script 4)

Outputs:
    - pharmacies_avec_scores_attractivite.csv : Scores d'attractivité
    - modeles_lightgbm/ : Modèles entraînés sauvegardés
    - rapport_gridsearch.txt : Rapport avec meilleurs paramètres et performances

Durée estimée: 10-20 minutes (selon GridSearch)

Auteur: Pipeline ML Pharmacies
Date: 2025-01-12
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
import logging
import json
import pickle
from datetime import datetime
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INTERMEDIATE_FILES,
    LOGGING_CONFIG
)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['log_file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AttractivityScorer:
    """
    Classe pour calculer le score d'attractivité avec LightGBM + GridSearch
    """
    
    def __init__(self):
        """Initialisation"""
        self.df = None
        self.models = {}  # Stockage des modèles entraînés
        self.best_params = {}  # Meilleurs hyperparamètres
        self.performances = {}  # Métriques de performance
        self.label_encoders = {}  # Pour variables catégorielles
        self.poids_composite = {}  # Pondérations pour le score composite

        # Dossier pour sauvegarder les modèles
        self.models_dir = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'].parent / 'modeles_lightgbm'
        self.models_dir.mkdir(exist_ok=True, parents=True)

        logger.info("Initialisation du calculateur de score d'attractivité")
    
    def load_data(self):
        """Charge les données complètes"""
        logger.info("Chargement des données...")
        
        input_path = INTERMEDIATE_FILES['pharmacies_features_complet']
        self.df = pd.read_csv(input_path)
        
        logger.info(f"  -> {len(self.df):,} pharmacies chargées")
        logger.info(f"  -> {len(self.df.columns)} colonnes disponibles")
    
    def select_features(self):
        """Sélectionne les features d'attractivité pour le ML"""
        logger.info("\nSélection des features d'attractivité...")

        # Liste des features à utiliser pour prédire le CA
        features = []

        # 1. Features HUBS (TOUS les isochrones)
        hubs_features = [
            'nb_services_seniors', 'nb_sante_generale', 'nb_sante_specialisee',
            'nb_medecin', 'nb_medecins_equivalent', 'nb_ehpad', 'nb_hopital',
            'nb_laboratoire', 'nb_supermarche', 'nb_bus', 'nb_accessibilite',
            'taux_colocalisation', 'nb_hubs_brut', 'nb_hubs_deduplique'
        ]

        # Utiliser TOUS les isochrones disponibles
        for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
            for hub in hubs_features:
                col = f'{hub}_{iso}'
                if col in self.df.columns:
                    features.append(col)

        # 2. Features POPULATION (TOUS les isochrones)
        pop_features = [
            'pop_totale',          # Taille totale du marché
            'pop_0_64',            # Non-seniors (actifs + enfants)
            'pop_65_plus',         # Total seniors
            'pop_65_74',           # Jeunes seniors
            'pop_75_84',           # Seniors âgés
            'pop_85_plus',         # Grand âge
            'pop_hommes_65_plus', 'pop_femmes_65_plus',
            'pop_hommes_65_74', 'pop_femmes_65_74',
            'pop_hommes_75_84', 'pop_femmes_75_84',
            'pop_hommes_85_plus', 'pop_femmes_85_plus',
            'taux_retraites', 'taux_cadres'
        ]

        # Utiliser TOUS les isochrones disponibles
        for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
            for pop in pop_features:
                col = f'{pop}_{iso}'
                if col in self.df.columns:
                    features.append(col)

        # 3. Features CONCURRENCE (TOUS les isochrones)
        for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
            col_conc = f'nb_pharmacies_concurrentes_{iso}'
            if col_conc in self.df.columns:
                features.append(col_conc)

        # Distance à la pharmacie la plus proche (peut avoir des variantes _x, _y suite à merges)
        for dist_col in ['distance_pharmacie_plus_proche', 'distance_pharmacie_plus_proche_x', 'distance_pharmacie_plus_proche_y']:
            if dist_col in self.df.columns and dist_col not in features:
                features.append(dist_col)

        # 4. Features DÉRIVÉES - TOUTES celles disponibles dans le fichier
        # Recherche automatique de toutes les features dérivées
        # IMPORTANT: Exclure 'delta' car c'est une variable créée APRÈS prédiction (data leakage!)
        derived_patterns = ['ratio_', 'densite_', 'zone_', 'concurrence_par_', 'voisins_']
        # Variables catégorielles à exclure du pattern matching (seront encodées plus tard)
        categorical_to_exclude = ['type_zone', 'departement', 'type_zone_touristique']

        for col in self.df.columns:
            if any(pattern in col for pattern in derived_patterns):
                # Exclure les colonnes de population brute ou HUBS bruts
                # ET exclure les variables catégorielles qui seront encodées
                if col not in categorical_to_exclude:
                    if not any(x in col for x in ['pop_', 'nb_']) or any(x in col for x in ['ratio_', 'densite_', 'concurrence_par_']):
                        if col not in features:
                            features.append(col)

        # 5. Features TOURISME - TOUTES celles disponibles dans le fichier
        # Recherche automatique de toutes les variables touristiques
        tourisme_patterns = ['nb_hotels_', 'nb_campings_', 'nb_residences_', 'capacite_accueil_', 'flag_commune_', 'nb_total_hebergements_']
        for col in self.df.columns:
            if any(pattern in col for pattern in tourisme_patterns):
                if col not in features:
                    features.append(col)

        # 6. Variables catégorielles à encoder
        categorical_features = ['type_zone', 'departement', 'type_zone_touristique']

        for cat_col in categorical_features:
            if cat_col in self.df.columns:
                # Label encoding - Convertir toutes les valeurs en str pour éviter les erreurs de type mixte
                le = LabelEncoder()
                self.df[f'{cat_col}_encoded'] = le.fit_transform(self.df[cat_col].fillna('unknown').astype(str))
                self.label_encoders[cat_col] = le
                features.append(f'{cat_col}_encoded')

        # Filtrer les features qui existent réellement ET exclure les colonnes catégorielles originales
        self.features = [f for f in features if f in self.df.columns and f not in categorical_features]

        # Statistiques par catégorie
        nb_hubs = len([f for f in self.features if any(x in f for x in ['nb_services_', 'nb_sante_', 'nb_medecin', 'nb_ehpad', 'nb_hopital', 'nb_laboratoire', 'nb_supermarche', 'nb_bus', 'nb_accessibilite', 'taux_colocalisation', 'nb_hubs_'])])
        nb_pop = len([f for f in self.features if f.startswith('pop_') or 'taux_retraites' in f or 'taux_cadres' in f])
        nb_conc = len([f for f in self.features if 'pharmacies_concurrentes' in f or 'distance_pharmacie' in f])
        nb_derived = len([f for f in self.features if any(x in f for x in ['ratio_', 'densite_', 'zone_']) and not f.startswith('pop_')])
        nb_tourisme = len([f for f in self.features if any(x in f for x in ['hotels_', 'campings_', 'residences_', 'capacite_accueil_', 'flag_commune_'])])
        nb_cat = len([f for f in self.features if '_encoded' in f])

        logger.info(f"  -> {len(self.features)} features selectionnees au total")
        logger.info(f"\nRepartition par categorie:")
        logger.info(f"    - HUBS              : {nb_hubs:3d} features")
        logger.info(f"    - POPULATION        : {nb_pop:3d} features")
        logger.info(f"    - CONCURRENCE       : {nb_conc:3d} features")
        logger.info(f"    - DERIVEES          : {nb_derived:3d} features")
        logger.info(f"    - TOURISME          : {nb_tourisme:3d} features")
        logger.info(f"    - CATEGORIELLES     : {nb_cat:3d} features")

        logger.info(f"\nPremiers exemples de features:")
        for i, feat in enumerate(self.features[:15], 1):
            logger.info(f"    {i:2d}. {feat}")
        if len(self.features) > 15:
            logger.info(f"    ... et {len(self.features) - 15} autres")

        return self.features
    
    def prepare_data(self, target):
        """
        Prépare X et y pour l'entraînement
        
        Args:
            target: Nom de la colonne cible ('ca_total', 'ca_ethique', 'ca_conseil')
        
        Returns:
            X_train, X_test, y_train, y_test, df_clean
        """
        logger.info(f"\nPréparation des données pour {target}...")
        
        # Filtrer les pharmacies avec CA disponible
        df_clean = self.df[self.df[target].notna()].copy()
        logger.info(f"  -> {len(df_clean):,} pharmacies avec {target} disponible")
        
        # Supprimer les CA négatifs ou nuls
        df_clean = df_clean[df_clean[target] > 0]
        logger.info(f"  -> {len(df_clean):,} pharmacies avec {target} > 0")
        
        # Préparer X et y
        X = df_clean[self.features].fillna(0)
        y = df_clean[target]
        
        # Split train/test (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        logger.info(f"  -> Train: {len(X_train):,} | Test: {len(X_test):,}")
        
        return X_train, X_test, y_train, y_test, df_clean
    
    def optimize_hyperparameters(self, X_train, y_train, target='ca_total'):
        """
        Optimise les hyperparamètres avec GridSearchCV POUR CHAQUE MODÈLE
        OU charge les hyperparamètres sauvegardés si disponibles

        Args:
            X_train: Features d'entraînement
            y_train: Cible d'entraînement
            target: Nom de la cible (ca_ethique, ca_conseil, delta, ca_total)

        Returns:
            best_params: Meilleurs hyperparamètres trouvés
        """
        logger.info(f"\n🔍 OPTIMISATION DES HYPERPARAMÈTRES POUR {target.upper()} (GridSearchCV)...")
        logger.info("="*80)

        # Vérifier si des hyperparamètres sauvegardés existent POUR CE MODÈLE
        params_path = self.models_dir / f'best_hyperparameters_{target}.json'

        if params_path.exists():
            logger.info(f"✅ Hyperparamètres sauvegardés trouvés : {params_path}")
            logger.info("   Chargement des paramètres optimisés (skip GridSearch)...")

            with open(params_path, 'r', encoding='utf-8') as f:
                best_params = json.load(f)

            logger.info("\n📋 Paramètres chargés :")
            for param, value in best_params.items():
                logger.info(f"  {param:20s} : {value}")

            return best_params, None

        # Si pas de sauvegarde, faire le GridSearch
        logger.info(f"⚠️  Aucun hyperparamètre sauvegardé pour {target}")
        logger.info("   Lancement du GridSearch complet...\n")

        # Grille de paramètres à tester - Optimisée pour ~250 fits par modèle
        # 81 combinaisons × 3 folds = 243 fits par modèle
        # 3 modèles × 243 fits = 729 fits total
        param_grid = {
            'n_estimators': [200, 300, 500],      # 3 valeurs
            'learning_rate': [0.01, 0.05, 0.1],   # 3 valeurs
            'max_depth': [7, 10],                 # 2 valeurs (pas 3 pour rester à 81)
            'num_leaves': [31, 50],               # 2 valeurs (pas 3 pour rester à 81)
            'min_child_samples': [20, 50],        # 2 valeurs (pas 3 pour rester à 81)
            'subsample': [0.8, 1.0],              # 2 valeurs (sans 0.9)
            'colsample_bytree': [0.8, 1.0]        # 2 valeurs (sans 0.9)
        }

        logger.info("Grille de paramètres :")
        for param, values in param_grid.items():
            logger.info(f"  {param:20s} : {values}")

        total_combinations = np.prod([len(v) for v in param_grid.values()])
        logger.info(f"\nNombre total de combinaisons : {total_combinations}")
        logger.info("Cela peut prendre 10-20 minutes...\n")

        # Créer le modèle de base
        lgb_model = lgb.LGBMRegressor(
            random_state=42,
            verbose=-1,
            force_col_wise=True
        )

        # GridSearchCV avec validation croisée 3-fold
        grid_search = GridSearchCV(
            estimator=lgb_model,
            param_grid=param_grid,
            cv=3,  # 3-fold cross-validation
            scoring='r2',  # Optimiser le R²
            n_jobs=1,  # FIX: Python 3.13 sur Windows a un bug avec n_jobs=-1 (ModuleNotFoundError: _posixsubprocess)
            verbose=2,  # Afficher la progression
            return_train_score=True
        )

        # Entraîner
        grid_search.fit(X_train, y_train)
        
        # Meilleurs paramètres
        best_params = grid_search.best_params_
        best_score = grid_search.best_score_
        
        logger.info("\n✅ OPTIMISATION TERMINÉE !")
        logger.info("="*80)
        logger.info(f"Meilleur R² (CV) : {best_score:.4f}")
        logger.info("\nMeilleurs paramètres :")
        for param, value in best_params.items():
            logger.info(f"  {param:20s} : {value}")
        
        # Sauvegarder les résultats de GridSearch
        cv_results = pd.DataFrame(grid_search.cv_results_)
        cv_results = cv_results.sort_values('rank_test_score')
        
        logger.info(f"\nTop 5 combinaisons :")
        logger.info("-"*80)
        for i, row in cv_results.head(5).iterrows():
            logger.info(f"Rang {row['rank_test_score']:.0f} | R² = {row['mean_test_score']:.4f} | Params: {row['params']}")

        # 💾 SAUVEGARDE INTERMÉDIAIRE - Hyperparamètres optimisés PAR MODÈLE
        logger.info(f"\n💾 Sauvegarde intermédiaire des hyperparamètres pour {target}...")
        params_path = self.models_dir / f'best_hyperparameters_{target}.json'
        with open(params_path, 'w', encoding='utf-8') as f:
            json.dump(best_params, f, indent=2)
        logger.info(f"   ✅ Sauvegardé: {params_path}")

        return best_params, grid_search
    
    def train_model(self, target):
        """
        Entraîne un modèle LightGBM avec les meilleurs hyperparamètres
        
        Args:
            target: Variable cible ('ca_total', 'ca_ethique', 'ca_conseil')
        
        Returns:
            model: Modèle entraîné
        """
        logger.info("\n" + "="*80)
        logger.info(f"ENTRAÎNEMENT DU MODÈLE : {target.upper()}")
        logger.info("="*80)
        
        # Préparer les données
        X_train, X_test, y_train, y_test, df_clean = self.prepare_data(target)

        # Optimiser les hyperparamètres POUR CHAQUE MODÈLE (pas de réutilisation)
        # Chaque modèle (ca_ethique, ca_conseil, delta) aura ses propres hyperparamètres optimaux
        best_params, grid_search = self.optimize_hyperparameters(X_train, y_train, target=target)
        
        # Entraîner le modèle avec les meilleurs paramètres
        logger.info("\nEntraînement du modèle final...")
        
        model = lgb.LGBMRegressor(
            **best_params,
            random_state=42,
            verbose=-1
        )
        
        model.fit(X_train, y_train)
        
        # Évaluation
        logger.info("\nÉvaluation du modèle :")
        logger.info("-"*80)
        
        # Sur train
        y_train_pred = model.predict(X_train)
        r2_train = r2_score(y_train, y_train_pred)
        mae_train = mean_absolute_error(y_train, y_train_pred)
        rmse_train = np.sqrt(mean_squared_error(y_train, y_train_pred))
        
        logger.info(f"TRAIN SET :")
        logger.info(f"  R² score  : {r2_train:.4f}")
        logger.info(f"  MAE       : {mae_train:,.0f} €")
        logger.info(f"  RMSE      : {rmse_train:,.0f} €")
        
        # Sur test
        y_test_pred = model.predict(X_test)
        r2_test = r2_score(y_test, y_test_pred)
        mae_test = mean_absolute_error(y_test, y_test_pred)
        rmse_test = np.sqrt(mean_squared_error(y_test, y_test_pred))
        
        logger.info(f"\nTEST SET :")
        logger.info(f"  R² score  : {r2_test:.4f}")
        logger.info(f"  MAE       : {mae_test:,.0f} €")
        logger.info(f"  RMSE      : {rmse_test:,.0f} €")
        
        # Overfitting check
        overfitting = r2_train - r2_test
        logger.info(f"\nOVERFITTING :")
        logger.info(f"  Écart R² (train - test) : {overfitting:.4f}")
        if overfitting > 0.1:
            logger.warning("  ⚠️  Overfitting détecté (écart > 0.10)")
        else:
            logger.info("  ✅ Pas d'overfitting significatif")
        
        # Feature importance
        logger.info(f"\nTOP 15 FEATURES LES PLUS IMPORTANTES :")
        logger.info("-"*80)
        
        feature_importance = pd.DataFrame({
            'feature': self.features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for i, row in feature_importance.head(15).iterrows():
            logger.info(f"  {row['feature']:50s} : {row['importance']:.0f}")
        
        # ========================================
        # EXTRACTION DE L'IMPORTANCE PAR TRANCHE D'ÂGE
        # ========================================
        logger.info(f"\n📊 IMPORTANCE DES TRANCHES D'ÂGE :")
        logger.info("-"*80)
        
        age_groups = {
            'pop_0_64': 'Non-seniors (0-64 ans)',
            'pop_65_74': 'Seniors actifs (65-74 ans)',
            'pop_75_84': 'Seniors âgés (75-84 ans)',
            'pop_85_plus': 'Grand âge (85+ ans)',
            'pop_65_plus': 'Total seniors (65+ ans)',
        }
        
        importance_by_age = {}
        for age_key, age_label in age_groups.items():
            # Chercher toutes les features contenant cette tranche d'âge
            age_features = feature_importance[
                feature_importance['feature'].str.contains(age_key, na=False)
            ]
            
            if len(age_features) > 0:
                total_importance = age_features['importance'].sum()
                importance_by_age[age_key] = total_importance
                logger.info(f"  {age_label:35s} : {total_importance:8.1f}")
        
        # Calculer la part des seniors dans le CA
        seniors_keys = ['pop_65_74', 'pop_75_84', 'pop_85_plus']
        importance_seniors = sum([importance_by_age.get(k, 0) for k in seniors_keys])
        importance_non_seniors = importance_by_age.get('pop_0_64', 0)
        importance_total_pop = importance_seniors + importance_non_seniors
        
        if importance_total_pop > 0:
            part_seniors = importance_seniors / importance_total_pop
        else:
            part_seniors = 0.5  # Valeur par défaut si impossible à calculer
        
        logger.info("")
        logger.info(f"📊 CONTRIBUTION ESTIMÉE DES SENIORS (65+) AU CA :")
        logger.info(f"   Importance totale seniors (65-74 + 75-84 + 85+) : {importance_seniors:.1f}")
        logger.info(f"   Importance totale non-seniors (0-64) : {importance_non_seniors:.1f}")
        logger.info(f"   Part estimée des seniors dans le CA : {part_seniors*100:.1f}%")

        # ========================================
        # FIN DE L'EXTRACTION
        # ========================================

        # Sauvegarder les performances - D'ABORD créer le dictionnaire
        self.performances[target] = {
            'r2_train': r2_train,
            'mae_train': mae_train,
            'rmse_train': rmse_train,
            'r2_test': r2_test,
            'mae_test': mae_test,
            'rmse_test': rmse_test,
            'overfitting': overfitting,
            'n_train': len(X_train),
            'n_test': len(X_test),
            'feature_importance': feature_importance.to_dict('records'),
            'importance_by_age': importance_by_age,
            'part_seniors_estimee': part_seniors
        }
        
        # 💾 SAUVEGARDE INTERMÉDIAIRE - Modèle + Performances
        logger.info(f"\n💾 Sauvegarde intermédiaire du modèle {target}...")

        # Sauvegarder le modèle
        model_path = self.models_dir / f'model_{target}.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        logger.info(f"   ✅ Modèle: {model_path}")

        # Sauvegarder les performances
        perf_path = self.models_dir / f'performances_{target}.json'
        with open(perf_path, 'w', encoding='utf-8') as f:
            # Fonction pour convertir récursivement les types numpy en types Python
            def convert_numpy(obj):
                if isinstance(obj, (np.integer, np.int64)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64)):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_numpy(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy(v) for v in obj]
                else:
                    return obj

            # Convertir les valeurs numpy en types Python pour JSON
            perf_json = {k: convert_numpy(v)
                        for k, v in self.performances[target].items()
                        if k != 'feature_importance'}
            json.dump(perf_json, f, indent=2)
        logger.info(f"   ✅ Performances: {perf_path}")

        return model
    
    def calculate_attractivity_scores(self):
        """Calcule les scores d'attractivité pour toutes les pharmacies"""
        logger.info("\n" + "="*80)
        logger.info("CALCUL DES SCORES D'ATTRACTIVITÉ")
        logger.info("="*80)
        
        # Préparer X pour toutes les pharmacies
        X_all = self.df[self.features].fillna(0)
        
        # Calculer les scores pour chaque modèle
        for target, model in self.models.items():
            logger.info(f"\nCalcul score pour {target}...")
            
            # Prédiction
            predictions = model.predict(X_all)
            
            # Normaliser 0-1
            predictions_norm = (predictions - predictions.min()) / (predictions.max() - predictions.min())
            
            # Sauvegarder
            self.df[f'score_{target}'] = predictions
            self.df[f'score_{target}_norm'] = predictions_norm
            
            logger.info(f"  -> Score min: {predictions.min():,.0f} | max: {predictions.max():,.0f}")
            logger.info(f"  -> Score normalisé min: {predictions_norm.min():.3f} | max: {predictions_norm.max():.3f}")
        
        # Score d'attractivité composite (moyenne pondérée basée sur les données réelles)
        # IMPORTANT: ca_total = ca_ethique + ca_conseil + delta
        # On utilise les 3 COMPOSANTES (ethique, conseil, delta) pour éviter le double comptage
        logger.info("\n" + "="*80)
        logger.info("CALCUL DES PONDERATIONS BASEES SUR LES DONNEES REELLES")
        logger.info("="*80)
        logger.info("IMPORTANT: CA_total = CA_ethique + CA_conseil + delta")
        logger.info("Score composite basé sur les 3 COMPOSANTES (pas de double comptage)")

        # Calculer les pondérations basées sur les moyennes des 3 COMPOSANTES
        targets_composantes = [t for t in ['ca_ethique', 'ca_conseil', 'delta']
                              if t in self.df.columns and self.df[t].notna().sum() > 0]

        if len(targets_composantes) >= 2:
            moyennes_ca = {}
            for target in targets_composantes:
                moyennes_ca[target] = self.df[target].dropna().mean()
                logger.info(f"  Moyenne {target:15s} : {moyennes_ca[target]:,.0f} €")

            # Calculer les pondérations proportionnelles
            somme_moyennes = sum(moyennes_ca.values())
            poids = {t: moyennes_ca[t] / somme_moyennes for t in moyennes_ca}

            logger.info(f"\nPondérations calculées:")
            for target, p in poids.items():
                logger.info(f"  {target:15s} : {p:.3f} ({p*100:.1f}%)")

            # Sauvegarder les poids
            self.poids_composite = poids
        else:
            # Valeurs par défaut si pas assez de CA disponibles
            logger.info("  Utilisation des pondérations par défaut (pas assez de CA disponibles)")
            poids = {'ca_ethique': 0.66, 'ca_conseil': 0.24, 'delta': 0.10}
            self.poids_composite = poids

        logger.info("\n" + "="*80)
        logger.info("CALCUL DU SCORE COMPOSITE")
        logger.info("="*80)

        if all(f'score_{t}_norm' in self.df.columns for t in ['ca_ethique', 'ca_conseil', 'delta']):
            w_ethique = poids.get('ca_ethique', 0.66)
            w_conseil = poids.get('ca_conseil', 0.24)
            w_delta = poids.get('delta', 0.10)

            self.df['score_attractivite_composite'] = (
                w_ethique * self.df['score_ca_ethique_norm'] +
                w_conseil * self.df['score_ca_conseil_norm'] +
                w_delta * self.df['score_delta_norm']
            )
            logger.info(f"  ✅ Score composite = {w_ethique:.3f}×ethique + {w_conseil:.3f}×conseil + {w_delta:.3f}×delta")
            logger.info(f"  (Pas de double comptage: ethique + conseil + delta = total)")
        else:
            # Fallback: utiliser ca_total si disponible
            if 'score_ca_total_norm' in self.df.columns:
                self.df['score_attractivite_composite'] = self.df['score_ca_total_norm']
                logger.info(f"  ✅ Score composite = score_ca_total_norm (composantes non disponibles)")
            else:
                # Sinon utiliser le premier disponible
                available = [t for t in ['ca_ethique', 'ca_conseil', 'delta'] if f'score_{t}_norm' in self.df.columns]
                if available:
                    self.df['score_attractivite_composite'] = self.df[f'score_{available[0]}_norm']
                    logger.info(f"  ✅ Score composite = score_{available[0]}_norm (seul disponible)")
        
        # ========================================
        # CALCUL DES SCORES AJUSTÉS 65+
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("📊 CALCUL DES SCORES SPÉCIFIQUES 65+")
        logger.info("="*80)
        
        # Pour chaque modèle, calculer un score ajusté pour les 65+
        for target, model in self.models.items():
            
            # Récupérer la part seniors estimée
            part_seniors = self.performances[target].get('part_seniors_estimee', 0.5)
            
            logger.info(f"\n{target}:")
            logger.info(f"  Part seniors estimée : {part_seniors*100:.1f}%")
            
            # Score ajusté pour les 65+ = Score total × Part seniors
            self.df[f'score_{target}_65plus'] = (
                self.df[f'score_{target}'] * part_seniors
            )
            
            # Normaliser
            score_65plus_col = self.df[f'score_{target}_65plus']
            if score_65plus_col.max() > score_65plus_col.min():
                self.df[f'score_{target}_65plus_norm'] = (
                    (score_65plus_col - score_65plus_col.min()) / 
                    (score_65plus_col.max() - score_65plus_col.min())
                )
            else:
                self.df[f'score_{target}_65plus_norm'] = 0.5
            
            logger.info(f"  Score 65+ min: {self.df[f'score_{target}_65plus'].min():,.0f}")
            logger.info(f"  Score 65+ max: {self.df[f'score_{target}_65plus'].max():,.0f}")
        
        # Score composite 65+ (utiliser les MÊMES poids que le score global)
        # IMPORTANT: Utiliser les 3 COMPOSANTES (ethique, conseil, delta) pour éviter le double comptage
        if all(f'score_{t}_65plus_norm' in self.df.columns for t in ['ca_ethique', 'ca_conseil', 'delta']):
            w_ethique = self.poids_composite.get('ca_ethique', 0.66)
            w_conseil = self.poids_composite.get('ca_conseil', 0.24)
            w_delta = self.poids_composite.get('delta', 0.10)

            self.df['score_attractivite_65plus_composite'] = (
                w_ethique * self.df['score_ca_ethique_65plus_norm'] +
                w_conseil * self.df['score_ca_conseil_65plus_norm'] +
                w_delta * self.df['score_delta_65plus_norm']
            )
            logger.info("\n✅ Score attractivité 65+ composite calculé")
            logger.info(f"   Pondération : {w_ethique:.3f}×ethique + {w_conseil:.3f}×conseil + {w_delta:.3f}×delta")
        else:
            # Fallback: utiliser ca_total si disponible
            if 'score_ca_total_65plus_norm' in self.df.columns:
                self.df['score_attractivite_65plus_composite'] = self.df['score_ca_total_65plus_norm']
                logger.info(f"\n✅ Score 65+ composite = ca_total_65plus_norm (composantes non disponibles)")
            else:
                # Utiliser le premier disponible
                available = [t for t in ['ca_ethique', 'ca_conseil', 'delta'] if f'score_{t}_65plus_norm' in self.df.columns]
                if available:
                    self.df['score_attractivite_65plus_composite'] = self.df[f'score_{available[0]}_65plus_norm']
                    logger.info(f"\n✅ Score 65+ composite = {available[0]}_65plus_norm")
        
        # ========================================
        # FIN DES SCORES AJUSTÉS 65+
        # ========================================

        logger.info(f"\n✅ Scores d'attractivité calculés pour {len(self.df):,} pharmacies")
        logger.info(f"   - Scores globaux (tous âges) : score_attractivite_composite")
        logger.info(f"   - Scores ajustés 65+ : score_attractivite_65plus_composite")

        # 💾 SAUVEGARDE INTERMÉDIAIRE - Tous les scores calculés
        logger.info(f"\n💾 Sauvegarde intermédiaire des scores...")

        # Colonnes à sauvegarder
        cols_checkpoint = ['id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude']
        cols_checkpoint.extend([c for c in self.df.columns if c.startswith('score_')])

        df_checkpoint = self.df[cols_checkpoint].copy()
        checkpoint_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'].parent / 'scores_checkpoint.csv'
        df_checkpoint.to_csv(checkpoint_path, index=False, encoding='utf-8')

        logger.info(f"   ✅ Checkpoint: {checkpoint_path}")
        logger.info(f"   ✅ {len(df_checkpoint):,} pharmacies × {len(df_checkpoint.columns)} colonnes sauvegardées")
    
    def generate_report(self):
        """Génère un rapport complet de GridSearch et performances"""
        logger.info("\nGénération du rapport...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT - SCORE D'ATTRACTIVITÉ (LightGBM + GridSearch)")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Nombre de pharmacies : {len(self.df):,}")
        report_lines.append(f"Nombre de features : {len(self.features)}")
        report_lines.append("")
        
        # Meilleurs hyperparamètres
        report_lines.append("MEILLEURS HYPERPARAMÈTRES (GridSearch)")
        report_lines.append("-" * 80)
        for param, value in self.best_params.items():
            report_lines.append(f"  {param:20s} : {value}")
        report_lines.append("")
        
        # Performances par modèle
        for target, perf in self.performances.items():
            report_lines.append(f"\nMODÈLE : {target.upper()}")
            report_lines.append("-" * 80)
            report_lines.append(f"Train set : {perf['n_train']:,} pharmacies")
            report_lines.append(f"Test set  : {perf['n_test']:,} pharmacies")
            report_lines.append("")
            report_lines.append(f"R² train  : {perf['r2_train']:.4f}")
            report_lines.append(f"R² test   : {perf['r2_test']:.4f}")
            report_lines.append(f"MAE train : {perf['mae_train']:,.0f} €")
            report_lines.append(f"MAE test  : {perf['mae_test']:,.0f} €")
            report_lines.append(f"RMSE train: {perf['rmse_train']:,.0f} €")
            report_lines.append(f"RMSE test : {perf['rmse_test']:,.0f} €")
            report_lines.append(f"Overfitting: {perf['overfitting']:.4f}")
            
            if perf['overfitting'] > 0.1:
                report_lines.append("  ⚠️  Overfitting détecté")
            else:
                report_lines.append("  ✅ Pas d'overfitting")
            
            # Importance par tranche d'âge
            if 'importance_by_age' in perf:
                report_lines.append("")
                report_lines.append("Importance par tranche d'âge :")
                for age_key, importance in perf['importance_by_age'].items():
                    report_lines.append(f"  {age_key:30s} : {importance:.1f}")
                
                if 'part_seniors_estimee' in perf:
                    report_lines.append("")
                    report_lines.append(f"📊 Part estimée des seniors (65+) dans le CA : {perf['part_seniors_estimee']*100:.1f}%")
            
            report_lines.append("")
            report_lines.append("Top 15 features importantes :")
            for i, feat_info in enumerate(perf['feature_importance'][:15], 1):
                report_lines.append(f"  {i:2d}. {feat_info['feature']:50s} : {feat_info['importance']:.0f}")
        
        report_lines.append("")
        report_lines.append("SCORES CRÉÉS")
        report_lines.append("-" * 80)
        report_lines.append("Scores globaux (tous âges) :")
        report_lines.append("  - score_attractivite_composite")
        report_lines.append("")
        report_lines.append("Scores ajustés 65+ :")
        report_lines.append("  - score_attractivite_65plus_composite")
        report_lines.append("  → Utilisé pour estimer le nombre de clients 65+ (Script 6)")
        report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Sauvegarder
        report_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'].parent / 'rapport_gridsearch_attractivite.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"  ✅ Rapport sauvegardé : {report_path}")
    
    def save_results(self):
        """Sauvegarde les résultats"""
        logger.info("\nSauvegarde des résultats...")
        
        # Sélectionner les colonnes à sauvegarder
        cols_to_save = ['id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude',
                        'code_postal', 'commune', 'departement', 'type_zone']
        
        # Ajouter les CA si disponibles
        for ca in ['ca_total', 'ca_ethique', 'ca_conseil']:
            if ca in self.df.columns:
                cols_to_save.append(ca)
        
        # Ajouter TOUS les scores (globaux + 65+)
        score_cols = [c for c in self.df.columns if c.startswith('score_')]
        cols_to_save.extend(score_cols)
        
        # Filtrer les colonnes disponibles
        cols_available = [c for c in cols_to_save if c in self.df.columns]
        
        df_output = self.df[cols_available].copy()
        
        # Sauvegarder
        output_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite']
        df_output.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"  ✅ Fichier sauvegardé : {output_path}")
        logger.info(f"  ✅ {len(df_output):,} pharmacies × {len(df_output.columns)} colonnes")
        
        # Afficher les colonnes de scores créées
        score_cols_created = [c for c in df_output.columns if c.startswith('score_')]
        logger.info(f"\n  📊 Scores créés ({len(score_cols_created)}) :")
        for col in sorted(score_cols_created):
            logger.info(f"     - {col}")
        
        # Sauvegarder aussi les hyperparamètres
        params_path = self.models_dir / 'best_hyperparameters.json'
        with open(params_path, 'w', encoding='utf-8') as f:
            json.dump(self.best_params, f, indent=2)
        logger.info(f"\n  ✅ Hyperparamètres sauvegardés : {params_path}")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DU SCRIPT 5 : SCORE D'ATTRACTIVITÉ (LightGBM + GridSearch)")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 1. Charger les données
            self.load_data()
            
            # 2. Sélectionner les features
            self.select_features()
            
            # 3. Entraîner les modèles (avec GridSearch sur le 1er)
            # IMPORTANT: ca_total = ca_ethique + ca_conseil + delta
            # On entraîne les 3 composantes + ca_total pour validation
            targets = ['ca_ethique', 'ca_conseil', 'delta', 'ca_total']

            for target in targets:
                if target in self.df.columns:
                    model = self.train_model(target)
                    self.models[target] = model
                else:
                    logger.warning(f"  ⚠️  Colonne {target} non disponible, ignorée")
            
            # 4. Calculer les scores d'attractivité
            if self.models:
                self.calculate_attractivity_scores()
            else:
                raise ValueError("Aucun modèle entraîné ! Vérifiez que les colonnes CA existent.")
            
            # 5. Générer le rapport
            self.generate_report()
            
            # 6. Sauvegarder
            self.save_results()
            
            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ SCRIPT 5 TERMINÉ AVEC SUCCÈS")
            logger.info(f"Durée d'exécution : {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    scorer = AttractivityScorer()
    scorer.run()


if __name__ == "__main__":
    main()
