# Pipeline d'Estimation des Clients 65+ pour Pharmacies (Phase 1)

## Vue d'ensemble

**Note** : Ce document décrit la Phase 1 (Pipeline ML) du projet. Pour la Phase 0 (préparation des données de base), voir `../GUIDE_IMPLEMENTATION.md`.

Ce pipeline estime le nombre de clients 65+ par pharmacie en France en utilisant un modèle de Huff basé sur les IRIS INSEE.

## Architecture du Pipeline

### 1. Scripts Principaux (dans `scripts/`)

#### Pipeline ML (ordre d'exécution)

1. **ml_01_prepare_hubs_par_isochrone.py**
   - Préparation des hubs médicaux par isochrone
   - Input: HUBS, isochrones
   - Output: `pharmacies_avec_hubs.csv`

2. **ml_02_prepare_concurrence.py**
   - Calcul de la concurrence entre pharmacies
   - Input: pharmacies_final.csv
   - Output: `pharmacies_avec_concurrence.csv`

3. **ml_03_prepare_population_isochrones.py**
   - Agrégation des données démographiques par isochrone
   - Input: population IRIS, isochrones
   - Output: `pharmacies_avec_population_isochrones.csv`

4. **ml_04_integration_complete.py**
   - Intégration de toutes les données
   - Output: `pharmacies_features_complet.csv`

5. **ml_05_score_attractivite_lightgbm.py**
   - Calcul du score d'attractivité avec LightGBM (4 modèles)
   - Modèles: CA Total, CA Éthique, CA Conseil, Delta CA
   - Output: `pharmacies_avec_scores_attractivite.csv`

6. **ml_06_HUFF_EXACT_IRIS_FIXED.py** ⭐
   - **VERSION FINALE** du modèle de Huff
   - Conservation parfaite de la population (ratio = 1.0)
   - Output: `pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`

#### Scripts d'Analyse des Corrélations

7. **analyse_correlation_sig_p20.py**
   - Corrélation entre SIG_P20 (UN/CAHT) et clients 65+
   - Output: `correlation_sig_p20_clients65.csv`

8. **analyse_correlation_avancee.py**
   - Corrélations par type de zone et tourisme
   - Output: `correlation_avancee_complete.csv`

9. **analyse_proximite_hubs_medicaux.py**
   - Corrélations selon proximité aux médecins/hôpitaux
   - Output: `correlation_hubs_medicaux_complete.csv`

#### Scripts Utilitaires

- **config_ml.py** - Configuration globale
- **data_quality_check.py** - Vérification qualité des données
- **nettoyer_matrice_iris_ET_pharmacies.py** - Nettoyage matrice (requis par ml_06)

### 2. Fichiers de Données Essentiels

#### Input (`data/input/`)

```
data/input/
├── data_cleaning/
│   └── pharmacies_final.csv                    # Liste des pharmacies (VERSION FINALE)
├── enrichissement/
│   └── pharmacie_iris_pond_cleaned.csv         # Matrice Pharmacie×IRIS (VERSION FINALE)
├── iris_insee/
│   ├── population_age.csv                      # Population par IRIS et âge
│   └── revenus.csv                             # Revenus par IRIS
├── HUBS_unified_final.csv                      # Hubs médicaux/touristiques
├── INSEE_hebergements_classes.csv              # Hébergements touristiques
└── RPPS/                                       # Données RPPS géocodées
```

#### Input Vérification (`intermediaire/input_verif/`)

- **SIG_P20.CSV** - Données d'activité (UN, CAHT) par pharmacie et mois

#### Output (`intermediaire/output/`)

**Fichiers du pipeline ML:**
- `pharmacies_avec_hubs.csv` (12 MB)
- `pharmacies_avec_concurrence.csv` (3.1 MB)
- `pharmacies_avec_population_isochrones.csv` (34 MB)
- `pharmacies_features_complet.csv` (52 MB)
- `pharmacies_avec_scores_attractivite.csv` (8.5 MB)
- `pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` (2.3 MB) ⭐ **RÉSULTAT FINAL**

