"""
Script 4 : INTÉGRATION COMPLÈTE de toutes les variables

Ce script fusionne tous les fichiers créés par les scripts 1-2-3 pour créer
un fichier master avec TOUTES les variables (hubs, concurrence, population, tourisme).

Inputs:
    - pharmacies_avec_hubs.csv (Script 1)
    - pharmacies_avec_concurrence.csv (Script 2)
    - pharmacies_avec_population_isochrones.csv (Script 3)
    - pharmacies_final_avec_variables_touristiques.csv (existant)

Outputs:
    - pharmacies_features_complet.csv : Fichier master avec TOUTES les variables
        (~100 variables totales)

Durée estimée: 2-3 minutes

Auteur: Pipeline ML Pharmacies
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
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


class IntegrationProcessor:
    """
    Classe pour intégrer toutes les variables en un fichier master
    """
    
    def __init__(self):
        """Initialisation du processeur"""
        self.df_master = None
        self.col_id = ISOCHRONES_CONFIG['colonne_id_pharmacie']
        
        logger.info("Initialisation du processeur d'intégration")
    
    def load_and_merge_all(self):
        """Charge et fusionne tous les fichiers"""
        logger.info("Chargement et fusion de tous les fichiers...")
        
        # 1. Fichier de base : pharmacies_final
        base_path = INPUT_FILES['pharmacies']
        logger.info(f"1. Chargement fichier de base : {base_path}")
        self.df_master = pd.read_csv(base_path, sep=';')
        logger.info(f"   -> {len(self.df_master):,} lignes x {len(self.df_master.columns)} colonnes")
        
        # Liste des fichiers à fusionner
        files_to_merge = [
            ('hubs', INTERMEDIATE_FILES['pharmacies_avec_hubs'], 'Variables hubs'),
            ('concurrence', INTERMEDIATE_FILES['pharmacies_avec_concurrence'], 'Variables concurrence'),
            ('population', INTERMEDIATE_FILES['pharmacies_avec_population_isochrones'], 'Variables population'),
            ('tourisme', INPUT_FILES.get('variables_touristiques'), 'Variables touristiques'),
        ]
        
        # Fusionner chaque fichier
        merge_count = 2
        for file_key, file_path, description in files_to_merge:
            if file_path is None:
                logger.warning(f"   Fichier {description} non configuré, ignoré")
                continue
            
            if not file_path.exists():
                logger.warning(f"   Fichier {description} introuvable : {file_path}")
                continue
            
            logger.info(f"{merge_count}. Fusion : {description}")
            logger.info(f"   Chemin : {file_path}")
            
            try:
                df_new = pd.read_csv(file_path)
                logger.info(f"   -> {len(df_new):,} lignes x {len(df_new.columns)} colonnes")
                
                # Identifier les nouvelles colonnes (exclure id et colonnes déjà présentes)
                common_cols = set(self.df_master.columns) & set(df_new.columns)
                new_cols = [col for col in df_new.columns if col not in common_cols or col == self.col_id]
                
                logger.info(f"   -> {len(new_cols) - 1} nouvelles colonnes à ajouter")
                
                # Fusionner sur la colonne ID
                self.df_master = self.df_master.merge(
                    df_new[new_cols],
                    on=self.col_id,
                    how='left',
                    suffixes=('', f'_{file_key}')
                )
                
                logger.info(f"   -> Après fusion : {len(self.df_master.columns)} colonnes totales")
                merge_count += 1
                
            except Exception as e:
                logger.error(f"   X Erreur lors de la fusion : {e}")
                continue
        
        logger.info(f"Fusion terminée : {len(self.df_master):,} lignes x {len(self.df_master.columns)} colonnes")
    
    def create_derived_features(self):
        """Crée des features dérivées utiles pour le ML"""
        logger.info("Création de features dérivées...")
        
        # Ratios population par isochrone
        if 'pop_65_plus_walk_5min' in self.df_master.columns and 'pop_totale_walk_5min' in self.df_master.columns:
            self.df_master['ratio_seniors_walk_5min'] = (
                self.df_master['pop_65_plus_walk_5min'] / 
                self.df_master['pop_totale_walk_5min'].replace(0, np.nan)
            ).fillna(0)
            logger.info("   OK ratio_seniors_walk_5min")
        
        if 'pop_65_plus_drive_10min' in self.df_master.columns and 'pop_totale_drive_10min' in self.df_master.columns:
            self.df_master['ratio_seniors_drive_10min'] = (
                self.df_master['pop_65_plus_drive_10min'] / 
                self.df_master['pop_totale_drive_10min'].replace(0, np.nan)
            ).fillna(0)
            logger.info("   OK ratio_seniors_drive_10min")
        
        # Ratio femmes/hommes 65+
        if 'pop_femmes_65_plus_walk_5min' in self.df_master.columns and 'pop_hommes_65_plus_walk_5min' in self.df_master.columns:
            self.df_master['ratio_femmes_hommes_65_walk_5min'] = (
                self.df_master['pop_femmes_65_plus_walk_5min'] / 
                self.df_master['pop_hommes_65_plus_walk_5min'].replace(0, np.nan)
            ).fillna(1.0)
            logger.info("   OK ratio_femmes_hommes_65_walk_5min")
        
        # Densité hubs par 1000 habitants 65+
        if 'nb_sante_generale_walk_5min' in self.df_master.columns and 'pop_65_plus_walk_5min' in self.df_master.columns:
            self.df_master['densite_hubs_sante_par_1000_seniors_walk'] = (
                self.df_master['nb_sante_generale_walk_5min'] * 1000 / 
                self.df_master['pop_65_plus_walk_5min'].replace(0, np.nan)
            ).fillna(0)
            logger.info("   OK densite_hubs_sante_par_1000_seniors_walk")
        
        # Ratio concurrence / population
        if 'nb_pharmacies_concurrentes_drive_10min' in self.df_master.columns and 'pop_65_plus_drive_10min' in self.df_master.columns:
            self.df_master['concurrence_par_1000_seniors_drive'] = (
                self.df_master['nb_pharmacies_concurrentes_drive_10min'] * 1000 / 
                self.df_master['pop_65_plus_drive_10min'].replace(0, np.nan)
            ).fillna(0)
            logger.info("   OK concurrence_par_1000_seniors_drive")
        
        # Indicateur zone isolée (peu de concurrence + loin de la plus proche)
        if 'nb_pharmacies_concurrentes_drive_10min' in self.df_master.columns and 'distance_pharmacie_plus_proche' in self.df_master.columns:
            self.df_master['zone_isolee'] = (
                (self.df_master['nb_pharmacies_concurrentes_drive_10min'] <= 2) & 
                (self.df_master['distance_pharmacie_plus_proche'] > 5.0)
            ).astype(int)
            logger.info("   OK zone_isolee")
        
        logger.info(f"Features dérivées créées : {len(self.df_master.columns)} colonnes totales")
    
    def clean_data(self):
        """Nettoyage final des données"""
        logger.info("Nettoyage des données...")
        
        # Remplacer infinis par NaN
        self.df_master.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # Remplir NaN par 0 pour les colonnes numériques (features)
        numeric_cols = self.df_master.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in [self.col_id, 'latitude', 'longitude']:
                self.df_master[col] = self.df_master[col].fillna(0)
        
        logger.info("Nettoyage terminé")
    
    def generate_report(self):
        """Génère un rapport sur le fichier intégré"""
        logger.info("Génération du rapport d'intégration...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT D'INTÉGRATION COMPLÈTE")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Statistiques générales
        report_lines.append("STATISTIQUES GÉNÉRALES")
        report_lines.append("-" * 80)
        report_lines.append(f"Nombre de pharmacies : {len(self.df_master):,}")
        report_lines.append(f"Nombre de variables totales : {len(self.df_master.columns)}")
        report_lines.append("")
        
        # Décompte par catégorie de variables
        report_lines.append("DÉCOMPTE PAR CATÉGORIE DE VARIABLES")
        report_lines.append("-" * 80)
        
        categories = {
            'Hubs': ['nb_sante', 'nb_medecin', 'nb_laboratoire', 'nb_ehpad', 'nb_commerce', 'nb_service', 'taux_colocalisation'],
            'Concurrence': ['nb_pharmacies_concurrentes', 'distance_pharmacie'],
            'Population': ['pop_', 'ratio_seniors', 'ratio_femmes', 'taux_retraites'],
            'Tourisme': ['indice_touristique', 'categorie_touristique', 'affluence'],
            'Base': ['latitude', 'longitude', 'departement', 'type_zone', 'ca_'],
        }
        
        for cat_name, keywords in categories.items():
            count = sum(1 for col in self.df_master.columns if any(kw in col for kw in keywords))
            report_lines.append(f"  {cat_name:20s} : {count:3d} variables")
        
        report_lines.append("")
        
        # Valeurs manquantes
        report_lines.append("VALEURS MANQUANTES")
        report_lines.append("-" * 80)
        
        missing_counts = self.df_master.isnull().sum()
        cols_with_missing = missing_counts[missing_counts > 0].sort_values(ascending=False)
        
        if len(cols_with_missing) > 0:
            report_lines.append(f"Nombre de colonnes avec valeurs manquantes : {len(cols_with_missing)}")
            report_lines.append("")
            report_lines.append("Top 10 colonnes avec le plus de valeurs manquantes :")
            for col, count in cols_with_missing.head(10).items():
                pct = count / len(self.df_master) * 100
                report_lines.append(f"  {col:50s} : {count:6,} ({pct:5.1f}%)")
        else:
            report_lines.append("Aucune valeur manquante OK")
        
        report_lines.append("")
        
        # Statistiques clés
        report_lines.append("STATISTIQUES CLÉS")
        report_lines.append("-" * 80)
        
        key_vars = [
            ('pop_65_plus_drive_10min', 'Population 65+ accessible (drive 10min)'),
            ('nb_sante_generale_drive_10min', 'Hubs santé générale (drive 10min)'),
            ('nb_pharmacies_concurrentes_drive_10min', 'Pharmacies concurrentes (drive 10min)'),
            ('distance_pharmacie_plus_proche', 'Distance pharmacie la plus proche (km)'),
        ]
        
        for var_name, var_label in key_vars:
            if var_name in self.df_master.columns:
                series = self.df_master[var_name]
                report_lines.append(f"\n{var_label} :")
                report_lines.append(f"  Moyenne : {series.mean():.2f}")
                report_lines.append(f"  Médiane : {series.median():.2f}")
                report_lines.append(f"  Min : {series.min():.2f}")
                report_lines.append(f"  Max : {series.max():.2f}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Écrire le rapport
        report_path = INTERMEDIATE_FILES['pharmacies_features_complet'].parent / 'rapport_integration.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Rapport sauvegardé : {report_path}")
        
        # Afficher aussi dans les logs
        logger.info("\n" + '\n'.join(report_lines))
    
    def save_results(self):
        """Sauvegarde le DataFrame final"""
        output_path = INTERMEDIATE_FILES['pharmacies_features_complet']
        logger.info(f"Sauvegarde du fichier master dans {output_path}")
        
        self.df_master.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"OK Fichier sauvegardé : {len(self.df_master):,} lignes x {len(self.df_master.columns)} colonnes")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DU SCRIPT 4 : INTÉGRATION COMPLÈTE")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 1. Charger et fusionner tous les fichiers
            self.load_and_merge_all()
            
            # 2. Créer features dérivées
            self.create_derived_features()
            
            # 3. Nettoyer les données
            self.clean_data()
            
            # 4. Générer le rapport
            self.generate_report()
            
            # 5. Sauvegarder
            self.save_results()
            
            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("=" * 80)
            logger.info(f"SCRIPT 4 TERMINÉ AVEC SUCCÈS")
            logger.info(f"Durée d'exécution : {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    processor = IntegrationProcessor()
    processor.run()


if __name__ == "__main__":
    main()
