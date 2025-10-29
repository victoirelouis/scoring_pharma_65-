"""
Scoring Pharma 65+ - Système de scoring du potentiel des pharmacies pour la population 65+
"""

__version__ = "0.1.0"
__author__ = "Victoire Louis"

from .scoring_engine import ScoringEngine
from .data_loader import DataLoader

__all__ = ["ScoringEngine", "DataLoader"]
