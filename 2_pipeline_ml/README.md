# Phase 2 - Pipeline Machine Learning

Ce dossier contient le **pipeline ML complet** pour l'estimation des clients 65+ par pharmacie utilisant le modèle de Huff avec scores d'attractivité LightGBM.

---

## 📁 Structure du dossier

```
2_pipeline_ml/
├── scripts/                     # Scripts organisés par fonction
│   ├── 1_pipeline_ml/          # Pipeline principal (6 étapes)
│   ├── 2_analyses_correlations/ # Analyses de corrélation (3 scripts)
│   └── 3_utilitaires/          # Outils de config et validation
└── output/                      # Tous les résultats du pipeline
    ├── 1_etapes_pipeline/      # Résultats intermédiaires
    ├── 2_resultats_finaux/     # Fichier final clients 65+
    ├── 3_analyses_correlations/ # Graphiques et rapports
    ├── 4_modeles/              # Modèles LightGBM sauvegardés
    └── 5_rapports/             # Rapports d'exécution
```

---

## 🎯 Vue d'ensemble

**Objectif** : Estimer le nombre de clients 65+ pour chaque pharmacie en France en combinant :
- Données démographiques INSEE par IRIS
- Zones d'accessibilité (isochrones)
- Points d'attractivité médicaux/touristiques (HUBS)
- Modèle de Huff avec scores d'attractivité ML

**Résultat final** : `pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` (19 307 pharmacies)

---

## 🔧 SCRIPTS - Pipeline ML (`scripts/`)

### Pipeline 1 : Pipeline ML principal (`1_pipeline_ml/`)

Exécution séquentielle des 6 étapes :

#### 1. `ml_01_prepare_hubs_par_isochrone.py`
**Objectif** : Compter les points d'attractivité (HUBS) dans chaque isochrone

**Input** :
- `../1_data_prep/output/HUBS_unified_final.csv` : Points d'attractivité
- `../1_data_prep/output/isochrones/` : 115k zones d'accessibilité
- `../1_data_prep/output/pharmacies_final.csv` : Base pharmacies

**Traitement** :
- Charge tous les isochrones (walk_5min, walk_10min, drive_5/10/15/20min)
- Compte les HUBS par catégorie dans chaque zone
- Multiprocessing pour performance

**Output** : `output/1_etapes_pipeline/pharmacies_avec_hubs.csv` (~12 MB)
- Colonnes ajoutées : `hubs_medecins_drive_10min`, `hubs_hopitaux_walk_5min`, etc.

---

#### 2. `ml_02_prepare_concurrence.py`
**Objectif** : Calculer la concurrence entre pharmacies

**Input** :
- `../1_data_prep/output/pharmacies_final.csv`

**Traitement** :
- KDTree spatial pour trouver pharmacies voisines
- Calcul nombre de concurrents dans rayons 1, 3, 5 km

**Output** : `output/1_etapes_pipeline/pharmacies_avec_concurrence.csv` (~3 MB)
- Colonnes ajoutées : `nb_concurrents_1km`, `nb_concurrents_3km`, `nb_concurrents_5km`

---

#### 3. `ml_03_prepare_population_isochrones.py`
**Objectif** : Agréger la population démographique par isochrone

**Input** :
- `../1_data_prep/output/matrice_w_iris_100pct.csv` : Matrice Pharmacie×IRIS avec w_IRIS (100% couverture)
- `../1_data_prep/input/2_insee_brutes/age_profession.CSV` : Population par âge et IRIS

**Traitement** :
- Pour chaque pharmacie : agrégation pondérée (w_IRIS) de la population
- Calcul pop_65_79, pop_80_plus, pop_totale par isochrone
- Multiprocessing par batch

**Output** : `output/1_etapes_pipeline/pharmacies_avec_population_isochrones.csv` (~34 MB)
- Colonnes ajoutées : `pop_65_79_drive_10min`, `pop_80_plus_walk_5min`, etc.

---

#### 4. `ml_04_integration_complete.py`
**Objectif** : Fusionner toutes les features (HUBS, concurrence, population, tourisme)

**Input** :
- `output/1_etapes_pipeline/pharmacies_avec_hubs.csv`
- `output/1_etapes_pipeline/pharmacies_avec_concurrence.csv`
- `output/1_etapes_pipeline/pharmacies_avec_population_isochrones.csv`
- `../1_data_prep/output/pharmacies_final_avec_variables_touristiques.csv`

**Traitement** :
- Fusion via `id_pharmacie`
- Vérification complétude des données
- Création du dataset complet pour ML

**Output** : `output/1_etapes_pipeline/pharmacies_features_complet.csv` (~52 MB)
- **262 features** prêtes pour entraînement ML

---

