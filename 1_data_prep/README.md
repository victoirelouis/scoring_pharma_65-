# Phase 1 - Préparation des Données 🔧

**Pipeline complet de préparation des données pour le modèle de scoring pharmacies 65+**

Ce dossier contient tous les scripts, données sources et résultats de la phase 1 : préparation et enrichissement des données pour le pipeline ML.

---

## 📋 Vue d'ensemble

La Phase 1 génère **3 fichiers clés** utilisés par le pipeline ML :

1. **`pharmacies_final_avec_variables_touristiques.csv`** : Dataset complet pharmacies (~19k lignes, 300+ features)
2. **`HUBS_unified_final.csv`** : Points d'attractivité dédoublonnés (~350k hubs)
3. **`matrice_w_iris_100pct.csv`** : Matrice Pharmacie×IRIS avec pondérations w_IRIS (100% couverture)

---

## 📁 Structure du dossier

```
1_data_prep/
├── input/                  # Données sources brutes (~5 GB)
│   ├── 1_sources_brutes/   # OSM, FINESS, RPPS, contours IRIS
│   ├── 2_insee_brutes/     # Population, revenus, logement par IRIS
│   ├── 3_pharmacies/       # Fichiers sources pharmacies
│   ├── 4_references/       # Tables de correspondance
│   └── 5_validation/       # Données de validation (SIG_P20)
│
├── output/                 # Résultats générés (~13 GB)
│   ├── pharmacies_final.csv
│   ├── HUBS_unified_final.csv
│   ├── matrice_w_iris.csv           # ⭐ Matrice w_IRIS (isochrones)
│   ├── matrice_w_iris_enriched.csv  # + géolocalisation
│   ├── matrice_w_iris_100pct.csv    # + couverture 100%
│   ├── isochrones/                   # 115k zones d'accessibilité
│   └── pharmacies_final_avec_variables_touristiques.csv
│
├── cache/                  # Cache de performance (~1-2 GB)
│   ├── checkpoints_w_iris/ # Sauvegardes calcul matrice
│   └── geocoding/          # Cache géocodage API
│
└── scripts/                # 5 pipelines organisés
    ├── config_prep.py      # ⚙️ Configuration centralisée Phase 1
    ├── 1_pharmacies/       # Création base pharmacies
    ├── 2_hubs/             # Points d'attractivité (HUBS)
    ├── 3_isochrones/       # Zones d'accessibilité + calcul w_IRIS
    ├── 4_enrichissement/   # Enrichissement INSEE + tourisme
    └── 5_validation/       # Contrôle qualité
```

---

## ⚙️ Configuration centralisée

### `scripts/config_prep.py`

**Fichier de configuration centralisé** utilisé par tous les scripts de la phase 1.

#### Contenu :
- **Chemins de base** : `PROJECT_ROOT`, `INPUT_DIR`, `OUTPUT_DIR`, `CACHE_DIR`
- **Dictionnaires de fichiers** :
  - `INPUT_FILES` : 26 fichiers d'entrée avec alias
  - `OUTPUT_FILES` : 25 fichiers de sortie
  - `RPPS_FILES` : 6 professions de santé
- **Paramètres de traitement** :
  - `GEOCODING_WORKERS = 10`
  - `ISOCHRONE_WORKERS = 4`
  - `DEDUP_DISTANCE_THRESHOLD = 50` (mètres)
  - `ISOCHRONE_TYPES` : 6 types d'isochrones
- **Configuration logging** : Format et niveau

#### Usage dans les scripts :
```python
from config_prep import INPUT_FILES, OUTPUT_FILES, PROJECT_ROOT
```

---

## 🔧 Pipelines de traitement

### Pipeline 1 : Pharmacies (`1_pharmacies/`)

**Objectif** : Créer la base de pharmacies géocodées avec variables de base

#### Script :
- **`a_create_pharmacies_final.py`**

#### Input :
- `input/3_pharmacies/pharmacies_raw.csv` (source UGA)

#### Traitement :
- Nettoyage et validation des coordonnées GPS
- Calcul du type de zone (urbain_dense, urbain, périurbain, rural)
- Comptage des pharmacies voisines (rayon 5km)
- Attribution d'un `id_pharmacie` unique

