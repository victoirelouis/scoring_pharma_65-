#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de FUSION COMPLÈTE : FINESS + RPPS + Hubs OSM
avec DÉDOUBLONNAGE INTELLIGENT (20m)

MISSION : Fusionner les 3 sources en évitant le double comptage
- Si 2 hubs sont à moins de 20m → garder celui avec le BONUS MAX

Entrées :
1. finess_complet.csv (établissements avec lat/lon)
2. rpps_geocoded_avec_poids.csv (médecins avec lat/lon et poids)
3. hubs OSM (hôpitaux, cliniques d'OpenStreetMap)

Sortie :
- hubs_complet.csv (fusion dédoublonnée des 3 sources)

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys
from math import radians, cos, sin, sqrt, atan2

warnings.filterwarnings('ignore')

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "data" / "output"

# Distance de dédoublonnage (en mètres)
DEDUPLICATE_DISTANCE = 20  # 20 mètres


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcule la distance en mètres entre deux points GPS (formule Haversine)
    
    Args:
        lat1, lon1: Coordonnées du point 1
        lat2, lon2: Coordonnées du point 2
        
    Returns:
        float: Distance en mètres
    """
    # Rayon de la Terre en mètres
    R = 6371000
    
    # Convertir en radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Différences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Formule Haversine
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def find_file(directory, patterns):
    """
    Recherche un fichier selon des patterns
    
    Args:
        directory (Path): Répertoire de recherche
        patterns (list): Liste de patterns
        
    Returns:
        Path: Fichier trouvé ou None
    """
    for pattern in patterns:
        files = list(directory.glob(pattern))
        if files:
            return files[0]
    return None


def load_finess():
    """
    Charge le fichier FINESS avec coordonnées
    
    Returns:
        pd.DataFrame: FINESS standardisé
    """
    print(f"\n🏥 CHARGEMENT FINESS...")
    
    # Chercher le fichier
    finess_file = find_file(PROCESSED_DIR, ["finess_complet.csv", "finess*.csv"])
    if not finess_file:
        finess_file = find_file(INPUT_DIR, ["finess_complet.csv", "finess*.csv"])
    
    if not finess_file:
        print("   ⚠️  Fichier FINESS non trouvé - IGNORÉ")
        return pd.DataFrame()
    
    print(f"   📁 {finess_file.name}")
    
    try:
        df = pd.read_csv(finess_file, encoding='utf-8', low_memory=False)
        print(f"   ✓ {len(df):,} établissements")
        
        # Vérifier colonnes essentielles
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            print(f"   ⚠️  Colonnes lat/lon manquantes - IGNORÉ")
            return pd.DataFrame()
        
        # Standardiser colonnes
        df = standardize_dataframe(df, 'FINESS')
        
        # Statistiques
        geocoded = df['latitude'].notna().sum()
        print(f"   ✓ Géocodés: {geocoded:,} ({geocoded/len(df)*100:.1f}%)")
        
        # Bonus moyen
        if 'bonus_attractivite' in df.columns:
            bonus_mean = df['bonus_attractivite'].mean()
            print(f"   ✓ Bonus moyen: {bonus_mean:.3f}")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return pd.DataFrame()


def load_rpps():
    """
    Charge le fichier RPPS géocodé avec poids
    
    Returns:
        pd.DataFrame: RPPS standardisé
    """
    print(f"\n👨‍⚕️ CHARGEMENT RPPS...")
    
    rpps_file = PROCESSED_DIR / "rpps_geocoded_avec_poids.csv"
    
    if not rpps_file.exists():
        print(f"   ⚠️  Fichier non trouvé - IGNORÉ")
        return pd.DataFrame()
    
    print(f"   📁 {rpps_file.name}")
    
    try:
        df = pd.read_csv(rpps_file, encoding='utf-8')
        print(f"   ✓ {len(df):,} médecins")
        
        # Standardiser
        df = standardize_dataframe(df, 'RPPS')
        
        # Stats
        geocoded = df['latitude'].notna().sum()
        print(f"   ✓ Géocodés: {geocoded:,} ({geocoded/len(df)*100:.1f}%)")
        
        bonus_mean = df['bonus_attractivite'].mean()
        print(f"   ✓ Bonus moyen: {bonus_mean:.3f}")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return pd.DataFrame()


def load_hubs_osm():
    """
    Charge les hubs OSM (hôpitaux, cliniques)
    
    Returns:
        pd.DataFrame: Hubs OSM standardisés
    """
    print(f"\n🗺️  CHARGEMENT HUBS OSM...")
    
    # Chercher fichier hubs OSM
    osm_file = find_file(PROCESSED_DIR, ["hubs*.csv", "osm*.csv"])
    if not osm_file:
        osm_file = find_file(INPUT_DIR, ["hubs*.csv", "osm*.csv"])
    
    if not osm_file:
        print(f"   ⚠️  Fichier hubs OSM non trouvé - IGNORÉ")
        return pd.DataFrame()
    
    print(f"   📁 {osm_file.name}")
    
    try:
        df = pd.read_csv(osm_file, encoding='utf-8')
        print(f"   ✓ {len(df):,} hubs OSM")
        
        # Standardiser
        df = standardize_dataframe(df, 'OSM')
        
        # Stats
        geocoded = df['latitude'].notna().sum()
        print(f"   ✓ Géocodés: {geocoded:,} ({geocoded/len(df)*100:.1f}%)")
        
        # Bonus moyen
        if 'bonus_attractivite' in df.columns:
            bonus_mean = df['bonus_attractivite'].mean()
            print(f"   ✓ Bonus moyen: {bonus_mean:.3f}")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return pd.DataFrame()


def standardize_dataframe(df, source):
    """
    Standardise un DataFrame aux colonnes communes
    
    Args:
        df (pd.DataFrame): DataFrame à standardiser
        source (str): Source des données ('FINESS', 'RPPS', 'OSM')
        
    Returns:
        pd.DataFrame: DataFrame standardisé
    """
    # Colonnes finales requises
    required_columns = [
        'id_hub',
        'nom',
        'adresse',
        'code_postal',
        'commune',
        'latitude',
        'longitude',
        'type_hub',
        'categorie',
        'bonus_attractivite',
        'source'
    ]
    
    # Créer un nouveau DataFrame avec colonnes standardisées
    df_std = pd.DataFrame()
    
    # id_hub
    if 'id_hub' in df.columns:
        df_std['id_hub'] = df['id_hub']
    else:
        df_std['id_hub'] = f"{source}_" + df.index.astype(str)
    
    # nom
    if 'nom' in df.columns:
        df_std['nom'] = df['nom']
    elif 'name' in df.columns:
        df_std['nom'] = df['name']
    elif 'rs' in df.columns:
        df_std['nom'] = df['rs']
    else:
        df_std['nom'] = f"{source} Hub"
    
    # adresse
    if 'adresse' in df.columns:
        df_std['adresse'] = df['adresse']
    elif 'voie' in df.columns:
        df_std['adresse'] = df['voie']
    else:
        df_std['adresse'] = ''
    
    # code_postal
    if 'code_postal' in df.columns:
        df_std['code_postal'] = df['code_postal']
    elif 'cp' in df.columns:
        df_std['code_postal'] = df['cp']
    else:
        df_std['code_postal'] = ''
    
    # commune
    if 'commune' in df.columns:
        df_std['commune'] = df['commune']
    elif 'ville' in df.columns:
        df_std['commune'] = df['ville']
    elif 'libcom' in df.columns:
        df_std['commune'] = df['libcom']
    else:
        df_std['commune'] = ''
    
    # latitude
    df_std['latitude'] = df['latitude']
    
    # longitude
    df_std['longitude'] = df['longitude']
    
    # type_hub
    if 'type_hub' in df.columns:
        df_std['type_hub'] = df['type_hub']
    else:
        if source == 'FINESS':
            df_std['type_hub'] = 'etablissement_finess'
        elif source == 'RPPS':
            df_std['type_hub'] = 'cabinet_medical'
        else:
            df_std['type_hub'] = 'hub_osm'
    
    # categorie
    if 'categorie' in df.columns:
        df_std['categorie'] = df['categorie']
    elif 'category' in df.columns:
        df_std['categorie'] = df['category']
    else:
        df_std['categorie'] = source
    
    # bonus_attractivite
    if 'bonus_attractivite' in df.columns:
        df_std['bonus_attractivite'] = df['bonus_attractivite']
    elif 'bonus' in df.columns:
        df_std['bonus_attractivite'] = df['bonus']
    else:
        # Valeur par défaut selon la source
        if source == 'FINESS':
            df_std['bonus_attractivite'] = 0.15
        elif source == 'RPPS':
            df_std['bonus_attractivite'] = 0.12
        else:
            df_std['bonus_attractivite'] = 0.10
    
    # source
    df_std['source'] = source
    
    return df_std


def deduplicate_by_proximity(df, distance_meters=DEDUPLICATE_DISTANCE):
    """
    Dédoublonne les hubs trop proches (< distance_meters)
    Garde celui avec le BONUS MAX
    
    Args:
        df (pd.DataFrame): DataFrame avec tous les hubs
        distance_meters (float): Distance de dédoublonnage en mètres
        
    Returns:
        pd.DataFrame: DataFrame dédoublonné
    """
    print(f"\n🔍 DÉDOUBLONNAGE (distance < {distance_meters}m)...")
    print(f"   Règle: Si 2 hubs à moins de {distance_meters}m → garder bonus MAX")
    
    # Ne garder que les lignes avec coordonnées valides
    df_valid = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    
    initial_count = len(df_valid)
    print(f"   Entrée: {initial_count:,} hubs géocodés")
    
    # Trier par bonus décroissant (pour garder les meilleurs)
    df_sorted = df_valid.sort_values('bonus_attractivite', ascending=False).reset_index(drop=True)
    
    # Liste des hubs à garder
    to_keep = []
    processed = set()
    
    print(f"   Traitement en cours...")
    
    for idx, row in df_sorted.iterrows():
        if idx in processed:
            continue
        
        # Coordonnées du hub actuel
        lat1 = row['latitude']
        lon1 = row['longitude']
        
        # Marquer comme traité
        to_keep.append(idx)
        processed.add(idx)
        
        # Chercher les doublons proches
        for idx2 in range(idx + 1, len(df_sorted)):
            if idx2 in processed:
                continue
            
            row2 = df_sorted.iloc[idx2]
            lat2 = row2['latitude']
            lon2 = row2['longitude']
            
            # Calculer distance
            dist = haversine_distance(lat1, lon1, lat2, lon2)
            
            # Si trop proche, marquer comme doublon
            if dist < distance_meters:
                processed.add(idx2)
        
        # Afficher progression tous les 1000
        if (idx + 1) % 1000 == 0:
            print(f"      {idx + 1:>6,}/{initial_count:<6,} traités...")
    
    # Créer le DataFrame final
    df_dedup = df_sorted.iloc[to_keep].copy()
    
    # Statistiques
    removed_count = initial_count - len(df_dedup)
    removed_pct = (removed_count / initial_count) * 100
    
    print(f"\n   ✅ Dédoublonnage terminé:")
    print(f"      • Avant: {initial_count:,} hubs")
    print(f"      • Après: {len(df_dedup):,} hubs")
    print(f"      • Supprimés: {removed_count:,} ({removed_pct:.1f}%)")
    
    # Statistiques par source
    print(f"\n   📊 Supprimés par source:")
    sources = ['FINESS', 'RPPS', 'OSM']
    for source in sources:
        before = len(df_sorted[df_sorted['source'] == source])
        after = len(df_dedup[df_dedup['source'] == source])
        removed = before - after
        if before > 0:
            pct = (removed / before) * 100
            print(f"      • {source:<10} : -{removed:>5,} ({pct:>5.1f}%)")
    
    return df_dedup


def merge_and_save(df_finess, df_rpps, df_osm):
    """
    Fusionne les 3 sources et sauvegarde
    
    Args:
        df_finess: FINESS
        df_rpps: RPPS
        df_osm: OSM
        
    Returns:
        pd.DataFrame: DataFrame fusionné et dédoublonné
    """
    print(f"\n🔗 FUSION DES SOURCES...")
    
    # Concaténer tous les DataFrames non vides
    dfs_to_concat = []
    
    if not df_finess.empty:
        dfs_to_concat.append(df_finess)
        print(f"   ✓ FINESS: {len(df_finess):,}")
    
    if not df_rpps.empty:
        dfs_to_concat.append(df_rpps)
        print(f"   ✓ RPPS: {len(df_rpps):,}")
    
    if not df_osm.empty:
        dfs_to_concat.append(df_osm)
        print(f"   ✓ OSM: {len(df_osm):,}")
    
    if not dfs_to_concat:
        print(f"   ❌ Aucune source disponible!")
        return pd.DataFrame()
    
    # Fusion
    df_merged = pd.concat(dfs_to_concat, ignore_index=True)
    total_before = len(df_merged)
    print(f"\n   ✓ Total fusionné: {total_before:,} hubs")
    
    # Dédoublonnage intelligent (20m)
    df_final = deduplicate_by_proximity(df_merged, distance_meters=DEDUPLICATE_DISTANCE)
    
    # Sauvegarder
    print(f"\n💾 SAUVEGARDE...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / "hubs_complet.csv"
    df_final.to_csv(output_file, index=False, encoding='utf-8')
    
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ {output_file.name} ({size_mb:.1f} MB)")
    
    return df_final


def display_summary(df):
    """
    Affiche le résumé final
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL - HUBS COMPLET")
    print("=" * 70)
    
    if df.empty:
        print("Aucune donnée")
        return
    
    total = len(df)
    geocoded = df['latitude'].notna().sum()
    
    print(f"\n✅ HUBS FUSIONNÉS ET DÉDOUBLONNÉS:")
    print(f"   Total: {total:,} hubs uniques")
    print(f"   Géocodés: {geocoded:,} ({geocoded/total*100:.1f}%)")
    
    # Par source
    print(f"\n📋 PAR SOURCE:")
    for source in df['source'].unique():
        count = len(df[df['source'] == source])
        pct = (count / total) * 100
        print(f"   • {source:<10} : {count:>6,} ({pct:>5.1f}%)")
    
    # Bonus
    print(f"\n💰 BONUS D'ATTRACTIVITÉ:")
    print(f"   Minimum: {df['bonus_attractivite'].min():.3f}")
    print(f"   Moyen: {df['bonus_attractivite'].mean():.3f}")
    print(f"   Maximum: {df['bonus_attractivite'].max():.3f}")
    
    # Top catégories
    print(f"\n🏆 TOP 10 CATÉGORIES:")
    for idx, (cat, count) in enumerate(df['categorie'].value_counts().head(10).items(), 1):
        bonus_mean = df[df['categorie']==cat]['bonus_attractivite'].mean()
        print(f"   {idx:>2}. {cat:<30} : {count:>6,}  (bonus: {bonus_mean:.3f})")
    
    # Fichier créé
    print(f"\n📁 FICHIER CRÉÉ:")
    print(f"   • data/output/hubs_complet.csv")
    
    print(f"\n💡 PRÊT POUR LE SCORING !")
    print(f"   Ce fichier peut être utilisé directement dans votre modèle")
    print(f"   de scoring des pharmacies 65+")
    
    print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔗 FUSION COMPLÈTE : FINESS + RPPS + OSM")
    print("=" * 70)
    print(f"📋 Ce script :")
    print(f"   1. Charge les 3 sources (FINESS, RPPS, OSM)")
    print(f"   2. Standardise les colonnes")
    print(f"   3. Fusionne tout ensemble")
    print(f"   4. DÉDOUBLONNE par proximité ({DEDUPLICATE_DISTANCE}m)")
    print(f"   5. Garde le hub avec BONUS MAX si collision")
    print(f"\n⚠️  IMPORTANT: Dédoublonnage à {DEDUPLICATE_DISTANCE}m")
    print(f"   → Évite le double comptage (ex: cardio À l'hôpital)")
    print("=" * 70)
    
    try:
        # Charger les 3 sources
        df_finess = load_finess()
        df_rpps = load_rpps()
        df_osm = load_hubs_osm()
        
        # Vérifier qu'on a au moins une source
        if df_finess.empty and df_rpps.empty and df_osm.empty:
            print("\n❌ Aucune source de données disponible!")
            return False
        
        # Fusionner et dédoublonner
        df_final = merge_and_save(df_finess, df_rpps, df_osm)
        
        if df_final.empty:
            print("\n❌ Échec de la fusion")
            return False
        
        # Résumé
        display_summary(df_final)
        
        print(f"\n✅ FUSION TERMINÉE AVEC SUCCÈS!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
