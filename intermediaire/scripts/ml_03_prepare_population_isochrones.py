"""
Script 3 : Calcul des variables POPULATION par isochrone depuis données IRIS

Ce script calcule pour chaque pharmacie la population accessible dans ses isochrones
en croisant les polygones isochrones avec les zones IRIS et leurs données démographiques.

FONCTIONNALITES :
    - Détection automatique des isochrones déjà calculés (évite les doublons)
    - Calcul uniquement des isochrones manquants
    - Checkpoints automatiques tous les 250 pharmacies pour reprise en cas d'interruption
    - Logs de progression toutes les 100 pharmacies avec ETA
    - Fusion automatique avec le fichier existant
    - Backup horodaté à la fin du traitement

Inputs:
    - population_age.csv : Données population par IRIS (codes INSEE P22_XXX)
    - contours_iris (GPKG) : Géométries des zones IRIS
    - pharmacies_final.csv : Fichier des pharmacies
    - isochrones/walk_5min/*.geojson : Polygones isochrones 5min à pied
    - isochrones/walk_10min/*.geojson : Polygones isochrones 10min à pied
    - isochrones/drive_5min/*.geojson : Polygones isochrones 5min en voiture
    - isochrones/drive_10min/*.geojson : Polygones isochrones 10min en voiture
    - isochrones/drive_15min/*.geojson : Polygones isochrones 15min en voiture
    - isochrones/drive_20min/*.geojson : Polygones isochrones 20min en voiture

Outputs:
    - pharmacies_avec_population_isochrones.csv : Variables population par pharmacie
        Colonnes créées (15 variables × 6 isochrones = 90 colonnes) :
        * pop_totale_{isochrone}
        * pop_65_plus_{isochrone}
        * pop_65_74_{isochrone}
        * pop_75_84_{isochrone}
        * pop_85_plus_{isochrone}
        * pop_65_plus_hommes_{isochrone}
        * pop_65_plus_femmes_{isochrone}
        * pop_65_74_hommes_{isochrone}
        * pop_65_74_femmes_{isochrone}
        * pop_75_84_hommes_{isochrone}
        * pop_75_84_femmes_{isochrone}
        * pop_85_plus_hommes_{isochrone}
        * pop_85_plus_femmes_{isochrone}
        * taux_retraites_{isochrone}
        * taux_cadres_{isochrone}

        (avec {isochrone} = walk_5min, walk_10min, drive_5min, drive_10min, drive_15min, drive_20min)

    - checkpoint_population.csv : Sauvegarde intermédiaire (tous les 250 pharmacies)
    - backups_population/pharmacies_population_{timestamp}.csv : Backup horodaté final

Durée estimée:
    - ~40 minutes pour les 6 isochrones (19,307 pharmacies)
    - ~30 minutes pour 4 isochrones si walk_5min et drive_10min déjà calculés
    - Script interruptible et reprise automatique au dernier checkpoint

Auteur: Pipeline ML Pharmacies
Date: 2025-01-12
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import json
import logging
from tqdm import tqdm
from shapely.geometry import shape
from datetime import datetime
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
    ISOCHRONES_CONFIG,
    POPULATION_CONFIG,
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


class PopulationProcessor:
    """
    Classe pour calculer les variables population par isochrone depuis IRIS
    """
    
    def __init__(self):
        """Initialisation du processeur"""
        self.pharmacies_df = None
        self.population_iris_df = None
        self.iris_geometries = None
        self.config_iso = ISOCHRONES_CONFIG
        self.config_pop = POPULATION_CONFIG
        self.isochrones_a_calculer = []  # Sera rempli après détection automatique

        logger.info("Initialisation du processeur de population")
    
    def load_data(self):
        """Charge toutes les données nécessaires"""
        logger.info("Chargement des données...")
        
        # 1. Charger les pharmacies
        pharmacies_path = INPUT_FILES['pharmacies']
        logger.info(f"Chargement des pharmacies depuis {pharmacies_path}")
        self.pharmacies_df = pd.read_csv(pharmacies_path, sep=';')
        logger.info(f"  -> {len(self.pharmacies_df):,} pharmacies chargees")
        
        # 2. Charger les données population IRIS
        population_path = INPUT_FILES['population_age_csv']
        logger.info(f"Chargement des données population depuis {population_path}")
        self.population_iris_df = pd.read_csv(population_path, sep=';', encoding='utf-8', dtype={'IRIS': str})
        logger.info(f"  -> {len(self.population_iris_df):,} IRIS charges")
        
        # Nettoyer le nom de la colonne IRIS (peut avoir des espaces)
        self.population_iris_df.columns = self.population_iris_df.columns.str.strip()
        
        # Vérifier colonne IRIS
        if 'IRIS' not in self.population_iris_df.columns:
            raise ValueError("Colonne 'IRIS' manquante dans population_age.csv")
        
        # Convertir les codes IRIS en string avec padding (ex: 10010000 -> '010010000')
        logger.info("Normalisation des codes IRIS...")
        self.population_iris_df['IRIS'] = self.population_iris_df['IRIS'].astype(str).str.zfill(9)
        
        # 3. Charger les géométries IRIS
        iris_gpkg_path = INPUT_FILES['zones_iris_gpkg']
        logger.info(f"Chargement des géométries IRIS depuis {iris_gpkg_path}")
        
        # Essayer de charger le GPKG
        try:
            self.iris_geometries = gpd.read_file(iris_gpkg_path)
            logger.info(f"  -> {len(self.iris_geometries):,} geometries IRIS chargees")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier GPKG: {e}")
            raise
        
        # Vérifier nom colonne IRIS dans géométries
        possible_cols = ['IRIS', 'CODE_IRIS', 'code_iris', 'dcomiris']
        iris_col = None
        for col in possible_cols:
            if col in self.iris_geometries.columns:
                iris_col = col
                break
        
        if iris_col is None:
            logger.error(f"Colonne IRIS introuvable. Colonnes disponibles: {list(self.iris_geometries.columns)}")
            raise ValueError("Colonne code IRIS non trouvée dans le fichier géométries")
        
        # Renommer pour uniformiser
        if iris_col != 'IRIS':
            self.iris_geometries = self.iris_geometries.rename(columns={iris_col: 'IRIS'})
            logger.info(f"  -> Colonne '{iris_col}' renommee en 'IRIS'")
        
        # Joindre population avec géométries
        logger.info("Jointure population + géométries IRIS...")
        self.iris_data_geo = self.iris_geometries.merge(
            self.population_iris_df,
            on='IRIS',
            how='inner'
        )
        logger.info(f"  -> {len(self.iris_data_geo):,} IRIS avec donnees + geometrie")
        
        # Convertir en GeoDataFrame si nécessaire
        if not isinstance(self.iris_data_geo, gpd.GeoDataFrame):
            self.iris_data_geo = gpd.GeoDataFrame(self.iris_data_geo, geometry='geometry')
        
        # Assurer que les géométries sont valides
        self.iris_data_geo['geometry'] = self.iris_data_geo['geometry'].make_valid()
        
        # OPTIMISATION 1: Precalculer les surfaces IRIS une seule fois
        logger.info("Precalcul des surfaces IRIS...")
        self.iris_data_geo['iris_area'] = self.iris_data_geo.geometry.area
        
        # OPTIMISATION 2: Forcer creation de l'index spatial (rtree)
        logger.info("Creation de l'index spatial...")
        _ = self.iris_data_geo.sindex
        
        logger.info("Toutes les données chargées avec succès")

        # Détection automatique des isochrones déjà calculés
        self._detect_isochrones_a_calculer()

    def _detect_isochrones_a_calculer(self):
        """Détecte automatiquement quels isochrones ont déjà été calculés"""
        logger.info("="*80)
        logger.info("DETECTION AUTOMATIQUE DES ISOCHRONES DEJA CALCULES")
        logger.info("="*80)

        # Vérifier si le fichier de sortie existe déjà
        output_file = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones']

        isochrones_deja_calcules = []

        if output_file.exists():
            logger.info(f"Fichier de sortie existant trouve : {output_file.name}")
            try:
                # Lire juste les colonnes (sans charger les données)
                existing_df = pd.read_csv(output_file, nrows=0)
                existing_cols = set(existing_df.columns)

                # Vérifier chaque isochrone
                for iso_type in self.config_iso['types_isochrones']:
                    # Chercher si des colonnes de cet isochrone existent
                    iso_cols = [c for c in existing_cols if f'_{iso_type}' in c]
                    if iso_cols:
                        isochrones_deja_calcules.append(iso_type)
                        logger.info(f"  [OK] {iso_type:15s} : DEJA CALCULE ({len(iso_cols)} colonnes trouvees)")
                    else:
                        logger.info(f"  [ ] {iso_type:15s} : A CALCULER")

            except Exception as e:
                logger.warning(f"Erreur lecture fichier existant : {e}")
                logger.warning("Tous les isochrones seront recalcules")
        else:
            logger.info("Aucun fichier de sortie existant")
            logger.info("Tous les isochrones seront calcules")

        # Déterminer les isochrones à calculer
        self.isochrones_a_calculer = [
            iso for iso in self.config_iso['types_isochrones']
            if iso not in isochrones_deja_calcules
        ]

        logger.info("")
        logger.info("RESUME :")
        logger.info(f"  Isochrones deja calcules (SKIP) : {isochrones_deja_calcules if isochrones_deja_calcules else 'Aucun'}")
        logger.info(f"  Isochrones a calculer : {self.isochrones_a_calculer}")
        logger.info(f"  Total a traiter : {len(self.isochrones_a_calculer)}/{len(self.config_iso['types_isochrones'])}")
        logger.info("="*80)
        logger.info("")

    def convert_insee_to_target_variables(self, iris_row):
        """
        Convertit les codes INSEE en variables cibles (65-74, 75-84, 85+)
        
        Args:
            iris_row: Ligne d'un IRIS avec codes INSEE
        
        Returns:
            dict avec variables cibles calculées
        """
        result = {}
        
        # Population totale
        result['pop_totale'] = iris_row.get('P22_POP', 0)
        
        # Calcul des tranches d'age par deduction depuis P22_POP65P et P22_POP75P
        # Colonnes disponibles: P22_POP65P, P22_POP75P, P22_POP80P
        
        # Population 65+ et 75+
        pop_65p = iris_row.get('P22_POP65P', 0)
        pop_75p = iris_row.get('P22_POP75P', 0)
        pop_80p = iris_row.get('P22_POP80P', 0)
        
        # CALCUL des tranches cibles par deduction:
        # 65-74 = 65+ MOINS 75+
        result['pop_65_74'] = max(0, pop_65p - pop_75p)
        
        # 75-84 = 75+ MOINS 85+ (approxime par 80+)
        result['pop_75_84'] = max(0, pop_75p - pop_80p)
        
        # 85+ approxime par 80+
        result['pop_85_plus'] = pop_80p
        
        # Total 65+
        result['pop_65_plus'] = pop_65p
        
        # PAR SEXE - meme logique
        # Hommes
        h_65p = iris_row.get('P22_H65P', 0)
        h_75p = iris_row.get('P22_H75P', 0)
        # Calcul ratio 80+ depuis total
        if pop_80p > 0 and pop_75p > 0:
            ratio_80p = pop_80p / pop_75p
        else:
            ratio_80p = 0.5
        h_80p = h_75p * ratio_80p
        
        result['pop_hommes_65_74'] = max(0, h_65p - h_75p)
        result['pop_hommes_75_84'] = max(0, h_75p - h_80p)
        result['pop_hommes_85_plus'] = h_80p
        result['pop_hommes_65_plus'] = h_65p
        
        # Femmes
        f_65p = iris_row.get('P22_F65P', 0)
        f_75p = iris_row.get('P22_F75P', 0)
        f_80p = f_75p * ratio_80p
        
        result['pop_femmes_65_74'] = max(0, f_65p - f_75p)
        result['pop_femmes_75_84'] = max(0, f_75p - f_80p)
        result['pop_femmes_85_plus'] = f_80p
        result['pop_femmes_65_plus'] = f_65p
        
        # VARIABLES BONUS : Retraités (utile pour le ML)
        pop_55p = iris_row.get('P22_POP55P', 0)
        retraites_55p = iris_row.get('C22_POP55P_STAT_GSEC32', 0)
        
        if pop_55p > 0:
            result['taux_retraites'] = retraites_55p / pop_55p
        else:
            result['taux_retraites'] = 0
        
        # Cadres (bonus)
        pop_15p = iris_row.get('C22_POP15P', 0)
        cadres = iris_row.get('C22_POP15P_STAT_GSEC13_23', 0)
        
        if pop_15p > 0:
            result['taux_cadres'] = cadres / pop_15p
        else:
            result['taux_cadres'] = 0
        
        return result
    
    @lru_cache(maxsize=2000)
    def load_isochrone(self, pharmacie_id, type_isochrone):
        """
        Charge un fichier isochrone GeoJSON et retourne un GeoDataFrame
        OPTIMISATION 3: Cache LRU pour eviter de recharger les memes fichiers
        
        Args:
            pharmacie_id: ID de la pharmacie
            type_isochrone: 'walk_5min' ou 'drive_10min'
        
        Returns:
            GeoDataFrame avec la géométrie de l'isochrone ou None
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
            elif 'geometry' in geojson_data:
                geometry = shape(geojson_data['geometry'])
            else:
                logger.warning(f"Format GeoJSON invalide pour {filename}")
                return None
            
            # Créer un GeoDataFrame
            gdf = gpd.GeoDataFrame([{'geometry': geometry}], crs='EPSG:4326')
            return gdf
        
        except FileNotFoundError:
            logger.debug(f"Fichier isochrone introuvable: {filename}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement de {filename}: {e}")
            return None
    
    def calculate_population_in_isochrone(self, isochrone_gdf):
        """
        Calcule la population dans un isochrone en croisant avec les IRIS
        OPTIMISATION 4: Bbox filtering + vectorisation complete de l'agregation
        
        Args:
            isochrone_gdf: GeoDataFrame de l'isochrone
        
        Returns:
            dict avec toutes les variables population agrégées
        """
        if isochrone_gdf is None or len(isochrone_gdf) == 0:
            return self._get_empty_population_dict()
        
        # Assurer même CRS
        if self.iris_data_geo.crs != isochrone_gdf.crs:
            isochrone_gdf = isochrone_gdf.to_crs(self.iris_data_geo.crs)
        
        # OPTIMISATION 4a: Bounding box filtering avec index spatial
        isochrone_polygon = isochrone_gdf.geometry.iloc[0]
        minx, miny, maxx, maxy = isochrone_polygon.bounds
        
        # Filtrer les IRIS candidats avec bbox
        candidates_idx = list(self.iris_data_geo.sindex.intersection((minx, miny, maxx, maxy)))
        if len(candidates_idx) == 0:
            return self._get_empty_population_dict()
        
        iris_candidates = self.iris_data_geo.iloc[candidates_idx].copy()
        
        # Intersection spatiale uniquement sur candidats (beaucoup plus rapide)
        try:
            intersected = gpd.overlay(
                iris_candidates,
                isochrone_gdf,
                how='intersection',
                keep_geom_type=False
            )
        except Exception as e:
            logger.warning(f"Erreur lors de l'intersection spatiale: {e}")
            return self._get_empty_population_dict()
        
        if len(intersected) == 0:
            return self._get_empty_population_dict()
        
        # Calculer la surface de chaque intersection
        intersected['intersection_area'] = intersected.geometry.area
        
        # Calculer le ratio de surface (iris_area deja precalculee)
        intersected['surface_ratio'] = (intersected['intersection_area'] / 
                                       intersected['iris_area']).clip(upper=1.0)
        
        # OPTIMISATION 4b: Vectorisation complete - calculer toutes les variables d'un coup
        # Population totale
        result = {
            'pop_totale': (intersected['P22_POP'].fillna(0) * intersected['surface_ratio']).sum()
        }
        
        # Variables d'age - Calcul par deduction depuis P22_POP65P et P22_POP75P
        pop_65p = intersected.get('P22_POP65P', pd.Series([0]*len(intersected))).fillna(0)
        pop_75p = intersected['P22_POP75P'].fillna(0)
        pop_80p = intersected.get('P22_POP80P', pd.Series([0]*len(intersected))).fillna(0)
        
        # Calcul ratio 80+ (vectorise)
        ratio_80p = np.where(pop_75p > 0, pop_80p / pop_75p, 0.5)
        pop_85p = pop_75p * ratio_80p
        
        # pop_65_74 = pop_65+ MOINS pop_75+ (deduction)
        pop_6574 = (pop_65p - pop_75p).clip(lower=0)
        
        result['pop_65_74'] = (pop_6574 * intersected['surface_ratio']).sum()
        result['pop_75_84'] = ((pop_75p - pop_85p).clip(lower=0) * intersected['surface_ratio']).sum()
        result['pop_85_plus'] = (pop_85p * intersected['surface_ratio']).sum()
        result['pop_65_plus'] = (pop_65p * intersected['surface_ratio']).sum()
        
        # Hommes - meme logique
        h_65p = intersected.get('P22_H65P', pd.Series([0]*len(intersected))).fillna(0)
        h_75p = intersected['P22_H75P'].fillna(0)
        h_85p = h_75p * ratio_80p
        h_6574 = (h_65p - h_75p).clip(lower=0)
        
        result['pop_hommes_65_74'] = (h_6574 * intersected['surface_ratio']).sum()
        result['pop_hommes_75_84'] = ((h_75p - h_85p).clip(lower=0) * intersected['surface_ratio']).sum()
        result['pop_hommes_85_plus'] = (h_85p * intersected['surface_ratio']).sum()
        result['pop_hommes_65_plus'] = (h_65p * intersected['surface_ratio']).sum()
        
        # Femmes - meme logique
        f_65p = intersected.get('P22_F65P', pd.Series([0]*len(intersected))).fillna(0)
        f_75p = intersected['P22_F75P'].fillna(0)
        f_85p = f_75p * ratio_80p
        f_6574 = (f_65p - f_75p).clip(lower=0)
        
        result['pop_femmes_65_74'] = (f_6574 * intersected['surface_ratio']).sum()
        result['pop_femmes_75_84'] = ((f_75p - f_85p).clip(lower=0) * intersected['surface_ratio']).sum()
        result['pop_femmes_85_plus'] = (f_85p * intersected['surface_ratio']).sum()
        result['pop_femmes_65_plus'] = (f_65p * intersected['surface_ratio']).sum()
        
        # Taux retraites (si colonnes disponibles)
        pop_55p = intersected.get('P22_POP55P', pd.Series([0]*len(intersected))).fillna(0)
        retraites_55p = intersected.get('C22_POP55P_STAT_GSEC32', pd.Series([0]*len(intersected))).fillna(0)
        if pop_55p.sum() > 0:
            taux_retraites = np.where(pop_55p > 0, retraites_55p / pop_55p, 0)
            result['taux_retraites'] = (taux_retraites * intersected['surface_ratio']).sum() / max(intersected['surface_ratio'].sum(), 1)
        else:
            result['taux_retraites'] = 0
        
        # Taux cadres (si colonnes disponibles)
        pop_15p = intersected.get('C22_POP15P', pd.Series([0]*len(intersected))).fillna(0)
        cadres = intersected.get('C22_POP15P_STAT_GSEC13_23', pd.Series([0]*len(intersected))).fillna(0)
        if pop_15p.sum() > 0:
            taux_cadres = np.where(pop_15p > 0, cadres / pop_15p, 0)
            result['taux_cadres'] = (taux_cadres * intersected['surface_ratio']).sum() / max(intersected['surface_ratio'].sum(), 1)
        else:
            result['taux_cadres'] = 0
        
        return result
    
    def _get_empty_population_dict(self):
        """Retourne un dictionnaire avec toutes les variables à zéro"""
        return {
            'pop_totale': 0,
            'pop_65_74': 0,
            'pop_75_84': 0,
            'pop_85_plus': 0,
            'pop_65_plus': 0,
            'pop_hommes_65_74': 0,
            'pop_hommes_75_84': 0,
            'pop_hommes_85_plus': 0,
            'pop_hommes_65_plus': 0,
            'pop_femmes_65_74': 0,
            'pop_femmes_75_84': 0,
            'pop_femmes_85_plus': 0,
            'pop_femmes_65_plus': 0,
            'taux_retraites': 0,
            'taux_cadres': 0,
        }
    
    def process_pharmacie(self, pharmacie_id):
        """
        Traite une pharmacie : calcule variables population pour les isochrones manquants

        Ne recalcule PAS les isochrones déjà traités (détection automatique).

        Args:
            pharmacie_id: ID de la pharmacie

        Returns:
            dict avec les variables pour cette pharmacie (uniquement nouveaux isochrones)
        """
        result = {self.config_iso['colonne_id_pharmacie']: pharmacie_id}

        # Pour chaque type d'isochrone À CALCULER (skip ceux déjà calculés)
        for type_iso in self.isochrones_a_calculer:
            # Charger l'isochrone
            isochrone_gdf = self.load_isochrone(pharmacie_id, type_iso)

            # Calculer population dans l'isochrone
            pop_vars = self.calculate_population_in_isochrone(isochrone_gdf)

            # Ajouter au résultat avec suffixe type_iso
            for var_name, var_value in pop_vars.items():
                result[f'{var_name}_{type_iso}'] = var_value

        return result
    
    def process_all_pharmacies(self):
        """
        Traite toutes les pharmacies et génère le DataFrame final

        Returns:
            DataFrame avec toutes les variables population par isochrone
        """
        logger.info("="*80)
        logger.info("CALCUL POPULATION POUR TOUS LES ISOCHRONES MANQUANTS")
        logger.info("="*80)

        if not self.isochrones_a_calculer:
            logger.info("AUCUN isochrone a calculer (tous sont deja faits)")
            logger.info("Retour du fichier existant...")
            output_file = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones']
            return pd.read_csv(output_file)

        logger.info(f"Isochrones a traiter : {self.isochrones_a_calculer}")
        logger.info(f"Nombre d'isochrones : {len(self.isochrones_a_calculer)}")

        # Estimation durée
        duree_par_iso = 15  # minutes
        duree_totale_min = len(self.isochrones_a_calculer) * duree_par_iso
        logger.info(f"Duree estimee : {duree_totale_min} min (~{duree_totale_min/60:.1f}h)")
        logger.info("")
        logger.info("PROGRESSION :")
        logger.info("  - Checkpoint automatique tous les 250 pharmacies")
        logger.info("  - Vous pouvez interrompre (Ctrl+C) et relancer")
        logger.info("="*80)
        logger.info("")

        col_id = self.config_iso['colonne_id_pharmacie']
        pharmacies_ids = self.pharmacies_df[col_id].tolist()
        
        # Checkpoint path
        checkpoint_path = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones'].parent / 'checkpoint_population.csv'
        
        results = []
        start_idx = 0
        
        # OPTIMISATION 5: Resume depuis checkpoint si existe
        if checkpoint_path.exists():
            try:
                checkpoint_df = pd.read_csv(checkpoint_path)
                results = checkpoint_df.to_dict('records')
                start_idx = len(results)
                logger.info(f"Reprise depuis checkpoint: {start_idx:,} pharmacies deja traitees")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement checkpoint: {e}")
                results = []
                start_idx = 0
        
        # Temps de départ
        import time
        start_time = time.time()

        # Traiter chaque pharmacie avec barre de progression
        for idx, pharmacie_id in enumerate(tqdm(pharmacies_ids[start_idx:],
                                                 desc=f"Calcul {len(self.isochrones_a_calculer)} isochrones",
                                                 initial=start_idx,
                                                 total=len(pharmacies_ids)), start_idx + 1):
            result = self.process_pharmacie(pharmacie_id)
            results.append(result)

            # Log visuel toutes les 100 pharmacies
            if idx % 100 == 0:
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

            # Checkpoint tous les 250 pharmacies (plus fréquent car c'est long)
            if idx % 250 == 0:
                checkpoint_df = pd.DataFrame(results)
                checkpoint_df.to_csv(checkpoint_path, index=False)
                logger.info(f"[CHECKPOINT] Sauvegarde : {idx:,} pharmacies traitees")
        
        # Supprimer checkpoint final
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        
        # Convertir en DataFrame
        population_vars_df = pd.DataFrame(results)

        logger.info("")
        logger.info("="*80)
        logger.info("FUSION DES RESULTATS")
        logger.info("="*80)

        # Charger le fichier existant s'il existe (contient walk_5min et drive_10min)
        output_file = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones']

        if output_file.exists():
            logger.info(f"Chargement fichier existant : {output_file.name}")
            existing_df = pd.read_csv(output_file)
            logger.info(f"  -> {len(existing_df):,} pharmacies, {len(existing_df.columns)} colonnes")

            # Fusionner avec les nouveaux résultats
            logger.info(f"Ajout des nouveaux isochrones : {self.isochrones_a_calculer}")
            pharmacies_avec_population = existing_df.merge(
                population_vars_df,
                on=col_id,
                how='left'
            )
            logger.info(f"  -> Fichier final : {len(pharmacies_avec_population.columns)} colonnes")
        else:
            # Pas de fichier existant : joindre avec pharmacies original
            logger.info("Aucun fichier existant, creation depuis pharmacies")
            pharmacies_avec_population = self.pharmacies_df.merge(
                population_vars_df,
                on=col_id,
                how='left'
            )

        logger.info(f"Traitement termine : {len(pharmacies_avec_population):,} pharmacies")
        logger.info(f"  -> {len(population_vars_df.columns) - 1} nouvelles variables creees")
        logger.info("="*80)

        return pharmacies_avec_population
    
    def generate_report(self, output_df):
        """
        Génère un rapport sur les données population
        
        Args:
            output_df: DataFrame final avec variables population
        """
        logger.info("Génération du rapport de population...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT D'ANALYSE POPULATION PAR ISOCHRONE")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Configuration
        report_lines.append("CONFIGURATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Nombre de pharmacies analysées : {len(output_df):,}")
        report_lines.append(f"Nombre d'IRIS utilisés : {len(self.iris_data_geo):,}")
        report_lines.append("")
        
        # Statistiques par isochrone
        report_lines.append("STATISTIQUES PAR ISOCHRONE")
        report_lines.append("-" * 80)
        
        for type_iso in self.config_iso['types_isochrones']:
            report_lines.append(f"\n{type_iso.upper()}:")
            
            # Population totale
            col_pop_tot = f'pop_totale_{type_iso}'
            if col_pop_tot in output_df.columns:
                report_lines.append(f"  Population totale moyenne : {output_df[col_pop_tot].mean():.0f}")
                report_lines.append(f"  Population totale médiane : {output_df[col_pop_tot].median():.0f}")
            
            # Population 65+
            col_pop_65 = f'pop_65_plus_{type_iso}'
            if col_pop_65 in output_df.columns:
                report_lines.append(f"  Population 65+ moyenne : {output_df[col_pop_65].mean():.0f}")
                report_lines.append(f"  Population 65+ médiane : {output_df[col_pop_65].median():.0f}")
                
                # Taux seniors moyen
                if col_pop_tot in output_df.columns:
                    taux_seniors = (output_df[col_pop_65] / output_df[col_pop_tot].replace(0, np.nan)).mean()
                    report_lines.append(f"  Taux seniors moyen : {taux_seniors * 100:.1f}%")
            
            # Par tranche
            for tranche in ['65_74', '75_84', '85_plus']:
                col = f'pop_{tranche}_{type_iso}'
                if col in output_df.columns:
                    report_lines.append(f"  Population {tranche} moyenne : {output_df[col].mean():.0f}")
        
        report_lines.append("")
        
        # Distribution population 65+
        report_lines.append("DISTRIBUTION POPULATION 65+ (drive_10min)")
        report_lines.append("-" * 80)
        
        col_pop_65_drive = 'pop_65_plus_drive_10min'
        if col_pop_65_drive in output_df.columns:
            pop_65 = output_df[col_pop_65_drive]
            report_lines.append(f"  - < 500 : {(pop_65 < 500).sum():,} pharmacies ({(pop_65 < 500).sum() / len(output_df) * 100:.1f}%)")
            report_lines.append(f"  - 500-1000 : {((pop_65 >= 500) & (pop_65 < 1000)).sum():,} pharmacies")
            report_lines.append(f"  - 1000-2000 : {((pop_65 >= 1000) & (pop_65 < 2000)).sum():,} pharmacies")
            report_lines.append(f"  - 2000-5000 : {((pop_65 >= 2000) & (pop_65 < 5000)).sum():,} pharmacies")
            report_lines.append(f"  - 5000+ : {(pop_65 >= 5000).sum():,} pharmacies")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Écrire le rapport
        report_path = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones'].parent / 'rapport_population.txt'
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
        output_path = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones']
        logger.info(f"Sauvegarde des résultats dans {output_path}")

        # Sauvegarde principale
        output_df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"✓ Fichier sauvegardé : {len(output_df):,} lignes × {len(output_df.columns)} colonnes")

        # Backup horodaté (pour sécurité)
        backup_dir = output_path.parent / "backups_population"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"pharmacies_population_{timestamp}.csv"
        output_df.to_csv(backup_path, index=False, encoding='utf-8')
        logger.info(f"✓ Backup horodaté : {backup_path.name}")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DU SCRIPT 3 : CALCUL POPULATION PAR ISOCHRONE")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Isochrones à traiter : {self.config_iso['types_isochrones']}")
        logger.info(f"Nombre total d'isochrones : {len(self.config_iso['types_isochrones'])}")
        logger.info("")
        logger.info("IMPORTANT :")
        logger.info("  - Durée estimée : 15-20 min par isochrone")
        logger.info("  - Checkpoints automatiques tous les 250 pharmacies")
        logger.info("  - Backup horodaté à la fin")
        logger.info("  - Vous pouvez interrompre (Ctrl+C) et relancer")
        logger.info("  - Le script reprendra automatiquement là où il s'est arrêté")
        logger.info("=" * 80)
        logger.info("")

        start_time = datetime.now()
        
        try:
            # 1. Charger les données
            self.load_data()
            
            # 2. Traiter toutes les pharmacies
            output_df = self.process_all_pharmacies()
            
            # 3. Générer le rapport
            self.generate_report(output_df)
            
            # 4. Sauvegarder
            self.save_results(output_df)
            
            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("=" * 80)
            logger.info(f"SCRIPT 3 TERMINÉ AVEC SUCCÈS")
            logger.info(f"Durée d'exécution : {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    processor = PopulationProcessor()
    processor.run()


if __name__ == "__main__":
    main()