#### Output :
- **`pharmacies_final.csv`** : 19 307 pharmacies avec :
  - Identifiant, nom, coordonnées (lat/lon)
  - Code postal, commune, département
  - Type de zone
  - CA total, CA éthique, CA conseil (si disponibles)
  - Nombre de voisins dans rayon 5km

**Temps d'exécution** : ~30 secondes

---

### Pipeline 2 : HUBS (`2_hubs/`)

**Objectif** : Créer la base unifiée des points d'attractivité (établissements de santé, transports, commerces)

#### Scripts (ordre d'exécution) :

**1. `a_finess_categories.py`**
- Configuration des catégories FINESS (regroupement et typage)
- Référence pour les scripts suivants

**2. `d_process_finess.py`**
- Input : `input/FINESS.csv`
- Traitement :
  - Fusion structure + géolocalisation
  - Conversion Lambert 93 → WGS84
  - Catégorisation simplifiée (hopital, ehpad, etc.)
- Output : **`FINESS_merged.csv`** (21 MB)
- **Temps** : ~2 minutes

**3. `c_geocode_rpps_optimise.py`**
- Input : Fichiers RPPS bruts (6 professions)
- Traitement : Géocodage via API BAN (parallèle, 10 workers)
- Output : **`rpps_geocode/RPPS_merged.csv`** (203 MB)
- **Temps** : ~30-45 minutes (selon API)

**4. `b_create_hubs_file.py`**
- Sources : OSM (transports, commerces), SNCF, RATP
- Extraction des points d'intérêt depuis OSM
- Output : `hubs.csv`
- **Temps** : ~5-10 minutes

**5. `e_merge_finess_rpps_hubs.py`**
- Fusion FINESS + RPPS + OSM
- Harmonisation des colonnes
- Output : `HUBS_unified.csv` (avant dédoublonnage)
- **Temps** : ~2 minutes

**6. `f_corriger_dedoublonner.py`**
- Dédoublonnage spatial (KDTree, seuil 50m)
- Correction des types d'établissements
- Output : **`HUBS_unified_final.csv`** (~350k hubs)
- **Temps** : ~5 minutes

#### Output final :
- **`HUBS_unified_final.csv`** : ~50 MB, 350 000 points d'attractivité

**Temps total pipeline** : ~45-60 minutes

---

### Pipeline 3 : Isochrones + w_IRIS (`3_isochrones/`)

**Objectif** : Générer les zones d'accessibilité + calculer la matrice de pondérations pharmacie-IRIS

#### Scripts (ordre d'exécution) :

**1. `a_generate_isochrones.py`** ⭐ Principal
- Input : `output/pharmacies_final.csv`
- Génération via **Valhalla** sur réseau OpenStreetMap
- Calcul des zones accessibles en temps réel de trajet
- Multiprocessing (4 workers)
- Output : **`isochrones/{type}/*.geojson`** (115 767 fichiers)
- **Temps** : ~48 heures

**2. `b_generate_missing_isochrones.py`**
- Complète les isochrones manquants après première exécution
- Relance uniquement pour pharmacies sans isochrone
- **Temps** : ~30 minutes (500 pharmacies)

**3. `c_calculate_w_iris.py`** ⭐ Calcul w_IRIS
- Input :
  - `isochrones/` (115k fichiers)
  - `contours_iris.gpkg` (polygones IRIS)
- Traitement :
  - Intersection géométrique : w_IRIS = Surface(Isochrone ∩ IRIS) / Surface(IRIS)
  - Optimisations : index spatial, checkpoints toutes les 1000 pharmacies
  - Seuil minimal : w_IRIS < 0.001 éliminé
- Output : **`matrice_w_iris.csv`** (~95k relations)
- **Temps** : ~3-4 minutes

**4. `d_associate_pharmacies_to_iris.py`**
- Enrichit la matrice avec pharmacies sans isochrones
- Méthode : intersection spatiale via coordonnées GPS
- Assigne w_IRIS = 1.0 (couverture totale IRIS local)
- Output : **`matrice_w_iris_enriched.csv`** (+~1k relations)
- **Temps** : ~10 secondes

