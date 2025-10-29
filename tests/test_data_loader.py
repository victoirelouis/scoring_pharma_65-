"""
Tests pour le module data_loader
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Ajout du répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scoring_pharma.data_loader import DataLoader


class TestDataLoader:
    """Tests pour la classe DataLoader"""
    
    def test_init(self):
        """Test de l'initialisation"""
        loader = DataLoader(data_dir='data')
        assert loader.data_dir == Path('data')
        assert loader.pharmacies is None
    
    def test_load_pharmacies_file_not_found(self):
        """Test du chargement avec fichier manquant"""
        loader = DataLoader(data_dir='/tmp/nonexistent')
        
        with pytest.raises(FileNotFoundError):
            loader.load_pharmacies()
    
    def test_validate_data_no_data(self):
        """Test de validation sans données"""
        loader = DataLoader()
        assert loader.validate_data() is False
    
    def test_validate_data_with_valid_data(self):
        """Test de validation avec des données valides"""
        loader = DataLoader()
        loader.pharmacies = pd.DataFrame({
            'id_pharmacie': ['P1', 'P2'],
            'latitude': [48.8566, 45.7640],
            'longitude': [2.3522, 4.8357]
        })
        
        assert loader.validate_data() is True
    
    def test_validate_data_missing_columns(self):
        """Test de validation avec colonnes manquantes"""
        loader = DataLoader()
        loader.pharmacies = pd.DataFrame({
            'id_pharmacie': ['P1', 'P2']
            # Manque latitude et longitude
        })
        
        assert loader.validate_data() is False
