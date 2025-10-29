"""
Tests pour le module utils
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Ajout du répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scoring_pharma.utils import (
    calculate_distance,
    validate_coordinates,
    generate_summary_report
)


class TestUtils:
    """Tests pour les fonctions utilitaires"""
    
    def test_calculate_distance(self):
        """Test du calcul de distance"""
        # Paris à Lyon (environ 400 km)
        dist = calculate_distance(48.8566, 2.3522, 45.7640, 4.8357)
        assert 390 < dist < 410
        
        # Distance nulle
        dist = calculate_distance(48.8566, 2.3522, 48.8566, 2.3522)
        assert dist == 0
    
    def test_validate_coordinates(self):
        """Test de validation des coordonnées"""
        assert validate_coordinates(48.8566, 2.3522) is True
        assert validate_coordinates(0, 0) is True
        assert validate_coordinates(90, 180) is True
        assert validate_coordinates(-90, -180) is True
        
        assert validate_coordinates(91, 0) is False
        assert validate_coordinates(0, 181) is False
        assert validate_coordinates(-91, 0) is False
    
    def test_generate_summary_report(self):
        """Test de génération du rapport de synthèse"""
        scores = pd.DataFrame({
            'score_total': [75, 85, 65, 90, 55],
            'category': ['B', 'A', 'B', 'A+', 'C']
        })
        
        report = generate_summary_report(scores)
        
        assert report['total_pharmacies'] == 5
        assert report['score_moyen'] == 74.0
        assert report['score_min'] == 55
        assert report['score_max'] == 90
        assert 'distribution_categories' in report
