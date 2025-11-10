#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de création du fichier hubs - VERSION FICHIER OSM LOCAL

MISSION : Lire un fichier OSM .pbf téléchargé manuellement depuis Geofabrik
et en extraire tous les POI nécessaires pour le scoring pharmacie 65+

PRÉREQUIS :
1. Télécharger france-latest.osm.pbf depuis :
   https://download.geofabrik.de/europe/france-latest.osm.pbf
   
2. Placer le fichier dans :
   data/input/france-latest.osm.pbf
   
3. Installer les dépendances :
   pip install osmium pandas geopandas shapely --break-system-packages

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
import warnings
import time
import sys
import traceback
import osmium
import requests

# Supprimer les warnings
warnings.filterwarnings('ignore')

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
CACHE_DIR = BASE_DIR / "data" / "cache"

# Fichiers
OSM_FILE = INPUT_DIR / "france-latest.osm.pbf"
OUTPUT_CSV = OUTPUT_DIR / "hubs.csv"
OUTPUT_GPKG = OUTPUT_DIR / "hubs.gpkg"
CHECKPOINT_FILE = CACHE_DIR / "osm_extraction_checkpoint.csv"

# Configuration des POI à extraire
# Note: Pharmacies exclues (l'utilisateur a déjà ces données)
POI_FILTERS = {
    'supermarche': {
        'tags': {'shop': ['supermarket', 'convenience']},
        'categorie': 'Supermarché',
        'bonus': 0.10
    },
    'bus': {
        'tags': {'highway': 'bus_stop'},
        'categorie': 'Arrêt de bus',
        'bonus': 0.15
    },
    'metro': {
        'tags': {'station': 'subway'},
        'categorie': 'Station de métro',
        'bonus': 0.08
    },
    'gare': {
        'tags': {'railway': 'station'},
        'categorie': 'Gare ferroviaire',
        'bonus': 0.10
    },
    'marche': {
        'tags': {'amenity': 'marketplace'},
        'categorie': 'Marché',
        'bonus': 0.20
    },
    'hopital': {
        'tags': {'amenity': 'hospital'},
        'categorie': 'Hôpital',
        'bonus': 0.20
    },
    'medecin': {
        'tags': {'amenity': ['doctors', 'clinic']},
        'categorie': 'Cabinet médical',
        'bonus': 0.10
    },
}


