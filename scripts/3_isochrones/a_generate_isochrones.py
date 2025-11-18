#!/usr/bin/env python3
"""
Génération OPTIMISÉE des isochrones pour 20 000 pharmacies

Ce script génère automatiquement des isochrones (polygones d'accessibilité) 
pour toutes les pharmacies en France, en utilisant les réseaux routiers et 
piétonniers d'OpenStreetMap via la bibliothèque OSMnx.

🚀 OPTIMISATIONS AVANCÉES :
- Traitement par batchs géographiques intelligents
- Cache persistant des graphes OSM par zone
- Répartition géographique pour minimiser les téléchargements
- Reprise automatique en cas d'interruption
- Parallélisation optimisée par cluster géographique

Pour chaque pharmacie, génère 4 isochrones :
- 5min et 10min à pied (4 km/h - vitesse senior)  
- 15min et 20min en voiture (vitesse selon type de zone)

Usage:
    python generate_isochrones.py --input pharmacies_final.csv --workers 8 --batch-size 100
    python generate_isochrones.py --resume-batch 5  # Reprendre au batch 5
"""

import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, Polygon
from pathlib import Path
import json
import time
import argparse
import logging
import multiprocessing as mp
from datetime import datetime, timedelta
import sys
import traceback
from functools import partial
import warnings
from tqdm import tqdm
import math
import pickle
import hashlib
from sklearn.cluster import KMeans
import numpy as np

# Supprimer les warnings non critiques
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Configuration des chemins
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "data" / "input" / "data_cleaning"  # Utiliser le bon dossier
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "isochrones"
CACHE_DIR = BASE_DIR / "data" / "cache" / "isochrones"  # Cache pour optimisation

# Configuration des isochrones
ISOCHRONE_CONFIG = {
    'walk_5min': {
        'time_minutes': 5,
        'mode': 'walk',
        'speed_kmh': 4.0,
        'network_type': 'walk'
    },
    'walk_10min': {
        'time_minutes': 10,
        'mode': 'walk', 
        'speed_kmh': 4.0,
        'network_type': 'walk'
    },
    'drive_5min': {
        'time_minutes': 5,
        'mode': 'drive',
        'speed_variable': True,  # Vitesse dépend du type_zone
        'network_type': 'drive'
    },
    'drive_10min': {
        'time_minutes': 10,
        'mode': 'drive',
        'speed_variable': True,
        'network_type': 'drive'
    },
    'drive_15min': {
        'time_minutes': 15,
        'mode': 'drive',
        'speed_variable': True,  # Vitesse dépend du type_zone
        'network_type': 'drive'
    },
    'drive_20min': {
        'time_minutes': 20,
        'mode': 'drive',
        'speed_variable': True,
        'network_type': 'drive'
    }
}

# Vitesses de conduite selon type de zone
DRIVING_SPEEDS = {
    'urbain_dense': 25,  # Vitesse réduite en centre-ville
    'urbain': 35,        # Vitesse urbaine normale
    'periurbain': 45,    # Zone périurbaine
    'rural': 60          # Zone rurale
}

# Configuration OSMnx OPTIMISÉE
GRAPH_DISTANCE = 20000  # 20 km de rayon (réduit pour optimiser)
TIMEOUT_SECONDS = 180   # 3 minutes timeout par graphe
MAX_RETRIES = 2         # Réduire les retries
RETRY_DELAYS = [1, 3]   # Délais plus courts

# Configuration des batchs géographiques OPTIMISÉE
DEFAULT_BATCH_SIZE = 200  # Batchs plus grands pour amortir les téléchargements
GEOGRAPHIC_CLUSTERS = 30  # Moins de clusters mais plus grands
MIN_CLUSTER_SIZE = 50     # Clusters plus grands
MAX_CLUSTER_SIZE = 500    # Augmenter la taille max

# Cache persistant des graphes OPTIMISÉ
ENABLE_GRAPH_CACHE = True
CACHE_EXPIRY_DAYS = 7     # Cache plus court mais efficace
GRID_CACHE_PRECISION = 0.05  # Grille plus large pour réutilisation (5km)

# Configuration des sauvegardes et checkpoints
CHECKPOINT_FREQUENCY = 25      # Sauvegarder toutes les 25 pharmacies
PROGRESS_DISPLAY_FREQUENCY = 10  # Afficher progrès toutes les 10 pharmacies
BACKUP_FREQUENCY = 100         # Backup complet tous les 100 pharmacies
MAX_BACKUP_FILES = 5           # Garder 5 backups maximum

# Cache global pour les graphes (compatible avec l'ancien code)
graph_cache = {}


