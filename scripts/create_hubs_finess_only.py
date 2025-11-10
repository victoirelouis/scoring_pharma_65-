#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de création du fichier hubs - FINESS uniquement avec géocodage rapide

APPROCHE PRAGMATIQUE :
- Charger les établissements FINESS réels (46,946 établissements)
- Géocoder prioritairement : EHPAD, hôpitaux, pharmacies
- Utiliser Photon API (rapide, sans rate limiting strict)
- Sauvegarder immédiatement les résultats pour éviter de perdre le travail

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
import requests
import time
from tqdm import tqdm

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
CACHE_DIR = BASE_DIR / "data" / "cache"

# Fichiers
FINESS_FILE = INPUT_DIR / "FINESS.csv"
OUTPUT_CSV = OUTPUT_DIR / "hubs.csv"
OUTPUT_GPKG = OUTPUT_DIR / "hubs.gpkg"
CACHE_FILE = CACHE_DIR / "geocode_cache.csv"

# Configuration FINESS
FINESS_MAPPING = {
    # EHPAD et résidences seniors (priorité 1)
    '500': {'type': 'ehpad', 'categorie': 'EHPAD', 'bonus': 0.25, 'priority': 1},
    '501': {'type': 'ehpad', 'categorie': 'Maison de retraite', 'bonus': 0.25, 'priority': 1},
    '502': {'type': 'ehpad', 'categorie': 'Résidence autonomie', 'bonus': 0.25, 'priority': 1},
    
    # Hôpitaux (priorité 1)
    '355': {'type': 'hopital', 'categorie': 'Centre Hospitalier', 'bonus': 0.20, 'priority': 1},
    '362': {'type': 'hopital', 'categorie': 'CH', 'bonus': 0.20, 'priority': 1},
    '365': {'type': 'hopital', 'categorie': 'Clinique', 'bonus': 0.20, 'priority': 1},
    '106': {'type': 'hopital', 'categorie': 'Hôpital Local', 'bonus': 0.20, 'priority': 1},
    
    # Pharmacies (priorité 2)
    '620': {'type': 'pharmacie', 'categorie': 'Pharmacie', 'bonus': 0.00, 'priority': 2},
    
    # Laboratoires (priorité 3)
    '611': {'type': 'laboratoire', 'categorie': 'Laboratoire', 'bonus': 0.10, 'priority': 3},
}


