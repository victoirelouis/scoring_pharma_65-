"""
Script 2 : Calcul des variables de CONCURRENCE par isochrone

Ce script calcule pour chaque pharmacie :
- Le nombre de pharmacies concurrentes dans ses isochrones (6 types)
- La distance à la pharmacie concurrente la plus proche

FONCTIONNALITES :
    - Détection automatique des isochrones déjà calculés (évite les doublons)
    - Calcul uniquement des isochrones manquants
    - Checkpoints automatiques tous les 250 pharmacies pour reprise en cas d'interruption
    - Logs de progression toutes les 100 pharmacies avec ETA
    - Fusion automatique avec le fichier existant
    - Backup horodaté à la fin du traitement

Inputs:
    - pharmacies_final.csv : Fichier des pharmacies avec id_pharmacie, latitude, longitude
    - isochrones/walk_5min/*.geojson : Polygones isochrones 5min à pied
    - isochrones/walk_10min/*.geojson : Polygones isochrones 10min à pied
    - isochrones/drive_5min/*.geojson : Polygones isochrones 5min en voiture
    - isochrones/drive_10min/*.geojson : Polygones isochrones 10min en voiture
    - isochrones/drive_15min/*.geojson : Polygones isochrones 15min en voiture
    - isochrones/drive_20min/*.geojson : Polygones isochrones 20min en voiture

Outputs:
    - pharmacies_avec_concurrence.csv : Variables concurrence par pharmacie
        Colonnes créées (6 isochrones + 1 distance = 7 variables) :
        * nb_pharmacies_concurrentes_walk_5min
        * nb_pharmacies_concurrentes_walk_10min
        * nb_pharmacies_concurrentes_drive_5min
        * nb_pharmacies_concurrentes_drive_10min
        * nb_pharmacies_concurrentes_drive_15min
        * nb_pharmacies_concurrentes_drive_20min
        * distance_pharmacie_plus_proche (km)

    - checkpoint_concurrence.csv : Sauvegarde intermédiaire (tous les 250 pharmacies)
    - backups_concurrence/pharmacies_concurrence_{timestamp}.csv : Backup horodaté final

Durée estimée:
    - ~15 minutes pour les 6 isochrones (19,307 pharmacies)
    - ~10 minutes pour 4 isochrones si walk_5min et drive_10min déjà calculés
    - Script interruptible et reprise automatique au dernier checkpoint

Auteur: Pipeline ML Pharmacies
Date: 2025-01-12
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from tqdm import tqdm
from shapely.geometry import Point, shape
from datetime import datetime
import geopandas as gpd
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
    ISOCHRONES_CONFIG,
    CONCURRENCE_CONFIG,
    LOGGING_CONFIG
)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['log_file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConcurrenceProcessor:
    """
    Classe pour calculer les variables de concurrence par isochrone
    """
    
    def __init__(self):
        """Initialisation du processeur"""
        self.pharmacies_df = None
        self.pharmacies_gdf = None  # GeoDataFrame pour requêtes spatiales
        self.distance_matrix = None  # Matrice de distances précalculée
        self.config_iso = ISOCHRONES_CONFIG
        self.config_concurrence = CONCURRENCE_CONFIG
        self.isochrones_a_calculer = []  # Sera rempli après détection automatique

        logger.info("Initialisation du processeur de concurrence")
    
    def load_data(self):
        """Charge les données pharmacies"""
        logger.info("Chargement des données pharmacies...")
        
        # Charger les pharmacies
        pharmacies_path = INPUT_FILES['pharmacies']
        logger.info(f"Chargement depuis {pharmacies_path}")
        self.pharmacies_df = pd.read_csv(pharmacies_path, sep=';')
        logger.info(f"  -> {len(self.pharmacies_df):,} pharmacies chargees")
        
        # Vérifier les colonnes nécessaires
        col_id = self.config_iso['colonne_id_pharmacie']
        required_cols = [col_id, 'latitude', 'longitude']
        missing_cols = [col for col in required_cols if col not in self.pharmacies_df.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes dans le fichier pharmacies: {missing_cols}")
        
        # Nettoyer les coordonnées manquantes
        before_clean = len(self.pharmacies_df)
        self.pharmacies_df = self.pharmacies_df.dropna(subset=['latitude', 'longitude'])
        after_clean = len(self.pharmacies_df)
        if before_clean > after_clean:
            logger.warning(f"  -> {before_clean - after_clean:,} pharmacies supprimees (coordonnees manquantes)")
        
        # Créer GeoDataFrame avec index spatial
        logger.info("Creation du GeoDataFrame avec index spatial...")
        geometry = [Point(xy) for xy in zip(self.pharmacies_df['longitude'], self.pharmacies_df['latitude'])]
        self.pharmacies_gdf = gpd.GeoDataFrame(
            self.pharmacies_df, 
            geometry=geometry,
            crs='EPSG:4326'
        )
        self.pharmacies_gdf.sindex  # Force la création de l'index spatial
        
        # Précalculer la matrice de distances (vectorisé)
        logger.info("Precalcul de la matrice de distances...")
        self._precalculate_distances()
        
        logger.info("Donnees chargees avec succes")
    
    def _precalculate_distances(self):
        """Précalcule la matrice de distances entre toutes les pharmacies (vectorisé)"""
        lats = np.radians(self.pharmacies_df['latitude'].values)
        lons = np.radians(self.pharmacies_df['longitude'].values)
        
        # Broadcasting pour calculer toutes les distances d'un coup
        R = 6371.0  # Rayon de la Terre en km
        
        # Utiliser la formule haversine vectorisée
        lat1 = lats[:, np.newaxis]
        lon1 = lons[:, np.newaxis]
        lat2 = lats[np.newaxis, :]
        lon2 = lons[np.newaxis, :]
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        self.distance_matrix = R * c
        logger.info(f"  -> Matrice de distances calculee: {self.distance_matrix.shape}")

    def _detect_isochrones_a_calculer(self):
        """Détecte automatiquement quels isochrones ont déjà été calculés"""
        logger.info("="*80)
        logger.info("DETECTION AUTOMATIQUE DES ISOCHRONES DEJA CALCULES")
        logger.info("="*80)

        output_file = INTERMEDIATE_FILES['pharmacies_avec_concurrence']
        isochrones_deja_calcules = []

        if output_file.exists():
            logger.info(f"Fichier de sortie existant trouve : {output_file.name}")
            existing_df = pd.read_csv(output_file, nrows=0)
            existing_cols = set(existing_df.columns)

            for iso_type in self.config_iso['types_isochrones']:
                col_name = f'nb_pharmacies_concurrentes_{iso_type}'
                if col_name in existing_cols:
                    isochrones_deja_calcules.append(iso_type)
                    logger.info(f"  [OK] {iso_type:15s} : DEJA CALCULE")
                else:
                    logger.info(f"  [ ] {iso_type:15s} : A CALCULER")
        else:
            logger.info("Aucun fichier de sortie existant")
            for iso_type in self.config_iso['types_isochrones']:
                logger.info(f"  [ ] {iso_type:15s} : A CALCULER")

        logger.info("")
        logger.info("RESUME :")
        if isochrones_deja_calcules:
            logger.info(f"  Isochrones deja calcules (SKIP) : {isochrones_deja_calcules}")

        self.isochrones_a_calculer = [
            iso for iso in self.config_iso['types_isochrones']
            if iso not in isochrones_deja_calcules
        ]

        logger.info(f"  Isochrones a calculer : {self.isochrones_a_calculer}")
        logger.info(f"  Total a traiter : {len(self.isochrones_a_calculer)}/{len(self.config_iso['types_isochrones'])}")
        logger.info("="*80)
        logger.info("")

    @lru_cache(maxsize=1000)
    def load_isochrone(self, pharmacie_id, type_isochrone):
        """
        Charge un fichier isochrone GeoJSON
        
        Args:
            pharmacie_id: ID de la pharmacie
            type_isochrone: 'walk_5min' ou 'drive_10min'
        
        Returns:
            shapely.geometry.Polygon ou None si erreur
        """
        # Construire le chemin du fichier
        iso_dir = INPUT_FILES[f'isochrones_{type_isochrone}']
        pattern = self.config_iso['pattern_nom_fichier']
        filename = pattern.format(id_pharmacie=pharmacie_id)
        filepath = iso_dir / filename
        
        # Charger le GeoJSON
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Extraire la géométrie
            if 'features' in geojson_data and len(geojson_data['features']) > 0:
                geometry = shape(geojson_data['features'][0]['geometry'])
                return geometry
            elif 'geometry' in geojson_data:
                geometry = shape(geojson_data['geometry'])
                return geometry
            else:
                logger.warning(f"Format GeoJSON invalide pour {filename}")
                return None
        
        except FileNotFoundError:
            logger.debug(f"Fichier isochrone introuvable: {filename}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement de {filename}: {e}")
            return None
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calcule la distance entre deux points GPS en km (formule haversine)
        
        Args:
            lat1, lon1: Coordonnées point 1
            lat2, lon2: Coordonnées point 2
        
        Returns:
            Distance en km
        """
        # Rayon de la Terre en km
        R = 6371.0
        
        # Conversion en radians
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        # Différences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Formule haversine
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def count_competitors_in_isochrone(self, pharmacie_id, isochrone_polygon):
        """
        Compte le nombre de pharmacies concurrentes dans un isochrone (OPTIMISÉ)
        
        Args:
            pharmacie_id: ID de la pharmacie de référence
            isochrone_polygon: Polygone shapely de l'isochrone
        
        Returns:
            Nombre de concurrents
        """
        if isochrone_polygon is None:
            return 0
        
        # OPTIMISATION 1 : Filtrage rapide par bounding box
        minx, miny, maxx, maxy = isochrone_polygon.bounds
        
        # Filtrer les pharmacies dans la bbox (très rapide)
        candidates = self.pharmacies_gdf[
            (self.pharmacies_gdf['latitude'] >= miny) & 
            (self.pharmacies_gdf['latitude'] <= maxy) &
            (self.pharmacies_gdf['longitude'] >= minx) & 
            (self.pharmacies_gdf['longitude'] <= maxx) &
            (self.pharmacies_gdf[self.config_iso['colonne_id_pharmacie']] != pharmacie_id)
        ]
        
        if len(candidates) == 0:
            return 0
        
        # OPTIMISATION 2 : Test vectorisé avec GeoDataFrame
        # within() est optimisé par geopandas
        count = candidates.geometry.within(isochrone_polygon).sum()
        
        return int(count)
    
    def find_nearest_competitor(self, pharmacie_id):
        """
        Trouve la distance à la pharmacie concurrente la plus proche (OPTIMISÉ)
        
        Args:
            pharmacie_id: ID de la pharmacie de référence
        
        Returns:
            Distance en km à la pharmacie la plus proche
        """
        # Trouver la position de cette pharmacie dans le DataFrame
        col_id = self.config_iso['colonne_id_pharmacie']
        try:
            # Utiliser iloc pour obtenir la position relative (0-based)
            mask = self.pharmacies_df[col_id] == pharmacie_id
            position = mask.to_numpy().nonzero()[0][0]
        except IndexError:
            return None
        
        # OPTIMISATION : Utiliser la matrice précalculée
        # Récupérer toutes les distances depuis cette pharmacie
        distances_from_pharma = self.distance_matrix[position].copy()
        
        # Exclure la distance à soi-même (= 0)
        distances_from_pharma[position] = np.inf
        
        # Trouver la distance minimale
        min_distance = np.min(distances_from_pharma)
        
        if np.isinf(min_distance):
            return None
        
        # Vérifier distance maximale configurée
        max_distance = self.config_concurrence['distance_max_plus_proche_km']
        if min_distance > max_distance:
            return max_distance  # Plafonner
        else:
            return float(min_distance)
    
    def process_pharmacie(self, pharmacie_id):
        """
        Traite une pharmacie : calcule variables concurrence

        Args:
            pharmacie_id: ID de la pharmacie

        Returns:
            dict avec les variables pour cette pharmacie
        """
        result = {self.config_iso['colonne_id_pharmacie']: pharmacie_id}

        # Pour chaque type d'isochrone À CALCULER (skip ceux déjà calculés)
        for type_iso in self.isochrones_a_calculer:
            # Charger l'isochrone
            isochrone = self.load_isochrone(pharmacie_id, type_iso)

            # Compter concurrents dans l'isochrone
            nb_concurrents = self.count_competitors_in_isochrone(pharmacie_id, isochrone)
            result[f'nb_pharmacies_concurrentes_{type_iso}'] = nb_concurrents

        # Distance à la pharmacie la plus proche (indépendant des isochrones)
        # Calculer seulement si pas déjà dans le fichier existant
        output_file = INTERMEDIATE_FILES['pharmacies_avec_concurrence']
        if not output_file.exists() or 'distance_pharmacie_plus_proche' not in pd.read_csv(output_file, nrows=0).columns:
            distance_plus_proche = self.find_nearest_competitor(pharmacie_id)
            result['distance_pharmacie_plus_proche'] = distance_plus_proche

        return result
    
    def process_all_pharmacies(self):
        """
        Traite toutes les pharmacies et génère le DataFrame final

        Returns:
            DataFrame avec toutes les variables concurrence
        """
        logger.info("="*80)
        logger.info("CALCUL CONCURRENCE POUR TOUS LES ISOCHRONES MANQUANTS")
        logger.info("="*80)
        logger.info(f"Isochrones a traiter : {self.isochrones_a_calculer}")
        logger.info(f"Nombre d'isochrones : {len(self.isochrones_a_calculer)}")
        logger.info("")
        logger.info("PROGRESSION :")
        logger.info("  - Checkpoint automatique tous les 250 pharmacies")
        logger.info("  - Vous pouvez interrompre (Ctrl+C) et relancer")
        logger.info("="*80)
        logger.info("")

        col_id = self.config_iso['colonne_id_pharmacie']
        pharmacies_ids = self.pharmacies_df[col_id].tolist()

        # Checkpoint path
        checkpoint_path = INTERMEDIATE_FILES['pharmacies_avec_concurrence'].parent / 'checkpoint_concurrence.csv'

        # Charger checkpoint si existe
        results = []
        start_idx = 0
        if checkpoint_path.exists():
            checkpoint_df = pd.read_csv(checkpoint_path)
            results = checkpoint_df.to_dict('records')
            start_idx = len(results)
            logger.info(f"Reprise depuis checkpoint: {start_idx:,} pharmacies deja traitees")

        # Traiter chaque pharmacie avec barre de progression et logs
        import time
        start_time = time.time()

        for idx, pharmacie_id in enumerate(tqdm(pharmacies_ids[start_idx:],
                                                 desc=f"Calcul {len(self.isochrones_a_calculer)} isochrones",
                                                 initial=start_idx,
                                                 total=len(pharmacies_ids)),
                                          start=start_idx):
            result = self.process_pharmacie(pharmacie_id)
            results.append(result)

            # Log visuel toutes les 100 pharmacies
            if idx > 0 and idx % 100 == 0:
                elapsed_min = (time.time() - start_time) / 60
                pharma_par_min = idx / elapsed_min if elapsed_min > 0 else 0
                restant = len(pharmacies_ids) - idx
                eta_min = restant / pharma_par_min if pharma_par_min > 0 else 0

                logger.info("")
                logger.info(f"{'='*80}")
                logger.info(f"PROGRESSION : {idx:,}/{len(pharmacies_ids):,} pharmacies ({idx/len(pharmacies_ids)*100:.1f}%)")
                logger.info(f"  Temps ecoule : {elapsed_min:.1f} min")
                logger.info(f"  Vitesse : {pharma_par_min:.1f} pharmacies/min")
                logger.info(f"  Temps restant estime : {eta_min:.1f} min (~{eta_min/60:.1f}h)")
                logger.info(f"{'='*80}")
                logger.info("")

            # Checkpoint tous les 250 pharmacies
            if idx > 0 and idx % 250 == 0:
                checkpoint_df = pd.DataFrame(results)
                checkpoint_df.to_csv(checkpoint_path, index=False)
                logger.info(f"[CHECKPOINT] Sauvegarde : {idx:,} pharmacies traitees")

        # Convertir en DataFrame
        concurrence_vars_df = pd.DataFrame(results)

        logger.info("")
        logger.info("="*80)
        logger.info("FUSION AVEC FICHIER EXISTANT")
        logger.info("="*80)

        output_file = INTERMEDIATE_FILES['pharmacies_avec_concurrence']

        # Fusionner avec fichier existant si présent
        if output_file.exists():
            logger.info(f"Chargement fichier existant : {output_file.name}")
            existing_df = pd.read_csv(output_file)
            logger.info(f"  -> {len(existing_df):,} pharmacies, {len(existing_df.columns)} colonnes")

            # Fusionner avec les nouveaux résultats
            logger.info(f"Ajout des nouveaux isochrones : {self.isochrones_a_calculer}")
            pharmacies_avec_concurrence = existing_df.merge(
                concurrence_vars_df,
                on=col_id,
                how='left'
            )
            logger.info(f"  -> Apres fusion : {len(pharmacies_avec_concurrence.columns)} colonnes")
        else:
            # Première exécution : joindre avec pharmacies original
            logger.info("Premiere execution : creation du fichier de sortie")
            pharmacies_avec_concurrence = self.pharmacies_df.merge(
                concurrence_vars_df,
                on=col_id,
                how='left'
            )

        logger.info(f"Traitement termine : {len(pharmacies_avec_concurrence):,} pharmacies")
        logger.info(f"  -> {len(concurrence_vars_df.columns) - 1} nouvelles variables creees")

        # Supprimer checkpoint final
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("Checkpoint supprime (calcul termine)")

        return pharmacies_avec_concurrence
    
    def generate_report(self, output_df):
        """
        Génère un rapport sur la concurrence
        
        Args:
            output_df: DataFrame final avec variables concurrence
        """
        logger.info("Génération du rapport de concurrence...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT D'ANALYSE DE LA CONCURRENCE")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Configuration
        report_lines.append("CONFIGURATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Nombre de pharmacies analysées : {len(output_df):,}")
        report_lines.append("")
        
        # Statistiques par isochrone
        report_lines.append("STATISTIQUES PAR ISOCHRONE")
        report_lines.append("-" * 80)
        
        for type_iso in self.config_iso['types_isochrones']:
            col = f'nb_pharmacies_concurrentes_{type_iso}'
            
            if col in output_df.columns:
                report_lines.append(f"\n{type_iso.upper()}:")
                report_lines.append(f"  Moyenne concurrents : {output_df[col].mean():.2f}")
                report_lines.append(f"  Médiane concurrents : {output_df[col].median():.0f}")
                report_lines.append(f"  Min concurrents : {output_df[col].min():.0f}")
                report_lines.append(f"  Max concurrents : {output_df[col].max():.0f}")
                
                # Distribution
                report_lines.append(f"  Distribution :")
                report_lines.append(f"    - 0 concurrent : {(output_df[col] == 0).sum():,} pharmacies ({(output_df[col] == 0).sum() / len(output_df) * 100:.1f}%)")
                report_lines.append(f"    - 1-2 concurrents : {((output_df[col] >= 1) & (output_df[col] <= 2)).sum():,} pharmacies")
                report_lines.append(f"    - 3-5 concurrents : {((output_df[col] >= 3) & (output_df[col] <= 5)).sum():,} pharmacies")
                report_lines.append(f"    - 6-10 concurrents : {((output_df[col] >= 6) & (output_df[col] <= 10)).sum():,} pharmacies")
                report_lines.append(f"    - 10+ concurrents : {(output_df[col] > 10).sum():,} pharmacies")
        
        report_lines.append("")
        
        # Statistiques distance pharmacie la plus proche
        report_lines.append("DISTANCE À LA PHARMACIE LA PLUS PROCHE")
        report_lines.append("-" * 80)
        
        col_dist = 'distance_pharmacie_plus_proche'
        if col_dist in output_df.columns:
            distances = output_df[col_dist].dropna()
            report_lines.append(f"Moyenne : {distances.mean():.2f} km")
            report_lines.append(f"Médiane : {distances.median():.2f} km")
            report_lines.append(f"Min : {distances.min():.2f} km")
            report_lines.append(f"Max : {distances.max():.2f} km")
            
            # Distribution
            report_lines.append(f"\nDistribution :")
            report_lines.append(f"  - < 500m : {(distances < 0.5).sum():,} pharmacies ({(distances < 0.5).sum() / len(distances) * 100:.1f}%)")
            report_lines.append(f"  - 0.5-1 km : {((distances >= 0.5) & (distances < 1)).sum():,} pharmacies")
            report_lines.append(f"  - 1-2 km : {((distances >= 1) & (distances < 2)).sum():,} pharmacies")
            report_lines.append(f"  - 2-5 km : {((distances >= 2) & (distances < 5)).sum():,} pharmacies")
            report_lines.append(f"  - 5-10 km : {((distances >= 5) & (distances < 10)).sum():,} pharmacies")
            report_lines.append(f"  - 10+ km : {(distances >= 10).sum():,} pharmacies")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Écrire le rapport
        report_path = INTERMEDIATE_FILES['pharmacies_avec_concurrence'].parent / 'rapport_concurrence.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Rapport sauvegardé : {report_path}")
        
        # Afficher aussi dans les logs
        logger.info("\n" + '\n'.join(report_lines))
    
    def save_results(self, output_df):
        """
        Sauvegarde le DataFrame final avec backup horodaté

        Args:
            output_df: DataFrame à sauvegarder
        """
        output_path = INTERMEDIATE_FILES['pharmacies_avec_concurrence']
        logger.info("")
        logger.info("="*80)
        logger.info("SAUVEGARDE DES RESULTATS")
        logger.info("="*80)
        logger.info(f"Fichier principal : {output_path.name}")

        # Sauvegarder le fichier principal
        output_df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"  -> {len(output_df):,} lignes x {len(output_df.columns)} colonnes")

        # Créer backup horodaté
        backup_dir = output_path.parent / "backups_concurrence"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"pharmacies_concurrence_{timestamp}.csv"
        output_df.to_csv(backup_path, index=False, encoding='utf-8')
        logger.info(f"Backup horodate : {backup_path.name}")
        logger.info("="*80)
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DEMARRAGE DU SCRIPT 2 : CALCUL CONCURRENCE PAR ISOCHRONE")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Isochrones a traiter : {self.config_iso['types_isochrones']}")
        logger.info(f"Nombre total d'isochrones : {len(self.config_iso['types_isochrones'])}")
        logger.info("")
        logger.info("IMPORTANT :")
        logger.info("  - Checkpoints automatiques tous les 250 pharmacies")
        logger.info("  - Backup horodate a la fin")
        logger.info("  - Vous pouvez interrompre (Ctrl+C) et relancer")
        logger.info("  - Le script reprendra automatiquement la ou il s'est arrete")
        logger.info("=" * 80)
        logger.info("")

        start_time = datetime.now()

        try:
            # 1. Charger les données
            self.load_data()

            # 2. Détecter les isochrones déjà calculés
            self._detect_isochrones_a_calculer()

            # Si aucun isochrone à calculer, terminer
            if len(self.isochrones_a_calculer) == 0:
                logger.info("Tous les isochrones ont deja ete calcules !")
                logger.info("Rien a faire. Script termine.")
                return

            # 3. Traiter toutes les pharmacies
            output_df = self.process_all_pharmacies()

            # 4. Générer le rapport
            self.generate_report(output_df)

            # 5. Sauvegarder
            self.save_results(output_df)

            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"SCRIPT 2 TERMINE AVEC SUCCES")
            logger.info(f"Duree d'execution : {duration}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    processor = ConcurrenceProcessor()
    processor.run()


if __name__ == "__main__":
    main()
