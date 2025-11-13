"""
Script 5 : FEATURE ENGINEERING AVANCÉ

Ce script crée des features avancées par transformation, binning, interactions
et encodage pour améliorer les performances du modèle ML.

Inputs:
    - pharmacies_features_complet.csv (Script 4)

Outputs:
    - pharmacies_features_engineered.csv : Features + transformations avancées
        (~150 variables totales)

Durée estimée: 3-5 minutes

Auteur: Pipeline ML Pharmacies
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from sklearn.preprocessing import StandardScaler, RobustScaler
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INTERMEDIATE_FILES,
    FEATURE_ENGINEERING_CONFIG,
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


class FeatureEngineer:
    """
    Classe pour créer des features avancées
    """
    
    def __init__(self):
        """Initialisation"""
        self.df = None
        self.config = FEATURE_ENGINEERING_CONFIG
        
        logger.info("Initialisation du Feature Engineer")
    
    def load_data(self):
        """Charge les données"""
        logger.info("Chargement des données...")
        
        input_path = INTERMEDIATE_FILES['pharmacies_features_complet']
        self.df = pd.read_csv(input_path)
        
        logger.info(f"  -> {len(self.df):,} lignes x {len(self.df.columns)} colonnes chargées")
    
    def create_log_transforms(self):
        """Crée des transformations logarithmiques pour variables avec grande variance"""
        logger.info("Création de transformations logarithmiques...")
        
        # Variables à transformer en log
        log_vars = [
            'pop_totale_walk_5min',
            'pop_totale_drive_10min',
            'pop_65_plus_walk_5min',
            'pop_65_plus_drive_10min',
            'ca_total',
            'distance_pharmacie_plus_proche',
        ]
        
        count = 0
        for var in log_vars:
            if var in self.df.columns:
                # Log(x + 1) pour gérer les zéros
                self.df[f'{var}_log'] = np.log1p(self.df[var])
                count += 1
        
        logger.info(f"  -> {count} transformations log créées")
    
    def create_polynomial_features(self):
        """Crée des features polynomiales (carrés, racines)"""
        logger.info("Création de features polynomiales...")
        
        # Variables pour lesquelles créer des carrés
        poly_vars = [
            'pop_65_plus_drive_10min',
            'nb_sante_generale_drive_10min',
            'nb_pharmacies_concurrentes_drive_10min',
        ]
        
        count = 0
        for var in poly_vars:
            if var in self.df.columns:
                # Carré
                self.df[f'{var}_squared'] = self.df[var] ** 2
                
                # Racine carrée
                self.df[f'{var}_sqrt'] = np.sqrt(self.df[var])
                
                count += 2
        
        logger.info(f"  -> {count} features polynomiales créées")
    
    def create_interaction_features(self):
        """Crée des interactions entre variables clés"""
        logger.info("Création de features d'interaction...")
        
        interactions = [
            # Population x Hubs santé
            ('pop_65_plus_drive_10min', 'nb_sante_generale_drive_10min', 'pop_x_hubs_sante_drive'),
            
            # Population x Concurrence
            ('pop_65_plus_drive_10min', 'nb_pharmacies_concurrentes_drive_10min', 'pop_x_concurrence_drive'),
            
            # Hubs santé x Concurrence
            ('nb_sante_generale_drive_10min', 'nb_pharmacies_concurrentes_drive_10min', 'hubs_x_concurrence_drive'),
            
            # Population femmes x Hubs santé
            ('pop_femmes_65_plus_walk_5min', 'nb_sante_generale_walk_5min', 'pop_femmes_x_hubs_walk'),
        ]
        
        count = 0
        for var1, var2, new_name in interactions:
            if var1 in self.df.columns and var2 in self.df.columns:
                self.df[new_name] = self.df[var1] * self.df[var2]
                count += 1
        
        logger.info(f"  -> {count} features d'interaction créées")
    
    def create_ratio_features(self):
        """Crée des ratios supplémentaires"""
        logger.info("Création de features ratios...")
        
        count = 0
        
        # Ratio population accessible walk vs drive
        if 'pop_65_plus_walk_5min' in self.df.columns and 'pop_65_plus_drive_10min' in self.df.columns:
            self.df['ratio_pop_walk_drive'] = (
                self.df['pop_65_plus_walk_5min'] / 
                self.df['pop_65_plus_drive_10min'].replace(0, np.nan)
            ).fillna(0).clip(upper=1.0)
            count += 1
        
        # Ratio hubs walk vs drive
        if 'nb_sante_generale_walk_5min' in self.df.columns and 'nb_sante_generale_drive_10min' in self.df.columns:
            self.df['ratio_hubs_walk_drive'] = (
                self.df['nb_sante_generale_walk_5min'] / 
                self.df['nb_sante_generale_drive_10min'].replace(0, np.nan)
            ).fillna(0).clip(upper=1.0)
            count += 1
        
        # Ratio CA par habitant 65+
        if 'ca_total' in self.df.columns and 'pop_65_plus_drive_10min' in self.df.columns:
            self.df['ca_par_senior_drive'] = (
                self.df['ca_total'] / 
                self.df['pop_65_plus_drive_10min'].replace(0, np.nan)
            ).fillna(0)
            count += 1
        
        logger.info(f"  -> {count} features ratios créées")
    
    def create_binned_features(self):
        """Crée des variables binned (catégories) depuis continues"""
        logger.info("Création de features binned...")
        
        count = 0
        
        # Catégorie population 65+
        if 'pop_65_plus_drive_10min' in self.df.columns:
            self.df['categorie_pop_65_drive'] = pd.cut(
                self.df['pop_65_plus_drive_10min'],
                bins=[-np.inf, 500, 1000, 2000, 5000, np.inf],
                labels=['très_faible', 'faible', 'moyen', 'élevé', 'très_élevé']
            ).astype(str)
            count += 1
        
        # Catégorie concurrence
        if 'nb_pharmacies_concurrentes_drive_10min' in self.df.columns:
            self.df['categorie_concurrence_drive'] = pd.cut(
                self.df['nb_pharmacies_concurrentes_drive_10min'],
                bins=[-np.inf, 0, 2, 5, 10, np.inf],
                labels=['isolée', 'faible', 'moyenne', 'forte', 'très_forte']
            ).astype(str)
            count += 1
        
        # Catégorie distance pharmacie proche
        if 'distance_pharmacie_plus_proche' in self.df.columns:
            self.df['categorie_distance_proche'] = pd.cut(
                self.df['distance_pharmacie_plus_proche'],
                bins=[-np.inf, 0.5, 1, 2, 5, np.inf],
                labels=['très_proche', 'proche', 'moyenne', 'loin', 'très_loin']
            ).astype(str)
            count += 1
        
        logger.info(f"  -> {count} features binned créées")
    
    def create_aggregate_features(self):
        """Crée des agrégations par groupes"""
        logger.info("Création de features agrégées par groupe...")
        
        count = 0
        
        # Moyennes par département
        if 'departement' in self.df.columns and 'ca_total' in self.df.columns:
            dept_means = self.df.groupby('departement')['ca_total'].transform('mean')
            self.df['ca_moyen_departement'] = dept_means
            
            # Écart à la moyenne département
            self.df['ecart_ca_departement'] = self.df['ca_total'] - dept_means
            count += 2
        
        # Moyennes par type de zone
        if 'type_zone' in self.df.columns and 'ca_total' in self.df.columns:
            zone_means = self.df.groupby('type_zone')['ca_total'].transform('mean')
            self.df['ca_moyen_type_zone'] = zone_means
            
            # Écart à la moyenne type zone
            self.df['ecart_ca_type_zone'] = self.df['ca_total'] - zone_means
            count += 2
        
        logger.info(f"  -> {count} features agrégées créées")
    
    def encode_categorical_features(self):
        """Encode les variables catégorielles"""
        logger.info("Encodage des variables catégorielles...")
        
        # One-hot encoding pour variables catégorielles
        categorical_cols = [
            'type_zone',
            'categorie_pop_65_drive',
            'categorie_concurrence_drive',
            'categorie_distance_proche',
        ]
        
        count_before = len(self.df.columns)
        
        for col in categorical_cols:
            if col in self.df.columns:
                # One-hot encoding
                dummies = pd.get_dummies(self.df[col], prefix=col, drop_first=True)
                self.df = pd.concat([self.df, dummies], axis=1)
        
        count_after = len(self.df.columns)
        
        logger.info(f"  -> {count_after - count_before} colonnes one-hot créées")
    
    def save_results(self):
        """Sauvegarde le DataFrame final"""
        output_path = INTERMEDIATE_FILES['pharmacies_features_engineered']
        logger.info(f"Sauvegarde des features engineered dans {output_path}")
        
        self.df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"OK Fichier sauvegardé : {len(self.df):,} lignes x {len(self.df.columns)} colonnes")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DU SCRIPT 5 : FEATURE ENGINEERING AVANCÉ")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 1. Charger les données
            self.load_data()
            
            # 2. Transformations log
            self.create_log_transforms()
            
            # 3. Features polynomiales
            self.create_polynomial_features()
            
            # 4. Interactions
            self.create_interaction_features()
            
            # 5. Ratios supplémentaires
            self.create_ratio_features()
            
            # 6. Binning
            self.create_binned_features()
            
            # 7. Agrégations par groupe
            self.create_aggregate_features()
            
            # 8. Encodage catégoriel
            self.encode_categorical_features()
            
            # 9. Sauvegarder
            self.save_results()
            
            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("=" * 80)
            logger.info(f"SCRIPT 5 TERMINÉ AVEC SUCCÈS")
            logger.info(f"Durée d'exécution : {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    engineer = FeatureEngineer()
    engineer.run()


if __name__ == "__main__":
    main()
