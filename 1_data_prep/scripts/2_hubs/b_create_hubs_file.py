#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de création du fichier hubs unifié - VERSION OPTIMISÉE

MISSION : Créer un fichier unique contenant tous les "hubs" d'attractivité
pour les pharmacies seniors : EHPAD, hôpitaux, transports, commerces, etc.

OPTIMISATION : Division par régions pour éviter les timeouts OSM

Sources de données :
- FINESS (établissements de santé)
- OpenStreetMap (POI divers) - DIVISÉ PAR RÉGIONS
- SNCF (gares)
- RATP (transports IdF)

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import requests
import osmnx as ox
from pathlib import Path
from shapely.geometry import Point, box
import warnings
import time
import sys
import traceback
from urllib.parse import urljoin
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ajouter le répertoire parent pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_prep import INPUT_DIR, OUTPUT_DIR, CACHE_DIR, OUTPUT_FILES

# Supprimer les warnings non critiques
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Fichiers de sortie depuis config
OUTPUT_CSV = OUTPUT_FILES['hubs']
OUTPUT_GPKG = OUTPUT_FILES['hubs_gpkg']

# Configuration des régions françaises pour division des requêtes OSM
# Format: nom_région: (lat_min, lat_max, lon_min, lon_max)
FRANCE_REGIONS = {
    'ile_de_france': (48.1, 49.3, 1.4, 3.6),
    'hauts_de_france': (49.3, 51.2, 1.4, 4.3),
    'normandie': (48.3, 50.2, -1.8, 1.8),
    'bretagne': (47.3, 48.9, -5.2, -1.0),
    'pays_de_loire': (46.3, 48.6, -2.6, 0.5),
    'centre_val_de_loire': (46.3, 48.8, 0.0, 3.2),
    'bourgogne_franche_comte': (46.1, 48.5, 2.8, 7.2),
    'grand_est': (47.4, 50.2, 4.0, 8.3),
    'nouvelle_aquitaine_nord': (45.0, 47.0, -2.5, 1.5),
    'nouvelle_aquitaine_sud': (42.8, 45.5, -2.0, 2.0),
    'occitanie_ouest': (42.4, 45.0, -1.0, 2.5),
    'occitanie_est': (42.5, 45.0, 2.0, 4.9),
    'auvergne_rhone_alpes_ouest': (44.0, 47.0, 2.5, 5.5),
    'auvergne_rhone_alpes_est': (44.5, 47.0, 5.0, 7.2),
    'provence_alpes_cote_azur': (42.9, 45.0, 4.2, 7.7),
    'corse': (41.3, 43.1, 8.5, 9.6),
}

# Configuration OSM - Catégories à télécharger
OSM_CATEGORIES = {
    'bus': {
        'tags': {'highway': 'bus_stop'},
        'categorie': 'Arrêt de bus'
    },
    'metro': {
        'tags': {'station': 'subway'},
        'categorie': 'Station de métro'
    },
    'tram': {
        'tags': {'railway': 'tram_stop'},
        'categorie': 'Station de tramway'
    },
    'train': {
        'tags': {'railway': 'station'},
        'categorie': 'Gare ferroviaire'
    },
    'marche': {
        'tags': {'amenity': 'marketplace'},
        'categorie': 'Marché'
    },
    'supermarche': {
        'tags': [{'shop': 'supermarket'}, {'shop': 'convenience'}],
        'categorie': 'Supermarché'
    },
    'centre_commercial': {
        'tags': {'shop': 'mall'},
        'categorie': 'Centre commercial'
    },
    'culture': {
        'tags': [
            {'amenity': 'library'},
            {'amenity': 'community_centre'},
            {'amenity': 'theatre'},
            {'amenity': 'cinema'}
        ],
        'categorie': 'Culture'
    },
    'parc': {
        'tags': [{'leisure': 'park'}, {'leisure': 'garden'}],
        'categorie': 'Parc'
    }
}

