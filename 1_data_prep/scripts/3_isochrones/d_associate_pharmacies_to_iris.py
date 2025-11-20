"""
Script pour associer les pharmacies sans clients aux IRIS via géolocalisation

OBJECTIF:
- Associer les 1,099 pharmacies sans clients (clients_65_plus_total = 0) à leurs IRIS
- Méthode: intersection spatiale via coordonnées GPS (latitude/longitude)
- Créer des relations pharmacie-IRIS avec w_IRIS = 1.0 (couverture totale IRIS de la pharmacie)

ENTRÉES:
- pharmacies_final.csv (coordonnées GPS)
- pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv (pour identifier pharmacies sans clients)
- contours_iris.gpkg (polygones IRIS)
- matrice_w_iris.csv (matrice existante)

SORTIE:
- matrice_w_iris_enriched.csv (matrice enrichie avec nouvelles associations)
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
import sys

# Ajouter config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_prep import INPUT_FILES, OUTPUT_FILES, PROJECT_ROOT

# Pour accéder aux résultats Phase 2 (clients estimés)
sys.path.insert(0, str(PROJECT_ROOT / "2_pipeline_ml/scripts"))
from config_ml import OUTPUT_FILES as ML_OUTPUT_FILES

print("="*80)
print("ASSOCIATION PHARMACIES -> IRIS PAR GÉOLOCALISATION")
print("="*80)

# 1. Charger pharmacies
print("\n1. CHARGEMENT DES PHARMACIES")
df_pharma = pd.read_csv(INPUT_FILES['pharmacies'], sep=';')
print(f"   Pharmacies totales    : {len(df_pharma):,}")

# Charger clients pour identifier pharmacies sans clients
df_clients = pd.read_csv(OUTPUT_FILES['pharmacies_clients_65plus_huff'])
pharma_sans_clients = df_clients[df_clients['clients_65_plus_total'] == 0]['id_pharmacie']
df_sans_clients = df_pharma[df_pharma['id_pharmacie'].isin(pharma_sans_clients)].copy()

print(f"   Pharmacies sans clients: {len(df_sans_clients):,}")
print(f"   Avec coordonnées      : {df_sans_clients[['latitude', 'longitude']].notna().all(axis=1).sum():,}")

# 2. Charger contours IRIS
print("\n2. CHARGEMENT CONTOURS IRIS")
contours_file = PROJECT_ROOT / "1_data_prep/input/1_sources_brutes/contours_iris.gpkg"

if not contours_file.exists():
    print(f"   ERREUR: Fichier non trouvé: {contours_file}")
    sys.exit(1)

gdf_iris = gpd.read_file(contours_file)
print(f"   IRIS chargés          : {len(gdf_iris):,}")
print(f"   CRS                   : {gdf_iris.crs}")

# Vérifier colonne CODE_IRIS
if 'CODE_IRIS' not in gdf_iris.columns:
    # Chercher colonne contenant 'IRIS' ou 'CODE'
    iris_col = [col for col in gdf_iris.columns if 'IRIS' in col.upper() or 'CODE' in col.upper()]
    if iris_col:
        print(f"   Colonnes disponibles  : {list(gdf_iris.columns)}")
        print(f"   Utilisation colonne   : {iris_col[0]}")
        gdf_iris = gdf_iris.rename(columns={iris_col[0]: 'CODE_IRIS'})
    else:
        print(f"   ERREUR: Pas de colonne CODE_IRIS trouvée")
        print(f"   Colonnes disponibles  : {list(gdf_iris.columns)}")
        sys.exit(1)

# 3. Créer GeoDataFrame des pharmacies
print("\n3. CRÉATION GEODATAFRAME PHARMACIES")

# Filter pharmacies avec coordonnées valides
df_sans_clients_valid = df_sans_clients.dropna(subset=['latitude', 'longitude'])
print(f"   Pharmacies valides    : {len(df_sans_clients_valid):,}")

# Créer points géométriques
geometry = [Point(lon, lat) for lon, lat in zip(df_sans_clients_valid['longitude'],
                                                  df_sans_clients_valid['latitude'])]
gdf_pharma = gpd.GeoDataFrame(
    df_sans_clients_valid,
    geometry=geometry,
    crs="EPSG:4326"  # WGS84
)

# Reprojeter en Lambert 93 (même que IRIS)
if gdf_iris.crs.to_epsg() != 4326:
    print(f"   Reprojection pharma   : WGS84 -> {gdf_iris.crs}")
    gdf_pharma = gdf_pharma.to_crs(gdf_iris.crs)

# 4. Intersection spatiale (spatial join)
print("\n4. INTERSECTION SPATIALE")
print(f"   Recherche IRIS pour {len(gdf_pharma):,} pharmacies...")

# Spatial join: pour chaque pharmacie, trouver l'IRIS qui la contient
gdf_joined = gpd.sjoin(
    gdf_pharma,
    gdf_iris[['CODE_IRIS', 'geometry']],
    how='left',
    predicate='within'
)

# Compter résultats
pharmacies_matchees = gdf_joined['CODE_IRIS'].notna().sum()
pharmacies_non_matchees = gdf_joined['CODE_IRIS'].isna().sum()

print(f"   Pharmacies matchées   : {pharmacies_matchees:,} ({100*pharmacies_matchees/len(gdf_joined):.1f}%)")
print(f"   Pharmacies non matchées: {pharmacies_non_matchees:,}")

# 5. Créer nouvelles relations pharmacie-IRIS
print("\n5. CRÉATION NOUVELLES RELATIONS")

# Préparer nouvelles lignes pour la matrice
nouvelles_relations = []

for idx, row in gdf_joined.iterrows():
    if pd.notna(row['CODE_IRIS']):
        nouvelles_relations.append({
            'id_pharmacie': row['id_pharmacie'],
            'CODE_IRIS': row['CODE_IRIS'],
            'w_IRIS': 1.0,  # Pondération totale (100% de l'IRIS accessible)
            'source': 'geoloc'
        })

df_nouvelles = pd.DataFrame(nouvelles_relations)
print(f"   Nouvelles relations   : {len(df_nouvelles):,}")

# Vérifier unicité (1 pharmacie = 1 IRIS)
duplicates = df_nouvelles.groupby('id_pharmacie').size()
if (duplicates > 1).any():
    print(f"   ATTENTION: {(duplicates > 1).sum()} pharmacies avec plusieurs IRIS")
    # Garder seulement la première relation par pharmacie
    df_nouvelles = df_nouvelles.drop_duplicates(subset='id_pharmacie', keep='first')
    print(f"   Après dédoublonnage   : {len(df_nouvelles):,}")

# 6. Charger matrice existante et fusionner
print("\n6. FUSION AVEC MATRICE EXISTANTE")

matrice_file = OUTPUT_FILES['matrice_w_iris']
df_matrice = pd.read_csv(matrice_file)
print(f"   Matrice existante     : {len(df_matrice):,} relations")
print(f"   Pharmacies existantes : {df_matrice['id_pharmacie'].nunique():,}")

# Vérifier que les nouvelles pharmacies ne sont pas déjà dans la matrice
pharma_existantes = set(df_matrice['id_pharmacie'])
pharma_nouvelles = set(df_nouvelles['id_pharmacie'])
pharma_deja_presentes = pharma_existantes & pharma_nouvelles

if len(pharma_deja_presentes) > 0:
    print(f"   ATTENTION: {len(pharma_deja_presentes)} pharmacies déjà présentes dans matrice")
    print(f"   Elles seront IGNORÉES (pas de remplacement)")
    df_nouvelles = df_nouvelles[~df_nouvelles['id_pharmacie'].isin(pharma_deja_presentes)]
    print(f"   Relations à ajouter   : {len(df_nouvelles):,}")

# Ajouter colonne source à matrice existante
if 'source' not in df_matrice.columns:
    df_matrice['source'] = 'isochrones'

# Fusionner
df_matrice_enriched = pd.concat([df_matrice, df_nouvelles[['id_pharmacie', 'CODE_IRIS', 'w_IRIS', 'source']]],
                                  ignore_index=True)

print(f"   Matrice enrichie      : {len(df_matrice_enriched):,} relations")
print(f"   Pharmacies totales    : {df_matrice_enriched['id_pharmacie'].nunique():,}")
print(f"   Nouvelles pharmacies  : {df_matrice_enriched['id_pharmacie'].nunique() - df_matrice['id_pharmacie'].nunique():,}")

# 7. Sauvegarder
print("\n7. SAUVEGARDE")

output_path = OUTPUT_FILES['matrice_w_iris_enriched']
df_matrice_enriched.to_csv(output_path, index=False)

print(f"   Fichier sauvegardé    : {output_path}")
print(f"   Taille                : {output_path.stat().st_size / 1024 / 1024:.1f} MB")

# Statistiques par source
print(f"\n   Répartition par source:")
print(df_matrice_enriched['source'].value_counts())

# 8. Rapport détaillé
print("\n8. RAPPORT DÉTAILLÉ")

# Pharmacies sans clients qui ont été matchées
pharma_matchees = set(df_nouvelles['id_pharmacie'])
taux_matching = 100 * len(pharma_matchees) / len(pharma_sans_clients)

print(f"   Pharmacies sans clients initiales : {len(pharma_sans_clients):,}")
print(f"   Pharmacies matchées géoloc        : {len(pharma_matchees):,}")
print(f"   Taux de matching                  : {taux_matching:.1f}%")
print(f"   Pharmacies restant sans IRIS      : {len(pharma_sans_clients) - len(pharma_matchees):,}")

# Exemples de pharmacies non matchées
pharma_non_matchees = pharma_sans_clients[~pharma_sans_clients.isin(pharma_matchees)]
if len(pharma_non_matchees) > 0:
    df_non_matchees = df_pharma[df_pharma['id_pharmacie'].isin(pharma_non_matchees)]
    print(f"\n   Exemples pharmacies non matchées (10 premiers):")
    print(df_non_matchees[['id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude']].head(10))

print("\n" + "="*80)
print("OK ASSOCIATION TERMINÉE")
print("="*80)
print(f"\nProchaine étape: Utiliser la matrice enrichie dans le script e")
print(f"   Fichier créé : {output_path}")
print(f"   Lancer script e : python e_associate_uncovered_iris.py")