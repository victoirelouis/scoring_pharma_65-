# Scoring Pharma 65+ 🏥

**Modélisation du potentiel commercial des pharmacies françaises auprès de la population 65+**

Ce projet estime, pour chaque pharmacie de France, le nombre de clients seniors potentiels, en utilisant un modèle gravitaire de Huff combiné à des scores d'attractivité machine learning.

---

## 📋 Vue d'ensemble

### Objectifs

- **Estimer les clients 65+** pour ~19 300 pharmacies françaises
- **Décomposer par âge** : 65-79 ans, 80+ ans
- **Estimer les visites annuelles** : Nombre de visites potentielles (12 visites/an par senior)
- **Intégrer la géographie fine** : Données INSEE par IRIS (~50 000 zones)
- **Prendre en compte** : Accessibilité réelle (isochrones), concurrence, hubs médicaux, tourisme

### Méthodologie en 2 étapes

1. **Calcul de l'attractivité** : Score composite combinant environnement médical (HUBS de proximité), population accessible (isochrones), concurrence locale, et caractéristiques géographiques/démographiques
2. **Modèle de Huff** : Distribution de la population 65+ par IRIS aux pharmacies proportionnellement à leur attractivité pondérée par l'accessibilité (w_IRIS)

### Résultats

- **Population France 65+** : 14,1 millions
- **Population couverte** : ~13,3 millions (94%)
- **Conservation parfaite** : 100% de la population couverte est distribuée
- **Corrélations** : R = 0.15-0.34 avec données réelles SIG_P20 (selon zone)

---

## 📁 Structure du projet

Le projet est organisé en **2 phases distinctes** avec documentation complète :

```
scoring_pharma_65-/
│
├── 1_data_prep/              # PHASE 1 - Préparation des données
│   ├── input/               # Données sources (FINESS, RPPS, INSEE, OSM)
│   ├── output/              # Résultats générés (~13 GB)
│   │   ├── matrice_w_iris.csv          # ⭐ Matrice Pharmacie×IRIS (w_IRIS)
│   │   ├── matrice_w_iris_enriched.csv # Matrice enrichie (geoloc)
│   │   └── matrice_w_iris_100pct.csv   # Matrice 100% couverture
│   ├── cache/               # Cache de performance
│   ├── scripts/             # 5 pipelines organisés
│   │   ├── config_prep.py  # ⚙️ Configuration centralisée Phase 1
│   │   ├── 1_pharmacies/   # Création base pharmacies
│   │   ├── 2_hubs/         # Points d'attractivité (HUBS)
│   │   ├── 3_isochrones/   # Zones d'accessibilité + calcul w_IRIS
│   │   ├── 4_enrichissement/ # Enrichissement INSEE + tourisme
│   │   └── 5_validation/   # Contrôle qualité
│   └── README.md            # 📖 Documentation complète Phase 1
│
├── 2_pipeline_ml/           # PHASE 2 - Pipeline Machine Learning
│   ├── scripts/             # Scripts ML organisés
│   │   ├── 1_pipeline_ml/  # 6 étapes ML (HUBS, concurrence, Huff...)
│   │   ├── 2_analyses_correlations/ # Validation avec SIG_P20
│   │   └── 3_utilitaires/  # Config et outils
│   ├── output/              # Résultats ML
│   │   ├── 1_etapes_pipeline/      # Résultats intermédiaires
│   │   ├── 2_resultats_finaux/     # ⭐ Fichier final clients 65+
│   │   ├── 3_analyses_correlations/ # Graphiques et rapports
│   │   ├── 4_modeles/              # Modèles PCA sauvegardés
│   │   └── 5_rapports/             # Logs d'exécution
│   └── README.md            # 📖 Documentation complète Phase 2
│
├── .gitignore               # Ignore les données volumineuses
└── README.md                # 📖 Ce fichier (vue d'ensemble)
```

---

## 🚀 Guide de démarrage rapide

### Prérequis

```bash
# Python 3.8+
pip install pandas geopandas shapely scikit-learn matplotlib seaborn tqdm
```

### Exécution complète

#### Phase 1 : Préparation des données (~48h pour isochrones)

```bash
cd 1_data_prep/scripts

# 1. Pharmacies
cd 1_pharmacies && python create_pharmacies_final.py

# 2. HUBS (chaîne complète)
cd ../2_hubs
python d_process_finess.py
python c_geocode_rpps_optimise.py
python b_create_hubs_file.py
python e_merge_finess_rpps_hubs.py
python f_corriger_dedoublonner.py

# 3. Isochrones + w_IRIS (LONG : ~48h)
cd ../3_isochrones
python a_generate_isochrones.py  # Génère 115k isochrones (~48h)
python c_calculate_w_iris.py     # Calcule matrice w_IRIS (~3-4 min)
python d_associate_pharmacies_to_iris.py  # Enrichissement geoloc (~10 sec)
python e_associate_uncovered_iris.py  # Couverture 100% (~5 sec)

# 4. Enrichissement
cd ../4_enrichissement
python b_enrichir_pharmacies_optimise.py
python a_calcul_variables_touristiques.py

# 5. Validation
cd ../5_validation && python check_data_quality.py
```