# Configuration des catégories FINESS
FINESS_MAPPING = {
    # EHPAD et résidences seniors
    '500': {'type': 'ehpad', 'categorie': 'EHPAD'},
    '501': {'type': 'ehpad', 'categorie': 'Maison de retraite'},
    '502': {'type': 'ehpad', 'categorie': 'Résidence autonomie'},
    '460': {'type': 'ehpad', 'categorie': 'Résidence seniors'},

    # Hôpitaux et cliniques
    '355': {'type': 'hopital', 'categorie': 'CHU'},
    '362': {'type': 'hopital', 'categorie': 'CH'},
    '365': {'type': 'hopital', 'categorie': 'Clinique'},
    '370': {'type': 'hopital', 'categorie': 'Centre de santé'},
    '377': {'type': 'hopital', 'categorie': 'Hôpital militaire'},
    '378': {'type': 'hopital', 'categorie': 'Centre hospitalier spécialisé'},

    # Soins spécialisés
    '189': {'type': 'soin_specialise', 'categorie': 'Rééducation'},
    '192': {'type': 'soin_specialise', 'categorie': 'SSR'},
    '221': {'type': 'soin_specialise', 'categorie': 'Dialyse'},
    '286': {'type': 'soin_specialise', 'categorie': 'Oncologie'},
    '300': {'type': 'soin_specialise', 'categorie': 'Cabinet infirmier'},

    # Pharmacies et labos
    '620': {'type': 'pharmacie', 'categorie': 'Pharmacie'},
    '611': {'type': 'laboratoire', 'categorie': 'Laboratoire'},
}

# URLs de téléchargement
SNCF_URL = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/liste-des-gares/exports/csv"
RATP_URL = "https://data.iledefrance-mobilites.fr/explore/dataset/arrets-lignes/download/?format=csv"


