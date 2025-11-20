"""
Script de calcul des variables touristiques pour les pharmacies
Optimisé avec traitement par batch et parallélisation

Utilise les isochrones drive_10min et walk_5min pour calculer :
- Nombre d'hébergements (hôtels, campings, premium) par isochrone
- Capacité d'accueil par isochrone
- Variables de contexte communal (montagne, littoral)
- Ratios et densités touristiques

Auteur: Claude
Date: 10/11/2025
"""

import pandas as pd
import geopandas as gpd
import json
import os
import time
import sys
from pathlib import Path
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Ajouter le répertoire parent pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_prep import (
    INPUT_DIR, OUTPUT_DIR, ISOCHRONES_DIR,
    OUTPUT_FILES, INPUT_FILES,
    ISOCHRONES_DRIVE_10MIN, ISOCHRONES_WALK_5MIN
)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Fichiers d'entrée depuis config
FICHIER_PHARMACIES = OUTPUT_FILES['pharmacies_enrichies_insee']
FICHIER_HEBERGEMENTS = INPUT_FILES.get('hebergements_hotels', INPUT_DIR / "INSEE_hebergements_classes.csv")
FICHIER_LOI_MONTAGNE = INPUT_DIR / "INSEE_loi_montagne.xlsx"
FICHIER_LOI_LITTORALE = INPUT_DIR / "INSEE_loi_littorale.xlsx"

# Fichier de sortie depuis config
FICHIER_OUTPUT = OUTPUT_FILES['pharmacies_avec_tourisme']

# Isochrones depuis config
CHEMIN_ISOCHRONES = ISOCHRONES_DIR

# Paramètres de parallélisation
N_WORKERS = 8  # Nombre de processus parallèles (ajuster selon votre CPU)
BATCH_SIZE = 500  # Taille des batchs pour le traitement


# ============================================================================
# FONCTIONS DE CHARGEMENT DES DONNÉES
# ============================================================================

def charger_hebergements():
    """
    Charge et nettoie le fichier des hébergements classés
    Retourne un GeoDataFrame avec les hébergements géocodés
    """
    print("\n[DATA] Chargement des hébergements classés...")
    
    # Charger le CSV avec le bon séparateur
    hebergements = pd.read_csv(
        FICHIER_HEBERGEMENTS,
        sep=';',
        encoding='utf-8',
        low_memory=False
    )
    
    print(f"   - {len(hebergements):,} hébergements chargés")
    
    # Nettoyer les colonnes
    hebergements.columns = hebergements.columns.str.strip()
    
    # Extraire les informations clés
    hebergements['type_etablissement'] = hebergements['TYPOLOGIE ÉTABLISSEMENT']
    hebergements['classement'] = hebergements['CLASSEMENT']
    hebergements['code_postal'] = hebergements['CODE POSTAL'].astype(str).str.zfill(5)
    hebergements['commune'] = hebergements['COMMUNE']
    hebergements['adresse_complete'] = (
        hebergements['ADRESSE'].astype(str) + ', ' + 
        hebergements['code_postal'] + ' ' + 
        hebergements['commune']
    )
    
    # Capacité d'accueil (prendre le maximum entre personnes, chambres, emplacements)
    # Convertir en numérique d'abord
    capacite_cols = [
        'CAPACITÉ D\'ACCUEIL (PERSONNES)',
        'NOMBRE DE CHAMBRES',
        'NOMBRE D\'EMPLACEMENTS'
    ]
    for col in capacite_cols:
        if col in hebergements.columns:
            hebergements[col] = pd.to_numeric(hebergements[col], errors='coerce')
    
    hebergements['capacite'] = hebergements[capacite_cols].fillna(0).max(axis=1).astype(int)
    
    # Flags pour types d'établissements
    hebergements['est_hotel'] = hebergements['type_etablissement'].str.contains(
        'HÔTEL', case=False, na=False
    ).astype(int)
    
    hebergements['est_camping'] = hebergements['type_etablissement'].str.contains(
        'CAMPING', case=False, na=False
    ).astype(int)
    
    hebergements['est_residence'] = hebergements['type_etablissement'].str.contains(
        'RÉSIDENCE', case=False, na=False
    ).astype(int)
    
    # Identifier les hôtels 4-5 étoiles (premium pour seniors aisés)
    hebergements['est_premium'] = (
        (hebergements['est_hotel'] == 1) &
        (hebergements['classement'].isin(['4 étoiles', '5 étoiles']))
    ).astype(int)
    
    print(f"   - {hebergements['est_hotel'].sum():,} hôtels")
    print(f"   - {hebergements['est_camping'].sum():,} campings")
    print(f"   - {hebergements['est_premium'].sum():,} hôtels premium (4-5*)")
    print(f"   - {hebergements['capacite'].sum():,} places d'accueil total")
    
    # Géocoder les adresses via l'API BAN
    print("\n[MAP]  Géocodage des hébergements en cours...")
    hebergements_geo = geocoder_hebergements_batch(hebergements)
    
    return hebergements_geo