**5. `e_associate_uncovered_iris.py`**
- Atteint 100% de couverture population
- Méthode : nearest neighbor + distance exponentielle
  - w_IRIS = exp(-distance_km / 20)
- Output : **`matrice_w_iris_100pct.csv`** (~96.5k relations)
- **Temps** : ~5 secondes

#### Outputs :
- **`isochrones/`** : 115 767 fichiers GeoJSON (~12 GB) :
  - `walk_5min/`, `walk_10min/`
  - `drive_5min/`, `drive_10min/`, `drive_15min/`, `drive_20min/`
- **`matrice_w_iris.csv`** : Matrice principale (isochrones)
- **`matrice_w_iris_enriched.csv`** : + géolocalisation
- **`matrice_w_iris_100pct.csv`** : + couverture 100%

**Temps total pipeline** : ~48h (génération) + 4 min (calcul matrice)

📖 **Documentation détaillée** : Voir [METHODE_CALCUL_MATRICE_W_IRIS.md](../METHODE_CALCUL_MATRICE_W_IRIS.md)

---

### Pipeline 4 : Enrichissement (`4_enrichissement/`)

**Objectif** : Enrichir les pharmacies avec données INSEE et tourisme

#### Scripts :

**1. `b_enrichir_pharmacies_optimise.py`** ⭐
- Input :
  - `output/pharmacies_final.csv`
  - `output/matrice_w_iris_100pct.csv` (pondérations w_IRIS)
  - Fichiers INSEE bruts (`input/2_insee_brutes/`)
- Traitement :
  - Agrégation pondérée par IRIS (multiprocessing)
  - Variables : population, revenus, logement, formation
  - Formule : valeur_pharma = Σ(valeur_iris × w_IRIS × pop_iris) / Σ(w_IRIS × pop_iris)
- Output : **`pharmacies_enrichies_insee.csv`** (~5 MB)
- **Temps** : ~3-5 minutes

**2. `a_calcul_variables_touristiques.py`** ⭐
- Input :
  - `output/pharmacies_enrichies_insee.csv`
  - Fichiers hébergements INSEE
  - `isochrones/`
- Traitement :
  - Calcul hébergements par isochrone (hôtels, campings, résidences)
  - Détection zones montagne/littoral
  - Flag commune touristique
- Output : **`pharmacies_final_avec_variables_touristiques.csv`** (~6 MB)
- **Temps** : ~2-3 minutes

#### Output final :
- **`pharmacies_final_avec_variables_touristiques.csv`** : Dataset ML complet (300+ features)

**Temps total pipeline** : ~5-8 minutes

---

### Pipeline 5 : Validation (`5_validation/`)

**Objectif** : Contrôle qualité des données enrichies

#### Scripts :

**`a_check_data_quality.py`**
- Input : `output/pharmacies_enrichies_insee.csv`
- Vérifications :
  - Complétude (valeurs manquantes < 10%)
  - Cohérence (coordonnées GPS valides, codes postaux)
  - Outliers (< 5% par variable)
  - Distribution géographique (toutes régions représentées)
- Output : Rapport console
- **Temps** : ~30 secondes

---

## 📊 Fichiers de résultats

### Fichiers finaux utilisés par le pipeline ML

| Fichier | Description | Taille | Pipeline |
|---------|-------------|--------|----------|
| **`pharmacies_final.csv`** | Base pharmacies géocodées | ~2 MB | 1 |
| **`HUBS_unified_final.csv`** | Points d'attractivité dédoublonnés | ~50 MB | 2 |
| **`matrice_w_iris.csv`** | Matrice w_IRIS (isochrones) | ~8 MB | 3 |
| **`matrice_w_iris_100pct.csv`** | Matrice 100% couverture | ~10 MB | 3 |
| **`isochrones/`** | 115k zones d'accessibilité | ~12 GB | 3 |
| **`pharmacies_enrichies_insee.csv`** | Pharmacies + INSEE | ~5 MB | 4 |
| **`pharmacies_final_avec_variables_touristiques.csv`** | Dataset ML complet | ~6 MB | 4 |

### Fichiers intermédiaires (reconstruction possible)

