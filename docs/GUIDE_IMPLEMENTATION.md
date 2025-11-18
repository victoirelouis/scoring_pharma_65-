# Guide d'Implémentation - Scoring Pharmacies 65+

## Vue d'ensemble

Ce document complète le README méthodologique principal en documentant **l'implémentation concrète** du projet à travers les différents scripts Python.

Le projet est organisé en **2 phases distinctes** :
- **Phase 0** (`scripts/`) : Préparation des données de base (HUBS, isochrones, enrichissement)
- **Phase 1** (`intermediaire/scripts/`) : Pipeline ML et analyses de corrélations

---

## Architecture des Dossiers

```
scoring_pharma_65-/
│
├── README.md                           # Méthodologie détaillée complète
├── GUIDE_IMPLEMENTATION.md             # Ce document (guide pratique)
│
├── scripts/                            # PHASE 0 : Préparation données de base
│   ├── (25 scripts Python)
│   └── cache/                          # Cache des isochrones
│
├── data/                               # Données brutes et enrichies
│   ├── input/                          # Données sources
│   │   ├── data_cleaning/              # Pharmacies nettoyées
│   │   ├── enrichissement/             # Matrice Pharmacie×IRIS
│   │   ├── geo/                        # Contours IRIS
│   │   ├── iris_insee/                 # Population et revenus INSEE
│   │   ├── RPPS/                       # Médecins géocodés (10 fichiers)
│   │   ├── FINESS.csv                  # Établissements sanitaires
│   │   └── INSEE_hebergements_classes.csv
│   │
│   └── output/                         # Résultats Phase 0
│       ├── HUBS_unified_final.csv      # HUBS finaux (71 MB) ⭐
│       └── pharmacies_final_avec_variables_touristiques.csv
│
├── intermediaire/                      # PHASE 1 : Pipeline ML
│   ├── scripts/                        # Scripts ML (13 scripts)
│   ├── input_verif/                    # SIG_P20.CSV
│   └── output/                         # Résultats ML et analyses
│       ├── pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv ⭐ FINAL
│       ├── modeles_lightgbm/           # 4 modèles LightGBM
│       └── (fichiers de corrélations)
│
├── src/                                # Code source (vide)
└── cache/                              # Cache global
```

---

## PHASE 0 : Préparation des Données de Base

Ces scripts créent les fichiers fondamentaux utilisés par le pipeline ML.

### 📍 Étape 1 : Géocodage RPPS

**Objectif** : Géocoder les adresses des médecins RPPS pour obtenir leurs coordonnées GPS.

**Scripts** :
- `geocode_rpps_optimise.py` - Géocodage via API BAN (Base Adresse Nationale)
- `test_geocode_10.py` - Test du géocodage sur 10 entrées

**Input** : Fichiers RPPS bruts (non versionnés)
**Output** : `data/input/RPPS/RPPS_format_BAN_partie_X_corrige.geocoded.csv` (10 fichiers)

**Commandes** :
```bash
cd scripts
python geocode_rpps_optimise.py
```

---

### 🏥 Étape 2 : Création des HUBS Médicaux

**Objectif** : Créer une base unifiée de tous les points d'intérêt (médecins, hôpitaux, commerces, transports).

#### 2.1 Création initiale

**Scripts de création** :
- `create_hubs_file.py` - Création initiale des hubs
- `create_hubs_file_OSM.py` - Ajout données OpenStreetMap
- `create_hubs_finess_only.py` - HUBS uniquement depuis FINESS
- `process_finess_with_weights.py` - Traitement FINESS avec poids
- `finess_categories_weights_seniors_only.py` - Poids spécifiques seniors

**Input** :
- `data/input/FINESS.csv` - Établissements sanitaires et sociaux
- OpenStreetMap via API Overpass

**Output** : Fichiers HUBS intermédiaires

#### 2.2 Fusion et enrichissement

**Scripts de fusion** :
- `merge_finess_rpps_hubs.py` - Fusion FINESS + RPPS géocodés
- `merge_rpps_add_weights.py` - Ajout des poids aux médecins RPPS
- `fusion_hubs_complet.py` - Fusion complète de toutes les sources

**Input** :
- Fichiers HUBS FINESS
- `data/input/RPPS/*.geocoded.csv`
- Données OSM

**Output** : `data/output/HUBS_unified_corriges.csv`

#### 2.3 Nettoyage et déduplication

**Scripts** :
- `corriger_dedoublonner.py` - Déduplication des hubs (même coordonnées GPS)
- `corriger_bonus.py` - Correction des bonus d'attractivité
- `merge_missing_clean.py` - Fusion des données manquantes