def geocoder_hebergements_batch(hebergements, batch_size=1000):
    """
    Géocode les hébergements par batch via l'API BAN (Base Adresse Nationale)
    Utilise le CSV batch endpoint pour optimiser les performances
    """
    import requests
    import io
    import time
    
    # Préparer le fichier CSV pour l'API BAN
    csv_data = hebergements[['adresse_complete']].copy()
    csv_data.columns = ['adresse']
    csv_data['id'] = range(len(csv_data))
    
    geometries = []
    
    # Traiter par batch
    total_batches = (len(csv_data) + batch_size - 1) // batch_size
    
    for i in tqdm(range(0, len(csv_data), batch_size), desc="   Géocodage", total=total_batches):
        batch = csv_data.iloc[i:i+batch_size]
        
        # Créer le CSV en mémoire
        csv_buffer = io.StringIO()
        batch.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Appel API BAN avec retry
        success = False
        for attempt in range(3):  # 3 tentatives max
            try:
                response = requests.post(
                    'https://api-adresse.data.gouv.fr/search/csv/',
                    files={'data': ('addresses.csv', csv_content)},
                    data={'columns': 'adresse'},
                    timeout=30
                )

                if response.status_code == 200:
                    result = pd.read_csv(io.StringIO(response.text))

                    # Extraire latitude et longitude
                    for _, row in result.iterrows():
                        if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                            geometries.append(Point(row['longitude'], row['latitude']))
                        else:
                            geometries.append(None)
                    success = True
                    break
                else:
                    if attempt < 2:
                        time.sleep(2)
                    continue

            except Exception as e:
                if attempt < 2:
                    print(f"\n   [WARN] Erreur batch {i} (tentative {attempt+1}/3): {str(e)[:100]}")
                    time.sleep(3)  # Pause plus longue avant retry
                else:
                    print(f"\n   [ERROR] Echec definitif batch {i}: {str(e)[:100]}")

        # Si toutes les tentatives ont échoué
        if not success:
            geometries.extend([None] * len(batch))

        # Pause pour respecter les limites de l'API
        time.sleep(0.5)
    
    # Créer le GeoDataFrame
    hebergements['geometry'] = geometries
    gdf = gpd.GeoDataFrame(
        hebergements[hebergements['geometry'].notna()].copy(),
        geometry='geometry',
        crs='EPSG:4326'
    )
    
    print(f"   OK {len(gdf):,} hébergements géocodés ({len(gdf)/len(hebergements)*100:.1f}%)")
    
    return gdf


def charger_communes_loi_montagne():
    """
    Charge la liste des communes concernées par la loi montagne
    Retourne un set de codes INSEE
    """
    print("\n[MTN]  Chargement des communes loi montagne...")
    
    df = pd.read_excel(
        FICHIER_LOI_MONTAGNE,
        sheet_name='Perimetre',
        skiprows=2
    )
    
    codes_insee = set(df['INSEE_COM'].astype(str))
    print(f"   - {len(codes_insee):,} communes loi montagne")
    
    return codes_insee