| Fichier | Description | Pipeline |
|---------|-------------|----------|
| `FINESS_merged.csv` | FINESS géocodés + catégorisés | 2 |
| `rpps_geocode/RPPS_merged.csv` | Médecins RPPS géocodés | 2 |
| `hubs.csv` | Points OSM (transport, commerce) | 2 |
| `HUBS_unified.csv` | Fusion avant dédoublonnage | 2 |
| `matrice_w_iris_enriched.csv` | Matrice + géolocalisation | 3 |

---

## 🚀 Exécution complète

### Génération initiale (une seule fois)

```bash
cd 1_data_prep/scripts

# 1. Pharmacies (~30 sec)
cd 1_pharmacies && python a_create_pharmacies_final.py

# 2. HUBS (chaîne complète, ~45-60 min)
cd ../2_hubs
python a_finess_categories.py  # Config
python d_process_finess.py
python c_geocode_rpps_optimise.py
python b_create_hubs_file.py
python e_merge_finess_rpps_hubs.py
python f_corriger_dedoublonner.py

# 3. Isochrones + w_IRIS (LONG : ~48h)
cd ../3_isochrones
python a_generate_isochrones.py       # ~48h
python b_generate_missing_isochrones.py  # ~30 min
python c_calculate_w_iris.py          # ~3-4 min
python d_associate_pharmacies_to_iris.py  # ~10 sec
python e_associate_uncovered_iris.py  # ~5 sec

# 4. Enrichissement (~5-8 min)
cd ../4_enrichissement
python b_enrichir_pharmacies_optimise.py
python a_calcul_variables_touristiques.py

# 5. Validation (~30 sec)
cd ../5_validation && python a_check_data_quality.py
```

### Mise à jour (nouvelles pharmacies)

```bash
cd 1_data_prep/scripts

# 1. Recréer base pharmacies
cd 1_pharmacies && python a_create_pharmacies_final.py

# 2. Générer isochrones manquants
cd ../3_isochrones && python b_generate_missing_isochrones.py

# 3. Recalculer matrice w_IRIS
python c_calculate_w_iris.py
python d_associate_pharmacies_to_iris.py
python e_associate_uncovered_iris.py

# 4. Réenrichir
cd ../4_enrichissement
python b_enrichir_pharmacies_optimise.py
python a_calcul_variables_touristiques.py
```

---

## ⏱️ Temps d'exécution

| Pipeline | Temps estimé | Commentaire |
|----------|--------------|-------------|
| 1. Pharmacies | 30 sec | Rapide |
| 2. HUBS | 45-60 min | Géocodage RPPS variable |
| 3. Isochrones | ~48 heures | Génération longue (une seule fois) |
| 3. Matrice w_IRIS | 3-4 min | Optimisé avec checkpoints |
| 4. Enrichissement | 5-8 min | Multiprocessing |
| 5. Validation | 30 sec | Rapide |
| **Total (initial)** | **~50 heures** | Dont 48h isochrones |

---

## 💾 Volumes de données

| Dossier | Taille approximative |
|---------|---------------------|
| `input/` | ~5 GB |
| `output/` | ~13 GB |
| `cache/` | Variable (~1-2 GB) |
| **Total** | **~20 GB** |

---

## 🔗 Prochaine étape

Une fois cette phase terminée, les fichiers générés dans `output/` sont utilisés par le **pipeline ML Phase 2** dans [`../2_pipeline_ml/`](../2_pipeline_ml/README.md).

### Fichiers requis pour le ML :
- ✅ `pharmacies_final_avec_variables_touristiques.csv`
- ✅ `HUBS_unified_final.csv`
- ✅ `matrice_w_iris_100pct.csv`
- ✅ `isochrones/` (tous les types)

---

## 📚 Documentation

- **[Méthode de calcul de la matrice w_IRIS](../METHODE_CALCUL_MATRICE_W_IRIS.md)** : Documentation technique complète du calcul des pondérations IRIS
- **[README projet](../README.md)** : Vue d'ensemble des 2 phases
- **[README Phase 2](../2_pipeline_ml/README.md)** : Pipeline ML

---

**Phase** : 1 - Préparation des données
**Dernière mise à jour** : Novembre 2025
**Version** : 2.0