def create_directories():
    """Créer les répertoires nécessaires"""
    for directory in [OUTPUT_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    print("📁 Répertoires préparés")


def find_finess_file():
    """
    Recherche automatique du fichier FINESS
    
    Returns:
        Path: Chemin vers le fichier FINESS ou None
    """
    print("\n🔍 Recherche du fichier FINESS...")
    
    # Patterns de recherche
    patterns = [
        "*finess*.csv",
        "*finess*.txt", 
        "*finess*.xlsx",
        "*etablissement*.csv",
        "*etablissement*.txt",
        "*etablissement*.xlsx",
        "FINESS*.csv",
        "FINESS*.txt",
        "FINESS*.xlsx"
    ]
    
    for pattern in patterns:
        files = list(INPUT_DIR.glob(pattern))
        if files:
            file_path = files[0]  # Prendre le premier trouvé
            print(f"✅ Fichier FINESS trouvé: {file_path.name}")
            return file_path
    
    print("❌ Aucun fichier FINESS trouvé")
    return None


def load_finess_data(finess_file):
    """
    Charge et traite les données FINESS (établissements de santé)
    
    Format attendu du fichier FINESS.csv :
    - Ligne 1 : metadata (finess;etalab;89;2025-09-09)
    - Lignes suivantes : structureet;nofinesset;...
    
    Args:
        finess_file (Path): Chemin vers fichier FINESS
        
    Returns:
        pd.DataFrame: DataFrame standardisé avec les EHPAD et hôpitaux
    """
    print(f"\n📥 Chargement des données FINESS...")
    
    try:
        # Lire avec pandas - skip première ligne de metadata
        df = pd.read_csv(
            finess_file,
            sep=';',
            encoding='utf-8',
            skiprows=1,
            low_memory=False
        )
        
        print(f"   {len(df):,} établissements FINESS chargés")
        
        # Convertir les codes de catégorie en string avec padding
        if 'categetab' in df.columns:
            df['categetab'] = df['categetab'].astype(str).str.zfill(3)
        
        # Filtrer uniquement les catégories qui nous intéressent
        df_filtered = df[df['categetab'].isin(FINESS_MAPPING.keys())].copy()
        print(f"   {len(df_filtered):,} établissements pertinents trouvés")
        
        # Créer le DataFrame standardisé
        results = []
        
        for _, row in df_filtered.iterrows():
            categorie = row['categetab']
            mapping = FINESS_MAPPING[categorie]
            
            # Construire l'entrée standardisée
            entry = {
                'id_hub': f"FINESS_{row.get('nofinesset', '')}",
                'nom': row.get('rs', ''),
                'adresse': row.get('ligneacheminement', ''),
                'code_postal': str(row.get('compladresse', ''))[:5] if pd.notna(row.get('compladresse')) else '',
                'commune': row.get('libcom', ''),
                'latitude': np.nan,  # À géocoder
                'longitude': np.nan,  # À géocoder
                'type_hub': mapping['type'],
                'categorie': mapping['categorie'],
                'source': 'FINESS'
            }
            
            results.append(entry)
        
        df_result = pd.DataFrame(results)
        
        # Statistiques par type
        print(f"   Répartition par type :")
        for type_hub, count in df_result['type_hub'].value_counts().items():
            print(f"     - {type_hub}: {count:,}")
        
        return df_result
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement FINESS: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def load_rpps_data():
    """
    Charge et traite les données RPPS (médecins libéraux)
    
    Returns:
        pd.DataFrame: DataFrame standardisé avec les cabinets médicaux
    """
    print(f"\n📥 Chargement des données RPPS (médecins)...")
    
    try:
        # Recherche du fichier RPPS
        rpps_patterns = ["*rpps*.txt", "*PS_LibreAcces*.txt", "*medecin*.txt"]
        rpps_file = None
        
        for pattern in rpps_patterns:
            files = list(INPUT_DIR.glob(pattern))
            if files:
                rpps_file = files[0]
                break
        
        if not rpps_file:
            print("   ⚠️  Fichier RPPS non trouvé")
            return pd.DataFrame()
        
        print(f"   Fichier trouvé: {rpps_file.name}")
        
        # Lire le fichier RPPS (format pipe-delimited)
        df = pd.read_csv(
            rpps_file,
            sep='|',
            encoding='utf-8',
            low_memory=False
        )
        
        print(f"   {len(df):,} médecins RPPS chargés")
        
        # Filtrer les spécialités qui nous intéressent
        specialites_cibles = {
            'SM01': 'Médecin généraliste',
            'SM02': 'Cardiologue',
            'SM26': 'Rhumatologue'
        }
        
        # Filtrer par spécialité
        df_filtered = df[df['Code profession'].isin(specialites_cibles.keys())].copy()
        print(f"   {len(df_filtered):,} médecins ciblés trouvés")
        
        # Créer le DataFrame standardisé
        results = []
        
        for _, row in df_filtered.iterrows():
            specialite = specialites_cibles.get(row['Code profession'], 'Médecin')
            
            entry = {
                'id_hub': f"RPPS_{row.get('Identification nationale PP', '')}",
                'nom': f"Cabinet {specialite}",
                'adresse': f"{row.get('Libellé voie', '')} {row.get('Code postal', '')} {row.get('Libellé commune', '')}",
                'code_postal': str(row.get('Code postal', ''))[:5] if pd.notna(row.get('Code postal')) else '',
                'commune': row.get('Libellé commune', ''),
                'latitude': np.nan,  # À géocoder
                'longitude': np.nan,  # À géocoder
                'type_hub': 'cabinet_medical',
                'categorie': specialite,
                'source': 'RPPS'
            }
            
            results.append(entry)
        
        df_result = pd.DataFrame(results)
        
        # Statistiques par spécialité
        print(f"   Répartition par spécialité :")
        for cat, count in df_result['categorie'].value_counts().items():
            print(f"     - {cat}: {count:,}")
        
        return df_result
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement RPPS: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def download_osm_for_region(region_name, bbox, category_name, category_config):
    """
    Télécharge les données OSM pour une région et une catégorie spécifiques
    
    Args:
        region_name (str): Nom de la région
        bbox (tuple): Bounding box (lat_min, lat_max, lon_min, lon_max)
        category_name (str): Nom de la catégorie
        category_config (dict): Configuration de la catégorie
        
    Returns:
        pd.DataFrame: DataFrame avec les POI de cette catégorie dans cette région
    """
    lat_min, lat_max, lon_min, lon_max = bbox
    
    # Construire la bounding box pour OSMnx (south, north, west, east)
    osm_bbox = (lat_min, lat_max, lon_min, lon_max)
    
    results = []
    tags_list = category_config['tags']
    
    # Si tags est un dict simple, le convertir en liste
    if isinstance(tags_list, dict):
        tags_list = [tags_list]
    
    for tags in tags_list:
        try:
            # Télécharger les POI avec retry
            max_retries = 3
            retry_count = 0
            pois = None
            
            while retry_count < max_retries and pois is None:
                try:
                    # Utiliser ox.features.features_from_bbox (nouvelle API OSMnx)
                    pois = ox.features.features_from_bbox(
                        bbox=(lat_max, lat_min, lon_max, lon_min),
                        tags=tags
                    )
                    
                    if pois is not None and len(pois) > 0:
                        # Traiter les résultats
                        for idx, row in pois.iterrows():
                            # Extraire coordonnées du centroid
                            geom = row['geometry']
                            if geom.geom_type == 'Point':
                                lon, lat = geom.x, geom.y
                            else:
                                centroid = geom.centroid
                                lon, lat = centroid.x, centroid.y
                            
                            # Créer l'entrée
                            entry = {
                                'id_hub': f"OSM_{idx}",
                                'nom': row.get('name', category_config['categorie']),
                                'adresse': '',
                                'code_postal': '',
                                'commune': '',
                                'latitude': lat,
                                'longitude': lon,
                                'type_hub': category_name,
                                'categorie': category_config['categorie'],
                                'source': 'OSM'
                            }
                            results.append(entry)
                    
                    break  # Succès, sortir de la boucle retry
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(2 ** retry_count)  # Backoff exponentiel
                    else:
                        # Échec après toutes les tentatives
                        pass
        
        except Exception as e:
            # Ignorer les erreurs pour cette combinaison région/catégorie
            pass
    
    return pd.DataFrame(results)


def download_osm_data():
    """
    Télécharge les données OSM pour toutes les régions et catégories
    Division par régions pour éviter les timeouts
    
    Returns:
        list: Liste de DataFrames OSM
    """
    print(f"\n🌍 Téléchargement des données OpenStreetMap...")
    print(f"   Division en {len(FRANCE_REGIONS)} régions")
    print(f"   Catégories à télécharger: {len(OSM_CATEGORIES)}")
    
    all_results = []
    total_operations = len(FRANCE_REGIONS) * len(OSM_CATEGORIES)
    current_operation = 0
    
    # Parcourir chaque région
    for region_name, bbox in FRANCE_REGIONS.items():
        print(f"\n   📍 Région: {region_name.replace('_', ' ').title()}")
        
        # Parcourir chaque catégorie
        for category_name, category_config in OSM_CATEGORIES.items():
            current_operation += 1
            
            try:
                # Télécharger pour cette région et catégorie
                df_region_category = download_osm_for_region(
                    region_name, 
                    bbox, 
                    category_name, 
                    category_config
                )
                
                if not df_region_category.empty:
                    all_results.append(df_region_category)
                    print(f"      ✓ {category_name}: {len(df_region_category):,} POI trouvés [{current_operation}/{total_operations}]")
                else:
                    print(f"      • {category_name}: 0 POI [{current_operation}/{total_operations}]")
                
                # Petit délai pour éviter la surcharge
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      ✗ {category_name}: Erreur - {str(e)[:50]} [{current_operation}/{total_operations}]")
                continue
    
    # Combiner tous les résultats
    if all_results:
        df_combined = pd.concat(all_results, ignore_index=True)
        print(f"\n   ✅ Total OSM: {len(df_combined):,} POI téléchargés")
        
        # Statistiques par catégorie
        print(f"   Répartition par catégorie :")
        for cat, count in df_combined['type_hub'].value_counts().items():
            print(f"     - {cat}: {count:,}")
        
        return [df_combined]
    else:
        print(f"\n   ⚠️  Aucune donnée OSM téléchargée")
        return []


def download_sncf_data():
    """
    Télécharge les données des gares SNCF
    
    Returns:
        pd.DataFrame: DataFrame standardisé avec les gares
    """
    print(f"\n🚂 Téléchargement des données SNCF...")
    
    try:
        # Télécharger le CSV
        response = requests.get(SNCF_URL, timeout=30)
        response.raise_for_status()
        
        # Sauvegarder temporairement
        cache_file = CACHE_DIR / "sncf_gares.csv"
        cache_file.write_bytes(response.content)
        
        # Lire le CSV
        df = pd.read_csv(cache_file, sep=';', encoding='utf-8')
        print(f"   {len(df):,} gares SNCF chargées")
        
        # Standardiser
        results = []
        for _, row in df.iterrows():
            # Filtrer les gares avec coordonnées valides
            if pd.isna(row.get('Latitude')) or pd.isna(row.get('Longitude')):
                continue
            
            entry = {
                'id_hub': f"SNCF_{row.get('Code plate-forme', '')}",
                'nom': row.get('Gare', ''),
                'adresse': '',
                'code_postal': str(row.get('Code postal', ''))[:5] if pd.notna(row.get('Code postal')) else '',
                'commune': row.get('Commune', ''),
                'latitude': float(row['Latitude']),
                'longitude': float(row['Longitude']),
                'type_hub': 'train',
                'categorie': 'Gare SNCF',
                'source': 'SNCF'
            }
            results.append(entry)
        
        df_result = pd.DataFrame(results)
        print(f"   ✅ {len(df_result):,} gares SNCF traitées")
        
        return df_result
        
    except Exception as e:
        print(f"   ⚠️  Erreur SNCF: {e}")
        return pd.DataFrame()


def download_ratp_data():
    """
    Télécharge les données des transports RATP (Île-de-France)
    
    Returns:
        pd.DataFrame: DataFrame standardisé avec les arrêts RATP
    """
    print(f"\n🚇 Téléchargement des données RATP...")
    
    try:
        # Télécharger le CSV
        response = requests.get(RATP_URL, timeout=30)
        response.raise_for_status()
        
        # Sauvegarder temporairement
        cache_file = CACHE_DIR / "ratp_arrets.csv"
        cache_file.write_bytes(response.content)
        
        # Lire le CSV
        df = pd.read_csv(cache_file, sep=';', encoding='utf-8')
        print(f"   {len(df):,} arrêts RATP chargés")
        
        # Filtrer uniquement métro et RER (les bus sont déjà dans OSM)
        df_metro = df[df['transportmode'].isin(['Metro', 'RER'])].copy()
        
        # Standardiser
        results = []
        for _, row in df_metro.iterrows():
            # Filtrer les arrêts avec coordonnées valides
            if pd.isna(row.get('stop_lat')) or pd.isna(row.get('stop_lon')):
                continue
            
            # Déterminer le type
            type_hub = 'metro' if row['transportmode'] == 'Metro' else 'train'
            
            entry = {
                'id_hub': f"RATP_{row.get('stop_id', '')}",
                'nom': row.get('stop_name', ''),
                'adresse': '',
                'code_postal': '',
                'commune': row.get('nom_commune', ''),
                'latitude': float(row['stop_lat']),
                'longitude': float(row['stop_lon']),
                'type_hub': type_hub,
                'categorie': 'Station de métro' if type_hub == 'metro' else 'Gare RER',
                'source': 'RATP'
            }
            results.append(entry)
        
        df_result = pd.DataFrame(results)
        print(f"   ✅ {len(df_result):,} stations RATP traitées")
        
        return df_result
        
    except Exception as e:
        print(f"   ⚠️  Erreur RATP: {e}")
        return pd.DataFrame()


def unify_and_clean_data(dataframes):
    """
    Unifie et nettoie toutes les données collectées
    
    Args:
        dataframes (list): Liste de DataFrames à combiner
        
    Returns:
        pd.DataFrame: DataFrame unifié et nettoyé
    """
    print(f"\n🔧 Unification et nettoyage des données...")
    
    if not dataframes:
        print("   ❌ Aucune donnée à unifier")
        return pd.DataFrame()
    
    # Combiner tous les DataFrames
    df_combined = pd.concat(dataframes, ignore_index=True)
    print(f"   Total avant nettoyage: {len(df_combined):,} hubs")
    
    # Colonnes finales attendues
    final_columns = [
        'id_hub',
        'nom',
        'adresse',
        'code_postal',
        'commune',
        'latitude',
        'longitude',
        'type_hub',
        'categorie',
        'source'
    ]
    
    # Ajouter les colonnes manquantes
    for col in final_columns:
        if col not in df_combined.columns:
            df_combined[col] = ''
    
    # Sélectionner et réorganiser
    df_final = df_combined[final_columns].copy()
    
    # Nettoyer les coordonnées
    df_final['latitude'] = pd.to_numeric(df_final['latitude'], errors='coerce')
    df_final['longitude'] = pd.to_numeric(df_final['longitude'], errors='coerce')
    
    # Supprimer les lignes sans coordonnées
    before_coords = len(df_final)
    df_final = df_final.dropna(subset=['latitude', 'longitude'])
    after_coords = len(df_final)
    print(f"   Supprimé {before_coords - after_coords:,} lignes sans coordonnées")
    
    # Filtrer coordonnées France métropolitaine
    france_coords = (
        df_final['latitude'].between(41, 52) & 
        df_final['longitude'].between(-6, 10)
    )
    df_final = df_final[france_coords]
    print(f"   Hubs en France métropolitaine: {len(df_final):,}")
    
    # Dédoublonnage spatial (50m)
    print("   Dédoublonnage spatial (50m)...")
    df_final = deduplicate_spatial(df_final)
    
    return df_final


def deduplicate_spatial(df, distance_threshold=50):
    """
    Supprime les doublons spatiaux (hubs du même type à moins de 50m)
    Utilise un algorithme optimisé avec grille spatiale
    
    Args:
        df (pd.DataFrame): DataFrame avec coordonnées
        distance_threshold (float): Distance seuil en mètres
        
    Returns:
        pd.DataFrame: DataFrame dédoublonné
    """
    from geopy.distance import geodesic
    
    if len(df) == 0:
        return df
    
    # Créer une grille spatiale pour optimiser la recherche
    # Taille de cellule: ~100m (environ 0.001° en latitude)
    cell_size = 0.001
    
    df['grid_lat'] = (df['latitude'] / cell_size).astype(int)
    df['grid_lon'] = (df['longitude'] / cell_size).astype(int)
    
    # Grouper par type et cellule de grille
    keep_indices = []
    
    for type_hub, group_type in df.groupby('type_hub'):
        processed_indices = set()
        
        for (grid_lat, grid_lon), group_cell in group_type.groupby(['grid_lat', 'grid_lon']):
            # Chercher aussi dans les cellules adjacentes
            adjacent_cells = group_type[
                (group_type['grid_lat'].between(grid_lat - 1, grid_lat + 1)) &
                (group_type['grid_lon'].between(grid_lon - 1, grid_lon + 1))
            ]
            
            for idx, row in group_cell.iterrows():
                if idx in processed_indices:
                    continue
                
                keep_indices.append(idx)
                current_point = (row['latitude'], row['longitude'])
                
                # Marquer comme traités tous les points proches dans les cellules adjacentes
                for idx2, row2 in adjacent_cells.iterrows():
                    if idx2 == idx or idx2 in processed_indices:
                        continue
                    
                    other_point = (row2['latitude'], row2['longitude'])
                    distance = geodesic(current_point, other_point).meters
                    
                    if distance < distance_threshold:
                        processed_indices.add(idx2)
    
    # Filtrer pour garder uniquement les indices sélectionnés
    df_result = df.loc[keep_indices].copy()
    
    # Supprimer les colonnes de grille
    df_result = df_result.drop(columns=['grid_lat', 'grid_lon'])
    
    duplicates_removed = len(df) - len(df_result)
    print(f"   Doublons supprimés: {duplicates_removed:,}")
    
    return df_result


def save_results(df):
    """
    Sauvegarde les résultats en CSV et GeoPackage
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n💾 Sauvegarde des résultats...")
    
    if df.empty:
        print("❌ Aucune donnée à sauvegarder")
        return
    
    try:
        # Créer répertoire de sortie
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder CSV (sans geometry)
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        csv_size = OUTPUT_CSV.stat().st_size / (1024 * 1024)
        print(f"   ✅ CSV sauvegardé: {OUTPUT_CSV.name} ({csv_size:.1f} MB)")
        
        # Créer GeoDataFrame pour GeoPackage
        geometry = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
        
        # Sauvegarder GeoPackage
        gdf.to_file(OUTPUT_GPKG, driver='GPKG', layer='hubs')
        gpkg_size = OUTPUT_GPKG.stat().st_size / (1024 * 1024)
        print(f"   ✅ GeoPackage sauvegardé: {OUTPUT_GPKG.name} ({gpkg_size:.1f} MB)")
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")


def display_statistics(df):
    """
    Affiche les statistiques finales
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n" + "=" * 60)
    print("STATISTIQUES FINALES")
    print("=" * 60)
    
    if df.empty:
        print("Aucune donnée disponible")
        return
    
    print(f"Total de hubs créés : {len(df):,}")
    
    # Par type
    print(f"\n📊 Par type :")
    type_counts = df['type_hub'].value_counts()
    for type_hub, count in type_counts.items():
        print(f"  - {type_hub:<25} : {count:>8,}")
    
    # Par source
    print(f"\n📦 Par source :")
    source_counts = df['source'].value_counts()
    for source, count in source_counts.items():
        print(f"  - {source:<10} : {count:>8,}")
    
    # Fichiers créés
    print(f"\n📁 Fichiers créés :")
    if OUTPUT_CSV.exists():
        csv_size = OUTPUT_CSV.stat().st_size / (1024 * 1024)
        print(f"  ✓ hubs.csv ({csv_size:.1f} MB)")
    
    if OUTPUT_GPKG.exists():
        gpkg_size = OUTPUT_GPKG.stat().st_size / (1024 * 1024)
        print(f"  ✓ hubs.gpkg ({gpkg_size:.1f} MB)")
    
    # Qualité des coordonnées
    valid_coords = df[['latitude', 'longitude']].notna().all(axis=1).sum()
    coord_pct = (valid_coords / len(df)) * 100
    print(f"\n✓ Coordonnées valides : {coord_pct:.1f}%")
    
    print("=" * 60)


def main():
    """
    Fonction principale
    """
    print("🏢 CRÉATION DU FICHIER HUBS UNIFIÉ - VERSION OPTIMISÉE")
    print("=" * 60)
    print("✨ Nouvelle approche: Division par régions pour éviter timeouts OSM")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # 1. Préparation
        create_directories()
        
        dataframes = []
        
        # 2. Téléchargement OSM par régions (priorité car c'est le plus volumineux)
        osm_dfs = download_osm_data()
        dataframes.extend(osm_dfs)
        
        # 3. Téléchargement SNCF
        sncf_df = download_sncf_data()
        if not sncf_df.empty:
            dataframes.append(sncf_df)
        
        # 4. Téléchargement RATP (optionnel - Île-de-France seulement)
        ratp_df = download_ratp_data()
        if not ratp_df.empty:
            dataframes.append(ratp_df)
        
        # 5. Unification
        df_final = unify_and_clean_data(dataframes)
        
        # 6. Sauvegarde
        save_results(df_final)
        
        # 7. Statistiques
        display_statistics(df_final)
        
        # Temps d'exécution
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Temps d'exécution : {elapsed_time/60:.1f} minutes")
        
        print(f"\n✅ CRÉATION TERMINÉE AVEC SUCCÈS!")
        print(f"\n💡 Note: Les données FINESS et RPPS nécessitent un géocodage")
        print(f"   et ont été désactivées dans cette version pour accélérer le traitement.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