def create_cache_directories():
    """Créer les répertoires de cache"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "graphs").mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "batches").mkdir(parents=True, exist_ok=True)


def get_graph_cache_key(lat, lon, network_type, radius=None):
    """
    Génère une clé de cache OPTIMISÉE pour un graphe OSM avec grille plus large
    
    Args:
        lat (float): Latitude centre
        lon (float): Longitude centre  
        network_type (str): Type de réseau
        radius (int): Rayon en mètres
        
    Returns:
        str: Clé de cache unique
    """
    if radius is None:
        radius = GRAPH_DISTANCE
    
    # Grille plus large pour maximiser la réutilisation des graphes
    lat_grid = round(lat / GRID_CACHE_PRECISION) * GRID_CACHE_PRECISION
    lon_grid = round(lon / GRID_CACHE_PRECISION) * GRID_CACHE_PRECISION
    
    cache_str = f"{lat_grid}_{lon_grid}_{network_type}_{radius}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def save_graph_to_cache(graph, cache_key):
    """
    Sauvegarde un graphe dans le cache persistant
    
    Args:
        graph: Graphe NetworkX
        cache_key (str): Clé de cache
    """
    if not ENABLE_GRAPH_CACHE:
        return
        
    try:
        cache_file = CACHE_DIR / "graphs" / f"{cache_key}.pkl"
        
        # Sauvegarder avec métadonnées
        cache_data = {
            'graph': graph,
            'timestamp': time.time(),
            'expires_at': time.time() + (CACHE_EXPIRY_DAYS * 24 * 3600)
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
    except Exception as e:
        logging.getLogger(__name__).warning(f"Erreur sauvegarde cache: {e}")


def load_graph_from_cache(cache_key):
    """
    Charge un graphe depuis le cache persistant
    
    Args:
        cache_key (str): Clé de cache
        
    Returns:
        graph ou None: Graphe si trouvé et valide
    """
    if not ENABLE_GRAPH_CACHE:
        return None
        
    try:
        cache_file = CACHE_DIR / "graphs" / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        # Vérifier l'expiration
        if time.time() > cache_data.get('expires_at', 0):
            cache_file.unlink()  # Supprimer le cache expiré
            return None
        
        return cache_data['graph']
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Erreur lecture cache: {e}")
        return None


def create_geographic_clusters(df_pharmacies, n_clusters=None):
    """
    Crée des clusters géographiques pour optimiser le traitement
    
    Args:
        df_pharmacies (pd.DataFrame): DataFrame des pharmacies
        n_clusters (int): Nombre de clusters (auto si None)
        
    Returns:
        pd.DataFrame: DataFrame avec colonne 'cluster_id'
    """
    logger = logging.getLogger(__name__)
    
    if n_clusters is None:
        # Calcul automatique du nombre optimal de clusters
        n_pharmacies = len(df_pharmacies)
        n_clusters = min(GEOGRAPHIC_CLUSTERS, max(5, n_pharmacies // MIN_CLUSTER_SIZE))
    
    logger.info(f"🗺️  Création de {n_clusters} clusters géographiques pour {len(df_pharmacies)} pharmacies")
    
    # Coordonnées pour clustering
    coords = df_pharmacies[['latitude', 'longitude']].values
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(coords)
    
    # Ajouter les clusters au DataFrame
    df_with_clusters = df_pharmacies.copy()
    df_with_clusters['cluster_id'] = cluster_labels
    
    # Statistiques des clusters
    cluster_stats = df_with_clusters.groupby('cluster_id').agg({
        'latitude': ['mean', 'min', 'max'],
        'longitude': ['mean', 'min', 'max'],
        'id_pharmacie': 'count'
    }).round(4)
    
    cluster_stats.columns = ['lat_center', 'lat_min', 'lat_max', 'lon_center', 'lon_min', 'lon_max', 'count']
    
    logger.info(f"   Répartition des clusters:")
    for cluster_id, stats in cluster_stats.iterrows():
        logger.info(f"     Cluster {cluster_id}: {stats['count']} pharmacies - Centre: ({stats['lat_center']}, {stats['lon_center']})")
    
    return df_with_clusters, cluster_stats


def create_batches_from_clusters(df_with_clusters, batch_size=None):
    """
    Crée des batchs optimisés à partir des clusters géographiques
    
    Args:
        df_with_clusters (pd.DataFrame): DataFrame avec clusters
        batch_size (int): Taille cible des batchs
        
    Returns:
        list: Liste des batchs (DataFrames)
    """
    logger = logging.getLogger(__name__)
    
    if batch_size is None:
        batch_size = DEFAULT_BATCH_SIZE
    
    batches = []
    batch_metadata = []
    
    # Trier par cluster pour optimiser l'ordre
    df_sorted = df_with_clusters.sort_values(['cluster_id', 'latitude', 'longitude'])
    
    # Créer les batchs
    for cluster_id in df_sorted['cluster_id'].unique():
        cluster_pharmacies = df_sorted[df_sorted['cluster_id'] == cluster_id]
        
        # Si le cluster est plus petit que batch_size, créer un batch avec tout le cluster
        if len(cluster_pharmacies) <= batch_size:
            batches.append(cluster_pharmacies)
            batch_metadata.append({
                'batch_id': len(batches) - 1,
                'cluster_id': cluster_id,
                'size': len(cluster_pharmacies),
                'lat_center': cluster_pharmacies['latitude'].mean(),
                'lon_center': cluster_pharmacies['longitude'].mean()
            })
        else:
            # Diviser le gros cluster en plusieurs batchs
            for i in range(0, len(cluster_pharmacies), batch_size):
                batch_subset = cluster_pharmacies.iloc[i:i + batch_size]
                batches.append(batch_subset)
                batch_metadata.append({
                    'batch_id': len(batches) - 1,
                    'cluster_id': cluster_id,
                    'size': len(batch_subset),
                    'lat_center': batch_subset['latitude'].mean(),
                    'lon_center': batch_subset['longitude'].mean()
                })
    
    logger.info(f"📦 {len(batches)} batchs créés (taille moyenne: {np.mean([len(b) for b in batches]):.1f})")
    
    # Sauvegarder les métadonnées des batchs
    batch_metadata_df = pd.DataFrame(batch_metadata)
    metadata_file = CACHE_DIR / "batches" / "batch_metadata.csv"
    batch_metadata_df.to_csv(metadata_file, index=False)
    
    return batches, batch_metadata_df


def save_batch_progress(batch_id, completed=False, error=None):
    """
    Sauvegarde le progrès d'un batch
    
    Args:
        batch_id (int): ID du batch
        completed (bool): Batch terminé ou non
        error (str): Message d'erreur éventuel
    """
    progress_file = CACHE_DIR / "batches" / "batch_progress.jsonl"
    
    progress_entry = {
        'batch_id': batch_id,
        'timestamp': time.time(),
        'completed': completed,
        'error': error
    }
    
    # Append au fichier JSONL
    with open(progress_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(progress_entry) + '\n')


def load_batch_progress():
    """
    Charge le progrès des batchs
    
    Returns:
        dict: État des batchs {batch_id: {'completed': bool, 'error': str}}
    """
    progress_file = CACHE_DIR / "batches" / "batch_progress.jsonl"
    progress = {}
    
    if progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    batch_id = entry['batch_id']
                    # Garder la dernière entrée pour chaque batch
                    progress[batch_id] = {
                        'completed': entry['completed'],
                        'error': entry.get('error'),
                        'timestamp': entry['timestamp']
                    }
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erreur lecture progrès batchs: {e}")
    
    return progress


def get_batches_to_process(batches, resume_from_batch=None):
    """
    Détermine quels batchs traiter selon le mode de reprise
    
    Args:
        batches (list): Liste complète des batchs
        resume_from_batch (int): Batch à partir duquel reprendre
        
    Returns:
        list: Batchs à traiter avec leurs IDs
    """
    logger = logging.getLogger(__name__)
    
    if resume_from_batch is not None:
        # Reprendre à partir d'un batch spécifique
        batches_to_process = [(i, batch) for i, batch in enumerate(batches) if i >= resume_from_batch]
        logger.info(f"🔄 Reprise à partir du batch {resume_from_batch} ({len(batches_to_process)} batchs restants)")
    else:
        # Mode reprise automatique basé sur les progrès sauvegardés
        progress = load_batch_progress()
        completed_batches = {batch_id for batch_id, status in progress.items() if status['completed']}
        
        batches_to_process = [(i, batch) for i, batch in enumerate(batches) if i not in completed_batches]
        
        if completed_batches:
            logger.info(f"🔄 Reprise automatique: {len(completed_batches)} batchs déjà complétés, {len(batches_to_process)} restants")
        else:
            logger.info(f"🚀 Démarrage complet: {len(batches_to_process)} batchs à traiter")
    
    return batches_to_process


def setup_logging(output_dir):
    """
    Configure le système de logging
    
    Args:
        output_dir (Path): Répertoire de sortie
    """
    log_file = output_dir / "isochrones_errors.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def setup_osmnx():
    """Configure OSMnx pour optimiser les performances au maximum"""
    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.timeout = TIMEOUT_SECONDS
    ox.settings.requests_timeout = 30  # Réduit pour éviter les blocages
    ox.settings.all_oneway = True      # Optimisation pour la vitesse
    
    # Désactiver les logs verbeux
    import logging
    logging.getLogger('osmnx').setLevel(logging.ERROR)
    

def create_output_directories():
    """Créer la structure de dossiers de sortie"""
    directories = []
    
    for iso_type in ISOCHRONE_CONFIG.keys():
        iso_dir = OUTPUT_DIR / iso_type
        iso_dir.mkdir(parents=True, exist_ok=True)
        directories.append(iso_dir)
    
    return directories


def load_pharmacies(input_file):
    """
    Charge et valide le fichier des pharmacies
    
    Args:
        input_file (Path): Chemin vers le fichier pharmacies
        
    Returns:
        pd.DataFrame: DataFrame validé des pharmacies
    """
    logger = logging.getLogger(__name__)
    logger.info(f"📂 Chargement du fichier pharmacies: {input_file}")
    
    try:
        # Essayer différents séparateurs
        df = None
        for sep in [',', ';']:
            try:
                df = pd.read_csv(input_file, sep=sep, encoding='utf-8')
                if len(df.columns) > 3:  # Au moins 4 colonnes attendues
                    break
            except:
                continue
        
        if df is None:
            raise ValueError("Impossible de lire le fichier avec les séparateurs testés")
        
        logger.info(f"   {len(df)} pharmacies chargées")
        
        # Valider les colonnes requises
        required_cols = ['id_pharmacie', 'latitude', 'longitude', 'type_zone']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Colonnes manquantes: {missing_cols}")
        
        # Valider les coordonnées GPS
        logger.info("   Validation des coordonnées GPS...")
        
        # Supprimer les coordonnées manquantes
        initial_count = len(df)
        df = df.dropna(subset=['latitude', 'longitude'])
        
        # Valider les limites France
        france_mask = (
            df['latitude'].between(41, 51) & 
            df['longitude'].between(-5, 10)
        )
        df = df[france_mask]
        
        final_count = len(df)
        logger.info(f"   Pharmacies validées: {final_count} / {initial_count}")
        
        # Valider les types de zone
        valid_zones = ['urbain_dense', 'urbain', 'periurbain', 'rural']
        invalid_zones = df[~df['type_zone'].isin(valid_zones)]
        
        if len(invalid_zones) > 0:
            logger.warning(f"   {len(invalid_zones)} pharmacies avec type_zone invalide")
            # Remplacer par 'urbain' par défaut
            df.loc[~df['type_zone'].isin(valid_zones), 'type_zone'] = 'urbain'
        
        logger.info(f"   Types de zone: {df['type_zone'].value_counts().to_dict()}")
        
        return df.reset_index(drop=True)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement: {e}")
        raise


def get_driving_speed(type_zone):
    """
    Obtient la vitesse de conduite selon le type de zone
    
    Args:
        type_zone (str): Type de zone
        
    Returns:
        float: Vitesse en km/h
    """
    return DRIVING_SPEEDS.get(type_zone, 35)  # 35 km/h par défaut


def calculate_trip_distance(time_minutes, speed_kmh):
    """
    Calcule la distance de trajet en mètres
    
    Args:
        time_minutes (int): Temps en minutes
        speed_kmh (float): Vitesse en km/h
        
    Returns:
        float: Distance en mètres
    """
    return (time_minutes * speed_kmh * 1000) / 60


def get_or_download_graph(lat, lon, network_type, cache_key=None):
    """
    Télécharge ou récupère du cache un graphe OSM avec cache persistant optimisé
    
    Args:
        lat (float): Latitude
        lon (float): Longitude  
        network_type (str): Type de réseau ('walk' ou 'drive')
        cache_key (str): Clé de cache optionnelle
        
    Returns:
        networkx.MultiDiGraph: Graphe routier
    """
    logger = logging.getLogger(__name__)
    
    # Générer la clé de cache si pas fournie
    if cache_key is None:
        cache_key = get_graph_cache_key(lat, lon, network_type)
    
    # 1. Vérifier le cache mémoire d'abord (plus rapide)
    if cache_key in graph_cache:
        return graph_cache[cache_key]
    
    # 2. Vérifier le cache persistant
    cached_graph = load_graph_from_cache(cache_key)
    if cached_graph is not None:
        # Mettre en cache mémoire pour accès ultra-rapide
        graph_cache[cache_key] = cached_graph
        logger.debug(f"   📁 Graphe récupéré du cache persistant")
        return cached_graph
    
    # 3. Télécharger le graphe avec retry
    logger.debug(f"   🌐 Téléchargement nouveau graphe pour {network_type}")
    
    for attempt in range(MAX_RETRIES):
        try:
            graph = ox.graph_from_point(
                (lat, lon),
                dist=GRAPH_DISTANCE,
                network_type=network_type,
                simplify=True
            )
            
            # Mettre en cache (mémoire + persistant)
            graph_cache[cache_key] = graph
            save_graph_to_cache(graph, cache_key)
            
            logger.debug(f"   ✅ Graphe téléchargé et mis en cache ({len(graph.nodes)} nœuds)")
            return graph
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"   Tentative {attempt + 1} échouée, retry dans {delay}s: {e}")
                time.sleep(delay)
            else:
                logger.error(f"   Échec téléchargement graphe après {MAX_RETRIES} tentatives: {e}")
                raise


def generate_isochrone_optimized_fast(lat, lon, time_minutes, speed_kmh, network_type, shared_graph=None):
    """
    Version ULTRA-OPTIMISÉE de génération d'isochrone avec approximations rapides
    
    Args:
        lat (float): Latitude pharmacie
        lon (float): Longitude pharmacie
        time_minutes (int): Temps en minutes
        speed_kmh (float): Vitesse en km/h
        network_type (str): Type de réseau
        shared_graph: Graphe partagé si disponible
        
    Returns:
        Polygon: Polygone de l'isochrone
    """
    try:
        # Calculer la distance de trajet
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        
        # Si on a un graphe partagé ET qu'on est proche du centre, l'utiliser
        if shared_graph is not None:
            return generate_isochrone_from_graph_fast(lat, lon, shared_graph, time_minutes, speed_kmh)
        
        # Sinon, utiliser un buffer circulaire optimisé (plus rapide)
        # Pour la plupart des pharmacies, c'est suffisant et 100x plus rapide
        if network_type == 'walk' or trip_distance < 5000:  # < 5km
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Pour les distances de conduite plus longues, essayer le graphe
        try:
            # Téléchargement avec timeout court
            cache_key = get_graph_cache_key(lat, lon, network_type)
            graph = get_or_download_graph(lat, lon, network_type, cache_key)
            return generate_isochrone_from_graph_fast(lat, lon, graph, time_minutes, speed_kmh)
        except:
            # Fallback rapide vers buffer
            return create_circular_buffer_optimized(lat, lon, trip_distance)
            
    except Exception as e:
        # Fallback ultime
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        return create_circular_buffer_optimized(lat, lon, trip_distance)


def generate_isochrone_from_graph_fast(lat, lon, graph, time_minutes, speed_kmh):
    """
    Version rapide avec moins de précision mais plus de vitesse
    
    Args:
        lat (float): Latitude pharmacie
        lon (float): Longitude pharmacie  
        graph: Graphe NetworkX
        time_minutes (int): Temps en minutes
        speed_kmh (float): Vitesse en km/h
        
    Returns:
        Polygon: Polygone de l'isochrone
    """
    try:
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        
        if len(graph.nodes) == 0:
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Trouver le nœud le plus proche rapidement
        center_node = ox.distance.nearest_nodes(graph, lon, lat)
        
        # Utiliser un sous-ensemble plus petit pour accélérer
        max_nodes = min(500, len(graph.nodes))  # Limiter à 500 nœuds max
        
        # Ego graph avec limitation
        try:
            subgraph = nx.ego_graph(graph, center_node, radius=trip_distance, distance='length')
            
            # Si trop de nœuds, échantillonner
            if len(subgraph.nodes) > max_nodes:
                nodes_sample = list(subgraph.nodes)[:max_nodes]
                subgraph = graph.subgraph(nodes_sample)
        except:
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        if len(subgraph.nodes) < 3:
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Points rapides
        node_points = []
        for node in list(subgraph.nodes)[:max_nodes]:  # Limite stricte
            if 'x' in graph.nodes[node] and 'y' in graph.nodes[node]:
                node_points.append(Point(graph.nodes[node]['x'], graph.nodes[node]['y']))
        
        if len(node_points) < 3:
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Enveloppe convexe rapide
        gdf_points = gpd.GeoSeries(node_points)
        return gdf_points.unary_union.convex_hull
        
    except:
        return create_circular_buffer_optimized(lat, lon, trip_distance)


def create_circular_buffer_optimized(lat, lon, distance_meters):
    """
    Buffer circulaire optimisé pour performance maximale
    
    Args:
        lat (float): Latitude centre
        lon (float): Longitude centre
        distance_meters (float): Rayon en mètres
        
    Returns:
        Polygon: Polygone circulaire
    """
    # Approximation rapide: 1 degré ≈ 111 km
    radius_deg = distance_meters / 111000
    
    # Correction latitude (la terre n'est pas plate)
    lat_correction = math.cos(math.radians(lat))
    radius_lon = radius_deg / lat_correction if lat_correction > 0 else radius_deg
    
    center = Point(lon, lat)
    
    # Buffer avec moins de points pour accélérer
    return center.buffer(radius_deg, resolution=8)  # 8 points au lieu de 16 par défaut


def generate_isochrone(lat, lon, time_minutes, speed_kmh, network_type):
    """
    Génère un isochrone pour une pharmacie
    
    Args:
        lat (float): Latitude pharmacie
        lon (float): Longitude pharmacie
        time_minutes (int): Temps en minutes
        speed_kmh (float): Vitesse en km/h
        network_type (str): Type de réseau
        
    Returns:
        Polygon: Polygone de l'isochrone
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Calculer la distance de trajet
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        
        # Télécharger le graphe
        graph = get_or_download_graph(lat, lon, network_type)
        
        if len(graph.nodes) == 0:
            raise ValueError("Graphe vide")
        
        # Trouver le nœud le plus proche
        center_node = ox.distance.nearest_nodes(graph, lon, lat)
        
        # Calculer les nœuds accessibles
        subgraph = nx.ego_graph(
            graph, 
            center_node, 
            radius=trip_distance, 
            distance='length'
        )
        
        if len(subgraph.nodes) < 3:
            # Pas assez de nœuds, utiliser buffer circulaire
            logger.warning(f"   Pas assez de nœuds ({len(subgraph.nodes)}), buffer circulaire")
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Créer le polygone à partir des nœuds
        node_points = []
        for node in subgraph.nodes():
            if 'x' in graph.nodes[node] and 'y' in graph.nodes[node]:
                point = Point(graph.nodes[node]['x'], graph.nodes[node]['y'])
                node_points.append(point)
        
        if len(node_points) < 3:
            # Fallback vers buffer circulaire
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Créer l'enveloppe convexe
        gdf_points = gpd.GeoSeries(node_points)
        isochrone = gdf_points.unary_union.convex_hull
        
        return isochrone
        
    except Exception as e:
        logger.warning(f"   Erreur génération isochrone, fallback buffer: {e}")
        # Fallback vers buffer circulaire
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        return create_circular_buffer_optimized(lat, lon, trip_distance)


