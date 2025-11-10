#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traitement du fichier FINESS.csv avec ajout des poids d'attractivité
et conversion des coordonnées Lambert 93 vers WGS84

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
from pathlib import Path
from pyproj import Transformer
import sys

# Importer la configuration
from finess_categories_weights_seniors_only import FINESS_CATEGORIES_WEIGHTS

# Chemins
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fichiers
FINESS_FILE = INPUT_DIR / "FINESS.csv"
OUTPUT_FILE = OUTPUT_DIR / "FINESS_with_weights.csv"


def main():
    print("=" * 80)
    print("TRAITEMENT FICHIER FINESS.CSV")
    print("=" * 80)
    
    # 1. Charger FINESS
    print(f"\n📖 Lecture de {FINESS_FILE}...")
    # Lire sans header, la première ligne contient des métadonnées
    df = pd.read_csv(FINESS_FILE, sep=';', encoding='utf-8', header=None, skiprows=1)
    
    # Définir les noms de colonnes basés sur la structure du fichier
    colonnes = [
        'categagretab', 'nofinesset', 'nofinessej', 'rs', 'rslongue',
        'complrs', 'compldistrib', 'numvoie', 'typvoie', 'voie',
        'compvoie', 'lieuditbp', 'commune', 'departement', 'libdepartement',
        'ligneacheminement', 'telephone', 'telecopie', 'categetab',
        'libcategetab', 'categagretab2', 'libcategagretab', 'siret',
        'codeape', 'codemft', 'libmft', 'codesph', 'libsph',
        'dateouv', 'dateautor', 'datemaj', 'numuai'
    ]
    
    # Si le fichier de geolocalisation est différent, ajuster
    if len(df.columns) > len(colonnes):
        # Ajouter les colonnes de géolocalisation
        colonnes.extend(['coordxet', 'coordyet'])
    
    df.columns = colonnes[:len(df.columns)]
    
    print(f"✓ {len(df):,} lignes chargées")
    print(f"Colonnes: {list(df.columns)[:10]}... ({len(df.columns)} total)")
    
    # 2. Séparer structureet et geolocalisation
    print(f"\n🔍 Analyse de la structure...")
    df_structure = df[df['categagretab'] == 'structureet'].copy()
    df_geo = df[df['categagretab'] == 'geolocalisation'].copy()
    
    print(f"  • structureet: {len(df_structure):,} lignes")
    print(f"  • geolocalisation: {len(df_geo):,} lignes")
    
    # 3. Fusionner structure + géolocalisation
    print(f"\n🔗 Fusion des données...")
    
    # Pour geolocalisation, les coordonnées sont dans les colonnes 2 et 3
    # Créer un DataFrame avec les coordonnées
    df_geo_coords = df_geo[['nofinesset']].copy()
    df_geo_coords['coordxet'] = pd.to_numeric(df_geo.iloc[:, 2], errors='coerce')  # Colonne 2
    df_geo_coords['coordyet'] = pd.to_numeric(df_geo.iloc[:, 3], errors='coerce')  # Colonne 3
    
    df_merged = df_structure.merge(
        df_geo_coords,
        on='nofinesset',
        how='left'
    )
    
    print(f"✓ {len(df_merged):,} établissements")
    
    # 4. Convertir Lambert 93 -> WGS84
    print(f"\n🌍 Conversion Lambert 93 -> WGS84...")
    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    
    def convert_coords(row):
        if pd.notna(row['coordxet']) and pd.notna(row['coordyet']):
            try:
                lon, lat = transformer.transform(row['coordxet'], row['coordyet'])
                return pd.Series({'longitude': lon, 'latitude': lat})
            except:
                return pd.Series({'longitude': None, 'latitude': None})
        return pd.Series({'longitude': None, 'latitude': None})
    
    df_merged[['longitude', 'latitude']] = df_merged.apply(convert_coords, axis=1)
    
    coords_ok = df_merged['latitude'].notna().sum()
    print(f"✓ {coords_ok:,} coordonnées converties ({coords_ok/len(df_merged)*100:.1f}%)")
    
    # 5. Ajouter les poids d'attractivité
    print(f"\n⚖️  Ajout des poids d'attractivité...")
    
    def get_weight(libelle):
        """Récupère le poids pour un libellé FINESS"""
        if pd.isna(libelle):
            return 0.0
        config = FINESS_CATEGORIES_WEIGHTS.get(libelle)
        return config['bonus'] if config else 0.0
    
    def get_category(libelle):
        """Récupère la catégorie simplifiée"""
        if pd.isna(libelle):
            return 'Non configuré'
        config = FINESS_CATEGORIES_WEIGHTS.get(libelle)
        return config['categorie'] if config else 'Non configuré'
    
    def get_type(libelle):
        """Récupère le type"""
        if pd.isna(libelle):
            return 'non_configure'
        config = FINESS_CATEGORIES_WEIGHTS.get(libelle)
        return config['type'] if config else 'non_configure'
    
    df_merged['bonus_attractivite'] = df_merged['libcategetab'].apply(get_weight)
    df_merged['categorie_simplifiee'] = df_merged['libcategetab'].apply(get_category)
    df_merged['type_etablissement'] = df_merged['libcategetab'].apply(get_type)
    
    # Statistiques
    avec_bonus = (df_merged['bonus_attractivite'] > 0).sum()
    sans_bonus = (df_merged['bonus_attractivite'] == 0).sum()
    
    print(f"  • Avec bonus (> 0): {avec_bonus:,} ({avec_bonus/len(df_merged)*100:.1f}%)")
    print(f"  • Sans bonus (= 0): {sans_bonus:,} ({sans_bonus/len(df_merged)*100:.1f}%)")
    
    # 6. Sélectionner colonnes essentielles
    print(f"\n📋 Sélection des colonnes essentielles...")
    colonnes_finales = [
        'nofinesset',           # Identifiant
        'rs',                   # Raison sociale
        'libcategetab',         # Catégorie originale
        'categorie_simplifiee', # Catégorie simplifiée
        'type_etablissement',   # Type (ehpad, hopital, etc.)
        'ligneacheminement',    # Adresse
        'compvoie',             # Complément voie
        'numvoie',              # Numéro voie
        'typvoie',              # Type voie
        'voie',                 # Nom voie
        'compldistrib',         # Distribution
        'commune',              # Code commune
        'departement',          # Département
        'coordxet',             # X Lambert 93
        'coordyet',             # Y Lambert 93
        'longitude',            # Longitude WGS84
        'latitude',             # Latitude WGS84
        'bonus_attractivite'    # Poids
    ]
    
    df_final = df_merged[colonnes_finales].copy()
    
    # 7. Sauvegarder
    print(f"\n💾 Sauvegarde...")
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"✓ Fichier sauvegardé: {OUTPUT_FILE}")
    print(f"  {len(df_final):,} lignes × {len(df_final.columns)} colonnes")
    
    # 8. Statistiques finales
    print(f"\n{'='*80}")
    print(f"STATISTIQUES PAR TYPE D'ÉTABLISSEMENT")
    print(f"{'='*80}")
    
    stats_type = df_final.groupby('type_etablissement').agg({
        'nofinesset': 'count',
        'bonus_attractivite': 'mean'
    }).round(3)
    stats_type.columns = ['Nombre', 'Bonus moyen']
    stats_type = stats_type.sort_values('Nombre', ascending=False)
    
    print(stats_type.to_string())
    
    # Top catégories avec bonus
    print(f"\n{'='*80}")
    print(f"TOP 20 CATÉGORIES AVEC BONUS")
    print(f"{'='*80}")
    
    top_bonus = df_final[df_final['bonus_attractivite'] > 0].groupby('categorie_simplifiee').agg({
        'nofinesset': 'count',
        'bonus_attractivite': 'first'
    })
    top_bonus.columns = ['Nombre', 'Bonus']
    top_bonus = top_bonus.sort_values('Nombre', ascending=False).head(20)
    
    for idx, row in top_bonus.iterrows():
        print(f"  {idx:40s} | N={row['Nombre']:>6,} | Bonus={row['Bonus']:.2f}")
    
    print(f"\n✅ Traitement terminé !")
    return df_final


if __name__ == "__main__":
    df = main()
