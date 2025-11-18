#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de création de pharmacies_final.csv à partir des données sources

OBJECTIF :
Transformer points_ventes_202509 - RETRAVAILLE.geocoded.csv (données UGA)
+ pharmacies.csv (données CA existantes)
→ pharmacies_final.csv (fichier final propre)

ÉTAPES :
1. Charger les points de vente géocodés (source UGA septembre 2025)
2. Charger les données CA existantes si disponibles
3. Nettoyer et valider les données
4. Calculer type_zone et autres variables dérivées
5. Exporter vers data/output/pharmacies_finales/pharmacies_final.csv

Auteur: Claude Code
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE")
SOURCE_FILE = BASE_DIR / "DATA" / "DONNEES_PHARMACIES" / "points_ventes_202509 - RETRAVAILLE.geocoded.csv"
CA_FILE = BASE_DIR / "Git" / "scoring_pharma_65-" / "data" / "input" / "pharmacies.csv"
OUTPUT_FILE = BASE_DIR / "Git" / "scoring_pharma_65-" / "data" / "output" / "pharmacies_finales" / "pharmacies_final.csv"

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def determine_type_zone(code_postal, commune):
    """
    Détermine le type de zone géographique

    Args:
        code_postal: Code postal (str)
        commune: Nom de la commune (str)

    Returns:
        str: Type de zone (urbain_dense, urbain, periurbain, rural)
    """
    if pd.isna(code_postal):
        return 'rural'

    code_postal = str(code_postal)

    # Grandes métropoles urbaines denses
    metropoles_denses = ['75', '13', '69', '59', '31', '44', '33', '67', '92', '93', '94']
    if any(code_postal.startswith(code) for code in metropoles_denses):
        return 'urbain_dense'

    # Zones urbaines (départements urbains)
    zones_urbaines = ['06', '34', '35', '38', '42', '45', '49', '54', '57', '62', '63', '64', '76', '80', '83', '84']
    if any(code_postal.startswith(code) for code in zones_urbaines):
        return 'urbain'

    # Zones périurbaines (par défaut pour codes postaux < 80000)
    try:
        cp_num = int(code_postal[:2]) if len(code_postal) >= 2 else 0
        if cp_num > 0 and cp_num < 95:
            return 'periurbain'
    except:
        pass

    return 'rural'

def calculate_voisins_5km(df):
    """
    Calcule le nombre de pharmacies voisines dans un rayon de 5km

    Args:
        df: DataFrame des pharmacies avec lat/lon

    Returns:
        Series: Nombre de voisins par pharmacie
    """
    from scipy.spatial import cKDTree

    # Filtrer pharmacies avec coordonnées valides
    df_valid = df.dropna(subset=['latitude', 'longitude']).copy()

    if len(df_valid) == 0:
        return pd.Series(0, index=df.index)

    # Créer KDTree (coordonnées en degrés, 1 degré ≈ 111 km)
    coords = df_valid[['latitude', 'longitude']].values
    tree = cKDTree(coords)

    # Chercher voisins dans rayon 5km (≈ 0.045 degrés)
    radius_deg = 5.0 / 111.0
    neighbors_count = []

    for coord in coords:
        # Query retourne indices des voisins (incluant le point lui-même)
        indices = tree.query_ball_point(coord, radius_deg)
        # Soustraire 1 pour exclure la pharmacie elle-même
        neighbors_count.append(len(indices) - 1)

    # Créer Series avec l'index original
    result = pd.Series(0, index=df.index)
    result.loc[df_valid.index] = neighbors_count

    return result

