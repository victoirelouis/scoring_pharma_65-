# Organisation des données - Projet Scoring Pharma 65+

## Structure des dossiers

```
data/
├── input/           # Sources de données brutes
├── cache/           # Données temporaires et cache
└── output/          # Résultats de traitement
```

## Sources de données (`data/input/`)

### 1. Données des pharmacies
- **`pharmacies.csv`** : Points de vente des pharmacies avec géocodage
  - Source : `DATA/DONNEES_PHARMACIES/points_ventes_202509 - RETRAVAILLE.geocoded.csv`
  - Contient : Coordonnées, adresses, informations légales

### 2. Données INSEE par IRIS (`iris_insee/`)
- **`population_age.csv`** : Répartition de la population par âge et IRIS
  - Source : `DATA/DONNEES_INSEE/2022/age/age_profession.CSV`
  - Contient : Population 65-74, 75-84, 85+ ans par IRIS

### 3. Données géographiques (`geo/`)
- **`contours_iris.gpkg`** : Contours géographiques des IRIS
  - Source : `DATA/DONNEES_INSEE/CONTOURS-IRIS-PE_3-0_GPKG_LAMB93_FXX-ED2025-01-01/contours-iris-pe.gpkg`
  - Format : GeoPackage avec géométries

### 4. Données d'enrichissement (`enrichissement/`)
- **`pharmacie_iris_pond.csv`** : Pharmacies avec pondérations IRIS
  - Source : `DATA/pharmacie_iris_pond.csv`
  
- **`pharmacies_enrichies.csv`** : Pharmacies avec données enrichies
  - Source : `DATA/pharmacies_enrichies.csv`

## Données supplémentaires disponibles

Les données suivantes sont disponibles dans le workspace principal mais pas encore intégrées :

### Données INSEE complémentaires
- **Logement** : `DATA/DONNEES_INSEE/2022/logement/logement.CSV`
- **Diplômes** : `DATA/DONNEES_INSEE/2022/diplome_formation/diplome_formation.CSV`
- **Familles** : `DATA/DONNEES_INSEE/2022/couples_familles/couples_familles.CSV`
- **Activité résidents** : `DATA/DONNEES_INSEE/2022/activites_residents/activite_residents.CSV`
- **Indicateurs CVI** : `DATA/DONNEES_INSEE/2022/FD_INDCVI_2022.csv`

### Intégration future
Pour ajouter ces données au projet :

```powershell
# Copier les données supplémentaires si nécessaire
Copy-Item "..\..\DATA\DONNEES_INSEE\2022\logement\logement.CSV" "data\input\iris_insee\logement.csv"
Copy-Item "..\..\DATA\DONNEES_INSEE\2022\diplome_formation\diplome_formation.CSV" "data\input\iris_insee\diplome_formation.csv"
```

## Utilisation dans le code

### Chargement des données principales

```python
import pandas as pd
from pathlib import Path

# Chemin de base
DATA_PATH = Path("data/input")

# Charger les pharmacies
pharmacies = pd.read_csv(DATA_PATH / "pharmacies.csv")

# Charger la population par âge
population_age = pd.read_csv(DATA_PATH / "iris_insee/population_age.csv")

# Charger les données enrichies
pharmacies_enrichies = pd.read_csv(DATA_PATH / "enrichissement/pharmacies_enrichies.csv")
```

### Données géographiques

```python
import geopandas as gpd

# Charger les contours IRIS
iris_contours = gpd.read_file(DATA_PATH / "geo/contours_iris.gpkg")
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