**Input** : `HUBS_unified_corriges.csv`
**Output** : `data/output/HUBS_unified_final.csv` (71 MB) ⭐

**Caractéristiques du fichier final** :
- 639,299 hubs au total
- Catégories : Cabinets médicaux, Hôpitaux, EHPAD, Marchés, Transports, etc.
- Poids d'attractivité pour chaque catégorie
- Coordonnées GPS précises

**Commandes** :
```bash
cd scripts
python process_finess_with_weights.py
python merge_finess_rpps_hubs.py
python corriger_dedoublonner.py
python corriger_bonus.py
# Résultat : data/output/HUBS_unified_final.csv
```

---

### 🗺️ Étape 3 : Génération des Isochrones

**Objectif** : Calculer les zones de chalandise réelles de chaque pharmacie (temps de trajet).

**Scripts principaux** :
- `generate_isochrones.py` - Génération isochrones complètes (API Valhalla/OSRM)
- `generate_simple_isochrones.py` - Isochrones simplifiées
- `generate_drive_short_isochrones.py` - Isochrones courtes en voiture
- `generate_geometric_fallback.py` - Fallback géométrique (cercles euclidiens)
- `generate_missing_isochrones.py` - Complétion des isochrones manquantes
- `generate_isochrones_backup.py` - Backup/reprise

**Scripts de gestion** :
- `prepare_pharmacies_for_isochrones.py` - Préparation du fichier pharmacies
- `manage_isochrone_batches.py` - Gestion des batches (par département)
- `monitor_isochrones.py` - Monitoring de la progression

**Types d'isochrones** :
- Walk 5min, 10min, 15min, 20min (zones urbaines)
- Drive 5min, 10min, 15min (zones rurales/périurbaines)

**Technologies** :
- OSMnx pour les graphes routiers
- API Valhalla ou OSRM pour le calcul des isochrones
- GeoPandas pour les opérations géographiques

**Input** : `data/input/data_cleaning/pharmacies_final.csv`
**Output** : Fichiers GeoJSON par pharmacie (stockés dans cache/, non versionnés)

**Commandes** :
```bash
cd scripts
python prepare_pharmacies_for_isochrones.py
python manage_isochrone_batches.py
python monitor_isochrones.py
```

**Note** : La génération complète des isochrones peut prendre plusieurs jours.

---

### 📊 Étape 4 : Enrichissement des Pharmacies

**Objectif** : Enrichir les données pharmacies avec données INSEE et variables touristiques.

#### 4.1 Enrichissement INSEE

**Script** : `enrichir_pharmacies_optimise.py`

**Opérations** :
- Intersection isochrones × IRIS pour chaque pharmacie
- Agrégation des données démographiques par isochrone
- Calcul densité de population 65+, revenus médians, etc.

**Input** :
- `data/input/data_cleaning/pharmacies_final.csv`
- `data/input/iris_insee/population_age.csv`
- `data/input/iris_insee/revenus.csv`
- Isochrones GeoJSON

**Output** : `data/output/pharmacies_enrichies_insee.csv` (13 MB)

#### 4.2 Variables Touristiques

**Script** : `calcul_variables_touristiques.py`

**Opérations** :
- Identification zones balnéaires (distance côte, résidences secondaires)
- Identification zones montagne (altitude, stations de ski)
- Identification zones thermales (fichier FINESS)
- Calcul capacité d'accueil touristique par isochrone

**Input** :
- `pharmacies_enrichies_insee.csv`
- `data/input/INSEE_hebergements_classes.csv`
- Données géographiques (altitude, littoral)

**Output** : `data/output/pharmacies_final_avec_variables_touristiques.csv` (2.6 MB)

**Commandes** :
```bash
cd scripts
python enrichir_pharmacies_optimise.py
python calcul_variables_touristiques.py
```

---

### ✅ Étape 5 : Contrôle Qualité

**Script** : `check_data_quality.py`

**Vérifications** :
- Complétude des données (pas de NaN critiques)
- Cohérence géographique (coordonnées GPS valides)
- Cohérence des CA (éthique + conseil ≤ total)
- Couverture isochrones (toutes les pharmacies ont des isochrones)

**Commandes** :
```bash
cd scripts
python check_data_quality.py
```

---

## PHASE 1 : Pipeline ML et Analyses

Cette phase utilise les données préparées en Phase 0 pour calculer l'attractivité, estimer les clients 65+, et analyser les corrélations.

### 🔄 Pipeline ML Principal (6 étapes)

#### Étape 1 : `ml_01_prepare_hubs_par_isochrone.py`

**Objectif** : Agréger les hubs médicaux par isochrone de chaque pharmacie.

