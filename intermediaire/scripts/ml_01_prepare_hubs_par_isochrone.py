"""
Script 1 : Préparation des variables HUBS par isochrone avec déduplication spatiale

Ce script calcule le nombre de hubs par catégorie et par isochrone pour chaque pharmacie,
en appliquant une déduplication spatiale pour éviter de sur-compter les hubs colocalisés
(ex: médecins dans un hôpital, cabinets partagés).

FONCTIONNALITES :
    - Détection automatique des isochrones déjà calculés (évite les doublons)
    - Calcul uniquement des isochrones manquants
    - Checkpoints automatiques tous les 250 pharmacies pour reprise en cas d'interruption
    - Logs de progression toutes les 100 pharmacies avec ETA
    - Fusion automatique avec le fichier existant
    - Backup horodaté à la fin du traitement

Inputs:
    - HUBS_unified_final.csv : Fichier des hubs avec colonnes:
        * hub_id
        * hub_type_detail : Type de hub (medecin, hopital, ehpad, etc.)
        * latitude, longitude
        * autres colonnes...
    - pharmacies.csv : Fichier des pharmacies avec id_pharmacie
    - isochrones/walk_5min/*.geojson : Polygones isochrones 5min à pied
    - isochrones/walk_10min/*.geojson : Polygones isochrones 10min à pied
    - isochrones/drive_5min/*.geojson : Polygones isochrones 5min en voiture
    - isochrones/drive_10min/*.geojson : Polygones isochrones 10min en voiture
    - isochrones/drive_15min/*.geojson : Polygones isochrones 15min en voiture
    - isochrones/drive_20min/*.geojson : Polygones isochrones 20min en voiture

Outputs:
    - pharmacies_avec_hubs.csv : Variables hubs agrégées par pharmacie
        Nouvelles colonnes créées par isochrone:
        * nb_sante_generale_{isochrone}
        * nb_sante_specialisee_{isochrone}
        * nb_services_seniors_{isochrone}
        * nb_accessibilite_{isochrone}
        * nb_medecins_equivalent_{isochrone} (si détails activés)
        * nb_ehpad_{isochrone}
        * nb_hopitaux_{isochrone}
        * nb_laboratoires_{isochrone}
        * nb_supermarches_{isochrone}
        * nb_bus_{isochrone}
        * taux_colocalisation_{isochrone}
        * ... et autres selon configuration

        (avec {isochrone} = walk_5min, walk_10min, drive_5min, drive_10min, drive_15min, drive_20min)

    - checkpoint_hubs.csv : Sauvegarde intermédiaire (tous les 250 pharmacies)
    - backups_hubs/pharmacies_hubs_{timestamp}.csv : Backup horodaté final
    - rapport_deduplication_hubs.txt : Rapport détaillé de la déduplication

Durée estimée:
    - ~60-80 minutes pour les 6 isochrones (19,307 pharmacies)
    - ~40-50 minutes pour 4 isochrones si walk_5min et drive_10min déjà calculés
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
from shapely.geometry import Point, shape
from sklearn.cluster import DBSCAN
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
    HUBS_DEDUPLICATION_CONFIG,
    HUBS_AGREGATIONS_CONFIG,
    ISOCHRONES_CONFIG,
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


class HubsProcessor:
    """
    Classe pour traiter les hubs par isochrone avec déduplication spatiale
    """
    
    def __init__(self):
        """Initialisation du processeur"""
        self.hubs_df = None
        self.hubs_gdf = None  # GeoDataFrame pour optimisation
        self.pharmacies_df = None
        self.config_dedup = HUBS_DEDUPLICATION_CONFIG
        self.config_agreg = HUBS_AGREGATIONS_CONFIG
        self.config_iso = ISOCHRONES_CONFIG
        self.isochrones_a_calculer = []  # Sera rempli après détection automatique

        # Statistiques de déduplication (pour rapport)
        self.stats_dedup = {
            'total_hubs_brut': 0,
            'total_hubs_dedupliques': 0,
            'total_clusters': 0,
            'clusters_multiples': 0,
            'taux_colocalisation_global': 0
        }

        # Configuration sauvegardes intermédiaires
        self.checkpoint_interval = 250  # Sauvegarder tous les 250 pharmacies
        self.checkpoint_file = INTERMEDIATE_FILES['pharmacies_avec_hubs'].parent / 'checkpoint_hubs.csv'

        # Compteurs pour statistiques de performance
        self.stats_perf = {
            'isochrones_charges': 0,
            'isochrones_manquants': 0,
            'pharmacies_traitees': 0
        }

        logger.info("Initialisation du processeur de hubs")
    
    def load_data(self):
        """Charge les données hubs et pharmacies"""
        logger.info("Chargement des données...")
        
        # Charger les hubs
        hubs_path = INPUT_FILES['hubs']
        logger.info(f"Chargement des hubs depuis {hubs_path}")
        self.hubs_df = pd.read_csv(hubs_path)
        logger.info(f"  → {len(self.hubs_df):,} hubs chargés")
        
        # Vérifier les colonnes nécessaires
        col_type = self.config_dedup['colonne_type']
        col_lat = self.config_dedup['colonne_latitude']
        col_lon = self.config_dedup['colonne_longitude']
        
        required_cols = [col_type, col_lat, col_lon]
        missing_cols = [col for col in required_cols if col not in self.hubs_df.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes dans le fichier hubs: {missing_cols}")
        
        # Nettoyer les coordonnées manquantes
        before_clean = len(self.hubs_df)
        self.hubs_df = self.hubs_df.dropna(subset=[col_lat, col_lon])
        after_clean = len(self.hubs_df)
        if before_clean > after_clean:
            logger.warning(f"  → {before_clean - after_clean:,} hubs supprimés (coordonnées manquantes)")
        
        # Créer un GeoDataFrame pour optimisation (calcul spatial plus rapide)
        logger.info("Création du GeoDataFrame pour optimisation spatiale...")
        geometry = [Point(xy) for xy in zip(self.hubs_df[col_lon], self.hubs_df[col_lat])]
        self.hubs_gdf = gpd.GeoDataFrame(self.hubs_df, geometry=geometry, crs='EPSG:4326')
        logger.info("  → GeoDataFrame créé")
        
        # Charger les pharmacies
        pharmacies_path = INPUT_FILES['pharmacies']
        logger.info(f"Chargement des pharmacies depuis {pharmacies_path}")
        self.pharmacies_df = pd.read_csv(pharmacies_path, sep=';')
        logger.info(f"  → {len(self.pharmacies_df):,} pharmacies chargées")
        
        # Vérifier colonne ID
        col_id = self.config_iso['colonne_id_pharmacie']
        if col_id not in self.pharmacies_df.columns:
            raise ValueError(f"Colonne '{col_id}' manquante dans le fichier pharmacies")
        
        logger.info("Données chargées avec succès")

    def _detect_isochrones_a_calculer(self):
        """Détecte automatiquement quels isochrones ont déjà été calculés"""
        logger.info("="*80)
        logger.info("DETECTION AUTOMATIQUE DES ISOCHRONES DEJA CALCULES")
        logger.info("="*80)

        output_file = INTERMEDIATE_FILES['pharmacies_avec_hubs']
        isochrones_deja_calcules = []

        if output_file.exists():
            logger.info(f"Fichier de sortie existant trouve : {output_file.name}")
            existing_df = pd.read_csv(output_file, nrows=0)
            existing_cols = set(existing_df.columns)

            # Pour chaque isochrone, vérifier si au moins une variable de cette famille existe
            # On vérifie la présence de colonnes clés comme nb_hubs_brut_{isochrone}
            for iso_type in self.config_iso['types_isochrones']:
                col_test = f'nb_hubs_brut_{iso_type}'
                if col_test in existing_cols:
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

    def load_isochrone(self, pharmacie_id, type_isochrone):
        """
        Charge un fichier isochrone GeoJSON (VERSION OPTIMISÉE)
        
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
                self.stats_perf['isochrones_charges'] += 1
                return geometry
            elif 'geometry' in geojson_data:
                geometry = shape(geojson_data['geometry'])
                self.stats_perf['isochrones_charges'] += 1
                return geometry
            else:
                logger.warning(f"Format GeoJSON invalide pour {filename}")
                self.stats_perf['isochrones_manquants'] += 1
                return None
        
        except FileNotFoundError:
            self.stats_perf['isochrones_manquants'] += 1
            return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement de {filename}: {e}")
            self.stats_perf['isochrones_manquants'] += 1
            return None
    
    def filter_hubs_in_isochrone(self, isochrone_polygon):
        """
        Filtre les hubs qui se trouvent dans un polygone isochrone (VERSION OPTIMISÉE)
        
        Args:
            isochrone_polygon: Polygone shapely de l'isochrone
        
        Returns:
            DataFrame des hubs dans l'isochrone
        """
        # Utiliser GeoDataFrame pour filtrage spatial optimisé (beaucoup plus rapide)
        mask = self.hubs_gdf.geometry.within(isochrone_polygon)
        hubs_in_iso = self.hubs_df[mask].copy()
        
        return hubs_in_iso
    
    def deduplicate_hubs(self, hubs_df):
        """
        Déduplique les hubs colocalisés avec clustering spatial
        
        Args:
            hubs_df: DataFrame des hubs à dédupliquer
        
        Returns:
            DataFrame avec colonnes ajoutées:
                - cluster_id: ID du cluster spatial
                - hub_dominant: Type du hub dominant dans le cluster
                - score_pondere: Score après pondération colocalisation
        """
        if len(hubs_df) == 0:
            return hubs_df
        
        # Ne pas dédupliquer si désactivé
        if not self.config_dedup['activer']:
            hubs_df['cluster_id'] = range(len(hubs_df))
            hubs_df['hub_dominant'] = hubs_df[self.config_dedup['colonne_type']]
            hubs_df['score_pondere'] = 1.0
            return hubs_df
        
        col_lat = self.config_dedup['colonne_latitude']
        col_lon = self.config_dedup['colonne_longitude']
        col_type = self.config_dedup['colonne_type']
        
        # Convertir epsilon (mètres) en degrés approximativement
        # 1 degré ≈ 111 km à l'équateur
        epsilon_metres = self.config_dedup['epsilon_metres']
        epsilon_degrees = epsilon_metres / (111 * 1000)
        
        # Clustering DBSCAN
        coords = hubs_df[[col_lat, col_lon]].values
        clustering = DBSCAN(eps=epsilon_degrees, min_samples=1, metric='euclidean')
        hubs_df['cluster_id'] = clustering.fit_predict(coords)
        
        # Pour chaque cluster, identifier le hub dominant et pondérer
        hierarchie = self.config_dedup['hierarchie']
        ponderations = self.config_dedup['ponderations_colocalisation']
        
        def process_cluster(cluster_df):
            """Traite un cluster pour identifier dominant et pondérer"""
            # Créer une copie pour éviter les problèmes avec pandas groupby
            cluster_df = cluster_df.copy()
            
            if len(cluster_df) == 1:
                # Hub standalone
                hub_type = cluster_df.iloc[0][col_type]
                cluster_df['hub_dominant'] = hub_type
                cluster_df['score_pondere'] = ponderations.get(
                    f'{hub_type}_standalone',
                    ponderations['default_standalone']
                )
                return cluster_df
            
            # Cluster avec plusieurs hubs
            # Identifier le hub dominant (priorité max dans hiérarchie)
            cluster_df['priorite'] = cluster_df[col_type].map(
                lambda x: hierarchie.get(x, 0)
            )
            hub_dominant_type = cluster_df.loc[cluster_df['priorite'].idxmax(), col_type]
            cluster_df['hub_dominant'] = hub_dominant_type
            
            # Pondérer chaque hub selon sa colocalisation
            def get_ponderation(row):
                hub_type = row[col_type]
                
                # Si c'est le hub dominant, pleine valeur
                if hub_type == hub_dominant_type:
                    return ponderations.get(
                        f'{hub_type}_standalone',
                        ponderations['default_standalone']
                    )
                
                # Sinon, pondération selon colocalisation
                key_specific = f'{hub_type}_avec_{hub_dominant_type}'
                key_generic = f'{hub_type}_avec_*'
                
                if key_specific in ponderations:
                    return ponderations[key_specific]
                elif key_generic in ponderations:
                    return ponderations[key_generic]
                else:
                    return ponderations['default_colocalise']
            
            cluster_df['score_pondere'] = cluster_df.apply(get_ponderation, axis=1)
            cluster_df.drop('priorite', axis=1, inplace=True)
            
            return cluster_df
        
        # Appliquer le traitement par cluster
        hubs_df = hubs_df.groupby('cluster_id', group_keys=False).apply(process_cluster)
        
        return hubs_df
    
    def aggregate_hubs(self, hubs_dedupliques):
        """
        Agrège les hubs dédupliqués en variables pour le ML
        
        Args:
            hubs_dedupliques: DataFrame des hubs après déduplication
        
        Returns:
            dict avec les variables agrégées
        """
        col_type = self.config_dedup['colonne_type']
        familles = self.config_agreg['familles']
        categories_detail = self.config_agreg['categories_detaillees']
        inclure_details = self.config_agreg['inclure_details']
        
        result = {}
        
        # Compter nombre de hubs bruts (avant déduplication)
        result['nb_hubs_brut'] = len(hubs_dedupliques)
        
        # Si aucun hub, retourner des zéros
        if len(hubs_dedupliques) == 0 or 'score_pondere' not in hubs_dedupliques.columns:
            result['nb_hubs_deduplique'] = 0
            result['taux_colocalisation'] = 0
            for famille_nom in familles.keys():
                result[f'nb_{famille_nom}'] = 0
            if inclure_details:
                for categorie in categories_detail:
                    result[f'nb_{categorie}'] = 0
            return result
        
        # Compter score dédupliqué total
        result['nb_hubs_deduplique'] = hubs_dedupliques['score_pondere'].sum()
        
        # Taux de colocalisation
        if result['nb_hubs_brut'] > 0:
            result['taux_colocalisation'] = 1 - (result['nb_hubs_deduplique'] / result['nb_hubs_brut'])
        else:
            result['taux_colocalisation'] = 0
        
        # Agrégation par familles
        for famille_nom, categories in familles.items():
            mask = hubs_dedupliques[col_type].isin(categories)
            score = hubs_dedupliques.loc[mask, 'score_pondere'].sum()
            result[f'nb_{famille_nom}'] = score
        
        # Agrégation par catégories détaillées
        if inclure_details:
            for categorie in categories_detail:
                mask = hubs_dedupliques[col_type] == categorie
                score = hubs_dedupliques.loc[mask, 'score_pondere'].sum()
                result[f'nb_{categorie}'] = score
        
        return result
    
    def process_pharmacie(self, pharmacie_id):
        """
        Traite une pharmacie : calcule variables hubs pour ses isochrones À CALCULER

        Args:
            pharmacie_id: ID de la pharmacie

        Returns:
            dict avec les variables pour cette pharmacie
        """
        self.stats_perf['pharmacies_traitees'] += 1
        result = {self.config_iso['colonne_id_pharmacie']: pharmacie_id}

        # Pour chaque type d'isochrone À CALCULER (skip ceux déjà calculés)
        for type_iso in self.isochrones_a_calculer:
            # Charger l'isochrone
            isochrone = self.load_isochrone(pharmacie_id, type_iso)
            
            if isochrone is None:
                # Remplir avec des zéros si isochrone manquant
                logger.debug(f"Isochrone manquant pour pharmacie {pharmacie_id} ({type_iso})")
                result[f'nb_hubs_brut_{type_iso}'] = 0
                result[f'nb_hubs_deduplique_{type_iso}'] = 0
                result[f'taux_colocalisation_{type_iso}'] = 0
                
                # Familles
                for famille in self.config_agreg['familles'].keys():
                    result[f'nb_{famille}_{type_iso}'] = 0
                
                # Détails
                if self.config_agreg['inclure_details']:
                    for categorie in self.config_agreg['categories_detaillees']:
                        result[f'nb_{categorie}_{type_iso}'] = 0
                
                continue
            
            # Filtrer les hubs dans l'isochrone
            hubs_in_iso = self.filter_hubs_in_isochrone(isochrone)
            
            # Dédupliquer
            hubs_dedup = self.deduplicate_hubs(hubs_in_iso)
            
            # Agréger
            agg_vars = self.aggregate_hubs(hubs_dedup)
            
            # Ajouter au résultat avec suffixe type_iso
            for var_name, var_value in agg_vars.items():
                if var_name != self.config_iso['colonne_id_pharmacie']:
                    result[f'{var_name}_{type_iso}'] = var_value
            
            # Mettre à jour les stats globales
            self.stats_dedup['total_hubs_brut'] += agg_vars['nb_hubs_brut']
            self.stats_dedup['total_hubs_dedupliques'] += agg_vars['nb_hubs_deduplique']
        
        return result
    
    def load_checkpoint(self):
        """
        Charge un checkpoint existant pour reprendre le traitement
        
        Returns:
            tuple (results_list, processed_ids_set) ou ([], set()) si pas de checkpoint
        """
        if not self.checkpoint_file.exists():
            logger.info("Aucun checkpoint trouvé, démarrage depuis le début")
            return [], set()
        
        logger.info(f"Checkpoint trouvé : {self.checkpoint_file}")
        try:
            checkpoint_df = pd.read_csv(self.checkpoint_file)
            col_id = self.config_iso['colonne_id_pharmacie']
            
            if col_id not in checkpoint_df.columns:
                logger.warning("Checkpoint invalide, démarrage depuis le début")
                return [], set()
            
            processed_ids = set(checkpoint_df[col_id].tolist())
            results = checkpoint_df.to_dict('records')
            
            logger.info(f"  → {len(results):,} pharmacies déjà traitées, reprise du traitement")
            return results, processed_ids
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement du checkpoint : {e}")
            logger.warning("Démarrage depuis le début")
            return [], set()
    
    def save_checkpoint(self, results):
        """
        Sauvegarde un checkpoint intermédiaire
        
        Args:
            results: Liste des résultats actuels
        """
        try:
            checkpoint_df = pd.DataFrame(results)
            checkpoint_df.to_csv(self.checkpoint_file, index=False, encoding='utf-8')
            logger.info(f"  💾 Checkpoint sauvegardé : {len(results):,} pharmacies")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du checkpoint : {e}")
    
    def process_all_pharmacies(self):
        """
        Traite toutes les pharmacies et génère le DataFrame final
        AVEC SAUVEGARDES INTERMÉDIAIRES, REPRISE ET FUSION

        Returns:
            DataFrame avec toutes les variables hubs par pharmacie
        """
        logger.info("="*80)
        logger.info("CALCUL HUBS POUR TOUS LES ISOCHRONES MANQUANTS")
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
        checkpoint_path = INTERMEDIATE_FILES['pharmacies_avec_hubs'].parent / 'checkpoint_hubs.csv'

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
        hubs_vars_df = pd.DataFrame(results)

        # FUSION avec le fichier existant si des isochrones étaient déjà calculés
        output_file = INTERMEDIATE_FILES['pharmacies_avec_hubs']
        if output_file.exists():
            logger.info("")
            logger.info("="*80)
            logger.info("FUSION AVEC FICHIER EXISTANT")
            logger.info("="*80)

            existing_df = pd.read_csv(output_file)
            logger.info(f"Fichier existant : {len(existing_df):,} lignes x {len(existing_df.columns)} colonnes")
            logger.info(f"Nouvelles donnees : {len(hubs_vars_df):,} lignes x {len(hubs_vars_df.columns)} colonnes")

            # Fusionner : les nouvelles colonnes écrasent les anciennes (si doublons)
            # On merge sur id_pharmacie, en gardant toutes les lignes (how='outer')
            merged_df = existing_df.merge(
                hubs_vars_df,
                on=col_id,
                how='outer',
                suffixes=('_old', '')
            )

            # Supprimer les colonnes _old (garder seulement les nouvelles valeurs)
            cols_to_drop = [c for c in merged_df.columns if c.endswith('_old')]
            if cols_to_drop:
                merged_df.drop(columns=cols_to_drop, inplace=True)
                logger.info(f"  -> {len(cols_to_drop)} anciennes colonnes remplacees")

            hubs_vars_df = merged_df
            logger.info(f"Resultat fusion : {len(hubs_vars_df):,} lignes x {len(hubs_vars_df.columns)} colonnes")
            logger.info("="*80)
        else:
            logger.info("Pas de fichier existant, creation d'un nouveau fichier")

        logger.info("")
        logger.info(f"Traitement termine : {len(hubs_vars_df):,} pharmacies")
        logger.info(f"  -> {len(hubs_vars_df.columns)} variables totales")

        # Supprimer le checkpoint après succès
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("  -> Checkpoint supprime apres succes")

        return hubs_vars_df
    
    def generate_report(self, output_df):
        """
        Génère un rapport de déduplication
        
        Args:
            output_df: DataFrame final avec variables hubs
        """
        logger.info("Génération du rapport de déduplication...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT DE DÉDUPLICATION DES HUBS")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Configuration utilisée
        report_lines.append("CONFIGURATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Déduplication activée : {self.config_dedup['activer']}")
        report_lines.append(f"Distance de clustering : {self.config_dedup['epsilon_metres']} mètres")
        report_lines.append(f"Nombre de pharmacies traitées : {len(output_df):,}")
        report_lines.append("")
        
        # Statistiques globales
        report_lines.append("STATISTIQUES GLOBALES")
        report_lines.append("-" * 80)
        report_lines.append(f"Total hubs avant déduplication : {self.stats_dedup['total_hubs_brut']:,.0f}")
        report_lines.append(f"Total hubs après déduplication : {self.stats_dedup['total_hubs_dedupliques']:,.1f}")
        
        if self.stats_dedup['total_hubs_brut'] > 0:
            reduction = (1 - self.stats_dedup['total_hubs_dedupliques'] / self.stats_dedup['total_hubs_brut']) * 100
            report_lines.append(f"Réduction due à colocalisation : {reduction:.1f}%")
        
        report_lines.append("")
        
        # Statistiques par isochrone
        report_lines.append("STATISTIQUES PAR ISOCHRONE")
        report_lines.append("-" * 80)
        
        for type_iso in self.config_iso['types_isochrones']:
            col_brut = f'nb_hubs_brut_{type_iso}'
            col_dedup = f'nb_hubs_deduplique_{type_iso}'
            col_taux = f'taux_colocalisation_{type_iso}'
            
            if col_brut in output_df.columns:
                total_brut = output_df[col_brut].sum()
                total_dedup = output_df[col_dedup].sum()
                taux_moyen = output_df[col_taux].mean() * 100
                
                report_lines.append(f"\n{type_iso.upper()}:")
                report_lines.append(f"  Total hubs brut : {total_brut:,.0f}")
                report_lines.append(f"  Total hubs dédupliqué : {total_dedup:,.1f}")
                report_lines.append(f"  Taux colocalisation moyen : {taux_moyen:.1f}%")
        
        report_lines.append("")
        
        # Statistiques par famille
        report_lines.append("STATISTIQUES PAR FAMILLE DE HUBS")
        report_lines.append("-" * 80)
        
        for famille in self.config_agreg['familles'].keys():
            report_lines.append(f"\nFamille '{famille}':")
            
            for type_iso in self.config_iso['types_isochrones']:
                col = f'nb_{famille}_{type_iso}'
                if col in output_df.columns:
                    total = output_df[col].sum()
                    moyenne = output_df[col].mean()
                    report_lines.append(f"  {type_iso} - Total: {total:,.1f} | Moyenne/pharma: {moyenne:.2f}")
        
        report_lines.append("")
        
        # Statistiques catégories détaillées
        if self.config_agreg['inclure_details']:
            report_lines.append("STATISTIQUES CATÉGORIES DÉTAILLÉES")
            report_lines.append("-" * 80)
            
            for categorie in self.config_agreg['categories_detaillees']:
                report_lines.append(f"\nCatégorie '{categorie}':")
                
                for type_iso in self.config_iso['types_isochrones']:
                    col = f'nb_{categorie}_{type_iso}'
                    if col in output_df.columns:
                        total = output_df[col].sum()
                        moyenne = output_df[col].mean()
                        report_lines.append(f"  {type_iso} - Total: {total:,.1f} | Moyenne/pharma: {moyenne:.2f}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Écrire le rapport
        report_path = INTERMEDIATE_FILES['pharmacies_avec_hubs'].parent / 'rapport_deduplication_hubs.txt'
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
        output_path = INTERMEDIATE_FILES['pharmacies_avec_hubs']
        logger.info("")
        logger.info("="*80)
        logger.info("SAUVEGARDE DES RESULTATS")
        logger.info("="*80)
        logger.info(f"Fichier principal : {output_path.name}")

        # Sauvegarder le fichier principal
        output_df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"  -> {len(output_df):,} lignes x {len(output_df.columns)} colonnes")

        # Créer backup horodaté
        backup_dir = output_path.parent / "backups_hubs"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"pharmacies_hubs_{timestamp}.csv"
        output_df.to_csv(backup_path, index=False, encoding='utf-8')
        logger.info(f"Backup horodate : {backup_path.name}")
        logger.info("="*80)

        # Afficher statistiques de performance
        logger.info("")
        logger.info("STATISTIQUES DE PERFORMANCE")
        logger.info("-" * 80)
        logger.info(f"  Pharmacies traitees : {self.stats_perf['pharmacies_traitees']:,}")
        logger.info(f"  Isochrones charges : {self.stats_perf['isochrones_charges']:,}")
        logger.info(f"  Isochrones manquants : {self.stats_perf['isochrones_manquants']:,}")
        if self.stats_perf['isochrones_charges'] + self.stats_perf['isochrones_manquants'] > 0:
            taux_succes = self.stats_perf['isochrones_charges'] / (self.stats_perf['isochrones_charges'] + self.stats_perf['isochrones_manquants']) * 100
            logger.info(f"  Taux de succes : {taux_succes:.1f}%")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DEMARRAGE DU SCRIPT 1 : PREPARATION HUBS PAR ISOCHRONE")
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
            logger.info(f"SCRIPT 1 TERMINE AVEC SUCCES")
            logger.info(f"Duree d'execution : {duration}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    processor = HubsProcessor()
    processor.run()


if __name__ == "__main__":
    main()
