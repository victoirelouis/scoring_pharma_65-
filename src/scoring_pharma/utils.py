"""
Fonctions utilitaires du projet
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_results(scores: pd.DataFrame, output_path: str, format: str = 'csv'):
    """
    Exporte les résultats dans un fichier
    
    Args:
        scores: DataFrame contenant les scores
        output_path: Chemin du fichier de sortie
        format: Format de sortie ('csv', 'excel', 'json')
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'csv':
        scores.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Résultats exportés en CSV : {output_path}")
    elif format == 'excel':
        scores.to_excel(output_path, index=False, engine='openpyxl')
        logger.info(f"Résultats exportés en Excel : {output_path}")
    elif format == 'json':
        scores.to_json(output_path, orient='records', indent=2, force_ascii=False)
        logger.info(f"Résultats exportés en JSON : {output_path}")
    else:
        raise ValueError(f"Format non supporté : {format}")


def generate_summary_report(scores: pd.DataFrame) -> Dict:
    """
    Génère un rapport de synthèse des scores
    
    Args:
        scores: DataFrame contenant les scores
        
    Returns:
        Dictionnaire contenant les statistiques de synthèse
    """
    report = {
        'total_pharmacies': len(scores),
        'score_moyen': scores['score_total'].mean(),
        'score_median': scores['score_total'].median(),
        'score_min': scores['score_total'].min(),
        'score_max': scores['score_total'].max(),
        'ecart_type': scores['score_total'].std(),
        'distribution_categories': scores['category'].value_counts().to_dict()
    }
    
    logger.info("Rapport de synthèse généré")
    return report


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en km entre deux points géographiques (formule de Haversine)
    
    Args:
        lat1, lon1: Coordonnées du premier point
        lat2, lon2: Coordonnées du second point
        
    Returns:
        Distance en kilomètres
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Rayon de la Terre en km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return distance


def find_competitors_in_radius(
    pharmacy_lat: float,
    pharmacy_lon: float,
    competitors: pd.DataFrame,
    radius_km: float = 2.0
) -> pd.DataFrame:
    """
    Trouve les pharmacies concurrentes dans un rayon donné
    
    Args:
        pharmacy_lat: Latitude de la pharmacie
        pharmacy_lon: Longitude de la pharmacie
        competitors: DataFrame des pharmacies concurrentes
        radius_km: Rayon de recherche en km
        
    Returns:
        DataFrame des concurrents dans le rayon
    """
    competitors = competitors.copy()
    competitors['distance'] = competitors.apply(
        lambda row: calculate_distance(
            pharmacy_lat, pharmacy_lon, 
            row['latitude'], row['longitude']
        ),
        axis=1
    )
    
    return competitors[competitors['distance'] <= radius_km].sort_values('distance')


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Valide des coordonnées géographiques
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True si les coordonnées sont valides
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180
