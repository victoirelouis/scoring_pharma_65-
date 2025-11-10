#!/usr/bin/env python3
"""
Générateur SIMPLE et RAPIDE d'isochrones manquants

Génère des isochrones géométriques (cercles) pour les pharmacies manquantes
basés sur des vitesses moyennes par type de zone.

🎯 STRATÉGIE SIMPLIFIÉE :
- Cercles géométriques rapides
- Vitesses adaptées par type de zone
- Génération en quelques minutes

Usage:
    python generate_simple_isochrones.py --missing-file pharmacies_missing.csv
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
import argparse
import logging
import math
from tqdm import tqdm
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration des rayons par type d'isochrone et zone (mètres)
ISOCHRONE_RADII = {
    'walk_5min': 330,   # 5min * 4km/h = 330m
    'walk_10min': 660,  # 10min * 4km/h = 660m
    'drive_15min': {
        'rural': 8750,       # 15min * 35km/h
        'periurbain': 6250,  # 15min * 25km/h
        'urbain': 5000,      # 15min * 20km/h
        'urbain_dense': 3750 # 15min * 15km/h
    },
    'drive_20min': {
        'rural': 11667,      # 20min * 35km/h
        'periurbain': 8333,  # 20min * 25km/h
        'urbain': 6667,      # 20min * 20km/h
        'urbain_dense': 5000 # 20min * 15km/h
    }
}

class SimpleIsochroneGenerator:
    def __init__(self, missing_file, output_dir):
        self.missing_file = Path(missing_file)
        self.output_dir = Path(output_dir)
        
        # Créer les dossiers pour chaque type d'isochrone
        for isochrone_type in ['walk_5min', 'walk_10min', 'drive_15min', 'drive_20min']:
            (self.output_dir / isochrone_type).mkdir(parents=True, exist_ok=True)
    
    def create_circle_polygon(self, lat, lon, radius_meters):
        """Créer un polygone circulaire"""
        # Nombre de points pour approximer le cercle
        num_points = 32
        angles = np.linspace(0, 2 * np.pi, num_points)
        
        # Conversion approximative mètres -> degrés
        lat_rad = math.radians(lat)
        meter_to_lat = 1 / 111000
        meter_to_lon = 1 / (111000 * math.cos(lat_rad))
        
        # Créer les points du cercle
        points = []
        for angle in angles:
            lat_offset = radius_meters * meter_to_lat * math.sin(angle)
            lon_offset = radius_meters * meter_to_lon * math.cos(angle)
            points.append([lon + lon_offset, lat + lat_offset])
        
        # Fermer le polygone
        points.append(points[0])
        
        return points
    
    def get_radius(self, isochrone_type, zone_type):
        """Obtenir le rayon approprié selon le type d'isochrone et de zone"""
        if isochrone_type in ['walk_5min', 'walk_10min']:
            return ISOCHRONE_RADII[isochrone_type]
        else:
            # Pour drive, dépend du type de zone
            zone_radii = ISOCHRONE_RADII[isochrone_type]
            return zone_radii.get(zone_type, zone_radii['periurbain'])  # Default: periurbain
    
    def save_isochrone_geojson(self, pharmacy_id, isochrone_type, coordinates):
        """Sauvegarder un isochrone en GeoJSON"""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "id_pharmacie": str(pharmacy_id),
                    "type": isochrone_type,
                    "method": "geometric_circle",
                    "timestamp": datetime.now().isoformat()
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }]
        }
        
        output_file = self.output_dir / isochrone_type / f"{pharmacy_id}.geojson"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
    
    def generate_isochrones(self):
        """Générer tous les isochrones manquants"""
        logger.info("Génération des isochrones géométriques...")
        
        # Charger les pharmacies manquantes
        df_missing = pd.read_csv(self.missing_file, sep=';')
        logger.info(f"Chargement de {len(df_missing)} pharmacies manquantes")
        
        isochrone_types = ['walk_5min', 'walk_10min', 'drive_15min', 'drive_20min']
        total_operations = len(df_missing) * len(isochrone_types)
        
        results = []
        success_count = 0
        
        with tqdm(total=total_operations, desc="Génération isochrones") as pbar:
            for _, pharmacy in df_missing.iterrows():
                pharmacy_id = str(pharmacy['id_pharmacie'])
                lat = float(pharmacy['latitude'])
                lon = float(pharmacy['longitude'])
                zone_type = pharmacy['type_zone']
                
                result_row = {
                    'id_pharmacie': pharmacy_id,
                    'error_message': '',
                    'processing_time_seconds': 0.01,
                    'cache_hits': 0,
                    'mode_used': 'geometric_simple'
                }
                
                pharmacy_success = True
                
                for isochrone_type in isochrone_types:
                    try:
                        # Obtenir le rayon approprié
                        radius = self.get_radius(isochrone_type, zone_type)
                        
                        # Créer le cercle
                        coordinates = self.create_circle_polygon(lat, lon, radius)
                        
                        # Sauvegarder
                        self.save_isochrone_geojson(pharmacy_id, isochrone_type, coordinates)
                        
                        # Enregistrer le succès
                        result_row[f'{isochrone_type}_success'] = 'True'
                        result_row[f'{isochrone_type}_file'] = f"{isochrone_type}/{pharmacy_id}.geojson"
                        
                    except Exception as e:
                        logger.warning(f"Erreur pour {pharmacy_id} {isochrone_type}: {e}")
                        result_row[f'{isochrone_type}_success'] = 'False'
                        result_row[f'{isochrone_type}_file'] = ''
                        result_row['error_message'] = str(e)
                        pharmacy_success = False
                    
                    pbar.update(1)
                
                if pharmacy_success:
                    success_count += 1
                
                results.append(result_row)
        
        # Sauvegarder le résumé
        df_results = pd.DataFrame(results)
        summary_file = self.output_dir / 'simple_isochrones_summary.csv'
        df_results.to_csv(summary_file, index=False)
        
        logger.info(f"Traitement terminé:")
        logger.info(f"  Pharmacies traitées: {len(results)}")
        logger.info(f"  Succès complet (4/4): {success_count} ({success_count/len(results)*100:.1f}%)")
        logger.info(f"  Fichiers GeoJSON créés: {success_count * 4}")
        
        return df_results

def main():
    parser = argparse.ArgumentParser(description='Génération simple des isochrones manquants')
    parser.add_argument('--missing-file', default='data/input/pharmacies_missing.csv',
                       help='Fichier des pharmacies manquantes')
    parser.add_argument('--output-dir', default='data/processed/isochrones',
                       help='Dossier de sortie')
    
    args = parser.parse_args()
    
    generator = SimpleIsochroneGenerator(
        missing_file=args.missing_file,
        output_dir=args.output_dir
    )
    
    results = generator.generate_isochrones()
    
    print("\nGÉNÉRATION TERMINÉE AVEC SUCCÈS!")
    print(f"Consultez les fichiers dans: {args.output_dir}")

if __name__ == "__main__":
    main()