#### 4b. `ml_04b_enrichir_sig_p20.py` (OPTIONNEL)
**Objectif** : Enrichir le dataset ML avec les variables réelles d'activité du SIG_P20

**Input** :
- `output/1_etapes_pipeline/pharmacies_features_complet.csv`
- `../1_data_prep/input/5_validation/SIG_P20.CSV` : Données d'activité mensuelles

**Traitement** :
- Agrégation des données mensuelles SIG_P20 (année la plus récente)
- Ajout de 2 variables d'activité réelle :
  - `UN_sig` : Unités vendues (volume d'activité)
  - `CAHT_sig` : Chiffre d'affaires total HT
- Imputation par médiane pour valeurs manquantes (21 pharmacies, ~0.1%)
- Normalisation Min-Max [0-1] pour compatibilité PCA

**Output** : `output/1_etapes_pipeline/pharmacies_features_complet_sig_enriched.csv` (~52 MB)
- **266 features** : 262 originales + 4 nouvelles (UN_sig, CAHT_sig + versions normalisées)
- **Taux de matching** : 99.9% (19 286 / 19 307 pharmacies)

**Note** : Ce script est optionnel. Il ajoute des indicateurs réels d'activité pharmacie pour améliorer le score d'attractivité PCA. Les variables CA_conseil et CA_ethique ne sont pas disponibles dans SIG_P20.

**Utilisation** :
```bash
python 1_pipeline_ml/ml_04b_enrichir_sig_p20.py
# Puis modifier ml_05 pour utiliser pharmacies_features_complet_sig_enriched.csv au lieu de pharmacies_features_complet.csv
```

---

#### 5. `ml_05_score_attractivite_pca.py`
**Objectif** : Calculer un score d'attractivité composite à partir des 300+ features disponibles

**Input** :
- `output/1_etapes_pipeline/pharmacies_features_complet.csv`

**Approche** :
Le script utilise l'**Analyse en Composantes Principales (PCA)** pour réduire la dimensionnalité des 300+ features et calculer un **score d'attractivité composite [0.1 - 1.0]**.

**Méthodologie PCA** :
1. **Sélection des features** : Population accessible, HUBS de proximité, concurrence, démographie, tourisme
2. **Standardisation** : StandardScaler pour normaliser les features
3. **Application PCA** : Extraction des composantes principales (variance expliquée > 1%)
4. **Calcul du score** : Pondération par variance expliquée
5. **Normalisation** : Score dans l'intervalle [0.1, 1.0]

**Avantages** :
- ✅ Approche non supervisée (pas besoin de données historiques)
- ✅ Prend en compte toutes les pharmacies
- ✅ Capture les dimensions latentes de l'attractivité
- ✅ Robuste aux corrélations entre features

**Output** :
- `output/1_etapes_pipeline/pharmacies_avec_scores_attractivite.csv` (~8.5 MB)
  - Colonne : `score_attractivite_65plus_composite`
- `output/5_rapports/rapport_pca_attractivite.txt`

---

#### 6. `ml_06_HUFF_EXACT_IRIS_FIXED.py` ⭐
**Objectif** : Appliquer le modèle de Huff pour distribuer la population 65+ aux pharmacies

**Input** :
- `output/1_etapes_pipeline/pharmacies_avec_scores_attractivite.csv`
- `../1_data_prep/output/matrice_w_iris_100pct.csv` : Matrice w_IRIS (100% couverture)
- `../1_data_prep/input/2_insee_brutes/age_profession.CSV` : Population par IRIS

**Modèle de Huff** :
```
Pour chaque IRIS :
  1. Récupérer les pharmacies accessibles (w_IRIS > 0)
  2. Calculer utilité : U_j = Attractivité_j × w_IRIS_j
  3. Normaliser : part_marché_j = U_j / Σ(U_k)
  4. Distribuer : clients_j += pop_IRIS × part_marché_j
```

**Garanties** :
- ✅ Conservation exacte de la population : Σ(clients) = Population couverte
- ✅ Pas de doublons de distribution
- ✅ Respect de l'accessibilité géographique

**Output** : `output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` ⭐ (~2.3 MB)

**Colonnes finales** :
- `id_pharmacie` : Identifiant unique
- `nom_pharmacie` : Nom de la pharmacie
- `attractivite_huff` : Score d'attractivité normalisé [0.1-1.0]
- `clients_65_79` : Nombre de clients 65-79 ans
- `clients_80_plus` : Nombre de clients 80+ ans
- `clients_65_plus_total` : Total clients 65+
- `visites_annuelles_65plus` : Visites annuelles (clients × 12)
- `decile_clients_65plus` : Décile (1 = moins de clients, 10 = plus de clients)

**Résultats typiques** :
- Population France 65+ : 14,125,725
- Population couverte : 13,302,521 (94.2%)
- Clients distribués : 13,302,521 (conservation 100.0%)
- Pharmacies avec clients : 18,208 / 19,307

---

### Pipeline 2 : Analyses de corrélation (`2_analyses_correlations/`)

Scripts pour valider la qualité des estimations via corrélations avec données réelles (SIG_P20).

#### 7. `analyse_correlation_sig_p20.py`
**Objectif** : Corrélation globale entre SIG_P20 (UN, CAHT) et clients 65+

**Input** :
- `output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`
- `input_verif/SIG_P20.CSV` : Données d'activité réelles

**Output** :
- `output/3_analyses_correlations/correlation_sig_p20_clients65.csv`
- Graphiques scatter plots (UN vs clients, CAHT vs clients)

**Résultats attendus** :
- Corrélation UN vs Clients 65+ : ~0.15
- Corrélation CAHT vs Clients 65+ : ~0.21

---

#### 8. `analyse_correlation_avancee.py`
**Objectif** : Corrélations stratifiées par type de zone et tourisme

**Input** :
- `output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`
- `input_verif/SIG_P20.CSV`

**Analyses** :
- Corrélations par `type_zone` (urbain_dense, urbain, periurbain, rural)
- Corrélations par profil touristique (tourisme oui/non)
- Analyses par déciles de clients

**Output** :
- `output/3_analyses_correlations/correlation_avancee_complete.csv`
- `output/3_analyses_correlations/summary_correlations_par_categorie.csv`
- Graphiques par catégorie

**Insights attendus** :
- Urbain dense : corrélation forte (~0.34)
- Rural : corrélation faible (~0.14)
- Zones touristiques : corrélation meilleure (~0.22)

---

#### 9. `analyse_proximite_hubs_medicaux.py`
**Objectif** : Corrélations selon proximité aux HUBS médicaux

**Input** :
- `output/2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`
- `input_verif/SIG_P20.CSV`

**Analyses** :
- Stratification par nombre de médecins/hôpitaux dans rayon 1km
- Catégories : 0 hubs, 1-3 hubs, 4-10 hubs, 10+ hubs

**Output** :
- `output/3_analyses_correlations/correlation_hubs_medicaux_complete.csv`
- `output/3_analyses_correlations/summary_hubs_medicaux.csv`
- Graphiques par catégorie de proximité

**Insights attendus** :
- 4-10 hubs à 1km : meilleure corrélation (~0.32)
- Aucun hub : corrélation modérée (~0.19)

---

### Pipeline 3 : Utilitaires (`3_utilitaires/`)

#### `config_ml.py`
**Rôle** : Configuration globale du pipeline ML Phase 2

**Contenu** :
- **Chemins des fichiers** :
  - Input depuis Phase 1 (`DATA_PREP_OUTPUT_DIR`)
  - Output Phase 2 (`PIPELINE_ML_OUTPUT_DIR`)
  - Références à `matrice_w_iris_100pct.csv`
- **Hyperparamètres LightGBM** : `num_leaves`, `learning_rate`, `n_estimators`
- **Paramètres modèle de Huff** : exposant β, seuils
- **Configuration multiprocessing** : Workers, batch_size

**Usage** :
```python
from config_ml import INPUT_FILES_ML, OUTPUT_FILES_ML
```

📝 **Note** : Les scripts utilitaires de préparation de données ont été déplacés vers Phase 1 :
- `associate_pharmacies_to_iris.py` → `1_data_prep/scripts/3_isochrones/d_*`
- `associate_uncovered_iris.py` → `1_data_prep/scripts/3_isochrones/e_*`
- `data_quality_check.py` → `1_data_prep/scripts/5_validation/b_*`
- `nettoyer_matrice_iris.py` → obsolète (intégré dans `c_calculate_w_iris.py`)

---

## 📤 OUTPUT - Résultats générés (`output/`)

### Structure des résultats :

| Dossier | Description | Taille approx. |
|---------|-------------|----------------|
| **`1_etapes_pipeline/`** | Résultats intermédiaires (6 étapes) | ~110 MB |
| **`2_resultats_finaux/`** | Fichier final clients 65+ ⭐ | ~2.3 MB |
| **`3_analyses_correlations/`** | Graphiques + rapports CSV | ~5 MB |
| **`4_modeles/`** | 4 modèles LightGBM sauvegardés | ~15 MB |
| **`5_rapports/`** | Logs d'exécution, GridSearch | ~1 MB |

### Fichier final utilisé pour décisions :

**`2_resultats_finaux/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`**

Ce fichier contient pour chaque pharmacie :
- Estimation du nombre de clients 65+ (65-79 ans et 80+ ans)
- Score d'attractivité normalisé
- Visites annuelles estimées
- Décile de performance

---

## 🔄 Ordre d'exécution complet

### Prérequis : Phase 1 (1_data_prep) terminée

Les fichiers suivants doivent exister :
- `../1_data_prep/output/pharmacies_final_avec_variables_touristiques.csv`
- `../1_data_prep/output/HUBS_unified_final.csv`
- `../1_data_prep/output/isochrones/` (115k fichiers)
- `../1_data_prep/output/matrice_w_iris_100pct.csv`

### Exécution du pipeline ML :

```bash
cd 2_pipeline_ml/scripts

# Pipeline ML principal (6 étapes séquentielles)
python 1_pipeline_ml/ml_01_prepare_hubs_par_isochrone.py
python 1_pipeline_ml/ml_02_prepare_concurrence.py
python 1_pipeline_ml/ml_03_prepare_population_isochrones.py
python 1_pipeline_ml/ml_04_integration_complete.py
python 1_pipeline_ml/ml_05_score_attractivite_pca.py
python 1_pipeline_ml/ml_06_HUFF_EXACT_IRIS_FIXED.py

# Analyses de corrélation (validation)
python 2_analyses_correlations/analyse_correlation_sig_p20.py
python 2_analyses_correlations/analyse_correlation_avancee.py
python 2_analyses_correlations/analyse_proximite_hubs_medicaux.py
```

### Temps d'exécution estimé :

| Script | Durée |
|--------|-------|
| ml_01_prepare_hubs_par_isochrone.py | ~30-45 min |
| ml_02_prepare_concurrence.py | ~5 min |
| ml_03_prepare_population_isochrones.py | ~15-20 min |
| ml_04_integration_complete.py | ~2 min |
| ml_05_score_attractivite_pca.py | ~5-10 min |
| ml_06_HUFF_EXACT_IRIS_FIXED.py | ~5-10 min |
| Analyses de corrélation (×3) | ~5 min chacune |
| **TOTAL** | **~90-120 min** |

---

## 📊 Métriques de qualité

### Modèle de Huff :

- ✅ **Conservation population** : 100.0% (garantie mathématique)
- ✅ **Couverture** : ~94% de la population 65+ française
- ✅ **Distribution** : 18,208 / 19,307 pharmacies ont des clients

### Corrélations avec SIG_P20 :

| Stratification | Corrélation UN vs Clients | Corrélation CAHT vs Clients |
|----------------|---------------------------|----------------------------|
| **Global** | 0.15 | 0.21 |
| Urbain dense | 0.34 | 0.42 |
| Rural | 0.14 | 0.18 |
| Zones touristiques | 0.22 | 0.28 |
| 4-10 hubs médicaux | 0.32 | 0.38 |

### Performance PCA :

| Métrique | Valeur |
|----------|--------|
| **Variance expliquée** (3 premières composantes) | ~65-75% |
| **Nombre de composantes retenues** | Variable (seuil: variance > 1%) |
| **Features les plus contributives** | Pop. drive_10min, nb_concurrents, hubs_medecins, Pop. 65+ |

---

## 🔗 Fichiers requis depuis Phase 1

Le pipeline ML dépend des outputs de `../1_data_prep/` :

### Depuis `1_data_prep/output/` :
- `pharmacies_final.csv` : Base pharmacies géocodées
- `pharmacies_final_avec_variables_touristiques.csv` : Dataset enrichi INSEE + tourisme
- `HUBS_unified_final.csv` : Points d'attractivité dédoublonnés
- **`matrice_w_iris_100pct.csv`** : Matrice Pharmacie×IRIS avec w_IRIS (100% couverture)
- `isochrones/` : 115,767 zones d'accessibilité

### Depuis `1_data_prep/input/` :
- `2_insee_brutes/age_profession.CSV` : Population par âge et IRIS

---

## 🚨 Dépendances importantes

### Python packages :
```bash
pip install pandas geopandas shapely scikit-learn lightgbm matplotlib seaborn tqdm
```

### Vérifications avant exécution :
1. ✅ Phase 1 (1_data_prep) complétée
2. ✅ Matrice w_IRIS 100% disponible (`matrice_w_iris_100pct.csv`)
3. ✅ Fichier `input_verif/SIG_P20.CSV` présent (pour analyses corrélations)

---

## 📚 Documentation

- **[README Phase 1](../1_data_prep/README.md)** : Guide de préparation des données
- **[Méthode de calcul de la matrice w_IRIS](../METHODE_CALCUL_MATRICE_W_IRIS.md)** : Documentation technique w_IRIS
- **[README projet](../README.md)** : Vue d'ensemble complète des 2 phases

---

**Dernière mise à jour** : Novembre 2025