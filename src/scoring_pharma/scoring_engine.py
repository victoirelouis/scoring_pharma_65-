"""
Module principal du calcul de scoring
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScoringEngine:
    """Moteur de calcul du score de potentiel pour les pharmacies"""
    
    # Poids des différentes composantes du score
    WEIGHTS = {
        'demographic': 0.35,
        'geographic': 0.25,
        'economic': 0.25,
        'service': 0.15
    }
    
    # Catégories de score
    CATEGORIES = {
        'A+': (90, 100),
        'A': (80, 89),
        'B': (65, 79),
        'C': (50, 64),
        'D': (0, 49)
    }
    
    def __init__(self):
        """Initialise le moteur de scoring"""
        self.scores = None
    
    @staticmethod
    def normalize_score(values: pd.Series, min_val: float = 0, max_val: float = 100) -> pd.Series:
        """
        Normalise une série de valeurs sur une échelle donnée
        
        Args:
            values: Série de valeurs à normaliser
            min_val: Valeur minimale de l'échelle
            max_val: Valeur maximale de l'échelle
            
        Returns:
            Série de valeurs normalisées
        """
        if values.max() == values.min():
            return pd.Series([50] * len(values), index=values.index)
        
        normalized = (values - values.min()) / (values.max() - values.min())
        return normalized * (max_val - min_val) + min_val
    
    def calculate_demographic_score(self, demographics: pd.DataFrame) -> pd.Series:
        """
        Calcule le score démographique
        
        Args:
            demographics: DataFrame avec les données démographiques
            
        Returns:
            Série de scores démographiques (0-100)
        """
        logger.info("Calcul du score démographique")
        
        # Densité 65+ (40% du score démo)
        density_score = self.normalize_score(demographics['population_65_plus']) * 0.4
        
        # Croissance (30% du score démo)
        growth_score = self.normalize_score(demographics.get('croissance_5ans', pd.Series([0]))) * 0.3
        
        # Structure d'âge - proportion 75+ (30% du score démo)
        age_structure_score = self.normalize_score(
            demographics.get('population_75_84', pd.Series([0])) + 
            demographics.get('population_85_plus', pd.Series([0]))
        ) * 0.3
        
        total_score = density_score + growth_score + age_structure_score
        return total_score
    
    def calculate_geographic_score(self, pharmacies: pd.DataFrame) -> pd.Series:
        """
        Calcule le score géographique
        
        Args:
            pharmacies: DataFrame avec les données des pharmacies
            
        Returns:
            Série de scores géographiques (0-100)
        """
        logger.info("Calcul du score géographique")
        
        # Pour l'instant, score par défaut - à enrichir avec données réelles
        # Accessibilité, zone de chalandise, concurrence
        n = len(pharmacies)
        return pd.Series([70.0] * n, index=pharmacies.index)
    
    def calculate_economic_score(self, economic: pd.DataFrame) -> pd.Series:
        """
        Calcule le score économique
        
        Args:
            economic: DataFrame avec les données économiques
            
        Returns:
            Série de scores économiques (0-100)
        """
        logger.info("Calcul du score économique")
        
        # Revenu médian (40% du score éco)
        income_score = self.normalize_score(economic.get('revenu_median', pd.Series([0]))) * 0.4
        
        # Équipements seniors (30% du score éco)
        equipment_score = self.normalize_score(
            economic.get('nb_residences_seniors', pd.Series([0])) +
            economic.get('nb_ehpad', pd.Series([0]))
        ) * 0.3
        
        # Dynamisme commercial (30% du score éco)
        commerce_score = self.normalize_score(economic.get('indice_commercial', pd.Series([0]))) * 0.3
        
        total_score = income_score + equipment_score + commerce_score
        return total_score
    
    def calculate_service_score(self, pharmacies: pd.DataFrame) -> pd.Series:
        """
        Calcule le score d'offre de services
        
        Args:
            pharmacies: DataFrame avec les données des pharmacies
            
        Returns:
            Série de scores de service (0-100)
        """
        logger.info("Calcul du score d'offre de services")
        
        # Score par défaut - à enrichir avec données réelles sur les services
        n = len(pharmacies)
        return pd.Series([60.0] * n, index=pharmacies.index)
    
    def calculate_total_score(
        self,
        pharmacies: pd.DataFrame,
        demographics: pd.DataFrame,
        economic: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calcule le score total pour chaque pharmacie
        
        Args:
            pharmacies: DataFrame des pharmacies
            demographics: DataFrame des données démographiques
            economic: DataFrame des données économiques
            
        Returns:
            DataFrame avec les scores détaillés et le score total
        """
        logger.info("Calcul du score total")
        
        result = pharmacies.copy()
        
        # Calcul des sous-scores
        result['score_demographic'] = self.calculate_demographic_score(demographics)
        result['score_geographic'] = self.calculate_geographic_score(pharmacies)
        result['score_economic'] = self.calculate_economic_score(economic)
        result['score_service'] = self.calculate_service_score(pharmacies)
        
        # Calcul du score total pondéré
        result['score_total'] = (
            result['score_demographic'] * self.WEIGHTS['demographic'] +
            result['score_geographic'] * self.WEIGHTS['geographic'] +
            result['score_economic'] * self.WEIGHTS['economic'] +
            result['score_service'] * self.WEIGHTS['service']
        )
        
        # Ajout de la catégorie
        result['category'] = result['score_total'].apply(self.categorize_score)
        
        self.scores = result
        return result
    
    @classmethod
    def categorize_score(cls, score: float) -> str:
        """
        Attribue une catégorie basée sur le score
        
        Args:
            score: Score total (0-100)
            
        Returns:
            Catégorie (A+, A, B, C, D)
        """
        for category, (min_score, max_score) in cls.CATEGORIES.items():
            if min_score <= score <= max_score:
                return category
        return 'D'
    
    def get_top_pharmacies(self, n: int = 10) -> pd.DataFrame:
        """
        Retourne les n pharmacies avec le meilleur score
        
        Args:
            n: Nombre de pharmacies à retourner
            
        Returns:
            DataFrame des meilleures pharmacies
        """
        if self.scores is None:
            logger.error("Aucun score calculé. Exécutez calculate_total_score d'abord.")
            return pd.DataFrame()
        
        return self.scores.nlargest(n, 'score_total')