#### Phase 2 : Pipeline ML (~90-120 min)

```bash
cd 2_pipeline_ml/scripts

# Prérequis : nettoyer matrice IRIS si besoin
python 3_utilitaires/nettoyer_matrice_iris_ET_pharmacies.py

# Pipeline ML (6 étapes séquentielles)
python 1_pipeline_ml/ml_01_prepare_hubs_par_isochrone.py
python 1_pipeline_ml/ml_02_prepare_concurrence.py
python 1_pipeline_ml/ml_03_prepare_population_isochrones.py
python 1_pipeline_ml/ml_04_integration_complete.py
python 1_pipeline_ml/ml_05_score_attractivite_pca.py
python 1_pipeline_ml/ml_06_HUFF_EXACT_IRIS_FIXED.py  # ⭐ Résultat final

# Analyses de corrélation (validation)
python 2_analyses_correlations/analyse_correlation_sig_p20.py
python 2_analyses_correlations/analyse_correlation_avancee.py
python 2_analyses_correlations/analyse_proximite_hubs_medicaux.py
```

---

## 📊 Fichiers de résultats clés

### Phase 1 (Données préparées)

| Fichier | Description | Taille |
|---------|-------------|--------|
| `1_data_prep/output/pharmacies_final_avec_variables_touristiques.csv` | Dataset complet pharmacies (300+ features) | ~6 MB |
| `1_data_prep/output/HUBS_unified_final.csv` | Points d'attractivité dédoublonnés | ~50 MB |
| `1_data_prep/output/isochrones/` | 115 767 zones d'accessibilité (6 types) | ~12 GB |
| **`1_data_prep/output/matrice_w_iris.csv`** ⭐ | **Matrice Pharmacie×IRIS avec w_IRIS** | ~8 MB |
| `1_data_prep/output/matrice_w_iris_100pct.csv` | Matrice 100% couverture population | ~10 MB |

### Phase 2 (Résultats ML)

| Fichier | Description | Taille |
|---------|-------------|--------|
| **`2_pipeline_ml/output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`** ⭐ | **RÉSULTAT FINAL** - Clients 65+ par pharmacie | ~2.3 MB |
| `2_pipeline_ml/output/pharmacie_iris_pond_cleaned.csv` | Matrice Pharmacie×IRIS nettoyée (prérequis ml_06) | ~200 MB |
| `2_pipeline_ml/output/1_etapes_pipeline/pharmacies_features_complet.csv` | Dataset ML complet (300+ features) | ~52 MB |
| `2_pipeline_ml/output/1_etapes_pipeline/pharmacies_avec_scores_attractivite.csv` | Scores d'attractivité composite | ~8.5 MB |

---

## 📖 Documentation détaillée

### Par phase

- **[Phase 1 - Préparation des données](1_data_prep/README.md)**
  - Structure complète des données sources
  - Documentation des 5 pipelines de traitement
  - Détail de chaque script avec inputs/outputs
  - Ordre d'exécution et temps estimés

- **[Phase 2 - Pipeline ML](2_pipeline_ml/README.md)**
  - Documentation des 12 scripts ML
  - Détail du modèle de Huff et scores PCA
  - Analyses de corrélation et validation
  - Métriques de qualité

### Méthodologie complète

Pour une compréhension approfondie de la méthodologie mathématique et des choix de modélisation, consulter :
- [Documentation méthodologique détaillée](METHODOLOGIE.md) (si créée séparément)

Cette documentation explique :
- Les composantes du score d'attractivité composite
- Le modèle de Huff et la distribution de population par IRIS
- Les paramètres du modèle gravitaire (attractivité × w_IRIS)
- Les contrôles qualité et seuils d'alerte

---

## 🔑 Concepts clés

### Isochrones
Zones géographiques accessibles depuis une pharmacie en un temps donné (ex: 10 min à pied). Calcul via OSMnx sur réseau routier/piétonnier réel.

### HUBS
Points d'attractivité qui augmentent le trafic potentiel : établissements de santé (EHPAD, hôpitaux), transports (bus, métro), commerces, marchés.