**Opérations** :
- Pour chaque pharmacie, intersection isochrones × HUBS
- Comptage par catégorie (nb médecins, nb hôpitaux, nb EHPAD, etc.)
- Calcul des bonus d'attractivité par catégorie

**Input** :
- `data/output/HUBS_unified_final.csv`
- Isochrones GeoJSON
- `data/input/data_cleaning/pharmacies_final.csv`

**Output** : `intermediaire/output/pharmacies_avec_hubs.csv` (12 MB)

**Colonnes ajoutées** :
- `nb_medecins_5min`, `nb_medecins_10min`, etc.
- `nb_hopitaux_drive_10min`
- `nb_ehpad_walk_15min`
- `bonus_hubs_total`

---

#### Étape 2 : `ml_02_prepare_concurrence.py`

**Objectif** : Calculer la distance à la pharmacie concurrente la plus proche.

**Opérations** :
- Calcul de la matrice de distances entre toutes les pharmacies
- Pour chaque pharmacie, identifier la plus proche concurrente
- Calcul du degré d'isolement/de concurrence

**Input** : `data/input/data_cleaning/pharmacies_final.csv`

**Output** : `intermediaire/output/pharmacies_avec_concurrence.csv` (3.1 MB)

**Colonnes ajoutées** :
- `distance_concurrente_plus_proche_km`
- `nb_concurrentes_rayon_5km`

---

#### Étape 3 : `ml_03_prepare_population_isochrones.py`

**Objectif** : Agréger les données démographiques IRIS par isochrone.

**Opérations** :
- Intersection isochrones × IRIS
- Pondération par le ratio de couverture (surface IRIS couverte / surface IRIS totale)
- Agrégation de la population par âge, revenus, etc.

**Input** :
- `data/input/iris_insee/population_age.csv`
- `data/input/iris_insee/revenus.csv`
- `data/input/geo/contours_iris.gpkg`
- Isochrones GeoJSON

**Output** : `intermediaire/output/pharmacies_avec_population_isochrones.csv` (34 MB)

**Colonnes ajoutées** :
- `population_65_plus_walk_10min`
- `population_75_84_drive_15min`
- `revenu_median_walk_10min`
- `densite_65plus_rayon_2km`

---

#### Étape 4 : `ml_04_integration_complete.py`

**Objectif** : Fusionner toutes les données en un seul dataset.

**Opérations** :
- Fusion des 4 sources : hubs, concurrence, population, tourisme
- Nettoyage des valeurs manquantes
- Calcul de features dérivées (ratios, indicateurs composites)
- Feature engineering

**Input** :
- `pharmacies_avec_hubs.csv`
- `pharmacies_avec_concurrence.csv`
- `pharmacies_avec_population_isochrones.csv`
- `data/output/pharmacies_final_avec_variables_touristiques.csv`

**Output** : `intermediaire/output/pharmacies_features_complet.csv` (52 MB)

**Nombre de features** : ~150 colonnes

---

#### Étape 5 : `ml_05_score_attractivite_lightgbm.py`

**Objectif** : Calculer le score d'attractivité composite avec 4 modèles LightGBM.

**Modèles entraînés** :
1. **CA Total** - Prédiction du CA global
2. **CA Éthique** - Prédiction du CA médicaments prescrits
3. **CA Conseil** - Prédiction du CA parapharmacie
4. **Delta CA** - Prédiction de la variation saisonnière

**Algorithme** :
- LightGBM (Gradient Boosting)
- GridSearchCV pour l'optimisation des hyperparamètres
- Validation croisée 5-fold

**Features utilisées** :
- Population 65+ par isochrone
- Densité médicale
- Revenus médians
- Variables touristiques
- Nb de concurrentes
- Bonus hubs

**Input** : `pharmacies_features_complet.csv`

**Output** :
- `intermediaire/output/pharmacies_avec_scores_attractivite.csv` (8.5 MB)
- `intermediaire/output/modeles_lightgbm/model_ca_total.pkl`
- `intermediaire/output/modeles_lightgbm/model_ca_ethique.pkl`
- `intermediaire/output/modeles_lightgbm/model_ca_conseil.pkl`
- `intermediaire/output/modeles_lightgbm/model_delta.pkl`
- `intermediaire/output/rapport_gridsearch_attractivite.txt`

**Colonnes ajoutées** :
- `score_ca_total`
- `score_ca_ethique`
- `score_ca_conseil`
- `score_delta`
- `score_attractivite_65plus_composite` ⭐ (moyenne pondérée)