def create_directories():
    """Créer les répertoires nécessaires"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print("📁 Répertoires préparés\n")


def load_finess_data():
    """
    Charge les données FINESS (établissements de santé)
    
    Returns:
        pd.DataFrame: Données FINESS filtrées
    """
    print(f"📋 Chargement du fichier FINESS...")
    
    if not FINESS_FILE.exists():
        print(f"❌ Fichier FINESS introuvable: {FINESS_FILE}")
        return pd.DataFrame()
    
    try:
        # Lire le fichier et parser manuellement
        lines = FINESS_FILE.read_text(encoding='utf-8').split('\n')
        data_lines = [line for line in lines if line.startswith('structureet')]
        
        if not data_lines:
            print("❌ Aucune ligne 'structureet' trouvée")
            return pd.DataFrame()
        
        # Parser les lignes
        parsed_data = []
        for line in data_lines:
            parts = line.split(';')
            if len(parts) > 19:
                cat_code = parts[18].strip()
                
                if cat_code in FINESS_MAPPING:
                    mapping = FINESS_MAPPING[cat_code]
                    
                    # Construire l'adresse complète
                    num_voie = parts[7].strip() if len(parts) > 7 else ''
                    type_voie = parts[8].strip() if len(parts) > 8 else ''
                    lib_voie = parts[9].strip() if len(parts) > 9 else ''
                    commune_complete = parts[15].strip() if len(parts) > 15 else ''
                    
                    adresse = f"{num_voie} {type_voie} {lib_voie}".strip()
                    
                    # Extraire code postal et commune
                    code_postal = ''
                    commune = commune_complete
                    if commune_complete:
                        cp_match = commune_complete.split(' ', 1)
                        if len(cp_match) == 2 and len(cp_match[0]) == 5 and cp_match[0].isdigit():
                            code_postal = cp_match[0]
                            commune = cp_match[1]
                    
                    parsed_data.append({
                        'finess': parts[1].strip(),
                        'nom': parts[3].strip(),
                        'type_hub': mapping['type'],
                        'categorie_detaillee': mapping['categorie'],
                        'bonus_attractivite': mapping['bonus'],
                        'priority': mapping['priority'],
                        'adresse': adresse,
                        'code_postal': code_postal,
                        'commune': commune,
                        'source': 'FINESS'
                    })
        
        if not parsed_data:
            print(f"❌ Aucun établissement pertinent dans {len(data_lines)} lignes")
            return pd.DataFrame()
        
        df = pd.DataFrame(parsed_data)
        
        print(f"✅ {len(df):,} établissements chargés")
        print(f"   Types: {df['type_hub'].value_counts().to_dict()}")
        print(f"   Priorité 1 (EHPAD + Hôpitaux): {len(df[df['priority']==1]):,}")
        print(f"   Priorité 2 (Pharmacies): {len(df[df['priority']==2]):,}")
        print(f"   Priorité 3 (Laboratoires): {len(df[df['priority']==3]):,}\n")
        
        return df
        
    except Exception as e:
        print(f"❌ Erreur chargement FINESS: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def geocode_with_photon(address, max_retries=2):
    """
    Géocode une adresse avec Photon API (rapide, gratuit, sans rate limit strict)
    
    Args:
        address (str): Adresse à géocoder
        max_retries (int): Nombre de tentatives
        
    Returns:
        tuple: (latitude, longitude) ou (None, None)
    """
    base_url = "https://photon.komoot.io/api/"
    
    for attempt in range(max_retries):
        try:
            params = {
                'q': address,
                'limit': 1,
                'lang': 'fr'
            }
            
            response = requests.get(base_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features'):
                    coords = data['features'][0]['geometry']['coordinates']
                    return coords[1], coords[0]  # lat, lon
            
            time.sleep(0.1)  # Petit délai entre tentatives
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.2)
                continue
    
    return None, None


def geocode_establishments(df, max_items=None):
    """
    Géocode les établissements par ordre de priorité
    
    Args:
        df (pd.DataFrame): DataFrame avec les établissements
        max_items (int): Nombre maximum à géocoder (pour tests)
        
    Returns:
        pd.DataFrame: DataFrame avec coordonnées GPS
    """
    print("🌍 Géocodage des établissements avec Photon API...")
    print("   (API rapide, gratuite, sans rate limiting strict)\n")
    
    # Charger le cache si existe
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache_df = pd.read_csv(CACHE_FILE)
            cache = dict(zip(cache_df['address'], zip(cache_df['latitude'], cache_df['longitude'])))
            print(f"📦 Cache chargé: {len(cache):,} adresses\n")
        except:
            pass
    
    # Trier par priorité
    df = df.sort_values('priority').copy()
    
    if max_items:
        df = df.head(max_items)
        print(f"⚠️  Mode test: géocodage des {max_items} premiers établissements\n")
    
    # Géocoder
    results = []
    success_count = 0
    cache_hits = 0
    new_geocodes = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Géocodage"):
        # Construire l'adresse complète
        full_address = f"{row['adresse']}, {row['code_postal']} {row['commune']}, France"
        full_address = full_address.replace('  ', ' ').strip()
        
        # Vérifier le cache
        if full_address in cache:
            lat, lon = cache[full_address]
            cache_hits += 1
        else:
            lat, lon = geocode_with_photon(full_address)
            
            if lat and lon:
                new_geocodes.append({
                    'address': full_address,
                    'latitude': lat,
                    'longitude': lon
                })
                success_count += 1
        
        if lat and lon:
            results.append({
                **row.to_dict(),
                'latitude': lat,
                'longitude': lon,
                'adresse_complete': full_address
            })
        
        # Sauvegarder le cache régulièrement
        if len(new_geocodes) >= 100:
            save_cache(new_geocodes, cache)
            new_geocodes = []
    
    # Sauvegarder le cache final
    if new_geocodes:
        save_cache(new_geocodes, cache)
    
    result_df = pd.DataFrame(results)
    
    print(f"\n✅ Géocodage terminé:")
    print(f"   - Cache hits: {cache_hits:,}")
    print(f"   - Nouveaux géocodages: {success_count:,}")
    print(f"   - Total avec GPS: {len(result_df):,}/{len(df):,} ({len(result_df)/len(df)*100:.1f}%)")
    
    return result_df


def save_cache(new_geocodes, existing_cache):
    """Sauvegarde le cache de géocodage"""
    try:
        # Combiner avec le cache existant
        all_geocodes = []
        for addr, (lat, lon) in existing_cache.items():
            all_geocodes.append({'address': addr, 'latitude': lat, 'longitude': lon})
        all_geocodes.extend(new_geocodes)
        
        cache_df = pd.DataFrame(all_geocodes)
        cache_df.drop_duplicates(subset=['address'], keep='last', inplace=True)
        cache_df.to_csv(CACHE_FILE, index=False)
        
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde cache: {e}")


def save_results(df):
    """Sauvegarde les résultats"""
    print("\n💾 Sauvegarde des résultats...")
    
    if df.empty:
        print("❌ Aucune donnée à sauvegarder")
        return False
    
    try:
        # CSV
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        print(f"   ✅ CSV sauvegardé: {OUTPUT_CSV}")
        
        # GeoPackage
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df['longitude'], df['latitude'])],
            crs='EPSG:4326'
        )
        gdf.to_file(OUTPUT_GPKG, driver='GPKG')
        print(f"   ✅ GeoPackage sauvegardé: {OUTPUT_GPKG}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        import traceback
        traceback.print_exc()
        return False


def display_statistics(df):
    """Affiche les statistiques finales"""
    print("\n" + "="*60)
    print("STATISTIQUES FINALES")
    print("="*60)
    
    if df.empty:
        print("Aucune donnée disponible")
        return
    
    print(f"\n📊 Total hubs: {len(df):,}")
    
    print(f"\n🏥 Par type:")
    for hub_type, count in df['type_hub'].value_counts().items():
        print(f"   - {hub_type}: {count:,}")
    
    print(f"\n⭐ Par catégorie:")
    for cat, count in df['categorie_detaillee'].value_counts().head(10).items():
        print(f"   - {cat}: {count:,}")
    
    print(f"\n🎯 Bonus attractivité moyen: {df['bonus_attractivite'].mean():.3f}")
    
    print(f"\n📍 Couverture géographique:")
    print(f"   - Latitude: {df['latitude'].min():.4f} à {df['latitude'].max():.4f}")
    print(f"   - Longitude: {df['longitude'].min():.4f} à {df['longitude'].max():.4f}")


def main():
    """Fonction principale"""
    print("🏢 CRÉATION DU FICHIER HUBS - FINESS UNIQUEMENT")
    print("="*60)
    print("✨ Géocodage rapide avec Photon API")
    print("="*60 + "\n")
    
    start_time = time.time()
    
    try:
        # 1. Préparation
        create_directories()
        
        # 2. Chargement FINESS
        df_finess = load_finess_data()
        
        if df_finess.empty:
            print("❌ Aucune donnée FINESS chargée")
            return False
        
        # 3. Géocodage (commencer par un test avec 100 établissements)
        print("🔧 Mode: Géocodage priorité 1 (EHPAD + Hôpitaux)")
        df_priority1 = df_finess[df_finess['priority'] == 1].copy()
        print(f"   À géocoder: {len(df_priority1):,} établissements\n")
        
        # Géocoder priorité 1 d'abord
        df_geocoded = geocode_establishments(df_priority1)
        
        if df_geocoded.empty:
            print("❌ Aucun établissement géocodé")
            return False
        
        # 4. Sauvegarde
        if save_results(df_geocoded):
            # 5. Statistiques
            display_statistics(df_geocoded)
            
            elapsed_time = time.time() - start_time
            print(f"\n⏱️  Temps d'exécution: {elapsed_time/60:.1f} minutes")
            print("\n✅ CRÉATION TERMINÉE AVEC SUCCÈS!")
            return True
        else:
            return False
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