### w_IRIS (poids IRIS)
Coefficient de pondération entre 0 et 1 représentant la part de population d'un IRIS accessible à une pharmacie, basé sur l'intersection isochrone/IRIS.

### Modèle de Huff
Modèle gravitaire qui distribue la population d'une zone aux pharmacies concurrentes proportionnellement à leur attractivité. Garantit que Σ(clients) = Population couverte.

### Score d'attractivité composite
Score normalisé [0.1 - 1.0] calculé à partir de 300+ features (population accessible, HUBS de proximité, concurrence, caractéristiques géographiques). Utilisé dans le modèle de Huff pour pondérer l'attraction de chaque pharmacie.

---

## 📈 Métriques de qualité

### Couverture et conservation

- ✅ **94.2%** de la population 65+ française couverte
- ✅ **100%** de conservation (pas de perte de population)
- ✅ **18 208 / 19 307** pharmacies ont des clients

### Corrélations avec données réelles (SIG_P20)

| Stratification | R (UN vs Clients) | R (CAHT vs Clients) |
|----------------|-------------------|---------------------|
| **Global** | 0.15 | 0.21 |
| Urbain dense | 0.34 | 0.42 |
| Rural | 0.14 | 0.18 |
| Zones touristiques | 0.22 | 0.28 |
| 4-10 hubs médicaux (1km) | 0.32 | 0.38 |

**Note** : Les corrélations avec UN (Unités) et CAHT (chiffre d'affaires) du SIG_P20 permettent de valider que les clients 65+ estimés sont cohérents avec l'activité réelle des pharmacies. Les corrélations varient fortement selon le type de zone (meilleures en urbain dense).

---

## 🛠️ Technologies utilisées

- **Python 3.8+** : Langage principal
- **Pandas / GeoPandas** : Manipulation de données tabulaires et géographiques
- **Shapely** : Géométrie et intersections
- **OSMnx** : Calcul d'isochrones sur réseau OpenStreetMap
- **Scikit-learn** : PCA, preprocessing et métriques ML
- **Matplotlib / Seaborn** : Visualisations

### Sources de données

- **INSEE** : Population par IRIS, revenus, logement, démographie
- **FINESS** : Établissements de santé et médico-sociaux
- **RPPS** : Répertoire des professionnels de santé
- **OpenStreetMap** : Réseau routier/piétonnier, commerces, transports
- **SIG_P20** : Données d'activité pharmacies (validation)

---

## ⚙️ Configuration

### Fichiers de configuration centralisée

Le projet utilise des fichiers de configuration centralisée pour faciliter la maintenance :

- **[1_data_prep/scripts/config.py](1_data_prep/scripts/config.py)** : Configuration Phase 1
  - Tous les chemins (INPUT_DIR, OUTPUT_DIR, CACHE_DIR)
  - Dictionnaires de fichiers (INPUT_FILES, OUTPUT_FILES)
  - Paramètres de traitement (workers, timeouts, seuils)

- **[2_pipeline_ml/scripts/3_utilitaires/config_ml.py](2_pipeline_ml/scripts/3_utilitaires/config_ml.py)** : Configuration Phase 2
  - Chemins du pipeline ML
  - Références aux fichiers de Phase 1
  - Paramètres PCA et du modèle de Huff

### Configuration Git

Le fichier [.gitignore](.gitignore) est configuré pour **ne versionner aucune donnée volumineuse** :

```gitignore
# Phase 1: Data preparation
1_data_prep/input/**
1_data_prep/output/**
1_data_prep/cache/**

# Phase 2: ML pipeline
2_pipeline_ml/output/**

# Fichiers de données
*.csv
*.json
*.geojson
*.gpkg
```

Seuls les **scripts Python** et les **fichiers de documentation** sont versionnés (~500 KB).

Les données sources et résultats (~20 GB) doivent être stockés localement ou sur un serveur de fichiers.

---

## 📞 Contact et support

Pour toute question sur le projet :
- **Documentation** : Consulter les README de chaque phase
- **Méthodologie** : Voir le document méthodologique détaillé
- **Bugs ou améliorations** : Créer une issue dans le dépôt Git

---

## 📝 Versions

- **v4.1** (Novembre 2025) : Réorganisation complète en 2 phases, configuration centralisée, documentation exhaustive
- **v4.0** (Octobre 2025) : Pipeline ML avec scores d'attractivité et modèle de Huff exact par IRIS
- **v3.x** (2024) : Versions expérimentales du modèle de Huff
- **v2.x** (2024) : Premiers pipelines de préparation de données
- **v1.x** (2023) : Prototypes initiaux

---

**Projet** : Modélisation Potentiel Pharmacies 65+
**Dernière mise à jour** : Novembre 2025
**Auteur** : Équipe Data Science