class POIHandler(osmium.SimpleHandler):
    """
    Handler pour extraire les POI du fichier OSM
    """
    
    def __init__(self, checkpoint_file=None):
        osmium.SimpleHandler.__init__(self)
        self.pois = []
        self.count = 0
        self.last_print = 0
        self.last_checkpoint = 0
        self.checkpoint_file = checkpoint_file
        
        # Charger le checkpoint si existe
        if checkpoint_file and checkpoint_file.exists():
            print(f"   📥 Reprise depuis checkpoint existant...")
            df_checkpoint = pd.read_csv(checkpoint_file)
            self.pois = df_checkpoint.to_dict('records')
            self.count = len(self.pois)
            self.last_print = self.count
            self.last_checkpoint = self.count
            print(f"   ✅ {self.count:,} POI déjà extraits, reprise en cours...")
    
    def check_tags(self, tags, filter_config):
        """
        Vérifie si un élément correspond aux filtres
        
        Args:
            tags: Tags de l'élément OSM
            filter_config: Configuration du filtre
            
        Returns:
            bool: True si correspond
        """
        filter_tags = filter_config['tags']
        
        for key, values in filter_tags.items():
            if key in tags:
                # Si values est une liste, vérifier si la valeur est dedans
                if isinstance(values, list):
                    if tags[key] in values:
                        return True
                # Sinon, vérifier égalité directe
                elif tags[key] == values:
                    return True
        
        return False
    
    def process_element(self, elem, elem_type):
        """
        Traite un élément OSM (node ou way)
        
        Args:
            elem: Élément OSM
            elem_type: Type ('node' ou 'way')
        """
        # Vérifier chaque type de POI
        for poi_type, filter_config in POI_FILTERS.items():
            if self.check_tags(elem.tags, filter_config):
                # Extraire les coordonnées
                if elem_type == 'node':
                    lat = elem.location.lat
                    lon = elem.location.lon
                elif elem_type == 'way' and hasattr(elem, 'nodes') and len(elem.nodes) > 0:
                    # Pour un way, prendre le centre (moyenne des coordonnées)
                    try:
                        lats = [n.location.lat for n in elem.nodes if n.location.valid()]
                        lons = [n.location.lon for n in elem.nodes if n.location.valid()]
                        if lats and lons:
                            lat = sum(lats) / len(lats)
                            lon = sum(lons) / len(lons)
                        else:
                            return
                    except:
                        return
                else:
                    return
                
                # Vérifier que c'est en France métropolitaine
                if not (41 <= lat <= 52 and -6 <= lon <= 10):
                    return
                
                # Extraire le nom
                nom = elem.tags.get('name', filter_config['categorie'])
                
                # Créer l'entrée
                poi = {
                    'id_hub': f"OSM_{poi_type}_{elem.id}",
                    'nom': nom,
                    'adresse': '',
                    'code_postal': elem.tags.get('addr:postcode', ''),
                    'commune': elem.tags.get('addr:city', ''),
                    'latitude': lat,
                    'longitude': lon,
                    'type_hub': poi_type,
                    'categorie': filter_config['categorie'],
                    'bonus_attractivite': filter_config['bonus'],
                    'source': 'OSM'
                }
                
                self.pois.append(poi)
                self.count += 1
                
                # Afficher progression toutes les 20000 POI
                if self.count - self.last_print >= 20000:
                    print(f"      Extrait: {self.count:,} POI...")
                    self.last_print = self.count
                
                # Sauvegarder checkpoint tous les 20000 POI
                if self.checkpoint_file and self.count - self.last_checkpoint >= 20000:
                    df_temp = pd.DataFrame(self.pois)
                    df_temp.to_csv(self.checkpoint_file, index=False, encoding='utf-8')
                    self.last_checkpoint = self.count
                    print(f"      💾 Checkpoint sauvegardé ({self.count:,} POI)")
                
                break  # Un élément ne peut être qu'un seul type de POI
    
    def node(self, n):
        """Traite un node"""
        self.process_element(n, 'node')
    
    def way(self, w):
        """Traite un way"""
        self.process_element(w, 'way')


def check_dependencies():
    """
    Vérifie que les dépendances sont installées
    
    Returns:
        bool: True si tout est OK
    """
    print("🔍 Vérification des dépendances...")
    
    try:
        import osmium
        print("   ✅ osmium installé")
    except ImportError:
        print("   ❌ osmium manquant")
        print("   Installer avec: pip install osmium --break-system-packages")
        return False
    
    try:
        import pandas
        print("   ✅ pandas installé")
    except ImportError:
        print("   ❌ pandas manquant")
        return False
    
    try:
        import geopandas
        print("   ✅ geopandas installé")
    except ImportError:
        print("   ❌ geopandas manquant")
        return False
    
    return True


def check_osm_file():
    """
    Vérifie que le fichier OSM existe
    
    Returns:
        bool: True si le fichier existe
    """
    print(f"\n📂 Vérification du fichier OSM...")
    print(f"   Recherche: {OSM_FILE}")
    
    if not OSM_FILE.exists():
        print(f"   ❌ Fichier non trouvé")
        print(f"\n   📥 Veuillez télécharger le fichier :")
        print(f"   URL: https://download.geofabrik.de/europe/france-latest.osm.pbf")
        print(f"   Destination: {OSM_FILE}")
        print(f"\n   💡 Alternatives régionales plus petites :")
        print(f"   - Île-de-France (~500 MB): https://download.geofabrik.de/europe/france/ile-de-france-latest.osm.pbf")
        print(f"   - Auvergne-Rhône-Alpes: https://download.geofabrik.de/europe/france/auvergne-rhone-alpes-latest.osm.pbf")
        return False
    
    file_size = OSM_FILE.stat().st_size / (1024 * 1024 * 1024)
    print(f"   ✅ Fichier trouvé ({file_size:.2f} GB)")
    
    return True