**Commandes** :
```bash
cd intermediaire/scripts
python ml_01_prepare_hubs_par_isochrone.py
python ml_02_prepare_concurrence.py
python ml_03_prepare_population_isochrones.py
python ml_04_integration_complete.py
python ml_05_score_attractivite_lightgbm.py
```

---

#### Étape 6 : `ml_06_HUFF_EXACT_IRIS_FIXED.py` ⭐

**Objectif** : Appliquer le modèle de Huff pour distribuer la population 65+ aux pharmacies.

**Principe du modèle de Huff** :
1. Pour chaque IRIS : récupérer les pharmacies accessibles (matrice Pharmacie×IRIS)
2. Calculer l'utilité de chaque pharmacie : U_j = Attractivité_j × w_IRIS
3. Normaliser pour obtenir les parts de marché : part_j = U_j / Σ(U_k)
4. Distribuer la population : clients_j += population_IRIS × part_j

**Garantie mathématique** :
- Σ(parts de marché par IRIS) = 100%
- Donc Σ(clients toutes pharmacies) = Population couverte
- **Conservation parfaite : ratio = 1.000000**

**Input** :
- `data/input/data_cleaning/pharmacies_final.csv`
- `data/input/enrichissement/pharmacie_iris_pond_cleaned.csv` (matrice Pharmacie×IRIS avec w_IRIS)
- `data/input/iris_insee/population_age.csv`
- `pharmacies_avec_scores_attractivite.csv`

**Output** : `intermediaire/output/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` (2.3 MB) ⭐

**Colonnes du fichier final** :
- `id_pharmacie`
- `nom_pharmacie`
- `attractivite_huff` (score normalisé [0.1-1.0])
- `clients_65_79` (nombre de clients 65-79 ans)
- `clients_80_plus` (nombre de clients 80+ ans)
- `clients_65_plus_total` (total)
- `visites_annuelles_65plus` (clients × 12)
- `decile_clients_65plus` (décile 1-10)

**Résultats** :
- Population France 65+ : 14,125,725
- Population couverte : 13,302,521 (94.2%)
- Clients distribués : 13,302,521
- **Conservation : 100.0%** ✓
- Pharmacies avec clients : 18,208 / 19,307

**Commandes** :
```bash
cd intermediaire/scripts
python ml_06_HUFF_EXACT_IRIS_FIXED.py
```

---

### 📈 Analyses de Corrélations (3 scripts)

#### Analyse 1 : `analyse_correlation_sig_p20.py`

**Objectif** : Analyser la corrélation entre données d'activité réelle (SIG_P20) et estimations clients 65+.

**Input** :
- `intermediaire/input_verif/SIG_P20.CSV` (UN et CAHT par pharmacie/mois)
- `pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`

**Opérations** :
- GroupBy `Pvactif` pour sommer UN et CAHT sur 12 mois
- Fusion avec estimations clients 65+
- Calcul des corrélations Pearson

**Output** :
- `correlation_sig_p20_clients65.csv`
- `correlation_sig_p20_graphs.png` (4 scatterplots)

**Résultats** :
- Corr UN-Clients 65+ : 0.150
- Corr CAHT-Clients 65+ : 0.210
- Ratio moyen : 0.70 UN par client, 47.53€ CAHT par client

---

#### Analyse 2 : `analyse_correlation_avancee.py`

**Objectif** : Analyser les corrélations par type de zone et tourisme.

**Input** :
- `correlation_sig_p20_clients65.csv`
- `pharmacies_avec_scores_attractivite.csv`

**Opérations** :
- Classification tourisme (départements côtiers, montagne)
- Calcul corrélations par type_zone (rural, urbain, urbain_dense)
- Calcul corrélations par zone touristique

**Output** :
- `correlation_avancee_complete.csv`
- `correlation_avancee_graphs.png` (6 graphiques)
- `summary_correlations_par_categorie.csv`

**Résultats clés** :
- **Urbain dense** : Corr CAHT = 0.342 (meilleure)
- **Zones touristiques** : Corr CAHT = 0.220 (vs 0.113 non-touristiques)
- **Zones montagne** : Corr CAHT = 0.293 (la plus forte des zones touristiques)

---

#### Analyse 3 : `analyse_proximite_hubs_medicaux.py`

**Objectif** : Analyser corrélations selon proximité aux hubs médicaux (médecins, hôpitaux).

**Input** :
- `data/output/HUBS_unified_final.csv`
- `correlation_sig_p20_clients65.csv`

**Opérations** :
- Filtrage hubs médicaux (cabinets médicaux, hôpitaux)
- Calcul de proximité avec scipy.spatial.cKDTree
- Comptage hubs dans rayons 500m, 1km, 2km
- Création de catégories de proximité

