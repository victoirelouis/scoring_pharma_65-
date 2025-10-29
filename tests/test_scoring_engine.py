"""
Tests pour le module scoring_engine
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Ajout du répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scoring_pharma.scoring_engine import ScoringEngine


class TestScoringEngine:
    """Tests pour la classe ScoringEngine"""
    
    def test_normalize_score(self):
        """Test de la normalisation des scores"""
        values = pd.Series([10, 20, 30, 40, 50])
        normalized = ScoringEngine.normalize_score(values)
        
        assert normalized.min() == 0
        assert normalized.max() == 100
        assert len(normalized) == len(values)
    
    def test_normalize_score_constant(self):
        """Test de la normalisation avec des valeurs identiques"""
        values = pd.Series([50, 50, 50])
        normalized = ScoringEngine.normalize_score(values)
        
        assert all(normalized == 50)
    
    def test_categorize_score(self):
        """Test de la catégorisation des scores"""
        assert ScoringEngine.categorize_score(95) == 'A+'
        assert ScoringEngine.categorize_score(85) == 'A'
        assert ScoringEngine.categorize_score(70) == 'B'
        assert ScoringEngine.categorize_score(55) == 'C'
        assert ScoringEngine.categorize_score(30) == 'D'
    
    def test_calculate_demographic_score(self):
        """Test du calcul du score démographique"""
        demographics = pd.DataFrame({
            'population_65_plus': [1000, 2000, 3000],
            'croissance_5ans': [5, 10, 15],
            'population_75_84': [200, 400, 600],
            'population_85_plus': [50, 100, 150]
        })
        
        engine = ScoringEngine()
        scores = engine.calculate_demographic_score(demographics)
        
        assert len(scores) == 3
        assert all(scores >= 0)
        assert all(scores <= 100)
        assert scores.iloc[2] > scores.iloc[0]  # Plus de population = meilleur score
    
    def test_calculate_total_score(self):
        """Test du calcul du score total"""
        pharmacies = pd.DataFrame({
            'id_pharmacie': ['P1', 'P2', 'P3'],
            'latitude': [48.8566, 45.7640, 43.2965],
            'longitude': [2.3522, 4.8357, 5.3698]
        })
        
        demographics = pd.DataFrame({
            'population_65_plus': [1000, 2000, 3000],
            'croissance_5ans': [5, 10, 15],
            'population_75_84': [200, 400, 600],
            'population_85_plus': [50, 100, 150]
        })
        
        economic = pd.DataFrame({
            'revenu_median': [25000, 30000, 35000],
            'nb_residences_seniors': [2, 4, 6],
            'nb_ehpad': [1, 2, 3],
            'indice_commercial': [50, 60, 70]
        })
        
        engine = ScoringEngine()
        result = engine.calculate_total_score(pharmacies, demographics, economic)
        
        assert 'score_total' in result.columns
        assert 'category' in result.columns
        assert 'score_demographic' in result.columns
        assert 'score_geographic' in result.columns
        assert 'score_economic' in result.columns
        assert 'score_service' in result.columns
        assert len(result) == 3
    
    def test_get_top_pharmacies(self):
        """Test de récupération des meilleures pharmacies"""
        pharmacies = pd.DataFrame({
            'id_pharmacie': [f'P{i}' for i in range(20)],
            'latitude': [48.8566] * 20,
            'longitude': [2.3522] * 20
        })
        
        demographics = pd.DataFrame({
            'population_65_plus': list(range(1000, 21000, 1000))
        })
        
        economic = pd.DataFrame({
            'revenu_median': list(range(20000, 40000, 1000))
        })
        
        engine = ScoringEngine()
        engine.calculate_total_score(pharmacies, demographics, economic)
        top = engine.get_top_pharmacies(5)
        
        assert len(top) == 5
        # Vérifie que les scores sont triés par ordre décroissant
        assert all(top['score_total'].iloc[i] >= top['score_total'].iloc[i+1] 
                  for i in range(len(top)-1))
