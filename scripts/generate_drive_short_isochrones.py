#!/usr/bin/env python3
"""
Générateur d'isochrones DRIVE 5min et 10min

Génère des isochrones de conduite courts (5min et 10min) pour toutes les pharmacies
basés sur des vitesses moyennes par type de zone.

🎯 NOUVEAUX ISOCHRONES :
- drive_5min : Rayons courts pour accessibilité immédiate
- drive_10min : Rayons moyens pour zone de chalandise proche

Usage:
    python generate_drive_short_isochrones.py --input pharmacies_final.csv
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

# Configuration des rayons pour drive 5min et 10min par type de zone (mètres)
DRIVE_SHORT_RADII = {
    'drive_5min': {
        'rural': 2917,       # 5min * 35km/h = 2.9km
        'periurbain': 2083,  # 5min * 25km/h = 2.1km
        'urbain': 1667,      # 5min * 20km/h = 1.7km
        'urbain_dense': 1250 # 5min * 15km/h = 1.25km
    },
    'drive_10min': {
        'rural': 5833,       # 10min * 35km/h = 5.8km
        'periurbain': 4167,  # 10min * 25km/h = 4.2km
        'urbain': 3333,      # 10min * 20km/h = 3.3km
        'urbain_dense': 2500 # 10min * 15km/h = 2.5km
    }
}

class DriveShortIsochroneGenerator:
    def __init__(self, input_file, output_dir):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        
        # Créer les dossiers pour chaque type d'isochrone
        for isochrone_type in ['drive_5min', 'drive_10min']:
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
        zone_radii = DRIVE_SHORT_RADII[isochrone_type]
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
                    "method": "geometric_drive_short",
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
        """Générer tous les isochrones drive courts"""
        logger.info("Génération des isochrones DRIVE 5min et 10min...")
        
        # Charger toutes les pharmacies
        df_pharmacies = pd.read_csv(self.input_file, sep=';')
        logger.info(f"Chargement de {len(df_pharmacies)} pharmacies")
        
        # Filtrer celles avec coordonnées valides
        df_valid = df_pharmacies.dropna(subset=['latitude', 'longitude'])
        
        # Valider les coordonnées France
        df_valid = df_valid[
            (df_valid['latitude'].between(41, 51)) & 
            (df_valid['longitude'].between(-5, 10))
        ]
        
        logger.info(f"Pharmacies avec coordonnées valides: {len(df_valid)}")
        
        isochrone_types = ['drive_5min', 'drive_10min']
        total_operations = len(df_valid) * len(isochrone_types)
        
        results = []
        success_count = 0
        
        with tqdm(total=total_operations, desc="Génération isochrones drive courts") as pbar:
            for _, pharmacy in df_valid.iterrows():
                pharmacy_id = str(pharmacy['id_pharmacie'])
                lat = float(pharmacy['latitude'])
                lon = float(pharmacy['longitude'])
                zone_type = pharmacy.get('type_zone', 'periurbain')
                
                result_row = {
                    'id_pharmacie': pharmacy_id,
                    'error_message': '',
                    'processing_time_seconds': 0.01,
                    'cache_hits': 0,
                    'mode_used': 'geometric_drive_short'
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
        summary_file = self.output_dir / 'drive_short_isochrones_summary.csv'
        df_results.to_csv(summary_file, index=False)
        
        logger.info(f"Traitement terminé:")
        logger.info(f"  Pharmacies traitées: {len(results)}")
        logger.info(f"  Succès complet (2/2): {success_count} ({success_count/len(results)*100:.1f}%)")
        logger.info(f"  Fichiers GeoJSON créés: {success_count * 2}")
        
        # Statistiques par type de zone
        logger.info("Répartition par type de zone:")
        zone_stats = df_valid['type_zone'].value_counts()
        for zone, count in zone_stats.items():
            logger.info(f"  {zone}: {count} pharmacies")
        
        return df_results

def main():
    parser = argparse.ArgumentParser(description='Génération des isochrones drive 5min et 10min')
    parser.add_argument('--input', default='data/input/data_cleaning/pharmacies_final.csv',
                       help='Fichier des pharmacies sources')
    parser.add_argument('--output-dir', default='data/processed/isochrones',
                       help='Dossier de sortie')
    
    args = parser.parse_args()
    
    print("🚗 GÉNÉRATION ISOCHRONES DRIVE COURTS (5min & 10min)")
    print("=" * 55)
    print(f"📁 Source: {args.input}")
    print(f"📂 Output: {args.output_dir}")
    print(f"🎯 Types: drive_5min, drive_10min")
    print()
    
    generator = DriveShortIsochroneGenerator(
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    results = generator.generate_isochrones()
    
    print("\n🎉 GÉNÉRATION TERMINÉE AVEC SUCCÈS!")
    print(f"📊 Résumé sauvé: {args.output_dir}/drive_short_isochrones_summary.csv")
    print(f"📁 Fichiers GeoJSON: {args.output_dir}/drive_5min/ et {args.output_dir}/drive_10min/")

if __name__ == "__main__":
    main()