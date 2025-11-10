#!/usr/bin/env python3
"""
Génération d'isochrones géométriques de fallback

Ce script génère des isochrones circulaires basés sur les vitesses standards
pour les pharmacies qui n'ont pas pu être traitées par OSMnx.

Usage:
    python generate_geometric_fallback.py --types drive_5min,drive_10min
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from pathlib import Path
import json
import argparse
import logging
from datetime import datetime
import math

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('geometric_fallback.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Chemins des dossiers
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "data" / "input" / "data_cleaning"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "isochrones"

# Configuration des vitesses par type de zone (km/h)
VITESSES_ZONE = {
    'urbain_dense': {'drive_5min': 15, 'drive_10min': 20},
    'urbain': {'drive_5min': 25, 'drive_10min': 30},
    'periurbain': {'drive_5min': 35, 'drive_10min': 40},
    'rural': {'drive_5min': 45, 'drive_10min': 50}
}

# Configuration des durées (minutes)
DUREES = {
    'drive_5min': 5,
    'drive_10min': 10
}

def calculate_radius(duration_min, speed_kmh):
    """
    Calcule le rayon en mètres pour une durée et vitesse données
    
    Args:
        duration_min (int): Durée en minutes
        speed_kmh (int): Vitesse en km/h
    
    Returns:
        float: Rayon en mètres
    """
    distance_km = (duration_min / 60) * speed_kmh
    return distance_km * 1000  # Conversion en mètres

def create_circular_isochrone(lat, lon, radius_m, pharmacy_id, isochrone_type, zone_type, speed_kmh):
    """
    Crée un isochrone circulaire autour d'un point
    
    Args:
        lat, lon: Coordonnées du centre
        radius_m: Rayon en mètres
        pharmacy_id: ID de la pharmacie
        isochrone_type: Type d'isochrone (drive_5min, drive_10min)
        zone_type: Type de zone
        speed_kmh: Vitesse utilisée
    
    Returns:
        dict: GeoJSON de l'isochrone
    """
    # Créer un point central
    center = Point(lon, lat)
    
    # Approximation simple pour créer un cercle en degrés
    # 1 degré ≈ 111 km à l'équateur
    radius_degrees = radius_m / (111000 * math.cos(math.radians(lat)))
    
    # Créer le cercle (approximation avec 32 points)
    angles = [i * (2 * math.pi / 32) for i in range(32)]
    circle_points = [
        (lon + radius_degrees * math.cos(angle), 
         lat + radius_degrees * math.sin(angle))
        for angle in angles
    ]
    
    # Fermer le polygone
    circle_points.append(circle_points[0])
    
    # Créer le polygone
    polygon = Polygon(circle_points)
    
    # Métadonnées
    properties = {
        'id_pharmacie': str(pharmacy_id),
        'type_isochrone': isochrone_type,
        'duree_minutes': DUREES[isochrone_type],
        'vitesse_kmh': speed_kmh,
        'type_zone': zone_type,
        'rayon_metres': radius_m,
        'method': 'geometric_fallback',
        'generated_at': datetime.now().isoformat()
    }
    
    # Créer le GeoJSON
    geojson = {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [list(polygon.exterior.coords)]
        },
        'properties': properties
    }
    
    return geojson

def load_pharmacies():
    """Charge le fichier des pharmacies"""
    logger.info("📂 Chargement du fichier pharmacies...")
    
    pharmacy_file = INPUT_DIR / "pharmacies_final.csv"
    df = pd.read_csv(pharmacy_file, delimiter=';')
    
    logger.info(f"   {len(df)} pharmacies chargées")
    return df

def find_missing_pharmacies(isochrone_types):
    """
    Identifie les pharmacies sans isochrones pour les types donnés
    
    Args:
        isochrone_types: Liste des types d'isochrones à vérifier
    
    Returns:
        dict: Dictionnaire {type: [liste_des_ids_manquants]}
    """
    logger.info("🔍 Identification des pharmacies manquantes...")
    
    # Charger toutes les pharmacies
    df = load_pharmacies()
    all_ids = set(df['id_pharmacie'].astype(str))
    
    missing_by_type = {}
    
    for iso_type in isochrone_types:
        # Lister les fichiers existants
        iso_dir = OUTPUT_DIR / iso_type
        if iso_dir.exists():
            existing_files = set([f.stem for f in iso_dir.glob('*.geojson')])
        else:
            existing_files = set()
        
        # Identifier les manquants
        missing_ids = all_ids - existing_files
        missing_by_type[iso_type] = missing_ids
        
        logger.info(f"   {iso_type}: {len(missing_ids)} pharmacies manquantes")
    
    return missing_by_type, df

def generate_geometric_isochrones(isochrone_types):
    """
    Génère les isochrones géométriques manquants
    
    Args:
        isochrone_types: Liste des types d'isochrones à générer
    """
    logger.info("🚀 GÉNÉRATION D'ISOCHRONES GÉOMÉTRIQUES DE FALLBACK")
    logger.info("=" * 60)
    
    # Identifier les pharmacies manquantes
    missing_by_type, df_pharmacies = find_missing_pharmacies(isochrone_types)
    
    total_to_generate = sum(len(missing_ids) for missing_ids in missing_by_type.values())
    logger.info(f"🎯 Total à générer: {total_to_generate} isochrones géométriques")
    
    if total_to_generate == 0:
        logger.info("✅ Aucun isochrone manquant - Rien à générer !")
        return
    
    generated_count = 0
    
    for iso_type in isochrone_types:
        missing_ids = missing_by_type[iso_type]
        if not missing_ids:
            continue
            
        logger.info(f"📊 Génération {iso_type}: {len(missing_ids)} isochrones")
        
        # Créer le dossier de sortie
        output_dir = OUTPUT_DIR / iso_type
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Traiter chaque pharmacie manquante
        for pharmacy_id in missing_ids:
            try:
                # Récupérer les données de la pharmacie
                pharmacy_row = df_pharmacies[df_pharmacies['id_pharmacie'].astype(str) == pharmacy_id]
                
                if pharmacy_row.empty:
                    logger.warning(f"   ⚠️ Pharmacie {pharmacy_id} non trouvée dans les données")
                    continue
                
                pharmacy = pharmacy_row.iloc[0]
                lat, lon = pharmacy['latitude'], pharmacy['longitude']
                zone_type = pharmacy['type_zone']
                
                # Déterminer la vitesse selon le type de zone
                if zone_type in VITESSES_ZONE:
                    speed_kmh = VITESSES_ZONE[zone_type][iso_type]
                else:
                    # Fallback pour zones inconnues
                    speed_kmh = VITESSES_ZONE['periurbain'][iso_type]
                    logger.warning(f"   ⚠️ Zone inconnue '{zone_type}' pour pharmacie {pharmacy_id}, utilisation vitesse périurbaine")
                
                # Calculer le rayon
                duration_min = DUREES[iso_type]
                radius_m = calculate_radius(duration_min, speed_kmh)
                
                # Générer l'isochrone géométrique
                geojson = create_circular_isochrone(
                    lat, lon, radius_m, pharmacy_id, iso_type, zone_type, speed_kmh
                )
                
                # Sauvegarder
                output_file = output_dir / f"{pharmacy_id}.geojson"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(geojson, f, ensure_ascii=False, indent=2)
                
                generated_count += 1
                
                if generated_count % 100 == 0:
                    logger.info(f"   📈 {generated_count}/{total_to_generate} générés ({generated_count/total_to_generate*100:.1f}%)")
                
            except Exception as e:
                logger.error(f"   ❌ Erreur pharmacie {pharmacy_id}: {str(e)}")
                continue
    
    logger.info("=" * 60)
    logger.info(f"✅ GÉNÉRATION TERMINÉE: {generated_count}/{total_to_generate} isochrones créés")
    logger.info(f"📊 Taux de succès: {generated_count/total_to_generate*100:.1f}%")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Génération d\'isochrones géométriques de fallback')
    parser.add_argument('--types', default='drive_5min,drive_10min',
                        help='Types d\'isochrones à générer (ex: drive_5min,drive_10min)')
    
    args = parser.parse_args()
    
    # Parser les types d'isochrones
    isochrone_types = [t.strip() for t in args.types.split(',')]
    
    # Valider les types
    valid_types = set(DUREES.keys())
    invalid_types = set(isochrone_types) - valid_types
    if invalid_types:
        logger.error(f"❌ Types invalides: {invalid_types}. Types valides: {valid_types}")
        return 1
    
    logger.info(f"🎯 Types d'isochrones à traiter: {isochrone_types}")
    
    try:
        generate_geometric_isochrones(isochrone_types)
        return 0
    except Exception as e:
        logger.error(f"❌ Erreur critique: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())