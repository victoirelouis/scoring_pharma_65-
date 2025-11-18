# Organisation des données - Projet Scoring Pharma 65+

## Structure des dossiers

```
data/
├── input/           # Sources de données brutes
├── cache/           # Données temporaires et cache
└── output/          # Résultats de traitement
```

## Sources de données (`data/input/`)

### 1. Sources brutes (`1_sources_brutes/`)
- **`france-latest.osm.pbf`** : Données OpenStreetMap France complètes
- **`contours_iris.gpkg`** : Contours géographiques des IRIS (Lambert 93)
- **Fichiers FINESS** : Établissements sanitaires et médico-sociaux
- **Fichiers RPPS** : Répertoire des professionnels de santé

### 2. Données INSEE (`2_insee_brutes/`)
- **`age_profession.CSV`** : Population par âge + professions par IRIS (49 277 IRIS)
  - Contient : Population totale, 65+, 65-79, 80+, secteurs d'activité
- **`diplome_formation.CSV`** : Niveau d'éducation par IRIS
- **`logement.CSV`** : Caractéristiques du logement par IRIS
- **`revenus.csv`** : Revenus médians par IRIS

### 3. Références (`4_references/`)
- **`correspondance-code-insee-code-postal.csv`** : Mapping communes ↔ codes postaux (36 743 communes)
- **`correspondance_iris_code_postal.csv`** : Mapping IRIS ↔ codes postaux (49 277 IRIS)

## Fichiers générés par le pipeline (`data/output/`)

### Phase 0 - Étapes préliminaires

**1. Pharmacies (`pharmacies_finales/`)**
- `pharmacies_final.csv` : Pharmacies géocodées avec variables de base (généré par `scripts/1_pharmacies/`)

**2. HUBS (`data/processed/`)**
- `HUBS_unified_final.csv` : Points d'attractivité (médecins, établissements, transports)
- `FINESS_with_weights.csv` : Établissements FINESS avec poids seniors
- `RPPS_merged_with_weights.csv` : Médecins RPPS avec poids
- `rpps_geocode/` : Médecins RPPS géocodés par batch (203 MB)

**3. Isochrones (`data/processed/isochrones/`)**
- 115k fichiers geojson organisés en 6 types :
  - `walk_5min/`, `walk_10min/`
  - `drive_5min/`, `drive_10min/`, `drive_15min/`, `drive_20min/`

**4. Enrichissement (`data/output/`)**
- `pharmacies_enrichies/` :
  - `pharmacie_iris_pond_cleaned.csv` : Pondérations w_IRIS précalculées (intersection isochrones × IRIS)
- `pharmacies_enrichies_insee.csv` : Pharmacies + données INSEE agrégées par w_IRIS
- `pharmacies_final_avec_variables_touristiques.csv` : Pharmacies + INSEE + tourisme

### Phase 1 (intermediaire/scripts/)
- **`intermediaire/output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`** : Estimations finales clients 65+

## Utilisation dans le code

### Chargement des données principales

```python
import pandas as pd
from pathlib import Path

# Chemins de base
DATA_INPUT = Path("data/input")
DATA_OUTPUT = Path("data/output")
DATA_PROCESSED = Path("data/processed")

# Charger les données sources INSEE
age_profession = pd.read_csv(DATA_INPUT / "2_insee_brutes/age_profession.CSV")
revenus = pd.read_csv(DATA_INPUT / "2_insee_brutes/revenus.csv")

# Charger les données calculées
pharmacies_final = pd.read_csv(DATA_OUTPUT / "pharmacies_finales/pharmacies_final.csv")
pharmacies_enrichies = pd.read_csv(DATA_OUTPUT / "pharmacies_enrichies_insee.csv")
hubs = pd.read_csv(DATA_OUTPUT / "HUBS_unified_final.csv")
```

### Données géographiques

```python
import geopandas as gpd

# Charger les contours IRIS
iris_contours = gpd.read_file(DATA_INPUT / "1_sources_brutes/contours_iris.gpkg")
```

## Format des données attendues

### PharmacyData (pour le modèle)
```python
@dataclass
class PharmacyData:
    id: str                      # Identifiant unique
    coords: Tuple[float, float]  # (latitude, longitude)
    ca_total: float             # CA total annuel
    ca_ethique: float           # CA éthique (ordonnances)
    ca_conseil: float           # CA conseil (parapharmacie)
    zone_type: ZoneType         # Type de zone géographique
    name: str = ""              # Nom de la pharmacie
```

### IrisData (pour le modèle)
```python
@dataclass
class IrisData:
    id: str                      # Code IRIS
    coords: Tuple[float, float]  # Centroïde (lat, lon)
    revenu_median: float         # Revenu médian de la zone
    population_total: int        # Population totale
    population_65_74: int        # Population 65-74 ans
    population_75_84: int        # Population 75-84 ans
    population_85_plus: int      # Population 85+ ans
```

## Cache et sorties

### `data/cache/`
- Données préprocessées pour accélérer les calculs
- Matrices de distance précalculées
- Données géographiques optimisées

### `data/output/`
- Résultats des calculs d'attractivité
- Rapports et visualisations
- Exports pour analyses ultérieures

## Notes techniques

### Système de coordonnées
- **Input** : WGS84 (EPSG:4326) pour les coordonnées lat/lon
- **Processing** : Lambert 93 (EPSG:2154) pour les calculs de distance
- **Output** : WGS84 pour la compatibilité

### Encodage des fichiers
- Privilégier UTF-8 pour tous les nouveaux fichiers
- Attention aux fichiers CSV avec caractères accentués

### Taille des données
- Surveiller la taille du cache pour éviter l'explosion
- Nettoyer régulièrement `data/cache/` si nécessaire