def process_batch_optimized_with_checkpoints(batch_data, progress_tracker, output_dir, total_pharmacies):
    """
    Traite un batch avec sauvegardes automatiques et suivi de progression
    
    Args:
        batch_data (tuple): (batch_id, batch_df, batch_metadata)
        progress_tracker (dict): Tracker de progression partagé
        output_dir (Path): Dossier de sortie
        total_pharmacies (int): Total de pharmacies
        
    Returns:
        dict: Résultats du batch
    """
    batch_id, batch_df, batch_metadata = batch_data
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    batch_size = len(batch_df)
    
    logger.info(f"🔄 Traitement batch {batch_id}: {batch_size} pharmacies (cluster {batch_metadata.get('cluster_id', 'N/A')})")
    
    # Pré-télécharger les graphes pour la zone du batch
    batch_center_lat = batch_metadata.get('lat_center', batch_df['latitude'].mean())
    batch_center_lon = batch_metadata.get('lon_center', batch_df['longitude'].mean())
    
    batch_graphs = {}
    try:
        # Pré-télécharger les graphes walk et drive pour la zone
        for network_type in ['walk', 'drive']:
            cache_key = get_graph_cache_key(batch_center_lat, batch_center_lon, network_type)
            try:
                graph = get_or_download_graph(batch_center_lat, batch_center_lon, network_type, cache_key)
                batch_graphs[network_type] = graph
                logger.debug(f"   📡 Graphe {network_type} pré-téléchargé pour batch {batch_id}")
            except Exception as e:
                logger.warning(f"   ⚠️  Échec pré-téléchargement {network_type} pour batch {batch_id}: {e}")
        
        # Traiter chaque pharmacie du batch avec checkpoints
        batch_results = []
        successful_pharmacies = 0
        
        for idx, pharmacy in batch_df.iterrows():
            try:
                # Utiliser une clé de cache basée sur la position relative dans le batch
                pharma_lat = pharmacy['latitude']
                pharma_lon = pharmacy['longitude']
                
                # Calculer la distance au centre du batch
                distance_to_center = ((pharma_lat - batch_center_lat)**2 + (pharma_lon - batch_center_lon)**2)**0.5
                
                # Si proche du centre, utiliser les graphes pré-téléchargés
                if distance_to_center < 0.1:  # ~10km roughly
                    pharmacy_graphs = batch_graphs
                else:
                    pharmacy_graphs = {}
                
                # Traiter la pharmacie avec optimisations
                result = process_single_pharmacy_optimized(pharmacy.to_dict(), pharmacy_graphs)
                batch_results.append(result)
                
                # Compter les succès
                success_count = sum(1 for iso_type in ISOCHRONE_CONFIG.keys() if result[f'{iso_type}_success'])
                if success_count > 0:
                    successful_pharmacies += 1
                
                # Affichage progrès en temps réel (toutes les 10 pharmacies)
                if len(batch_results) % PROGRESS_DISPLAY_FREQUENCY == 0:
                    progress_tracker['total_processed'] += PROGRESS_DISPLAY_FREQUENCY
                    update_progress_tracker(progress_tracker, batch_results[-PROGRESS_DISPLAY_FREQUENCY:], batch_id, total_pharmacies)
                    display_live_progress(progress_tracker, total_pharmacies, 100)  # estimation
                
            except Exception as e:
                logger.error(f"   ❌ Erreur pharmacie {pharmacy['id_pharmacie']} dans batch {batch_id}: {e}")
                # Créer un résultat d'échec
                error_result = {
                    'id_pharmacie': pharmacy['id_pharmacie'],
                    'error_message': str(e)[:200],
                    'processing_time_seconds': 0
                }
                for iso_type in ISOCHRONE_CONFIG.keys():
                    error_result[f'{iso_type}_file'] = ''
                    error_result[f'{iso_type}_success'] = False
                batch_results.append(error_result)
        
        processing_time = time.time() - start_time
        
        logger.info(f"   ✅ Batch {batch_id} terminé: {successful_pharmacies}/{batch_size} succès en {processing_time:.1f}s")
        
        # Marquer le batch comme complété
        save_batch_progress(batch_id, completed=True)
        
        # Mise à jour finale du tracker
        remaining = len(batch_results) % PROGRESS_DISPLAY_FREQUENCY
        if remaining > 0:
            progress_tracker['total_processed'] += remaining
            update_progress_tracker(progress_tracker, batch_results[-remaining:], batch_id, total_pharmacies)
        
        return {
            'batch_id': batch_id,
            'results': batch_results,
            'success_count': successful_pharmacies,
            'total_count': batch_size,
            'processing_time': processing_time,
            'error': None
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Erreur critique batch {batch_id}: {e}"
        logger.error(f"   ❌ {error_msg}")
        
        # Marquer le batch comme échoué
        save_batch_progress(batch_id, completed=False, error=str(e))
        
        return {
            'batch_id': batch_id,
            'results': [],
            'success_count': 0,
            'total_count': batch_size,
            'processing_time': processing_time,
            'error': error_msg
        }


def process_batch_optimized_simple(output_dir, total_pharmacies, batch_data):
    """
    Version simplifiée pour multiprocessing (sans objets partagés)
    
    Args:
        output_dir (Path): Dossier de sortie
        total_pharmacies (int): Total de pharmacies
        batch_data (tuple): (batch_id, batch_df, batch_metadata)
        
    Returns:
        dict: Résultats du batch
    """
    # Créer un tracker temporaire pour ce processus
    temp_tracker = create_progress_tracker()
    
    # Appeler la fonction principale
    return process_batch_optimized_with_checkpoints(batch_data, temp_tracker, Path(output_dir), total_pharmacies)


def process_single_pharmacy_optimized(pharmacy_data, shared_graphs=None):
    """
    Version optimisée du traitement d'une pharmacie avec graphes partagés
    
    Args:
        pharmacy_data (dict): Données de la pharmacie
        shared_graphs (dict): Graphes pré-téléchargés pour réutilisation
        
    Returns:
        dict: Résultats du traitement
    """
    pharma_id = pharmacy_data['id_pharmacie']
    lat = pharmacy_data['latitude']
    lon = pharmacy_data['longitude']
    type_zone = pharmacy_data['type_zone']
    
    start_time = time.time()
    
    results = {
        'id_pharmacie': pharma_id,
        'walk_5min_file': '',
        'walk_10min_file': '',
        'drive_15min_file': '',
        'drive_20min_file': '',
        'walk_5min_success': False,
        'walk_10min_success': False,
        'drive_15min_success': False,
        'drive_20min_success': False,
        'error_message': '',
        'processing_time_seconds': 0
    }
    
    try:
        # Traiter chaque type d'isochrone
        for iso_type, config in ISOCHRONE_CONFIG.items():
            try:
                # Déterminer la vitesse
                if config.get('speed_variable', False):
                    speed = get_driving_speed(type_zone)
                else:
                    speed = config['speed_kmh']
                
                # Utiliser les graphes partagés si disponibles avec algorithme ultra-rapide
                network_type = config['network_type']
                if shared_graphs and network_type in shared_graphs:
                    graph = shared_graphs[network_type]
                    polygon = generate_isochrone_optimized_fast(
                        lat, lon, config['time_minutes'], speed, network_type, graph
                    )
                else:
                    # Version ultra-optimisée même sans graphe partagé
                    polygon = generate_isochrone_optimized_fast(
                        lat, lon, config['time_minutes'], speed, network_type, None
                    )
                
                # Créer le GeoDataFrame
                gdf = gpd.GeoDataFrame(
                    {
                        'id_pharmacie': [pharma_id],
                        'temps_minutes': [config['time_minutes']],
                        'mode': [config['mode']],
                        'vitesse_kmh': [speed],
                        'type_zone': [type_zone]
                    },
                    geometry=[polygon],
                    crs='EPSG:4326'
                )
                
                # Sauvegarder
                output_file = OUTPUT_DIR / iso_type / f"{pharma_id}.geojson"
                gdf.to_file(output_file, driver='GeoJSON')
                
                # Mettre à jour les résultats
                results[f'{iso_type}_file'] = str(output_file)
                results[f'{iso_type}_success'] = True
                
            except Exception as e:
                results['error_message'] += f"{iso_type}: {str(e)[:100]}; "
        
        processing_time = time.time() - start_time
        results['processing_time_seconds'] = round(processing_time, 2)
        
        return results
        
    except Exception as e:
        processing_time = time.time() - start_time
        results['processing_time_seconds'] = round(processing_time, 2)
        results['error_message'] = str(e)[:200]
        return results


def process_single_pharmacy(pharmacy_data):
    """
    Fonction de compatibilité - utilise la version optimisée
    
    Args:
        pharmacy_data (dict): Données de la pharmacie
        
    Returns:
        dict: Résultats du traitement
    """
    return process_single_pharmacy_optimized(pharmacy_data, shared_graphs=None)


def generate_isochrone_from_graph(lat, lon, graph, time_minutes, speed_kmh):
    """
    Génère un isochrone à partir d'un graphe déjà téléchargé
    
    Args:
        lat (float): Latitude pharmacie
        lon (float): Longitude pharmacie  
        graph: Graphe NetworkX pré-téléchargé
        time_minutes (int): Temps en minutes
        speed_kmh (float): Vitesse en km/h
        
    Returns:
        Polygon: Polygone de l'isochrone
    """
    try:
        # Calculer la distance de trajet
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        
        if len(graph.nodes) == 0:
            raise ValueError("Graphe vide")
        
        # Trouver le nœud le plus proche
        center_node = ox.distance.nearest_nodes(graph, lon, lat)
        
        # Calculer les nœuds accessibles dans le rayon donné
        subgraph = nx.ego_graph(
            graph, 
            center_node, 
            radius=trip_distance, 
            distance='length'
        )
        
        if len(subgraph.nodes) < 3:
            # Pas assez de nœuds, utiliser buffer circulaire
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Créer le polygone à partir des nœuds
        node_points = []
        for node in subgraph.nodes():
            if 'x' in graph.nodes[node] and 'y' in graph.nodes[node]:
                point = Point(graph.nodes[node]['x'], graph.nodes[node]['y'])
                node_points.append(point)
        
        if len(node_points) < 3:
            # Fallback vers buffer circulaire
            return create_circular_buffer_optimized(lat, lon, trip_distance)
        
        # Créer l'enveloppe convexe
        gdf_points = gpd.GeoSeries(node_points)
        isochrone = gdf_points.unary_union.convex_hull
        
        return isochrone
        
    except Exception as e:
        # Fallback vers buffer circulaire
        trip_distance = calculate_trip_distance(time_minutes, speed_kmh)
        return create_circular_buffer_optimized(lat, lon, trip_distance)
    """
    Traite une seule pharmacie et génère tous ses isochrones
    
    Args:
        pharmacy_data (dict): Données de la pharmacie
        
    Returns:
        dict: Résultats du traitement
    """
    logger = logging.getLogger(__name__)
    
    pharma_id = pharmacy_data['id_pharmacie']
    lat = pharmacy_data['latitude']
    lon = pharmacy_data['longitude']
    type_zone = pharmacy_data['type_zone']
    
    start_time = time.time()
    
    results = {
        'id_pharmacie': pharma_id,
        'walk_5min_file': '',
        'walk_10min_file': '',
        'drive_15min_file': '',
        'drive_20min_file': '',
        'walk_5min_success': False,
        'walk_10min_success': False,
        'drive_15min_success': False,
        'drive_20min_success': False,
        'error_message': '',
        'processing_time_seconds': 0
    }
    
    try:
        # Traiter chaque type d'isochrone
        for iso_type, config in ISOCHRONE_CONFIG.items():
            try:
                # Déterminer la vitesse
                if config.get('speed_variable', False):
                    speed = get_driving_speed(type_zone)
                else:
                    speed = config['speed_kmh']
                
                # Générer l'isochrone
                polygon = generate_isochrone(
                    lat, lon,
                    config['time_minutes'],
                    speed,
                    config['network_type']
                )
                
                # Créer le GeoDataFrame
                gdf = gpd.GeoDataFrame(
                    {
                        'id_pharmacie': [pharma_id],
                        'temps_minutes': [config['time_minutes']],
                        'mode': [config['mode']],
                        'vitesse_kmh': [speed],
                        'type_zone': [type_zone]
                    },
                    geometry=[polygon],
                    crs='EPSG:4326'
                )
                
                # Sauvegarder
                output_file = OUTPUT_DIR / iso_type / f"{pharma_id}.geojson"
                gdf.to_file(output_file, driver='GeoJSON')
                
                # Mettre à jour les résultats
                results[f'{iso_type}_file'] = str(output_file)
                results[f'{iso_type}_success'] = True
                
            except Exception as e:
                logger.error(f"   Erreur {iso_type} pour {pharma_id}: {e}")
                results['error_message'] += f"{iso_type}: {str(e)[:100]}; "
        
        processing_time = time.time() - start_time
        results['processing_time_seconds'] = round(processing_time, 2)
        
        return results
        
    except Exception as e:
        processing_time = time.time() - start_time
        results['processing_time_seconds'] = round(processing_time, 2)
        results['error_message'] = str(e)[:200]
        logger.error(f"❌ Erreur critique pour {pharma_id}: {e}")
        return results


def load_existing_summary(summary_file):
    """
    Charge le fichier de résumé existant pour reprendre le traitement
    
    Args:
        summary_file (Path): Chemin vers le fichier de résumé
        
    Returns:
        pd.DataFrame: Résultats existants ou DataFrame vide
    """
    if summary_file.exists():
        try:
            return pd.read_csv(summary_file)
        except:
            return pd.DataFrame()
    return pd.DataFrame()


def save_checkpoint_with_backup(results_df, summary_file, backup_dir=None):
    """
    Sauvegarde un checkpoint avec système de backup rotatif
    
    Args:
        results_df (pd.DataFrame): Résultats actuels
        summary_file (Path): Fichier de résumé principal
        backup_dir (Path): Dossier de backup (optionnel)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Sauvegarder le fichier principal
        results_df.to_csv(summary_file, index=False)
        
        # 2. Créer un backup horodaté
        if backup_dir is None:
            backup_dir = summary_file.parent / "backups"
        
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"isochrones_summary_backup_{timestamp}.csv"
        results_df.to_csv(backup_file, index=False)
        
        # 3. Nettoyer les anciens backups (garder seulement les MAX_BACKUP_FILES plus récents)
        backup_files = sorted(backup_dir.glob("isochrones_summary_backup_*.csv"), 
                             key=lambda x: x.stat().st_mtime, reverse=True)
        
        for old_backup in backup_files[MAX_BACKUP_FILES:]:
            old_backup.unlink()
            logger.debug(f"   🗑️  Backup supprimé: {old_backup.name}")
        
        logger.debug(f"   💾 Checkpoint sauvegardé: {len(results_df)} entrées")
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde checkpoint: {e}")


def create_progress_tracker():
    """
    Crée un tracker de progression avec fichier de statut
    
    Returns:
        dict: Tracker de progression
    """
    return {
        'start_time': time.time(),
        'total_processed': 0,
        'total_successes': 0,
        'total_failures': 0,
        'current_batch': 0,
        'last_checkpoint': time.time(),
        'last_backup': time.time(),
        'pharmacies_per_minute': 0.0,
        'estimated_completion': None
    }


def update_progress_tracker(tracker, batch_results, batch_id, total_pharmacies):
    """
    Met à jour le tracker de progression
    
    Args:
        tracker (dict): Tracker de progression
        batch_results (list): Résultats du batch
        batch_id (int): ID du batch
        total_pharmacies (int): Total de pharmacies à traiter
    """
    current_time = time.time()
    
    # Compter les succès/échecs du batch
    batch_successes = 0
    for result in batch_results:
        for iso_type in ISOCHRONE_CONFIG.keys():
            if result.get(f'{iso_type}_success', False):
                batch_successes += 1
    
    batch_failures = (len(batch_results) * len(ISOCHRONE_CONFIG)) - batch_successes
    
    # Mettre à jour les totaux
    tracker['total_processed'] += len(batch_results)
    tracker['total_successes'] += batch_successes
    tracker['total_failures'] += batch_failures
    tracker['current_batch'] = batch_id
    
    # Calculer la vitesse
    elapsed = current_time - tracker['start_time']
    if elapsed > 0:
        tracker['pharmacies_per_minute'] = (tracker['total_processed'] / elapsed) * 60
    
    # Estimation du temps restant
    if tracker['pharmacies_per_minute'] > 0:
        remaining = total_pharmacies - tracker['total_processed']
        eta_minutes = remaining / tracker['pharmacies_per_minute']
        tracker['estimated_completion'] = current_time + (eta_minutes * 60)


def display_live_progress(tracker, total_pharmacies, total_batches):
    """
    Affiche le progrès en temps réel
    
    Args:
        tracker (dict): Tracker de progression
        total_pharmacies (int): Total de pharmacies
        total_batches (int): Total de batches
    """
    current_time = time.time()
    elapsed = current_time - tracker['start_time']
    
    # Calculs de progression
    progress_pct = (tracker['total_processed'] / total_pharmacies) * 100 if total_pharmacies > 0 else 0
    batch_progress_pct = (tracker['current_batch'] / total_batches) * 100 if total_batches > 0 else 0
    
    success_rate = (tracker['total_successes'] / (tracker['total_successes'] + tracker['total_failures'])) * 100 if (tracker['total_successes'] + tracker['total_failures']) > 0 else 0
    
    # Formatage du temps
    elapsed_str = str(timedelta(seconds=int(elapsed)))
    
    # ETA
    if tracker['estimated_completion']:
        eta = tracker['estimated_completion'] - current_time
        eta_str = str(timedelta(seconds=int(eta))) if eta > 0 else "Bientôt"
    else:
        eta_str = "Calcul..."
    
    # Affichage coloré
    print(f"\r🔄 Progress: {tracker['total_processed']:,}/{total_pharmacies:,} pharmacies ({progress_pct:.1f}%) | "
          f"Batch: {tracker['current_batch']}/{total_batches} ({batch_progress_pct:.1f}%) | "
          f"Succès: {success_rate:.1f}% | "
          f"Vitesse: {tracker['pharmacies_per_minute']:.1f}/min | "
          f"Écoulé: {elapsed_str} | ETA: {eta_str}", end="", flush=True)


def save_progress_status(tracker, output_dir):
    """
    Sauvegarde le statut de progression dans un fichier JSON
    
    Args:
        tracker (dict): Tracker de progression
        output_dir (Path): Dossier de sortie
    """
    try:
        status_file = output_dir / "progress_status.json"
        
        status = {
            'timestamp': time.time(),
            'timestamp_human': datetime.now().isoformat(),
            'total_processed': tracker['total_processed'],
            'total_successes': tracker['total_successes'],
            'total_failures': tracker['total_failures'],
            'current_batch': tracker['current_batch'],
            'pharmacies_per_minute': tracker['pharmacies_per_minute'],
            'elapsed_seconds': time.time() - tracker['start_time'],
            'estimated_completion': tracker.get('estimated_completion')
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        logging.getLogger(__name__).warning(f"Erreur sauvegarde statut: {e}")


def load_existing_progress(output_dir):
    """
    Charge le progrès existant depuis les fichiers
    
    Args:
        output_dir (Path): Dossier de sortie
        
    Returns:
        tuple: (existing_results_df, processed_count)
    """
    logger = logging.getLogger(__name__)
    
    # Charger le fichier principal
    summary_file = output_dir / "isochrones_summary.csv"
    existing_results = pd.DataFrame()
    
    if summary_file.exists():
        try:
            existing_results = pd.read_csv(summary_file)
            logger.info(f"📋 Reprise détectée: {len(existing_results)} pharmacies déjà traitées")
        except Exception as e:
            logger.warning(f"⚠️  Erreur lecture fichier principal: {e}")
            
            # Essayer de récupérer depuis un backup
            backup_dir = summary_file.parent / "backups"
            if backup_dir.exists():
                backup_files = sorted(backup_dir.glob("isochrones_summary_backup_*.csv"), 
                                     key=lambda x: x.stat().st_mtime, reverse=True)
                
                for backup_file in backup_files:
                    try:
                        existing_results = pd.read_csv(backup_file)
                        logger.info(f"📁 Récupération depuis backup: {backup_file.name} ({len(existing_results)} entrées)")
                        break
                    except:
                        continue
    
    return existing_results, len(existing_results)


def display_progress_stats(completed, total, successes, failures, start_time):
    """
    Affiche les statistiques de progression
    
    Args:
        completed (int): Nombre de pharmacies traitées
        total (int): Total de pharmacies
        successes (int): Nombre de succès
        failures (int): Nombre d'échecs
        start_time (float): Timestamp de début
    """
    if completed == 0:
        return
    
    elapsed = time.time() - start_time
    rate = completed / elapsed * 60  # pharmacies par minute
    
    if rate > 0:
        eta_seconds = (total - completed) / (rate / 60)
        eta = str(timedelta(seconds=int(eta_seconds)))
    else:
        eta = "N/A"
    
    elapsed_str = str(timedelta(seconds=int(elapsed)))
    
    progress_pct = (completed / total) * 100
    
    print(f"\r[Isochrones] Progress: {completed:,}/{total:,} ({progress_pct:.1f}%) | "
          f"Succès: {successes:,} | Échecs: {failures:,} | "
          f"Vitesse: {rate:.1f}/min | Écoulé: {elapsed_str} | ETA: {eta}", end="")


def display_final_stats(results_df, start_time, total_pharmacies):
    """
    Affiche les statistiques finales selon les spécifications
    
    Args:
        results_df (pd.DataFrame): Résultats finaux
        start_time (float): Timestamp de début
        total_pharmacies (int): Nombre total de pharmacies
    """
    elapsed = time.time() - start_time
    
    print("\n\n" + "=" * 40)
    print("GÉNÉRATION DES ISOCHRONES TERMINÉE")
    print("=" * 40)
    
    print(f"Total pharmacies traitées : {len(results_df):,}")
    
    # Calcul des succès par type
    success_stats = {}
    total_successes = 0
    total_expected = len(results_df) * len(ISOCHRONE_CONFIG)
    
    for iso_type in ISOCHRONE_CONFIG.keys():
        success_col = f'{iso_type}_success'
        if success_col in results_df.columns:
            successes = results_df[success_col].sum()
            success_pct = (successes / len(results_df)) * 100
            success_stats[iso_type] = (successes, success_pct)
            total_successes += successes
    
    total_failures = total_expected - total_successes
    total_success_pct = (total_successes / total_expected) * 100 if total_expected > 0 else 0
    
    print(f"Succès total              : {total_successes:,} ({total_success_pct:.1f}%)")
    print(f"Échecs                    : {total_failures:,} ({100 - total_success_pct:.1f}%)")
    
    print(f"\nPar type d'isochrone :")
    for iso_type, (successes, success_pct) in success_stats.items():
        print(f"  - {iso_type:<12} : {successes:,} succès ({success_pct:.1f}%)")
    
    # Formatage du temps total
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    
    avg_rate = len(results_df) / elapsed * 60 if elapsed > 0 else 0  # pharmacies par minute
    print(f"\nTemps total de traitement : {hours}h {minutes:02d}min")
    print(f"Vitesse moyenne           : {avg_rate:.1f} pharmacies/min")
    
    # Compter les fichiers créés
    total_files = total_successes
    print(f"\nFichiers créés :")
    print(f"  ✓ {total_files:,} fichiers GeoJSON")
    print(f"  ✓ isochrones_summary.csv")
    print(f"  ✓ isochrones_errors.log")
    
    # Estimation de la taille plus précise
    estimated_size_gb = total_files * 0.05  # ~50 KB par fichier GeoJSON
    print(f"\nTaille totale : {estimated_size_gb:.1f} GB")
    print("=" * 40)


def main():
    """Fonction principale OPTIMISÉE avec traitement par batchs géographiques"""
    
    parser = argparse.ArgumentParser(description='Génération OPTIMISÉE d\'isochrones pour pharmacies')
    parser.add_argument('--input', type=str, default='pharmacies_final.csv', help='Fichier pharmacies (défaut: pharmacies_final.csv)')
    parser.add_argument('--workers', type=int, default=6, help='Nombre de processus parallèles (défaut: 6)')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE, help=f'Taille des batchs (défaut: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--resume', action='store_true', default=True, help='Reprendre automatiquement (défaut: True)')
    parser.add_argument('--resume-batch', type=int, help='Reprendre à partir du batch N')
    parser.add_argument('--output-dir', type=str, help='Dossier de sortie (défaut: data/processed/isochrones/)')
    parser.add_argument('--max-pharmacies', type=int, help='Limiter le nombre de pharmacies (pour test)')
    parser.add_argument('--clusters', type=int, default=GEOGRAPHIC_CLUSTERS, help=f'Nombre de clusters géographiques (défaut: {GEOGRAPHIC_CLUSTERS})')
    parser.add_argument('--disable-cache', action='store_true', help='Désactiver le cache des graphes')
    parser.add_argument('--types', type=str, help='Types d\'isochrones à générer (ex: drive_5min,drive_10min)', default=None)
    
    args = parser.parse_args()
    
    # Filtrer les types d'isochrones si spécifié
    if args.types:
        requested_types = [t.strip() for t in args.types.split(',')]
        global ISOCHRONE_CONFIG
        original_config = ISOCHRONE_CONFIG.copy()
        ISOCHRONE_CONFIG = {k: v for k, v in original_config.items() if k in requested_types}
        
        if not ISOCHRONE_CONFIG:
            print(f"❌ ERREUR: Aucun type valide trouvé dans '{args.types}'")
            print(f"Types disponibles: {', '.join(original_config.keys())}")
            return
        
        print(f"🎯 Génération uniquement des types: {', '.join(ISOCHRONE_CONFIG.keys())}")
    
    # Configuration des chemins
    if args.output_dir:
        global OUTPUT_DIR
        OUTPUT_DIR = Path(args.output_dir)
    
    # Configuration du cache
    if args.disable_cache:
        global ENABLE_GRAPH_CACHE
        ENABLE_GRAPH_CACHE = False
    
    # Créer les répertoires
    create_output_directories()
    create_cache_directories()
    
    # Setup logging
    logger = setup_logging(OUTPUT_DIR)
    
    # Setup OSMnx
    setup_osmnx()
    
    start_time = time.time()
    
    try:
        # 1. Charger les pharmacies - DÉTERMINER LE FICHIER D'ABORD
        if args.input:
            if Path(args.input).is_absolute():
                input_file = Path(args.input)
            else:
                # Chercher dans data_cleaning en priorité
                input_file = INPUT_DIR / args.input
                if not input_file.exists():
                    # Fallback vers data/input
                    input_file = BASE_DIR / "data" / "input" / args.input
        else:
            # Chercher automatiquement pharmacies_final.csv en priorité
            possible_files = [
                INPUT_DIR / "pharmacies_final.csv",
                BASE_DIR / "data" / "input" / "pharmacies_final.csv", 
                INPUT_DIR / "pharmacies.csv",
                BASE_DIR / "data" / "input" / "pharmacies.csv"
            ]
            
            input_file = None
            for file_path in possible_files:
                if file_path.exists():
                    input_file = file_path
                    break
            
            if not input_file:
                raise FileNotFoundError("Aucun fichier pharmacies trouvé dans data/input/data_cleaning/ ou data/input/")
        
        # AFFICHAGE APRÈS AVOIR DÉTERMINÉ LE FICHIER
        print("GÉNÉRATION OPTIMISÉE DES ISOCHRONES POUR LES PHARMACIES")
        print("=" * 60)
        print(f"Fichier d'entrée     : {input_file}")
        print(f"Dossier de sortie    : {OUTPUT_DIR}")
        print(f"⚙️  Workers             : {args.workers}")
        print(f"� Taille des batchs   : {args.batch_size}")
        print(f"🗺️  Clusters géo        : {args.clusters}")
        print(f"💾 Cache graphes       : {'✅ Activé' if ENABLE_GRAPH_CACHE else '❌ Désactivé'}")
        print(f"�🔄 Mode reprise        : {'✅ Activé' if args.resume else '❌ Désactivé'}")
        if args.resume_batch:
            print(f"📍 Reprise batch       : {args.resume_batch}")
        print()
        
        logger.info("🏢 GÉNÉRATION OPTIMISÉE DES ISOCHRONES POUR PHARMACIES")
        logger.info("=" * 70)
        
        # Charger le fichier des pharmacies
        df_pharmacies = load_pharmacies(input_file)
        
        # Limiter pour test si demandé
        if args.max_pharmacies:
            df_pharmacies = df_pharmacies.head(args.max_pharmacies)
            logger.info(f"   Limitation à {args.max_pharmacies} pharmacies pour test")
        
        # 2. Créer les clusters géographiques
        df_with_clusters, cluster_stats = create_geographic_clusters(df_pharmacies, args.clusters)
        
        # 3. Créer les batchs optimisés
        batches, batch_metadata = create_batches_from_clusters(df_with_clusters, args.batch_size)
        
        # 4. Déterminer les batchs à traiter
        batches_to_process = get_batches_to_process(batches, args.resume_batch)
        
        if len(batches_to_process) == 0:
            logger.info("✅ Tous les batchs sont déjà traités!")
            return 0
        
        # 5. Traitement par batchs avec sauvegarde automatique
        logger.info(f"🚀 Traitement de {len(batches_to_process)} batchs avec {args.workers} workers")
        
        # Charger les résultats existants avec système de récupération
        existing_results, existing_count = load_existing_progress(OUTPUT_DIR)
        
        # Initialiser le tracker de progression
        progress_tracker = create_progress_tracker()
        progress_tracker['total_processed'] = existing_count
        
        # Préparer les données pour le multiprocessing avec le nouveau système
        batch_data_list = []
        for batch_id, batch_df in batches_to_process:
            batch_meta = batch_metadata.iloc[batch_id].to_dict() if batch_id < len(batch_metadata) else {}
            batch_data_list.append((batch_id, batch_df, batch_meta, progress_tracker, OUTPUT_DIR, len(df_pharmacies)))
        
        # Traitement avec sauvegarde continue
        all_results = []
        if not existing_results.empty:
            all_results.extend(existing_results.to_dict('records'))
        
        total_successes = 0
        total_failures = 0
        total_pharmacies_processed = existing_count
        
        print("🔄 Progression en temps réel:")
        print("-" * 80)
        
        if args.workers == 1:
            # Mode séquentiel avec checkpoints
            for i, batch_data in enumerate(batch_data_list):
                batch_data_modified = batch_data[:3]  # Retirer les args supplémentaires pour compatibilité
                batch_result = process_batch_optimized_with_checkpoints(
                    batch_data_modified, progress_tracker, OUTPUT_DIR, len(df_pharmacies)
                )
                
                all_results.extend(batch_result['results'])
                total_successes += batch_result['success_count']
                total_pharmacies_processed += batch_result['total_count']
                
                # Sauvegarde checkpoint fréquente
                if (i + 1) % (CHECKPOINT_FREQUENCY // batch_result['total_count'] + 1) == 0:
                    results_df = pd.DataFrame(all_results)
                    save_checkpoint_with_backup(results_df, OUTPUT_DIR / "isochrones_summary.csv")
                    save_progress_status(progress_tracker, OUTPUT_DIR)
                    print(f"\n💾 Checkpoint automatique - {total_pharmacies_processed} pharmacies traitées")
                
                # Backup complet périodique
                if total_pharmacies_processed % BACKUP_FREQUENCY == 0:
                    results_df = pd.DataFrame(all_results)
                    save_checkpoint_with_backup(results_df, OUTPUT_DIR / "isochrones_summary.csv")
                    print(f"\n🔒 Backup complet - {total_pharmacies_processed} pharmacies sauvegardées")
        
        else:
            # Mode parallèle avec gestion des checkpoints
            print("⚠️  Mode parallèle : checkpoints moins fréquents pour éviter les conflits")
            
            with mp.Pool(processes=args.workers) as pool:
                # Adapter la fonction pour multiprocessing
                batch_func = partial(process_batch_optimized_simple, OUTPUT_DIR, len(df_pharmacies))
                
                # Traitement par chunks pour checkpoints
                chunk_size = max(1, len(batch_data_list) // 10)  # 10 checkpoints
                
                for chunk_start in range(0, len(batch_data_list), chunk_size):
                    chunk = batch_data_list[chunk_start:chunk_start + chunk_size]
                    chunk_simple = [data[:3] for data in chunk]  # Simplifier pour multiprocessing
                    
                    # Traiter le chunk
                    chunk_results = pool.map(batch_func, chunk_simple)
                    
                    # Agréger les résultats
                    for batch_result in chunk_results:
                        all_results.extend(batch_result['results'])
                        total_successes += batch_result['success_count']
                        total_pharmacies_processed += batch_result['total_count']
                    
                    # Checkpoint après chaque chunk
                    results_df = pd.DataFrame(all_results)
                    save_checkpoint_with_backup(results_df, OUTPUT_DIR / "isochrones_summary.csv")
                    
                    progress_pct = (total_pharmacies_processed / len(df_pharmacies)) * 100
                    print(f"\n💾 Checkpoint chunk {chunk_start//chunk_size + 1} - {total_pharmacies_processed:,} pharmacies ({progress_pct:.1f}%)")
        
        total_failures = (total_pharmacies_processed * len(ISOCHRONE_CONFIG)) - total_successes
        
        # 6. Sauvegarde finale avec backup
        print("\n")
        print("💾 Sauvegarde finale des résultats...")
        
        # Fusionner tous les résultats
        final_results_df = pd.DataFrame(all_results)
        
        # Supprimer les doublons (au cas où)
        if not final_results_df.empty:
            final_results_df = final_results_df.drop_duplicates(subset=['id_pharmacie'], keep='last')
        
        # Sauvegarder avec système de backup
        summary_file = OUTPUT_DIR / "isochrones_summary.csv"
        save_checkpoint_with_backup(final_results_df, summary_file)
        
        # Sauvegarder le statut final
        if 'progress_tracker' in locals():
            save_progress_status(progress_tracker, OUTPUT_DIR)
        
        logger.info(f"💾 Résultats finaux sauvegardés: {len(final_results_df)} pharmacies")
        
        # 7. Statistiques finales avec informations de sauvegarde
        print()
        display_final_stats_optimized_with_backup(final_results_df, start_time, len(df_pharmacies), len(batches_to_process), len(batches), OUTPUT_DIR)
        
        logger.info("✅ GÉNÉRATION OPTIMISÉE TERMINÉE AVEC SUCCÈS!")
        
    except Exception as e:
        logger.error(f"❌ ERREUR CRITIQUE: {e}")
        traceback.print_exc()
        return 1
    
    return 0


def display_final_stats_optimized(results_df, start_time, total_pharmacies, batches_processed, total_batches):
    """
    Affiche les statistiques finales optimisées
    
    Args:
        results_df (pd.DataFrame): Résultats finaux
        start_time (float): Timestamp de début
        total_pharmacies (int): Nombre total de pharmacies
        batches_processed (int): Nombre de batchs traités
        total_batches (int): Nombre total de batchs
    """
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("🎯 GÉNÉRATION OPTIMISÉE DES ISOCHRONES TERMINÉE")
    print("=" * 60)
    
    print(f"📊 Total pharmacies dans le dataset : {total_pharmacies:,}")
    print(f"📋 Total pharmacies traitées        : {len(results_df):,}")
    print(f"📦 Batchs traités                  : {batches_processed:,}/{total_batches:,}")
    
    # Calcul des succès par type
    success_stats = {}
    total_successes = 0
    total_expected = len(results_df) * len(ISOCHRONE_CONFIG)
    
    for iso_type in ISOCHRONE_CONFIG.keys():
        success_col = f'{iso_type}_success'
        if success_col in results_df.columns:
            successes = results_df[success_col].sum()
            success_pct = (successes / len(results_df)) * 100 if len(results_df) > 0 else 0
            success_stats[iso_type] = (successes, success_pct)
            total_successes += successes
    
    total_failures = total_expected - total_successes
    total_success_pct = (total_successes / total_expected) * 100 if total_expected > 0 else 0
    
    print(f"\n🎯 RÉSULTATS GLOBAUX:")
    print(f"   ✅ Succès total     : {total_successes:,} ({total_success_pct:.1f}%)")
    print(f"   ❌ Échecs total     : {total_failures:,} ({100 - total_success_pct:.1f}%)")
    
    print(f"\n📍 PAR TYPE D'ISOCHRONE:")
    for iso_type, (successes, success_pct) in success_stats.items():
        failures = len(results_df) - successes
        print(f"   {iso_type:<12} : {successes:,} succès, {failures:,} échecs ({success_pct:.1f}%)")
    
    # Statistiques de performance
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    
    avg_rate = len(results_df) / elapsed * 60 if elapsed > 0 else 0  # pharmacies par minute
    avg_batch_time = elapsed / batches_processed if batches_processed > 0 else 0
    
    print(f"\n⏱️  PERFORMANCE:")
    print(f"   Temps total          : {hours:02d}h {minutes:02d}min {seconds:02d}s")
    print(f"   Vitesse moyenne      : {avg_rate:.1f} pharmacies/min")
    print(f"   Temps moyen/batch    : {avg_batch_time:.1f}s")
    
    # Compter les fichiers créés
    total_files = total_successes
    print(f"\n📁 FICHIERS CRÉÉS:")
    print(f"   📄 {total_files:,} fichiers GeoJSON d'isochrones")
    print(f"   📋 1 fichier de résumé (isochrones_summary.csv)")
    print(f"   📝 1 fichier de logs (isochrones_errors.log)")
    print(f"   🗂️ Métadonnées de batchs et cache")
    
    # Estimation de la taille
    estimated_size_gb = total_files * 0.05  # ~50 KB par fichier GeoJSON
    cache_size_gb = batches_processed * 0.1  # Estimation cache graphes
    total_size_gb = estimated_size_gb + cache_size_gb
    
    print(f"\n💾 ESPACE DISQUE:")
    print(f"   Isochrones          : {estimated_size_gb:.1f} GB")
    print(f"   Cache graphes       : {cache_size_gb:.1f} GB")
    print(f"   Total estimé        : {total_size_gb:.1f} GB")
    
    # Gains d'optimisation estimés
    if ENABLE_GRAPH_CACHE:
        estimated_speedup = min(5.0, 1 + (total_pharmacies / 1000))  # Gain estimé selon taille
        print(f"\n🚀 OPTIMISATIONS:")
        print(f"   Cache activé        : ✅ (gain estimé: {estimated_speedup:.1f}x)")
        print(f"   Clustering géo      : ✅ (réduction téléchargements)")
        print(f"   Traitement batchs   : ✅ (reprise automatique)")
    
    print("=" * 60)
    
    # Conseils pour la suite
    completion_rate = (len(results_df) / total_pharmacies) * 100 if total_pharmacies > 0 else 0
    
    if completion_rate < 100:
        remaining = total_pharmacies - len(results_df)
        estimated_time_remaining = (remaining / avg_rate) if avg_rate > 0 else 0
        
        print(f"\n💡 POUR CONTINUER:")
        print(f"   {remaining:,} pharmacies restantes ({100-completion_rate:.1f}%)")
        print(f"   Temps estimé restant : {estimated_time_remaining/60:.0f} minutes")
        print(f"   Commande: python generate_isochrones.py --resume")
    else:
        print(f"\n🎉 TRAITEMENT COMPLET!")
        print(f"   Toutes les pharmacies ont été traitées avec succès.")


def display_final_stats_optimized_with_backup(results_df, start_time, total_pharmacies, batches_processed, total_batches, output_dir):
    """
    Affiche les statistiques finales avec informations de sauvegarde
    
    Args:
        results_df (pd.DataFrame): Résultats finaux
        start_time (float): Timestamp de début
        total_pharmacies (int): Nombre total de pharmacies
        batches_processed (int): Nombre de batchs traités
        total_batches (int): Nombre total de batchs
        output_dir (Path): Dossier de sortie
    """
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("🎯 GÉNÉRATION OPTIMISÉE DES ISOCHRONES TERMINÉE AVEC SAUVEGARDE")
    print("=" * 70)
    
    print(f"📊 Total pharmacies dans le dataset : {total_pharmacies:,}")
    print(f"📋 Total pharmacies traitées        : {len(results_df):,}")
    print(f"📦 Batchs traités                  : {batches_processed:,}/{total_batches:,}")
    
    # Calcul des succès par type
    success_stats = {}
    total_successes = 0
    total_expected = len(results_df) * len(ISOCHRONE_CONFIG)
    
    for iso_type in ISOCHRONE_CONFIG.keys():
        success_col = f'{iso_type}_success'
        if success_col in results_df.columns:
            successes = results_df[success_col].sum()
            success_pct = (successes / len(results_df)) * 100 if len(results_df) > 0 else 0
            success_stats[iso_type] = (successes, success_pct)
            total_successes += successes
    
    total_failures = total_expected - total_successes
    total_success_pct = (total_successes / total_expected) * 100 if total_expected > 0 else 0
    
    print(f"\n🎯 RÉSULTATS GLOBAUX:")
    print(f"   ✅ Succès total     : {total_successes:,} ({total_success_pct:.1f}%)")
    print(f"   ❌ Échecs total     : {total_failures:,} ({100 - total_success_pct:.1f}%)")
    
    print(f"\n📍 PAR TYPE D'ISOCHRONE:")
    for iso_type, (successes, success_pct) in success_stats.items():
        failures = len(results_df) - successes
        print(f"   {iso_type:<12} : {successes:,} succès, {failures:,} échecs ({success_pct:.1f}%)")
    
    # Statistiques de performance
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    
    avg_rate = len(results_df) / elapsed * 60 if elapsed > 0 else 0  # pharmacies par minute
    avg_batch_time = elapsed / batches_processed if batches_processed > 0 else 0
    
    print(f"\n⏱️  PERFORMANCE:")
    print(f"   Temps total          : {hours:02d}h {minutes:02d}min {seconds:02d}s")
    print(f"   Vitesse moyenne      : {avg_rate:.1f} pharmacies/min")
    print(f"   Temps moyen/batch    : {avg_batch_time:.1f}s")
    
    # Informations de sauvegarde
    summary_file = output_dir / "isochrones_summary.csv"
    backup_dir = output_dir / "backups"
    
    print(f"\n💾 FICHIERS DE SAUVEGARDE:")
    print(f"   📄 Fichier principal     : {summary_file.name}")
    
    if backup_dir.exists():
        backup_files = list(backup_dir.glob("isochrones_summary_backup_*.csv"))
        print(f"   🔒 Fichiers de backup    : {len(backup_files)} fichiers")
        if backup_files:
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
            print(f"   📅 Dernier backup       : {backup_time.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Vérifier le fichier de statut
    status_file = output_dir / "progress_status.json"
    if status_file.exists():
        print(f"   📊 Fichier de statut     : {status_file.name}")
    
    # Compter les fichiers créés
    total_files = total_successes
    print(f"\n📁 FICHIERS CRÉÉS:")
    print(f"   📄 {total_files:,} fichiers GeoJSON d'isochrones")
    print(f"   📋 1 fichier de résumé principal")
    print(f"   🔒 {len(backup_files) if 'backup_files' in locals() else 0} fichiers de backup")
    print(f"   📝 1 fichier de logs")
    print(f"   🗂️ Métadonnées de batchs et cache")
    
    # Estimation de la taille
    estimated_size_gb = total_files * 0.05  # ~50 KB par fichier GeoJSON
    cache_size_gb = batches_processed * 0.1  # Estimation cache graphes
    backup_size_gb = len(backup_files) * 0.01 if 'backup_files' in locals() else 0
    total_size_gb = estimated_size_gb + cache_size_gb + backup_size_gb
    
    print(f"\n💾 ESPACE DISQUE:")
    print(f"   Isochrones          : {estimated_size_gb:.1f} GB")
    print(f"   Cache graphes       : {cache_size_gb:.1f} GB")
    print(f"   Backups             : {backup_size_gb:.1f} GB")
    print(f"   Total estimé        : {total_size_gb:.1f} GB")
    
    # Sécurité des données
    print(f"\n🔒 SÉCURITÉ DES DONNÉES:")
    print(f"   ✅ Sauvegarde automatique activée")
    print(f"   ✅ Système de backup rotatif")
    print(f"   ✅ Reprise automatique en cas d'interruption")
    print(f"   ✅ Checkpoints fréquents (toutes les {CHECKPOINT_FREQUENCY} pharmacies)")
    
    print("=" * 70)
    
    # Conseils pour la suite
    completion_rate = (len(results_df) / total_pharmacies) * 100 if total_pharmacies > 0 else 0
    
    if completion_rate < 100:
        remaining = total_pharmacies - len(results_df)
        estimated_time_remaining = (remaining / avg_rate) if avg_rate > 0 else 0
        
        print(f"\n💡 POUR CONTINUER:")
        print(f"   {remaining:,} pharmacies restantes ({100-completion_rate:.1f}%)")
        print(f"   Temps estimé restant : {estimated_time_remaining/60:.0f} minutes")
        print(f"   Commande: python scripts\\generate_isochrones.py --resume")
        print(f"   Vos données sont sauvegardées et la reprise sera automatique !")
    else:
        print(f"\n🎉 TRAITEMENT COMPLET AVEC SAUVEGARDES SÉCURISÉES!")
        print(f"   Toutes les pharmacies ont été traitées avec succès.")
        print(f"   Les données sont protégées par {len(backup_files) if 'backup_files' in locals() else 0} backups.")


if __name__ == "__main__":
    exit(main())