def charger_communes_loi_littorale():
    """
    Charge la liste des communes concernées par la loi littoral
    Retourne un DataFrame avec code INSEE et type (Mer, Lac, Estuaire)
    """
    print("\n[SEA] Chargement des communes loi littoral...")
    
    df = pd.read_excel(
        FICHIER_LOI_LITTORALE,
        sheet_name='Perimetre',
        skiprows=2
    )
    
    # Créer un dictionnaire code_insee -> type
    littoral_dict = dict(zip(
        df['INSEE_COM'].astype(str),
        df['CLASSEMENT']
    ))
    
    print(f"   - {len(littoral_dict):,} communes loi littoral")
    print(f"     • Mer: {sum(1 for v in littoral_dict.values() if v == 'Mer')}")
    print(f"     • Lac: {sum(1 for v in littoral_dict.values() if v == 'Lac')}")
    print(f"     • Estuaire: {sum(1 for v in littoral_dict.values() if v == 'Estuaire')}")
    
    return littoral_dict


def charger_pharmacies():
    """
    Charge le fichier des pharmacies
    """
    print("\n[PHARMA] Chargement des pharmacies...")
    
    pharmacies = pd.read_csv(FICHIER_PHARMACIES, encoding='utf-8')
    
    print(f"   - {len(pharmacies):,} pharmacies chargées")
    
    return pharmacies


# ============================================================================
# FONCTIONS DE CALCUL PAR PHARMACIE
# ============================================================================

def charger_isochrone(id_pharmacie, type_isochrone):
    """
    Charge le polygone d'un isochrone pour une pharmacie donnée
    
    Args:
        id_pharmacie: ID de la pharmacie
        type_isochrone: 'drive_10min' ou 'walk_5min'
    
    Returns:
        Polygone Shapely ou None si fichier absent
    """
    fichier_iso = CHEMIN_ISOCHRONES / f"{type_isochrone}" / f"{id_pharmacie}.geojson"
    
    if not fichier_iso.exists():
        return None
    
    try:
        with open(fichier_iso, 'r') as f:
            geojson_data = json.load(f)
        
        # Extraire la géométrie (premier feature)
        if 'features' in geojson_data and len(geojson_data['features']) > 0:
            geometry = shape(geojson_data['features'][0]['geometry'])
            return geometry
        else:
            return None
    
    except Exception:
        return None


