"""
Script pour recalculer correctement les w_IRIS à partir des isochrones

OBJECTIF:
- Recalculer les w_IRIS comme la proportion d'IRIS couverte par l'isochrone
- Méthode: intersection géométrique (surface isochrone ∩ IRIS) / surface IRIS
- Sauvegardes régulières toutes les 1000 pharmacies

ENTRÉES:
- isochrones/*.geojson (115,767 fichiers)
- contours_iris.gpkg (polygones IRIS)
- pharmacies_final.csv (liste pharmacies)

SORTIE:
- matrice_w_iris.csv (matrice avec w_IRIS calculés)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union
import sys
import time
from datetime import datetime, timedelta

# Force unbuffered output (pour voir les prints immédiatement)
import functools
print = functools.partial(print, flush=True)

# Ajouter config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_prep import INPUT_FILES, OUTPUT_FILES, PROJECT_ROOT

print("="*80)
print("RECALCUL CORRECT DES w_IRIS À PARTIR DES ISOCHRONES")
print("="*80)
print(f"Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Chemins
ISOCHRONES_DIR = OUTPUT_FILES['isochrones_dir']
CONTOURS_FILE = INPUT_FILES['contours_iris_gpkg']
OUTPUT_DIR = OUTPUT_FILES['matrice_w_iris'].parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# Checkpoint directory (cache)
CHECKPOINT_DIR = OUTPUT_DIR.parent / 'cache' / 'checkpoints_w_iris'
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Charger les contours IRIS
print("\n1. CHARGEMENT CONTOURS IRIS")
gdf_iris = gpd.read_file(CONTOURS_FILE)

# Identifier colonne CODE_IRIS
if 'code_iris' in gdf_iris.columns:
    gdf_iris = gdf_iris.rename(columns={'code_iris': 'CODE_IRIS'})
elif 'CODE_IRIS' not in gdf_iris.columns:
    print(f"   ERREUR: Colonne CODE_IRIS non trouvée")
    sys.exit(1)

gdf_iris['CODE_IRIS'] = gdf_iris['CODE_IRIS'].astype(str)

# Calculer surfaces IRIS (en m²)
if gdf_iris.crs is None or gdf_iris.crs.to_epsg() != 2154:
    print(f"   Reprojection en Lambert 93...")
    gdf_iris = gdf_iris.to_crs(epsg=2154)

gdf_iris['surface_iris_m2'] = gdf_iris.geometry.area

print(f"   IRIS chargés          : {len(gdf_iris):,}")
print(f"   Surface min           : {gdf_iris['surface_iris_m2'].min()/1e6:.2f} km²")
print(f"   Surface max           : {gdf_iris['surface_iris_m2'].max()/1e6:.2f} km²")
print(f"   Surface médiane       : {gdf_iris['surface_iris_m2'].median()/1e6:.2f} km²")

# Créer un index spatial pour accélérer les recherches
gdf_iris_sindex = gdf_iris.sindex

# 2. Charger pharmacies
print("\n2. CHARGEMENT PHARMACIES")
df_pharma = pd.read_csv(INPUT_FILES['pharmacies'], sep=';')
print(f"   Pharmacies totales    : {len(df_pharma):,}")

# 3. Types d'isochrones à traiter
ISOCHRONE_TYPES = ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']

# Priorité: utiliser le plus grand isochrone disponible pour chaque pharmacie
ISOCHRONE_PRIORITY = ['drive_20min', 'drive_15min', 'drive_10min', 'drive_5min', 'walk_10min', 'walk_5min']

print(f"\n3. TYPES D'ISOCHRONES")
for iso_type in ISOCHRONE_TYPES:
    iso_dir = ISOCHRONES_DIR / iso_type
    if iso_dir.exists():
        n_files = len(list(iso_dir.glob("*.geojson")))
        print(f"   {iso_type:15s} : {n_files:,} fichiers")

# 4. Vérifier checkpoint existant
print("\n4. VÉRIFICATION CHECKPOINT")
checkpoint_file = CHECKPOINT_DIR / "checkpoint_latest.csv"
checkpoint_meta = CHECKPOINT_DIR / "checkpoint_meta.txt"

start_idx = 0
relations_accumulees = []

if checkpoint_file.exists():
    print(f"   Checkpoint trouvé     : {checkpoint_file}")
    df_checkpoint = pd.read_csv(checkpoint_file)
    relations_accumulees = df_checkpoint.to_dict('records')

    # Lire métadonnées
    if checkpoint_meta.exists():
        with open(checkpoint_meta, 'r') as f:
            meta = f.read()
            print(f"   {meta}")

    # Continuer à partir de la dernière pharmacie
    pharma_traitees = set(df_checkpoint['id_pharmacie'].unique())
    start_idx = sum(1 for p in df_pharma['id_pharmacie'] if p in pharma_traitees)

    print(f"   Pharmacies déjà OK    : {start_idx:,}")
    print(f"   Relations existantes  : {len(relations_accumulees):,}")
    print(f"   Continuation automatique depuis checkpoint...")

# 5. Traitement des pharmacies
print("\n5. TRAITEMENT DES PHARMACIES")
print(f"   Début à l'index       : {start_idx:,}")
print(f"   Pharmacies restantes  : {len(df_pharma) - start_idx:,}")

# Estimation temps
temps_debut = time.time()
SAVE_INTERVAL = 1000  # Sauvegarder tous les 1000 pharmacies

pharmacies_traitees = 0
pharmacies_avec_isochrone = 0
pharmacies_sans_isochrone = 0

for idx in range(start_idx, len(df_pharma)):
    pharma = df_pharma.iloc[idx]
    id_pharma = pharma['id_pharmacie']

    # Trouver l'isochrone (priorité: plus grand d'abord)
    isochrone_path = None
    iso_type_trouve = None

    for iso_type in ISOCHRONE_PRIORITY:
        iso_dir = ISOCHRONES_DIR / iso_type
        potential_path = iso_dir / f"{id_pharma}.geojson"

        if potential_path.exists():
            isochrone_path = potential_path
            iso_type_trouve = iso_type
            break

    if isochrone_path is None:
        pharmacies_sans_isochrone += 1
        # Pas d'isochrone = pas de relation
        continue

    pharmacies_avec_isochrone += 1

    # Charger isochrone
    try:
        gdf_iso = gpd.read_file(isochrone_path)

        # Reprojeter en Lambert 93 si besoin
        if gdf_iso.crs is None or gdf_iso.crs.to_epsg() != 2154:
            gdf_iso = gdf_iso.to_crs(epsg=2154)

        # Union de toutes les géométries (au cas où plusieurs polygones)
        iso_geom = unary_union(gdf_iso.geometry)

        # Trouver les IRIS qui intersectent l'isochrone (via index spatial)
        possible_matches_idx = list(gdf_iris_sindex.intersection(iso_geom.bounds))
        possible_matches = gdf_iris.iloc[possible_matches_idx]

        # OPTIMISATION 1: Préparer l'isochrone une seule fois
        iso_prepared = iso_geom.buffer(0)  # Fix topology errors

        # OPTIMISATION 2: Extraire colonnes en arrays numpy (éviter row access)
        iris_geoms = possible_matches.geometry.values
        iris_codes = possible_matches['CODE_IRIS'].values
        iris_surfaces = possible_matches['surface_iris_m2'].values

        # OPTIMISATION 3: Vectoriser les calculs d'intersection
        iso_bounds = iso_prepared.bounds  # (minx, miny, maxx, maxy)

        for i in range(len(possible_matches)):
            iris_geom = iris_geoms[i]
            iris_bounds = iris_geom.bounds

            # Test rapide d'intersection via bounds (plus rapide que .intersects())
            # Deux rectangles se chevauchent si:
            # iso.maxx >= iris.minx AND iso.minx <= iris.maxx AND
            # iso.maxy >= iris.miny AND iso.miny <= iris.maxy
            if not (iso_bounds[2] >= iris_bounds[0] and iso_bounds[0] <= iris_bounds[2] and
                    iso_bounds[3] >= iris_bounds[1] and iso_bounds[1] <= iris_bounds[3]):
                continue

            # Intersection réelle seulement si bounds se chevauchent
            try:
                intersection = iso_prepared.intersection(iris_geom)
            except:
                continue

            if intersection.is_empty:
                continue

            # Calculer w_IRIS = surface_intersection / surface_IRIS
            surface_intersection = intersection.area
            surface_iris = iris_surfaces[i]

            if surface_iris == 0:
                continue

            w_iris = surface_intersection / surface_iris

            # Clip à [0, 1] (parfois légèrement > 1 à cause d'erreurs numériques)
            w_iris = min(1.0, max(0.0, w_iris))

            # Seuil minimal pour éviter les relations négligeables
            if w_iris < 0.001:
                continue

            relations_accumulees.append({
                'id_pharmacie': id_pharma,
                'CODE_IRIS': iris_codes[i],
                'w_IRIS': w_iris,
                'source': f'isochrone_{iso_type_trouve}',
                'surface_intersection_m2': surface_intersection,
                'surface_iris_m2': surface_iris
            })

    except Exception as e:
        print(f"\n   ERREUR pharmacie {id_pharma}: {e}")
        continue

    pharmacies_traitees += 1

    # Affichage progression + estimation temps
    if pharmacies_traitees % 100 == 0:
        temps_ecoule = time.time() - temps_debut
        temps_par_pharma = temps_ecoule / pharmacies_traitees
        pharmacies_restantes = len(df_pharma) - (start_idx + pharmacies_traitees)
        temps_restant_sec = temps_par_pharma * pharmacies_restantes

        temps_restant = timedelta(seconds=int(temps_restant_sec))

        print(f"\n   [{datetime.now().strftime('%H:%M:%S')}] Progression:")
        print(f"      Traitées            : {start_idx + pharmacies_traitees:,} / {len(df_pharma):,} ({100*(start_idx + pharmacies_traitees)/len(df_pharma):.1f}%)")
        print(f"      Avec isochrone      : {pharmacies_avec_isochrone:,}")
        print(f"      Sans isochrone      : {pharmacies_sans_isochrone:,}")
        print(f"      Relations créées    : {len(relations_accumulees):,}")
        print(f"      Temps par pharmacie : {temps_par_pharma:.2f}s")
        print(f"      Temps restant estimé: {temps_restant}")

    # Sauvegarde checkpoint
    if pharmacies_traitees % SAVE_INTERVAL == 0:
        print(f"\n   SAUVEGARDE CHECKPOINT a {pharmacies_traitees:,} pharmacies...")

        df_temp = pd.DataFrame(relations_accumulees)
        df_temp.to_csv(checkpoint_file, index=False)

        # Métadonnées
        with open(checkpoint_meta, 'w') as f:
            f.write(f"Checkpoint: {start_idx + pharmacies_traitees:,} / {len(df_pharma):,} pharmacies\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Relations: {len(relations_accumulees):,}\n")
            f.write(f"Pharmacies avec isochrone: {pharmacies_avec_isochrone:,}\n")

        print(f"   Checkpoint sauvegarde : {checkpoint_file}")
        print(f"   Taille: {checkpoint_file.stat().st_size / 1024 / 1024:.1f} MB")

# 6. Sauvegarde finale
print("\n6. SAUVEGARDE FINALE")

df_final = pd.DataFrame(relations_accumulees)

print(f"   Relations totales     : {len(df_final):,}")
print(f"   Pharmacies uniques    : {df_final['id_pharmacie'].nunique():,}")
print(f"   IRIS uniques          : {df_final['CODE_IRIS'].nunique():,}")
print(f"\n   Statistiques w_IRIS:")
print(f"      Moyenne             : {df_final['w_IRIS'].mean():.3f}")
print(f"      Médiane             : {df_final['w_IRIS'].median():.3f}")
print(f"      w_IRIS = 1.0        : {(df_final['w_IRIS'] == 1.0).sum():,} ({100*(df_final['w_IRIS'] == 1.0).sum()/len(df_final):.1f}%)")
print(f"      w_IRIS > 0.8        : {(df_final['w_IRIS'] > 0.8).sum():,} ({100*(df_final['w_IRIS'] > 0.8).sum()/len(df_final):.1f}%)")
print(f"      w_IRIS > 0.5        : {(df_final['w_IRIS'] > 0.5).sum():,} ({100*(df_final['w_IRIS'] > 0.5).sum()/len(df_final):.1f}%)")

# Sauvegarder
output_path = OUTPUT_FILES['matrice_w_iris']
df_final_save = df_final[['id_pharmacie', 'CODE_IRIS', 'w_IRIS', 'source']].copy()
df_final_save.to_csv(output_path, index=False)

print(f"\n   Fichier sauvegardé    : {output_path}")
print(f"   Taille                : {output_path.stat().st_size / 1024 / 1024:.1f} MB")

# Comparaison avec ancienne matrice (si elle existe)
print("\n7. COMPARAISON AVEC ANCIENNE MATRICE")
old_matrix_path = OUTPUT_FILES['matrice_w_iris']
if old_matrix_path.exists():
    df_old = pd.read_csv(old_matrix_path)
else:
    print("   Pas d'ancienne matrice à comparer")
    df_old = None

if df_old is not None:
    print(f"   Ancienne matrice:")
    print(f"      Relations           : {len(df_old):,}")
    print(f"      w_IRIS moyen        : {df_old['w_IRIS'].mean():.3f}")
    print(f"      w_IRIS = 1.0        : {(df_old['w_IRIS'] == 1.0).sum():,} ({100*(df_old['w_IRIS'] == 1.0).sum()/len(df_old):.1f}%)")
    print(f"\n   Nouvelle matrice:")
    print(f"      Relations           : {len(df_final):,}")
    print(f"      w_IRIS moyen        : {df_final['w_IRIS'].mean():.3f}")
    print(f"      w_IRIS = 1.0        : {(df_final['w_IRIS'] == 1.0).sum():,} ({100*(df_final['w_IRIS'] == 1.0).sum()/len(df_final):.1f}%)")

# Temps total
temps_total = time.time() - temps_debut
print(f"\n8. TEMPS D'EXÉCUTION")
print(f"   Temps total           : {timedelta(seconds=int(temps_total))}")
print(f"   Temps par pharmacie   : {temps_total/(pharmacies_traitees or 1):.2f}s")

print("\n" + "="*80)
print("OK RECALCUL TERMINÉ")
print("="*80)
print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nFichier créé : {output_path}")
print(f"Ce fichier est référencé dans config_ml.py et utilisé par ml_06")