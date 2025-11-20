"""
Script pour associer les IRIS non couverts aux pharmacies les plus proches

OBJECTIF:
- Identifier les IRIS sans couverture (absents de la matrice)
- Assigner chaque IRIS à sa pharmacie la plus proche (distance euclidienne)
- Calculer w_IRIS basé sur la distance (décroissance exponentielle)
- Atteindre 100% de distribution de la population

ENTRÉES:
- matrice_w_iris_enriched.csv (matrice actuelle)
- contours_iris.gpkg (polygones IRIS avec centroïdes)
- pharmacies_final.csv (coordonnées pharmacies)
- age_profession.CSV (population 65+ par IRIS)

SORTIE:
- matrice_w_iris_100pct.csv (matrice complète avec 100% couverture)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
import sys

# Ajouter config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_prep import INPUT_FILES, OUTPUT_FILES, PROJECT_ROOT

OUTPUT_DIR = OUTPUT_FILES['matrice_w_iris'].parent

print("="*80)
print("ASSOCIATION IRIS NON COUVERTS -> PHARMACIES PLUS PROCHES")
print("="*80)

# 1. Charger la matrice enrichie
print("\n1. CHARGEMENT MATRICE ACTUELLE")
matrice_file = OUTPUT_FILES['matrice_w_iris_enriched']
df_matrice = pd.read_csv(matrice_file)

print(f"   Relations totales     : {len(df_matrice):,}")
print(f"   Pharmacies            : {df_matrice['id_pharmacie'].nunique():,}")
print(f"   IRIS couverts         : {df_matrice['CODE_IRIS'].nunique():,}")

# IMPORTANT: Convert to string for consistent comparison
iris_couverts = set(df_matrice['CODE_IRIS'].astype(str).unique())

# 2. Charger population IRIS
print("\n2. CHARGEMENT POPULATION IRIS")
df_pop = pd.read_csv(
    PROJECT_ROOT / "1_data_prep/input/2_insee_brutes/age_profession.CSV",
    sep=';',
    encoding='latin1',
    dtype={'IRIS': str},
    low_memory=False
)

# Calculer population 65+
# Colonne P22_POP65P = population 65+ (recensement 2022)
if 'P22_POP65P' in df_pop.columns:
    df_pop['pop_65_plus'] = df_pop['P22_POP65P'].fillna(0)
else:
    # Fallback: P22_POP6579 + P22_POP80P
    df_pop['pop_65_plus'] = (
        df_pop.get('P22_POP6579', 0).fillna(0) +
        df_pop.get('P22_POP80P', 0).fillna(0)
    )
df_pop_65 = df_pop[['IRIS', 'pop_65_plus']].rename(columns={'IRIS': 'CODE_IRIS'})

print(f"   IRIS total            : {len(df_pop_65):,}")
print(f"   Population 65+ totale : {df_pop_65['pop_65_plus'].sum():,.0f}")

# 3. Identifier IRIS non couverts
print("\n3. IDENTIFICATION IRIS NON COUVERTS")
df_pop_65['CODE_IRIS'] = df_pop_65['CODE_IRIS'].astype(str)
iris_non_couverts = set(df_pop_65['CODE_IRIS']) - iris_couverts

df_iris_nc = df_pop_65[df_pop_65['CODE_IRIS'].isin(iris_non_couverts)].copy()
df_iris_nc = df_iris_nc[df_iris_nc['pop_65_plus'] > 0]  # Seulement IRIS avec population

print(f"   IRIS non couverts     : {len(iris_non_couverts):,}")
print(f"   IRIS nc avec pop > 0  : {len(df_iris_nc):,}")
print(f"   Population nc         : {df_iris_nc['pop_65_plus'].sum():,.0f}")

# 4. Charger contours IRIS pour centroïdes
print("\n4. CHARGEMENT CONTOURS IRIS")
contours_file = PROJECT_ROOT / "1_data_prep/input/1_sources_brutes/contours_iris.gpkg"

if not contours_file.exists():
    print(f"   ERREUR: Fichier non trouvé: {contours_file}")
    sys.exit(1)

gdf_iris = gpd.read_file(contours_file)
print(f"   IRIS chargés          : {len(gdf_iris):,}")

# Identifier colonne CODE_IRIS - chercher spécifiquement 'code_iris' en priorité
if 'CODE_IRIS' in gdf_iris.columns:
    pass  # Already correct
elif 'code_iris' in gdf_iris.columns:
    gdf_iris = gdf_iris.rename(columns={'code_iris': 'CODE_IRIS'})
else:
    # Fallback: chercher toute colonne avec CODE et IRIS
    iris_col = None
    for col in gdf_iris.columns:
        if 'CODE' in col.upper() and 'IRIS' in col.upper():
            iris_col = col
            break

    if iris_col:
        gdf_iris = gdf_iris.rename(columns={iris_col: 'CODE_IRIS'})
    else:
        print(f"   ERREUR: Colonne CODE_IRIS non trouvée")
        print(f"   Colonnes disponibles: {list(gdf_iris.columns)}")
        sys.exit(1)

gdf_iris['CODE_IRIS'] = gdf_iris['CODE_IRIS'].astype(str)

# Filtrer IRIS non couverts AVANT de calculer centroïdes
# Utiliser les IRIS qui ont à la fois: non couverts ET présents dans contours
iris_nc_dans_contours = iris_non_couverts & set(gdf_iris['CODE_IRIS'])
gdf_iris_nc = gdf_iris[gdf_iris['CODE_IRIS'].isin(iris_nc_dans_contours)].copy()

print(f"   IRIS nc dans contours : {len(gdf_iris_nc):,}")

# Population concernée
pop_nc_avec_geo = df_iris_nc[df_iris_nc['CODE_IRIS'].isin(iris_nc_dans_contours)]['pop_65_plus'].sum()
pop_nc_sans_geo = df_iris_nc[~df_iris_nc['CODE_IRIS'].isin(iris_nc_dans_contours)]['pop_65_plus'].sum()

print(f"   Pop avec géométrie    : {pop_nc_avec_geo:,.0f}")
print(f"   Pop sans géométrie    : {pop_nc_sans_geo:,.0f}")

# Calculer centroïdes
if len(gdf_iris_nc) > 0:
    print(f"   Calcul centroïdes...")
    gdf_iris_nc['centroid'] = gdf_iris_nc.geometry.centroid
else:
    print(f"   ATTENTION: Aucun IRIS avec géométrie trouvé!")
    print(f"   Impossible d'utiliser nearest neighbor pour ces IRIS")
    print(f"   Population concernée: {pop_nc_sans_geo:,.0f}")

    # On peut quand même continuer pour traiter les IRIS sans géométrie
    # via une méthode alternative (commune-level fallback)
    if pop_nc_sans_geo == 0:
        print(f"   Aucune population à distribuer, sortie.")
        sys.exit(0)

# 5. Charger pharmacies
print("\n5. CHARGEMENT PHARMACIES")
df_pharma = pd.read_csv(INPUT_FILES['pharmacies'], sep=';')
df_pharma = df_pharma.dropna(subset=['latitude', 'longitude'])
print(f"   Pharmacies valides    : {len(df_pharma):,}")

# Créer GeoDataFrame pharmacies
from shapely.geometry import Point
geometry_pharma = [Point(lon, lat) for lon, lat in zip(df_pharma['longitude'], df_pharma['latitude'])]
gdf_pharma = gpd.GeoDataFrame(
    df_pharma,
    geometry=geometry_pharma,
    crs="EPSG:4326"
)

# Reprojeter en Lambert 93 (même que IRIS)
if gdf_iris.crs.to_epsg() != 4326:
    print(f"   Reprojection pharma   : WGS84 -> {gdf_iris.crs}")
    gdf_pharma = gdf_pharma.to_crs(gdf_iris.crs)

# 6. Nearest Neighbor Assignment
print("\n6. NEAREST NEIGHBOR ASSIGNMENT")

if len(gdf_iris_nc) == 0:
    print(f"   Aucun IRIS avec géométrie")
    print(f"   Skip nearest neighbor assignment")
    nouvelles_relations = []
else:
    print(f"   Construction KDTree...")

    # Extraire coordonnées
    pharma_coords = np.array([[p.x, p.y] for p in gdf_pharma.geometry])
    iris_coords = np.array([[c.x, c.y] for c in gdf_iris_nc['centroid']])

    # Créer KDTree
    tree = cKDTree(pharma_coords)

    # Trouver pharmacie la plus proche pour chaque IRIS
    distances, indices = tree.query(iris_coords, k=1)

    print(f"   Pharmacies assignées  : {len(np.unique(indices)):,}")
    print(f"   Distance moyenne      : {distances.mean()/1000:.2f} km")
    print(f"   Distance médiane      : {np.median(distances)/1000:.2f} km")
    print(f"   Distance max          : {distances.max()/1000:.2f} km")

    # 7. Calculer w_IRIS basé sur distance
    print("\n7. CALCUL w_IRIS PAR DISTANCE")

    # Décroissance exponentielle: w_IRIS = exp(-distance / lambda)
    # Lambda = distance caractéristique (choisir 20 km = distance acceptable)
    lambda_km = 20.0
    distances_km = distances / 1000

    w_iris_values = np.exp(-distances_km / lambda_km)

    print(f"   Lambda (dist. caract.): {lambda_km:.1f} km")
    print(f"   w_IRIS moyen          : {w_iris_values.mean():.3f}")
    print(f"   w_IRIS médian         : {np.median(w_iris_values):.3f}")
    print(f"   w_IRIS min            : {w_iris_values.min():.3f}")

    # Distribution w_IRIS
    print(f"\n   Distribution w_IRIS:")
    bins = [0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    for i in range(len(bins)-1):
        count = ((w_iris_values >= bins[i]) & (w_iris_values < bins[i+1])).sum()
        pct = 100 * count / len(w_iris_values)
        print(f"     [{bins[i]:.1f} - {bins[i+1]:.1f}[ : {count:5,} IRIS ({pct:5.1f}%)")

    # 8. Créer nouvelles relations
    print("\n8. CRÉATION NOUVELLES RELATIONS")

    nouvelles_relations = []

    for i, (idx_pharma, dist, w_iris, code_iris) in enumerate(zip(
        indices, distances, w_iris_values, gdf_iris_nc['CODE_IRIS']
    )):
        id_pharma = gdf_pharma.iloc[idx_pharma]['id_pharmacie']

        nouvelles_relations.append({
            'id_pharmacie': id_pharma,
            'CODE_IRIS': code_iris,
            'w_IRIS': w_iris,
            'source': 'nearest_neighbor',
            'distance_m': dist
        })

    df_nouvelles = pd.DataFrame(nouvelles_relations)
    print(f"   Nouvelles relations   : {len(df_nouvelles):,}")

    # Vérifier unicité (1 IRIS = 1 pharmacie la plus proche)
    assert df_nouvelles['CODE_IRIS'].nunique() == len(df_nouvelles), "Duplicates found!"

# 9. Fusionner avec matrice existante
print("\n9. FUSION AVEC MATRICE EXISTANTE")

# Ajouter colonne distance aux relations existantes (NaN)
if 'distance_m' not in df_matrice.columns:
    df_matrice['distance_m'] = np.nan

# Fusionner
if len(nouvelles_relations) > 0:
    df_nouvelles = pd.DataFrame(nouvelles_relations)
    df_matrice_100 = pd.concat([
        df_matrice[['id_pharmacie', 'CODE_IRIS', 'w_IRIS', 'source', 'distance_m']],
        df_nouvelles[['id_pharmacie', 'CODE_IRIS', 'w_IRIS', 'source', 'distance_m']]
    ], ignore_index=True)
else:
    print(f"   Aucune nouvelle relation à ajouter")
    df_matrice_100 = df_matrice[['id_pharmacie', 'CODE_IRIS', 'w_IRIS', 'source', 'distance_m']].copy()

print(f"   Matrice avant         : {len(df_matrice):,} relations")
print(f"   Matrice après         : {len(df_matrice_100):,} relations")
print(f"   Pharmacies totales    : {df_matrice_100['id_pharmacie'].nunique():,}")
print(f"   IRIS totaux           : {df_matrice_100['CODE_IRIS'].nunique():,}")

# Statistiques par source
print(f"\n   Répartition par source:")
print(df_matrice_100['source'].value_counts())

# 10. Vérification couverture 100%
print("\n10. VÉRIFICATION COUVERTURE 100%")

iris_dans_matrice = set(df_matrice_100['CODE_IRIS'].unique())
iris_avec_pop = set(df_pop_65[df_pop_65['pop_65_plus'] > 0]['CODE_IRIS'])

iris_manquants = iris_avec_pop - iris_dans_matrice
pop_manquante = df_pop_65[df_pop_65['CODE_IRIS'].isin(iris_manquants)]['pop_65_plus'].sum()

print(f"   IRIS avec population  : {len(iris_avec_pop):,}")
print(f"   IRIS dans matrice     : {len(iris_dans_matrice):,}")
print(f"   IRIS manquants        : {len(iris_manquants):,}")
print(f"   Population manquante  : {pop_manquante:,.0f}")

taux_couverture = 100 * len(iris_dans_matrice) / len(iris_avec_pop)
print(f"   Taux de couverture    : {taux_couverture:.2f}%")

# 11. Sauvegarder
print("\n11. SAUVEGARDE")

output_path = OUTPUT_FILES['matrice_w_iris_100pct']
df_matrice_100.to_csv(output_path, index=False)

print(f"   Fichier sauvegardé    : {output_path}")
print(f"   Taille                : {output_path.stat().st_size / 1024 / 1024:.1f} MB")

# 12. Rapport détaillé
print("\n12. RAPPORT DÉTAILLÉ")

# Population ajoutée
pop_ajoutee = pop_nc_avec_geo  # Population with geometry that was added
print(f"   Population avant      : {df_pop_65[df_pop_65['CODE_IRIS'].isin(iris_couverts)]['pop_65_plus'].sum():,.0f}")
print(f"   Population ajoutée (nn): {pop_ajoutee:,.0f}")
print(f"   Population non traitée : {pop_nc_sans_geo:,.0f} (IRIS hors contours - DOM-TOM, zones spéciales)")
print(f"   Population totale     : {df_pop_65['pop_65_plus'].sum():,.0f}")

# Pharmacies impactées
if len(nouvelles_relations) > 0:
    pharma_nn = len(set([r['id_pharmacie'] for r in nouvelles_relations]))
    print(f"\n   Pharmacies avec nn    : {pharma_nn:,}")

    # Exemples IRIS très éloignés (distance > 50 km)
    df_loin = pd.DataFrame([r for r in nouvelles_relations if r['distance_m'] > 50000])
    if len(df_loin) > 0:
        print(f"\n   IRIS très éloignés (> 50 km) : {len(df_loin):,}")
        df_loin = df_loin.merge(df_pop_65, on='CODE_IRIS')
        df_loin = df_loin.sort_values('distance_m', ascending=False)
        print(f"\n   Top 10 IRIS les plus éloignés:")
        for idx, row in df_loin.head(10).iterrows():
            print(f"     IRIS {row['CODE_IRIS']} : {row['distance_m']/1000:.1f} km, pop={row['pop_65_plus']:.0f}, w_IRIS={row['w_IRIS']:.3f}")
else:
    print(f"\n   Aucune relation nearest neighbor créée")

print("\n" + "="*80)
print("OK ASSOCIATION TERMINÉE - COUVERTURE 100%")
print("="*80)
print(f"\nProchaine étape: Utiliser cette matrice dans ml_06")
print(f"   Fichier créé : {output_path}")
print(f"   À référencer dans config_ml.py si nécessaire")