**Fichiers d'analyse des corrélations:**
- `correlation_sig_p20_clients65.csv` + graphs
- `correlation_avancee_complete.csv` + graphs
- `correlation_hubs_medicaux_complete.csv` + graphs
- `summary_correlations_par_categorie.csv`
- `summary_hubs_medicaux.csv`

**Modèles:**
- `modeles_lightgbm/` - 4 modèles LightGBM (CA Total, Éthique, Conseil, Delta)
- `rapport_gridsearch_attractivite.txt` - Hyperparamètres optimaux

### 3. Résultats Clés

#### Modèle de Huff (ml_06_HUFF_EXACT_IRIS_FIXED.py)

- **Population France 65+:** 14,125,725
- **Population couverte:** 13,302,521 (94.2%)
- **Clients distribués:** 13,302,521
- **Conservation:** 100.0% ✓
- **Pharmacies avec clients:** 18,208 / 19,307

#### Corrélations SIG_P20 vs Clients 65+

**Global:**
- UN vs Clients 65+: 0.150
- CAHT vs Clients 65+: 0.210

**Par type de zone:**
- Urbain dense: 0.342 (meilleure corrélation)
- Rural: 0.141

**Par tourisme:**
- Zones touristiques: 0.220
- Zones non-touristiques: 0.113

**Par proximité hubs médicaux:**
- 4-10 hubs à 1km: 0.320 (meilleure corrélation)
- Aucun hub: 0.192

## Exécution du Pipeline

```bash
# 1. Pipeline ML
cd intermediaire/scripts
python ml_01_prepare_hubs_par_isochrone.py
python ml_02_prepare_concurrence.py
python ml_03_prepare_population_isochrones.py
python ml_04_integration_complete.py
python ml_05_score_attractivite_lightgbm.py
python ml_06_HUFF_EXACT_IRIS_FIXED.py

# 2. Analyses de corrélation
python analyse_correlation_sig_p20.py
python analyse_correlation_avancee.py
python analyse_proximite_hubs_medicaux.py
```

## Fichier Final de Sortie

**`pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`**

Colonnes:
- `id_pharmacie` - Identifiant unique
- `nom_pharmacie` - Nom de la pharmacie
- `attractivite_huff` - Score d'attractivité normalisé [0.1-1.0]
- `clients_65_79` - Nombre de clients 65-79 ans
- `clients_80_plus` - Nombre de clients 80+ ans
- `clients_65_plus_total` - Total clients 65+ (65-79 + 80+)
- `visites_annuelles_65plus` - Visites annuelles (clients × 12)
- `decile_clients_65plus` - Décile (1-10)

## Notes Techniques

### Modèle de Huff

Le modèle garantit la conservation exacte de la population via:

1. Pour chaque IRIS: récupération des pharmacies accessibles
2. Calcul utilité: U_j = Attractivité_j × w_IRIS
3. Normalisation: part_marché_j = U_j / Σ(U_k)
4. Distribution: clients_j += pop_IRIS × part_marché_j

Σ(parts de marché) = 100% → Σ(clients) = Population couverte ✓

### Nettoyage Effectué

Scripts supprimés (47 fichiers):
- Tous les scripts `diagnostic_*.py`, `test_*.py`, `debug_*.py`
- Versions obsolètes: `ml_06_HUFF_EXACT.py`, `ml_06_HUFF_EXACT_IRIS.py`
- Scripts expérimentaux de couverture IRIS

Fichiers data supprimés:
- Versions intermédiaires de la matrice IRIS (8 fichiers)
- Anciennes versions de résultats HUFF (3 fichiers)
- Rapports de validation temporaires (21 fichiers JSON)

**Total conservé:** 13 scripts essentiels + fichiers de données finaux