def calculer_variables_pharmacie(args):
    """
    Calcule toutes les variables touristiques pour une pharmacie
    Fonction appelée en parallèle

    Args:
        args: tuple (pharmacie_row, hebergements_gdf, spatial_index, communes_montagne, communes_littoral)

    Returns:
        dict avec toutes les variables calculées
    """
    pharmacie, hebergements_gdf, spatial_index, communes_montagne, communes_littoral = args
    
    id_pharmacie = pharmacie['id_pharmacie']
    code_commune = str(pharmacie.get('code_postal', ''))[:5]  # Premiers 5 chiffres du code postal
    
    # Initialiser le résultat
    resultat = {'id_pharmacie': id_pharmacie}
    
    # ========================================================================
    # VARIABLES DE CONTEXTE COMMUNAL (1 seule fois)
    # ========================================================================
    
    # Flag montagne
    resultat['flag_commune_montagne'] = 1 if code_commune in communes_montagne else 0
    
    # Flags littoral
    type_littoral = communes_littoral.get(code_commune, None)
    resultat['flag_commune_littoral'] = 1 if type_littoral is not None else 0
    resultat['flag_commune_littoral_mer'] = 1 if type_littoral == 'Mer' else 0
    resultat['flag_commune_littoral_lac'] = 1 if type_littoral == 'Lac' else 0
    resultat['flag_commune_littoral_estuaire'] = 1 if type_littoral == 'Estuaire' else 0
    
    # Flag mixte (montagne ET littoral)
    resultat['flag_commune_mixte'] = 1 if (resultat['flag_commune_montagne'] == 1 and 
                                            resultat['flag_commune_littoral'] == 1) else 0
    
    # Type de zone touristique (typologie synthétique)
    if resultat['flag_commune_mixte'] == 1:
        resultat['type_zone_touristique'] = 'mixte_montagne_littoral'
    elif resultat['flag_commune_montagne'] == 1:
        resultat['type_zone_touristique'] = 'montagne'
    elif resultat['flag_commune_littoral'] == 1:
        if resultat['flag_commune_littoral_mer'] == 1:
            resultat['type_zone_touristique'] = 'littoral_mer'
        elif resultat['flag_commune_littoral_lac'] == 1:
            resultat['type_zone_touristique'] = 'littoral_lac'
        else:
            resultat['type_zone_touristique'] = 'littoral_estuaire'
    else:
        resultat['type_zone_touristique'] = 'non_touristique'
    
    # ========================================================================
    # VARIABLES PAR ISOCHRONE
    # ========================================================================
    
    for type_iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
        
        # Charger le polygone de l'isochrone
        polygone_iso = charger_isochrone(id_pharmacie, type_iso)
        
        if polygone_iso is None:
            # Isochrone manquant : mettre 0 partout
            resultat[f'nb_hotels_{type_iso}'] = 0
            resultat[f'nb_campings_{type_iso}'] = 0
            resultat[f'nb_residences_{type_iso}'] = 0
            resultat[f'nb_hotels_premium_{type_iso}'] = 0
            resultat[f'capacite_accueil_{type_iso}'] = 0
            resultat[f'nb_total_hebergements_{type_iso}'] = 0
            continue
        
        # Filtrer les hébergements qui intersectent l'isochrone (OPTIMISÉ avec STRtree)
        # Étape 1 : Requête spatiale rapide avec l'index (O(log n))
        potential_indices = list(spatial_index.query(polygone_iso))

        # Étape 2 : Filtrer seulement les candidats (beaucoup moins que 21,060)
        if len(potential_indices) > 0:
            hebergements_candidats = hebergements_gdf.iloc[potential_indices]
            hebergements_dans_iso = hebergements_candidats[
                hebergements_candidats.geometry.intersects(polygone_iso)
            ]
        else:
            hebergements_dans_iso = hebergements_gdf.iloc[0:0]  # DataFrame vide
        
        # Calculer les variables
        resultat[f'nb_hotels_{type_iso}'] = int(hebergements_dans_iso['est_hotel'].sum())
        resultat[f'nb_campings_{type_iso}'] = int(hebergements_dans_iso['est_camping'].sum())
        resultat[f'nb_residences_{type_iso}'] = int(hebergements_dans_iso['est_residence'].sum())
        resultat[f'nb_hotels_premium_{type_iso}'] = int(hebergements_dans_iso['est_premium'].sum())
        resultat[f'capacite_accueil_{type_iso}'] = int(hebergements_dans_iso['capacite'].sum())
        resultat[f'nb_total_hebergements_{type_iso}'] = len(hebergements_dans_iso)
    
    # ========================================================================
    # VARIABLES COMBINÉES (RATIOS)
    # ========================================================================
    
    # Ratio capacité walk / drive (indicateur d'urbanité touristique)
    capa_walk = resultat['capacite_accueil_walk_5min']
    capa_drive = resultat['capacite_accueil_drive_10min']
    
    if capa_drive > 0:
        resultat['ratio_walk_drive_capacite'] = round(capa_walk / capa_drive, 3)
    else:
        resultat['ratio_walk_drive_capacite'] = 0.0
    
    # Densité touristique locale (capacité walk / surface walk)
    # Note: on approxime la surface avec l'aire du polygone
    if resultat['capacite_accueil_walk_5min'] > 0:
        polygone_walk = charger_isochrone(id_pharmacie, 'walk_5min')
        if polygone_walk is not None:
            # Convertir en projection métrique pour calculer l'aire (approximation)
            # On utilise une projection locale française (Lambert-93)
            from shapely.ops import transform
            import pyproj
            
            # Transformer en Lambert-93 (EPSG:2154)
            project = pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:2154', always_xy=True).transform
            polygone_walk_m = transform(project, polygone_walk)
            
            # Aire en km²
            aire_km2 = polygone_walk_m.area / 1_000_000
            
            if aire_km2 > 0:
                resultat['densite_touristique_walk_5'] = round(
                    resultat['capacite_accueil_walk_5min'] / aire_km2, 1
                )
            else:
                resultat['densite_touristique_walk_5'] = 0.0
        else:
            resultat['densite_touristique_walk_5'] = 0.0
    else:
        resultat['densite_touristique_walk_5'] = 0.0
    
    return resultat