def main():
    logger.info("=" * 80)
    logger.info("CRÉATION DE PHARMACIES_FINAL.CSV")
    logger.info("=" * 80)

    # 1. Charger les données sources géocodées
    logger.info("\n1. CHARGEMENT DES DONNÉES SOURCES")

    if not SOURCE_FILE.exists():
        logger.error(f"Fichier source introuvable : {SOURCE_FILE}")
        return

    df_source = pd.read_csv(SOURCE_FILE, sep=';', dtype={'Pvactif': str, 'Postal': str})
    logger.info(f"   Fichier source        : {len(df_source):,} lignes")

    # 2. Renommer et sélectionner colonnes
    logger.info("\n2. RENOMMAGE ET SÉLECTION DES COLONNES")

    df = df_source.rename(columns={
        'Pvactif': 'id_pharmacie',
        'Nom_Pv': 'nom_pharmacie',
        'Postal': 'code_postal',
        'Commune': 'commune'
    }).copy()

    # Garder uniquement colonnes nécessaires
    colonnes_base = ['id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude',
                     'code_postal', 'commune', 'result_status']

    df = df[colonnes_base].copy()
    logger.info(f"   Colonnes conservées   : {len(df.columns)}")

    # 3. Nettoyage des données
    logger.info("\n3. NETTOYAGE DES DONNÉES")

    # Supprimer lignes sans ID
    df = df[df['id_pharmacie'].notna()].copy()
    logger.info(f"   Après suppression NaN ID : {len(df):,}")

    # Supprimer doublons sur id_pharmacie
    nb_duplicates = df.duplicated(subset=['id_pharmacie']).sum()
    df = df.drop_duplicates(subset=['id_pharmacie'], keep='first')
    logger.info(f"   Doublons supprimés    : {nb_duplicates}")

    # Supprimer pharmacies sans coordonnées valides
    df = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    df = df[(df['latitude'] != 0) & (df['longitude'] != 0)].copy()
    logger.info(f"   Avec coordonnées      : {len(df):,}")

    # Filtrer uniquement géocodage réussi
    if 'result_status' in df.columns:
        df = df[df['result_status'] == 'ok'].copy()
        logger.info(f"   Géocodage OK          : {len(df):,}")

    # 4. Calculer département
    logger.info("\n4. CALCUL DU DÉPARTEMENT")

    def get_departement(code_postal):
        if pd.isna(code_postal):
            return None
        cp = str(code_postal)
        if len(cp) >= 2:
            # Départements spéciaux (Corse, DOM-TOM)
            if cp.startswith('20'):
                return '2A' if int(cp[2:3]) < 5 else '2B'
            elif cp.startswith('97'):
                return cp[:3]
            else:
                return cp[:2]
        return None

    df['departement'] = df['code_postal'].apply(get_departement)
    logger.info(f"   Départements calculés : {df['departement'].notna().sum():,}")

    # 5. Calculer type_zone
    logger.info("\n5. CALCUL DU TYPE DE ZONE")

    df['type_zone'] = df.apply(
        lambda row: determine_type_zone(row['code_postal'], row['commune']),
        axis=1
    )

    type_zone_counts = df['type_zone'].value_counts()
    logger.info(f"   Types de zones :")
    for zone, count in type_zone_counts.items():
        logger.info(f"     {zone:15s} : {count:,} ({100*count/len(df):.1f}%)")

    # 6. Charger données CA si disponibles
    logger.info("\n6. FUSION AVEC DONNÉES CA")

    if CA_FILE.exists():
        try:
            df_ca = pd.read_csv(CA_FILE, sep=';', dtype={'Pvactif': str})

            # Renommer pour correspondre
            if 'Pvactif' in df_ca.columns:
                df_ca = df_ca.rename(columns={'Pvactif': 'id_pharmacie'})

            # Sélectionner colonnes CA
            ca_cols = ['id_pharmacie', 'ca_total', 'ca_ethique', 'ca_conseil']
            ca_cols_available = [col for col in ca_cols if col in df_ca.columns]

            if len(ca_cols_available) > 1:
                df_ca_subset = df_ca[ca_cols_available].copy()
                df = df.merge(df_ca_subset, on='id_pharmacie', how='left')
                logger.info(f"   Données CA fusionnées : {df[ca_cols_available[1]].notna().sum():,} pharmacies")
            else:
                logger.warning("   Colonnes CA non trouvées dans pharmacies.csv")
        except Exception as e:
            logger.warning(f"   Impossible de charger CA : {e}")
    else:
        logger.warning(f"   Fichier CA introuvable : {CA_FILE}")

    # 7. Calculer delta si CA disponibles
    if 'ca_total' in df.columns and 'ca_ethique' in df.columns and 'ca_conseil' in df.columns:
        logger.info("\n7. CALCUL DU DELTA")
        df['delta'] = df['ca_total'] - df['ca_ethique'] - df['ca_conseil']
        logger.info(f"   Delta calculé         : {df['delta'].notna().sum():,} pharmacies")

    # 8. Calculer voisins_5km
    logger.info("\n8. CALCUL DES VOISINS 5KM")

    try:
        df['voisins_5km'] = calculate_voisins_5km(df)
        logger.info(f"   Voisins calculés      : OK")
        logger.info(f"   Moyenne voisins       : {df['voisins_5km'].mean():.1f}")
    except Exception as e:
        logger.warning(f"   Erreur calcul voisins : {e}")
        df['voisins_5km'] = 0

    # 9. Supprimer colonnes temporaires
    if 'result_status' in df.columns:
        df = df.drop(columns=['result_status'])

    # 10. Réorganiser colonnes dans l'ordre final
    logger.info("\n9. FINALISATION")

    colonnes_finales = ['id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude',
                       'code_postal', 'commune', 'departement', 'type_zone']

    # Ajouter colonnes CA si disponibles
    if 'ca_total' in df.columns:
        colonnes_finales.extend(['ca_total', 'ca_ethique', 'ca_conseil', 'delta'])

    colonnes_finales.append('voisins_5km')

    # Garder uniquement colonnes qui existent
    colonnes_disponibles = [col for col in colonnes_finales if col in df.columns]
    df = df[colonnes_disponibles].copy()

    # 11. Sauvegarder
    logger.info("\n10. SAUVEGARDE")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, sep=';')

    logger.info(f"   Fichier sauvegardé    : {OUTPUT_FILE}")
    logger.info(f"   Pharmacies totales    : {len(df):,}")
    logger.info(f"   Colonnes              : {len(df.columns)}")

    # 12. Statistiques finales
    logger.info("\n11. STATISTIQUES FINALES")

    logger.info(f"   NaN par colonne :")
    for col in df.columns:
        nb_nan = df[col].isna().sum()
        if nb_nan > 0:
            logger.info(f"     {col:20s} : {nb_nan:,} ({100*nb_nan/len(df):.1f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("OK CRÉATION TERMINÉE")
    logger.info("=" * 80)

if __name__ == '__main__':
    main()