def extract_pois_from_osm():
    """
    Extrait les POI du fichier OSM
    
    Returns:
        pd.DataFrame: DataFrame avec les POI extraits
    """
    print(f"\n🗺️  Extraction des POI du fichier OSM...")
    print(f"   Cela peut prendre 10-30 minutes selon la taille du fichier")
    print(f"   💾 Sauvegarde automatique tous les 20 000 POI pour reprise possible")
    
    # Créer le handler avec checkpoint
    handler = POIHandler(checkpoint_file=CHECKPOINT_FILE)
    
    # Appliquer le handler au fichier
    # apply_file lit le fichier et appelle node()/way() pour chaque élément
    handler.apply_file(str(OSM_FILE), locations=True, idx='flex_mem')
    
    # Sauvegarder un dernier checkpoint final
    if handler.checkpoint_file and handler.count > handler.last_checkpoint:
        df_temp = pd.DataFrame(handler.pois)
        df_temp.to_csv(handler.checkpoint_file, index=False, encoding='utf-8')
        print(f"      💾 Checkpoint final sauvegardé ({handler.count:,} POI)")
    
    print(f"\n   ✅ Extraction terminée: {len(handler.pois):,} POI trouvés")
    
    # Convertir en DataFrame
    df = pd.DataFrame(handler.pois)
    
    # Statistiques par type
    print(f"\n   📊 Répartition par type :")
    for poi_type, count in df['type_hub'].value_counts().items():
        print(f"     - {poi_type:<15} : {count:>8,}")
    
    return df


def load_sncf_data():
    """
    Charge les données SNCF
    
    Returns:
        pd.DataFrame: DataFrame avec les gares
    """
    print(f"\n🚂 Chargement des gares SNCF...")
    
    url = 'https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/liste-des-gares/exports/csv'
    cache_file = CACHE_DIR / 'sncf_gares.csv'
    
    try:
        if cache_file.exists():
            df = pd.read_csv(cache_file, encoding='utf-8')
            print(f"   💾 {len(df):,} gares (cache)")
            return df
        
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        temp_file = CACHE_DIR / 'sncf_raw.csv'
        temp_file.write_bytes(response.content)
        
        df_raw = pd.read_csv(temp_file, sep=';', encoding='utf-8')
        
        results = []
        for _, row in df_raw.iterrows():
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
                'type_hub': 'gare',
                'categorie': 'Gare SNCF',
                'bonus_attractivite': 0.10,
                'source': 'SNCF'
            }
            results.append(entry)
        
        df_result = pd.DataFrame(results)
        df_result.to_csv(cache_file, index=False, encoding='utf-8')
        
        print(f"   ✅ {len(df_result):,} gares traitées")
        return df_result
        
    except Exception as e:
        print(f"   ⚠️  Erreur: {e}")
        return pd.DataFrame()


def clean_and_deduplicate(df):
    """
    Nettoie et déduplique les données
    
    Args:
        df (pd.DataFrame): DataFrame à nettoyer
        
    Returns:
        pd.DataFrame: DataFrame nettoyé
    """
    print(f"\n🔧 Nettoyage et dédoublonnage...")
    print(f"   Données initiales: {len(df):,}")
    
    # Nettoyer coordonnées
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    print(f"   Après suppression sans coordonnées: {len(df):,}")
    
    # France métropolitaine seulement
    france_coords = (
        df['latitude'].between(41, 52) & 
        df['longitude'].between(-6, 10)
    )
    df = df[france_coords]
    print(f"   France métropolitaine: {len(df):,}")
    
    # Dédoublonnage par ID
    df = df.drop_duplicates(subset=['id_hub'])
    print(f"   Après dédoublonnage par ID: {len(df):,}")
    
    # Dédoublonnage spatial (même type, coordonnées très proches)
    df['lat_round'] = df['latitude'].round(4)
    df['lon_round'] = df['longitude'].round(4)
    df = df.drop_duplicates(subset=['type_hub', 'lat_round', 'lon_round'])
    df = df.drop(columns=['lat_round', 'lon_round'])
    
    print(f"   Après dédoublonnage spatial: {len(df):,}")
    
    return df