# ============================================================================
# TRAITEMENT PRINCIPAL AVEC PARALLÉLISATION
# ============================================================================

def traiter_pharmacies_par_batch(pharmacies, hebergements_gdf, communes_montagne,
                                  communes_littoral, n_workers=8, batch_size=500):
    """
    Traite toutes les pharmacies en parallèle avec affichage de progression

    Args:
        pharmacies: DataFrame des pharmacies
        hebergements_gdf: GeoDataFrame des hébergements
        communes_montagne: set des codes INSEE montagne
        communes_littoral: dict des codes INSEE littoral -> type
        n_workers: nombre de processus parallèles
        batch_size: taille des batchs

    Returns:
        DataFrame avec toutes les variables calculées
    """
    print(f"\n[START] Traitement parallele avec {n_workers} workers (batch size: {batch_size})...")

    # OPTIMISATION : Créer l'index spatial STRtree une seule fois
    print(f"[OPTIM] Construction index spatial STRtree pour {len(hebergements_gdf):,} hebergements...")
    temps_index_debut = time.time()
    spatial_index = STRtree(hebergements_gdf.geometry)
    temps_index = time.time() - temps_index_debut
    print(f"[OPTIM] Index spatial cree en {temps_index:.1f}s - Gain attendu: 10-50x sur les requetes spatiales")

    # Préparer les arguments pour chaque pharmacie
    args_list = [
        (row, hebergements_gdf, spatial_index, communes_montagne, communes_littoral)
        for _, row in pharmacies.iterrows()
    ]
    
    resultats = []

    # Fichier checkpoint
    fichier_checkpoint = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'output',
        'checkpoint_variables_touristiques.csv'
    )

    # Traiter par batch avec ProcessPoolExecutor
    total_pharmacies = len(args_list)
    compteur = 0
    temps_debut = time.time()

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Soumettre tous les jobs
        futures = [
            executor.submit(calculer_variables_pharmacie, args)
            for args in args_list
        ]

        # Collecter les résultats avec barre de progression
        for future in tqdm(as_completed(futures), total=total_pharmacies, desc="   Calcul"):
            try:
                resultat = future.result()
                resultats.append(resultat)
                compteur += 1

                # Checkpoint tous les 1000 pharmacies
                if compteur % 1000 == 0:
                    df_checkpoint = pd.DataFrame(resultats)
                    df_checkpoint.to_csv(fichier_checkpoint, index=False)

                    temps_ecoule = time.time() - temps_debut
                    vitesse = compteur / (temps_ecoule / 60)  # pharmacies par minute
                    temps_restant = (total_pharmacies - compteur) / vitesse if vitesse > 0 else 0

                    print(f"\n   [SAVE] Checkpoint : {compteur:,}/{total_pharmacies:,} pharmacies ({compteur/total_pharmacies*100:.1f}%)")
                    print(f"   Vitesse : {vitesse:.1f} pharm/min - Temps restant : {temps_restant:.1f} min (~{temps_restant/60:.1f}h)")

            except Exception as e:
                print(f"\n   [WARN] Erreur: {e}")
    
    # Convertir en DataFrame
    df_resultats = pd.DataFrame(resultats)
    
    # Réordonner les colonnes de manière logique
    colonnes_ordre = ['id_pharmacie']

    # Variables de contexte communal
    colonnes_ordre.extend([
        'flag_commune_montagne',
        'flag_commune_littoral',
        'flag_commune_littoral_mer',
        'flag_commune_littoral_lac',
        'flag_commune_littoral_estuaire',
        'flag_commune_mixte',
        'type_zone_touristique'
    ])

    # Variables pour chaque isochrone (6 isochrones)
    for iso in ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']:
        colonnes_ordre.extend([
            f'nb_hotels_{iso}',
            f'nb_campings_{iso}',
            f'nb_residences_{iso}',
            f'nb_hotels_premium_{iso}',
            f'capacite_accueil_{iso}',
            f'nb_total_hebergements_{iso}'
        ])

    # Variables combinées
    colonnes_ordre.extend([
        'ratio_walk_drive_capacite',
        'densite_touristique_walk_5'
    ])

    # Garder seulement les colonnes qui existent
    colonnes_existantes = [col for col in colonnes_ordre if col in df_resultats.columns]
    df_resultats = df_resultats[colonnes_existantes]
    
    print(f"\nOK {len(df_resultats):,} pharmacies traitées avec succès")
    
    return df_resultats


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """
    Fonction principale d'exécution du script
    """
    print("=" * 80)
    print("CALCUL DES VARIABLES TOURISTIQUES POUR LES PHARMACIES")
    print("=" * 80)
    
    # Créer le dossier de sortie si nécessaire
    CHEMIN_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # CHARGEMENT DES DONNÉES
    # ========================================================================
    
    # Charger les pharmacies
    pharmacies = charger_pharmacies()
    
    # Charger les hébergements (avec géocodage)
    hebergements_gdf = charger_hebergements()
    
    # Charger les communes loi montagne et littoral
    communes_montagne = charger_communes_loi_montagne()
    communes_littoral = charger_communes_loi_littorale()
    
    # ========================================================================
    # TRAITEMENT
    # ========================================================================
    
    # Calculer les variables pour toutes les pharmacies
    df_variables = traiter_pharmacies_par_batch(
        pharmacies,
        hebergements_gdf,
        communes_montagne,
        communes_littoral,
        n_workers=N_WORKERS,
        batch_size=BATCH_SIZE
    )
    
    # ========================================================================
    # EXPORT
    # ========================================================================
    
    print(f"\n[SAVE] Export des résultats...")
    df_variables.to_csv(FICHIER_OUTPUT, index=False, encoding='utf-8')
    print(f"   OK Fichier sauvegardé : {FICHIER_OUTPUT}")
    
    # ========================================================================
    # STATISTIQUES DESCRIPTIVES
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("STATISTIQUES DESCRIPTIVES")
    print("=" * 80)
    
    print("\n[STATS] Contexte communal:")
    print(f"   - Pharmacies en zone montagne : {df_variables['flag_commune_montagne'].sum():,}")
    print(f"   - Pharmacies en zone littoral : {df_variables['flag_commune_littoral'].sum():,}")
    print(f"   - Pharmacies en zone mixte : {df_variables['flag_commune_mixte'].sum():,}")
    
    print("\n[STATS] Typologie touristique:")
    print(df_variables['type_zone_touristique'].value_counts())
    
    print("\n[STATS] Hébergements dans walk_5min:")
    print(f"   - Moyenne hôtels : {df_variables['nb_hotels_walk_5min'].mean():.1f}")
    print(f"   - Moyenne campings : {df_variables['nb_campings_walk_5min'].mean():.1f}")
    print(f"   - Moyenne capacité : {df_variables['capacite_accueil_walk_5min'].mean():.0f} places")
    
    print("\n[STATS] Hébergements dans drive_10min:")
    print(f"   - Moyenne hôtels : {df_variables['nb_hotels_drive_10min'].mean():.1f}")
    print(f"   - Moyenne campings : {df_variables['nb_campings_drive_10min'].mean():.1f}")
    print(f"   - Moyenne capacité : {df_variables['capacite_accueil_drive_10min'].mean():.0f} places")
    
    print("\n[STATS] Ratios:")
    print(f"   - Ratio walk/drive moyen : {df_variables['ratio_walk_drive_capacite'].mean():.3f}")
    print(f"   - Densité touristique walk_5 moyenne : {df_variables['densite_touristique_walk_5'].mean():.1f} places/km²")
    
    print("\n" + "=" * 80)
    print("OK TRAITEMENT TERMINÉ AVEC SUCCÈS")
    print("=" * 80)


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == '__main__':
    main()
