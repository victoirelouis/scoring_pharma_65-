"""
Module de chargement et validation des données
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Classe pour charger et valider les données du projet"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialise le chargeur de données
        
        Args:
            data_dir: Répertoire contenant les fichiers de données
        """
        self.data_dir = Path(data_dir)
        self.pharmacies = None
        self.demographics = None
        self.economic = None
        self.competitors = None
    
    def load_pharmacies(self, filename: str = "pharmacies.csv") -> pd.DataFrame:
        """
        Charge les données des pharmacies
        
        Args:
            filename: Nom du fichier CSV
            
        Returns:
            DataFrame contenant les données des pharmacies
        """
        filepath = self.data_dir / filename
        logger.info(f"Chargement des pharmacies depuis {filepath}")
        
        try:
            self.pharmacies = pd.read_csv(filepath)
            logger.info(f"Chargé {len(self.pharmacies)} pharmacies")
            return self.pharmacies
        except FileNotFoundError:
            logger.error(f"Fichier non trouvé : {filepath}")
            raise
    
    def load_demographics(self, filename: str = "demographics.csv") -> pd.DataFrame:
        """
        Charge les données démographiques
        
        Args:
            filename: Nom du fichier CSV
            
        Returns:
            DataFrame contenant les données démographiques
        """
        filepath = self.data_dir / filename
        logger.info(f"Chargement des données démographiques depuis {filepath}")
        
        try:
            self.demographics = pd.read_csv(filepath)
            logger.info(f"Chargé {len(self.demographics)} zones démographiques")
            return self.demographics
        except FileNotFoundError:
            logger.error(f"Fichier non trouvé : {filepath}")
            raise
    
    def load_economic(self, filename: str = "economic.csv") -> pd.DataFrame:
        """
        Charge les données économiques
        
        Args:
            filename: Nom du fichier CSV
            
        Returns:
            DataFrame contenant les données économiques
        """
        filepath = self.data_dir / filename
        logger.info(f"Chargement des données économiques depuis {filepath}")
        
        try:
            self.economic = pd.read_csv(filepath)
            logger.info(f"Chargé {len(self.economic)} zones économiques")
            return self.economic
        except FileNotFoundError:
            logger.error(f"Fichier non trouvé : {filepath}")
            raise
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        Charge toutes les données disponibles
        
        Returns:
            Dictionnaire contenant tous les DataFrames
        """
        data = {}
        
        try:
            data['pharmacies'] = self.load_pharmacies()
        except FileNotFoundError:
            logger.warning("Données pharmacies non disponibles")
        
        try:
            data['demographics'] = self.load_demographics()
        except FileNotFoundError:
            logger.warning("Données démographiques non disponibles")
        
        try:
            data['economic'] = self.load_economic()
        except FileNotFoundError:
            logger.warning("Données économiques non disponibles")
        
        return data
    
    def validate_data(self) -> bool:
        """
        Valide que les données chargées sont cohérentes
        
        Returns:
            True si les données sont valides, False sinon
        """
        if self.pharmacies is None:
            logger.error("Aucune donnée de pharmacies chargée")
            return False
        
        required_cols_pharmacy = ['id_pharmacie', 'latitude', 'longitude']
        missing_cols = [col for col in required_cols_pharmacy if col not in self.pharmacies.columns]
        
        if missing_cols:
            logger.error(f"Colonnes manquantes dans pharmacies: {missing_cols}")
            return False
        
        logger.info("Validation des données réussie")
        return True