def save_results(df):
    """
    Sauvegarde les résultats
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n💾 Sauvegarde des résultats...")
    
    if df.empty:
        print("❌ Aucune donnée à sauvegarder")
        return
    
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # CSV
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        csv_size = OUTPUT_CSV.stat().st_size / (1024 * 1024)
        print(f"   ✅ CSV: {OUTPUT_CSV.name} ({csv_size:.1f} MB)")
        
        # GeoPackage
        geometry = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
        gdf.to_file(OUTPUT_GPKG, driver='GPKG', layer='hubs')
        gpkg_size = OUTPUT_GPKG.stat().st_size / (1024 * 1024)
        print(f"   ✅ GPKG: {OUTPUT_GPKG.name} ({gpkg_size:.1f} MB)")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")


def display_statistics(df):
    """
    Affiche les statistiques finales
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)
    
    if df.empty:
        print("Aucune donnée disponible")
        return
    
    print(f"\n✅ Total de hubs créés : {len(df):,}")
    
    print(f"\n📦 Par type de hub :")
    type_counts = df['type_hub'].value_counts()
    for type_hub, count in type_counts.items():
        pct = (count / len(df)) * 100
        print(f"  • {type_hub:<20} : {count:>8,}  ({pct:>5.1f}%)")
    
    print(f"\n🔗 Par source :")
    source_counts = df['source'].value_counts()
    for source, count in source_counts.items():
        pct = (count / len(df)) * 100
        print(f"  • {source:<10} : {count:>8,}  ({pct:>5.1f}%)")
    
    bonus_moy = df['bonus_attractivite'].mean()
    print(f"\n💰 Bonus d'attractivité moyen : {bonus_moy:.3f}")
    
    print(f"\n📁 Fichiers créés :")
    if OUTPUT_CSV.exists():
        print(f"  ✓ {OUTPUT_CSV.name}")
    if OUTPUT_GPKG.exists():
        print(f"  ✓ {OUTPUT_GPKG.name}")
    
    print("=" * 70)


def main():
    """
    Fonction principale
    """
    print("=" * 70)
    print("🏢 CRÉATION HUBS - VERSION FICHIER OSM LOCAL")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # 1. Vérifications
        if not check_dependencies():
            return False
        
        if not check_osm_file():
            return False
        
        # Créer répertoires
        for directory in [OUTPUT_DIR, CACHE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        all_dataframes = []
        
        # 2. Extraire POI du fichier OSM
        df_osm = extract_pois_from_osm()
        if not df_osm.empty:
            all_dataframes.append(df_osm)
        
        # 3. Ajouter les gares SNCF (complément)
        df_sncf = load_sncf_data()
        if not df_sncf.empty:
            all_dataframes.append(df_sncf)
        
        # 4. Combiner
        if all_dataframes:
            df_combined = pd.concat(all_dataframes, ignore_index=True)
        else:
            print("\n❌ Aucune donnée extraite")
            return False
        
        # 5. Nettoyage
        df_final = clean_and_deduplicate(df_combined)
        
        # 6. Sauvegarde
        save_results(df_final)
        
        # 7. Statistiques
        display_statistics(df_final)
        
        # 8. Nettoyer le checkpoint
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
            print(f"\n🗑️  Checkpoint supprimé (extraction complète)")
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Temps d'exécution : {elapsed_time/60:.1f} minutes")
        
        print(f"\n✅ CRÉATION TERMINÉE AVEC SUCCÈS!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)