**Output** :
- `correlation_hubs_medicaux_complete.csv`
- `correlation_hubs_medicaux_graphs.png` (6 graphiques)
- `summary_hubs_medicaux.csv`

**Résultats clés** :
- **4-10 hubs à 1km** : Corr CAHT = 0.320 (meilleure)
- **1 hub à 1km** : Corr CAHT = 0.263
- **Aucun hub** : Corr CAHT = 0.192

**Commandes** :
```bash
cd intermediaire/scripts
python analyse_correlation_sig_p20.py
python analyse_correlation_avancee.py
python analyse_proximite_hubs_medicaux.py
```

---

### 🛠️ Scripts Utilitaires

- **config_ml.py** - Configuration globale (chemins, paramètres)
- **data_quality_check.py** - Vérification qualité des données
- **nettoyer_matrice_iris_ET_pharmacies.py** - Nettoyage matrice (supprime IRIS sans population et pharmacies absentes)
- **nettoyer_matrice_iris_sans_pop.py** - Nettoyage IRIS uniquement

---

## Exécution Complète du Projet

### Ordre d'exécution recommandé

```bash
# ========== PHASE 0 : Préparation Données ==========
cd scripts

# 1. Géocodage RPPS (si nécessaire)
python geocode_rpps_optimise.py

# 2. Création HUBS
python process_finess_with_weights.py
python merge_finess_rpps_hubs.py
python corriger_dedoublonner.py
python corriger_bonus.py

# 3. Génération isochrones
python prepare_pharmacies_for_isochrones.py
python manage_isochrone_batches.py

# 4. Enrichissement
python enrichir_pharmacies_optimise.py
python calcul_variables_touristiques.py

# 5. Contrôle qualité
python check_data_quality.py

# ========== PHASE 1 : Pipeline ML ==========
cd ../intermediaire/scripts

# 6. Pipeline ML
python ml_01_prepare_hubs_par_isochrone.py
python ml_02_prepare_concurrence.py
python ml_03_prepare_population_isochrones.py
python ml_04_integration_complete.py
python ml_05_score_attractivite_lightgbm.py
python ml_06_HUFF_EXACT_IRIS_FIXED.py

# 7. Analyses de corrélation
python analyse_correlation_sig_p20.py
python analyse_correlation_avancee.py
python analyse_proximite_hubs_medicaux.py
```

---

## Fichiers de Sortie Essentiels

### Phase 0
- ⭐ `data/output/HUBS_unified_final.csv` (71 MB) - Base HUBS complète
- ⭐ `data/output/pharmacies_final_avec_variables_touristiques.csv` (2.6 MB)

### Phase 1
- ⭐ `intermediaire/output/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` (2.3 MB) - **RÉSULTAT FINAL**
- `intermediaire/output/pharmacies_avec_scores_attractivite.csv` (8.5 MB) - Scores LightGBM
- `intermediaire/output/modeles_lightgbm/*.pkl` (4 modèles)
- Fichiers de corrélation (3 fichiers CSV + 3 PNG)

---

## Dépendances Python

```
pandas
numpy
scikit-learn
lightgbm
scipy
geopandas
shapely
osmnx
requests
matplotlib
seaborn
```

---

## Notes Importantes

### Matrice Pharmacie×IRIS

Le fichier `data/input/enrichissement/pharmacie_iris_pond_cleaned.csv` est **critique**.

**Structure** :
- `id_pharmacie` - ID pharmacie
- `CODE_IRIS` - Code IRIS
- `w_IRIS` - Poids normalisé (Σw_IRIS par IRIS = 1.0)

Ce fichier définit quels IRIS sont accessibles depuis chaque pharmacie et avec quel poids. Il est généré à partir des isochrones.

### Conservation de la Population

Le modèle de Huff garantit mathématiquement que **100% de la population couverte est distribuée** aux pharmacies, sans double comptage ni perte.

Cela n'est vrai que parce que les poids w_IRIS sont normalisés : pour chaque IRIS, Σ(w_IRIS de toutes les pharmacies) = 1.0.

### Nettoyage Effectué

60+ fichiers obsolètes supprimés :
- 47 scripts de debug/diagnostic
- 3 versions obsolètes de ml_06
- 21 rapports JSON de validation
- 8 versions intermédiaires de matrices IRIS

Le projet contient maintenant uniquement les **38 scripts essentiels** (25 Phase 0 + 13 Phase 1).

---

## Contact

**Projet** : Scoring Pharmacies 65+
**Organisation** : GERS
**Responsable** : Victoire LOUIS
**Date** : Novembre 2025