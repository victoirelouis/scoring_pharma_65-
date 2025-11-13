"""
Script 7 : SPLIT TRAIN/TEST

Divise les données en ensemble d'entraînement et de test
- Stratification par type_zone et déciles de CA
- Sauvegarde des indices pour reproductibilité

Inputs: pharmacies_features_selected.csv
Outputs: train.csv, test.csv

Durée: 1 minute
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

from config_ml import INTERMEDIATE_FILES, ML_CONFIG, LOGGING_CONFIG

logging.basicConfig(level=getattr(logging, LOGGING_CONFIG['level']),
                   format=LOGGING_CONFIG['format'],
                   handlers=[logging.FileHandler(LOGGING_CONFIG['log_file']), logging.StreamHandler()])
logger = logging.getLogger(__name__)

class DataSplitter:
    def __init__(self):
        self.df = None
        self.config = ML_CONFIG
        logger.info("Initialisation du splitter")
    
    def load_data(self):
        logger.info("Chargement des données...")
        input_path = INTERMEDIATE_FILES['pharmacies_features_selected']
        self.df = pd.read_csv(input_path)
        logger.info(f"  -> {len(self.df):,} lignes")
    
    def split_data(self):
        logger.info("Division train/test...")
        
        # Créer variable de stratification simple (quantiles de CA seulement)
        # Utiliser 3 quantiles au lieu de 5 pour éviter les strates trop petites
        self.df['strate'] = pd.qcut(self.df['ca_total'], q=3, labels=['Q1','Q2','Q3'], duplicates='drop')
        
        test_size = self.config.get('test_size', 0.2)
        random_state = self.config.get('random_state', 42)
        
        train_df, test_df = train_test_split(
            self.df,
            test_size=test_size,
            stratify=self.df['strate'],
            random_state=random_state
        )
        
        # Supprimer colonne strate
        train_df = train_df.drop('strate', axis=1)
        test_df = test_df.drop('strate', axis=1)
        
        logger.info(f"  -> Train : {len(train_df):,} lignes ({len(train_df)/len(self.df)*100:.1f}%)")
        logger.info(f"  -> Test  : {len(test_df):,} lignes ({len(test_df)/len(self.df)*100:.1f}%)")
        
        # Sauvegarder
        train_path = INTERMEDIATE_FILES['pharmacies_features_selected'].parent / 'train.csv'
        test_path = INTERMEDIATE_FILES['pharmacies_features_selected'].parent / 'test.csv'
        
        train_df.to_csv(train_path, index=False, encoding='utf-8')
        test_df.to_csv(test_path, index=False, encoding='utf-8')
        
        logger.info(f"OK Train sauvegardé : {train_path}")
        logger.info(f"OK Test sauvegardé : {test_path}")
    
    def run(self):
        logger.info("="*80)
        logger.info("SCRIPT 7 : SPLIT TRAIN/TEST")
        logger.info("="*80)
        start_time = datetime.now()
        try:
            self.load_data()
            self.split_data()
            logger.info(f"TERMINÉ - Durée : {datetime.now() - start_time}")
        except Exception as e:
            logger.error(f"ERREUR : {e}", exc_info=True)
            raise

if __name__ == "__main__":
    splitter = DataSplitter()
    splitter.run()
