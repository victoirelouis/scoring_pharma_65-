#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de préparation des données pharmacies pour génération d'isochrones

MISSION : Préparer le fichier pharmacies.csv avec les bonnes colonnes et types de zone
- Nettoyer et formater les données
- Ajouter la colonne type_zone
- Valider les coordonnées

Auteur: Système de scoring pharmacie 65+
Date: Octobre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_FILE = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\DATA\pharmacies_enrichies.csv")
OUTPUT_FILE = BASE_DIR / "data" / "input" / "pharmacies.csv"

def setup_logging():
    """Configure le logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def determine_zone_type(row):
    """
    Détermine le type de zone selon l'IRIS
    
    Args:
        row: Ligne du DataFrame
        
    Returns:
        str: Type de zone
    """
    type_iris = str(row.get('type_iris', '')).upper()
    code_insee = str(row.get('code_insee', ''))
    
    # Zones urbaines denses (grandes métropoles)
    grandes_metropoles = ['75', '13', '69', '59', '31', '44', '33', '67']
    if any(code_insee.startswith(code) for code in grandes_metropoles):
        if type_iris == 'H':  # Zone d'habitat
            return 'urbain_dense'
        else:
            return 'urbain'
    
    # Classification selon type IRIS
    if type_iris == 'H':  # Zone d'habitat
        # Population density proxy via code INSEE
        if code_insee.startswith(('92', '93', '94')):  # Petite couronne parisienne
            return 'urbain_dense'
        else:
            return 'urbain'
    
    elif type_iris == 'A':  # Zone d'activité
        return 'periurbain'
    
    elif type_iris == 'D':  # Zone diverse
        return 'periurbain'
        
    elif type_iris == 'Z':  # Zone rurale
        return 'rural'
    
    else:
        # Par défaut selon code département
        dept = code_insee[:2] if len(code_insee) >= 2 else ''
        if dept in ['75', '92', '93', '94']:  # Paris + petite couronne
            return 'urbain_dense'
        elif dept in ['77', '78', '91', '95']:  # Grande couronne
            return 'periurbain'
        else:
            return 'urbain'  # Par défaut

def main():
    """Fonction principale"""
    logger = setup_logging()
    
    logger.info("🏢 PRÉPARATION DES DONNÉES PHARMACIES POUR ISOCHRONES")
    logger.info("=" * 60)
    
    try:
        # Créer le dossier de sortie
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Charger les données
        logger.info(f"📂 Chargement de {INPUT_FILE}")
        
        # Essayer différents séparateurs
        df = None
        for sep in [',', ';']:
            try:
                df = pd.read_csv(INPUT_FILE, sep=sep, encoding='utf-8')
                if len(df.columns) > 10:
                    break
            except:
                continue
        
        if df is None:
            raise ValueError("Impossible de charger le fichier")
        
        logger.info(f"   {len(df)} pharmacies chargées")
        logger.info(f"   Colonnes: {list(df.columns)}")
        
        # 2. Nettoyer et renommer les colonnes
        logger.info("🧹 Nettoyage des données...")
        
        # Mapping des colonnes
        df_clean = pd.DataFrame()
        df_clean['id_pharmacie'] = df['Pvactif'].astype(str)
        df_clean['nom_pharmacie'] = df['Nom_Pv']
        df_clean['adresse'] = df['Adresse'] 
        df_clean['commune'] = df['Commune']
        df_clean['code_postal'] = df['Postal']
        df_clean['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df_clean['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df_clean['code_iris'] = df['CODE_IRIS']
        df_clean['nom_iris'] = df['NOM_IRIS']
        df_clean['code_insee'] = df['code_insee']
        df_clean['type_iris'] = df['type_iris']
        
        # 3. Valider les coordonnées
        logger.info("📍 Validation des coordonnées...")
        
        initial_count = len(df_clean)
        
        # Supprimer les valeurs manquantes
        df_clean = df_clean.dropna(subset=['latitude', 'longitude', 'id_pharmacie'])
        
        # Valider les limites France métropolitaine
        france_mask = (
            df_clean['latitude'].between(41, 51) & 
            df_clean['longitude'].between(-5, 10)
        )
        df_clean = df_clean[france_mask]
        
        logger.info(f"   Pharmacies validées: {len(df_clean)} / {initial_count}")
        
        # 4. Déterminer le type de zone
        logger.info("🗺️  Détermination des types de zone...")
        
        df_clean['type_zone'] = df_clean.apply(determine_zone_type, axis=1)
        
        # Statistiques des types de zone
        zone_stats = df_clean['type_zone'].value_counts()
        logger.info("   Répartition des types de zone:")
        for zone, count in zone_stats.items():
            pct = (count / len(df_clean)) * 100
            logger.info(f"     {zone}: {count:,} ({pct:.1f}%)")
        
        # 5. Sélectionner les colonnes finales pour l'export
        columns_export = ['id_pharmacie', 'latitude', 'longitude', 'type_zone', 
                         'nom_pharmacie', 'adresse', 'commune', 'code_postal']
        
        df_final = df_clean[columns_export].copy()
        
        # 6. Sauvegarder
        logger.info(f"💾 Sauvegarde vers {OUTPUT_FILE}")
        
        df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        
        # 7. Statistiques finales
        logger.info("\n" + "=" * 50)
        logger.info("PRÉPARATION TERMINÉE")
        logger.info("=" * 50)
        logger.info(f"Pharmacies traitées : {len(df_final):,}")
        logger.info(f"Fichier créé        : {OUTPUT_FILE}")
        logger.info(f"Taille fichier      : {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Aperçu des données
        logger.info("\nAperçu des données:")
        logger.info(f"\n{df_final.head(3).to_string()}")
        
        logger.info("\n✅ PRÉPARATION TERMINÉE AVEC SUCCÈS!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())