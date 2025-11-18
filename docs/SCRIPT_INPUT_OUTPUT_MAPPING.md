# COMPREHENSIVE SCRIPT INPUT/OUTPUT MAPPING

**Generated:** 2025-01-18
**Project:** Scoring Pharma 65+ - Pharmacy Patient Profile Analysis

This document maps all Python scripts to their input and output files, organized by phase.

---

## PHASE 0: DATA PREPARATION (scripts/)

### **1. create_pharmacies_final.py**
**Description:** Creates the base pharmacies file from raw UGA data + existing CA data

**INPUTS:**
- N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\DATA\DONNEES_PHARMACIES\points_ventes_202509 - RETRAVAILLE.geocoded.csv
- data/input/pharmacies.csv (optional, for CA data)

**OUTPUTS:**
- data/input/data_cleaning/pharmacies_final.csv

**STATUS:** ✓ Valid (creates base pharmacy file)

---

### **2. create_hubs_file.py**
**Description:** Creates unified HUBS file from FINESS, RPPS, SNCF, RATP, and OSM data (optimized by region)

**INPUTS:**
- data/input/FINESS*.csv (auto-detected)
- data/input/*rpps*.txt (auto-detected)
- SNCF API: https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/liste-des-gares/exports/csv
- RATP API: https://data.iledefrance-mobilites.fr/explore/dataset/arrets-lignes/download/?format=csv
- OpenStreetMap API (divided by 16 French regions)

**OUTPUTS:**
- data/processed/hubs.csv
- data/processed/hubs.gpkg
- data/cache/sncf_gares.csv (temp)
- data/cache/ratp_arrets.csv (temp)

**STATUS:** ✓ Valid (hub data extraction)

**NOTES:** Does NOT include FINESS/RPPS in final version (requires geocoding)

---

### **3. create_hubs_file_OSM.py**
**Description:** Alternative OSM-only HUBS extractor with checkpoint system

**INPUTS:**
- OpenStreetMap API

**OUTPUTS:**
- data/processed/hubs_osm.csv
- data/cache/osm_checkpoint.csv (incremental saves)

**STATUS:** ⚠ Check (alternative to create_hubs_file.py, may be redundant)

---

### **4. create_hubs_finess_only.py**
**Description:** Extracts HUBS from FINESS data only

**INPUTS:**
- data/input/FINESS*.csv (auto-detected)

**OUTPUTS:**
- data/processed/hubs_finess.csv
- data/cache/finess_cache.csv

**STATUS:** ⚠ Check (alternative extraction, may be redundant)

---

### **5. merge_finess_rpps_hubs.py**
**Description:** Merges FINESS and RPPS hubs into unified file

**INPUTS:**
- (Multiple hub files to merge)

**OUTPUTS:**
- (Unified hub file)

**STATUS:** ⚠ Check (merging utility, check if still used)

---

### **6. corriger_bonus.py**
**Description:** Recalculates bonus_attractivite for ALL hub categories (focuses on senior health hubs)

**INPUTS:**
- data/processed/HUBS_unified.csv

**OUTPUTS:**
- data/output/HUBS_unified_corriges.csv
- data/processed/HUBS_unified_old.csv (backup)

**STATUS:** ✓ Valid (bonus correction - CRITICAL for ML pipeline)

**NOTES:**
- Reduces bonus for transport/commercial (bus: 0.15→0.02, markets: 0.20→0.03)
- Increases bonus for senior structures (EHPAD, dialysis, etc.)

---

### **7. corriger_dedoublonner.py**
**Description:** Deduplicates generic structures vs. RPPS doctors (50m threshold) using KDTree spatial indexing

**INPUTS:**
- data/output/HUBS_unified_corriges.csv

**OUTPUTS:**
- data/output/HUBS_unified_final.csv
- data/output/HUBS_unified_corriges_backup.csv (backup)
- data/cache/deduplicate_checkpoint.pkl (checkpoint)

**STATUS:** ✓ Valid (deduplication - CRITICAL for ML pipeline)

**NOTES:**
- Removes generic structures (hospitals, medical centers) if doctor <50m away
- Keeps ALL RPPS doctors
- Uses spatial indexing for optimization

---

### **8. enrichir_pharmacies_optimise.py**
**Description:** Enriches pharmacies with INSEE data (population age, income, housing, education) aggregated by IRIS zones with w_IRIS weighting

**INPUTS:**
- data/input/data_cleaning/pharmacies_final.csv
- data/input/enrichissement/pharmacie_iris_pond.csv
- data/input/iris_insee/population_age.csv
- data/input/iris_insee/diplome_formation.csv
- data/input/iris_insee/logement.csv
- data/input/iris_insee/revenus.csv

**OUTPUTS:**
- data/output/pharmacies_enrichies_insee.csv
- data/cache/enrichissement_checkpoint.pkl (checkpoint)
- data/cache/enrichissement_batch_*.csv (incremental saves)

**STATUS:** ✓ Valid (INSEE enrichment - CRITICAL)

**NOTES:**
- Multiprocessing with N_WORKERS CPUs
- Calculates age groups: 65-74, 75-84, 85+ (by gender)
- Saves every 1000 pharmacies (BATCH_SIZE)

---

### **9. check_data_quality.py**
**Description:** Quality control checks for enriched pharmacy data

**INPUTS:**
- data/output/pharmacies_enrichies_insee.csv
- data/output/HUBS_unified_final.csv
- data/processed/isochrones/*/*.geojson

**OUTPUTS:**
- data/reports/data_quality_report.txt

**STATUS:** ✓ Valid (utility - quality validation)

---

### **10. calcul_variables_touristiques.py**
**Description:** Calculates tourism variables for pharmacies (hotels, camping, coastal/mountain flags) per isochrone

**INPUTS:**
- data/output/pharmacies_enrichies_insee.csv
- data/input/INSEE_hebergements_classes.csv
- data/input/INSEE_loi_montagne.xlsx
- data/input/INSEE_loi_littorale.xlsx
- data/processed/isochrones/walk_5min/*.geojson
- data/processed/isochrones/walk_10min/*.geojson
- data/processed/isochrones/drive_5min/*.geojson
- data/processed/isochrones/drive_10min/*.geojson
- data/processed/isochrones/drive_15min/*.geojson
- data/processed/isochrones/drive_20min/*.geojson

**OUTPUTS:**
- data/output/pharmacies_final_avec_variables_touristiques.csv
- intermediaire/output/checkpoint_variables_touristiques.csv (checkpoint)

**STATUS:** ✓ Valid (tourism data enrichment)

**NOTES:**
- Uses STRtree spatial index for optimization
- Geocodes accommodations via BAN API
- Processes 6 isochrone types

---

### **11-24. Isochrone Generation Scripts**

#### generate_isochrones.py
**Description:** Main isochrone generator (walk/drive)
**INPUTS:** pharmacies_final.csv
**OUTPUTS:** data/processed/isochrones/{type}/*.geojson
**STATUS:** ✓ Valid

#### generate_simple_isochrones.py
**Description:** Simplified isochrone generator
**STATUS:** ⚠ Check (alternative to generate_isochrones.py)

#### generate_drive_short_isochrones.py
**Description:** Short-distance drive isochrones
**STATUS:** ⚠ Check (specific use case)

#### generate_missing_isochrones.py
**Description:** Fills in missing isochrones
**STATUS:** ✓ Valid (utility for gaps)

#### generate_geometric_fallback.py
**Description:** Creates geometric buffers when isochrone API fails
**STATUS:** ✓ Valid (fallback utility)

#### manage_isochrone_batches.py
**Description:** Batch management for isochrone generation
**STATUS:** ✓ Valid (utility for batch processing)

#### monitor_isochrones.py
**Description:** Monitors isochrone generation progress
**STATUS:** ✓ Valid (utility - progress tracking)

---

### **25. geocode_rpps_optimise.py**
**Description:** Geocodes RPPS doctors via BAN API

**INPUTS:**
- data/input/*rpps*.txt

**OUTPUTS:**
- data/processed/rpps_geocoded.csv

**STATUS:** ✓ Valid (geocoding utility)

---

### **26. Other Support Scripts**
- prepare_pharmacies_for_isochrones.py: ✓ Valid (prep utility)
- test_geocode_10.py: ⚠ Check (test script - can delete)
- finess_categories_weights_seniors_only.py: ✓ Valid (config/weights)
- process_finess_with_weights.py: ✓ Valid (FINESS processing)
- merge_rpps_add_weights.py: ⚠ Check (merging utility)
- merge_missing_clean.py: ⚠ Check (cleanup utility)
- fusion_hubs_complet.py: ✓ Valid (hub fusion)

---

## PHASE 1: ML PIPELINE (intermediaire/scripts/)

### **ML-1. ml_01_prepare_hubs_par_isochrone.py**
**Description:** Calculates hub counts by category and isochrone with spatial deduplication (50m clustering)

**INPUTS:**
- data/output/HUBS_unified_final.csv
- data/input/data_cleaning/pharmacies_final.csv
- data/processed/isochrones/{walk_5min,walk_10min,drive_5min,drive_10min,drive_15min,drive_20min}/*.geojson

**OUTPUTS:**
- intermediaire/output/pharmacies_avec_hubs.csv
- intermediaire/output/checkpoint_hubs.csv (checkpoint every 250 pharmacies)
- intermediaire/output/backups_hubs/pharmacies_hubs_{timestamp}.csv (backup)
- intermediaire/output/rapport_deduplication_hubs.txt

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1)

**NOTES:**
- Creates aggregated variables per isochrone (6 types)
- Spatial deduplication using DBSCAN clustering
- Auto-detects already calculated isochrones
- Variables created: nb_services_seniors, nb_sante_generale, nb_sante_specialisee, nb_medecin, nb_ehpad, nb_hopital, nb_laboratoire, nb_supermarche, nb_bus, nb_accessibilite, taux_colocalisation

---

### **ML-2. ml_02_prepare_concurrence.py**
**Description:** Calculates competition metrics per isochrone (competitor pharmacy counts + distance to nearest)

**INPUTS:**
- data/input/data_cleaning/pharmacies_final.csv
- data/processed/isochrones/{6 types}/*.geojson

**OUTPUTS:**
- intermediaire/output/pharmacies_avec_concurrence.csv
- intermediaire/output/checkpoint_concurrence.csv (checkpoint)
- intermediaire/output/backups_concurrence/pharmacies_concurrence_{timestamp}.csv (backup)

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1)

**NOTES:**
- Precalculates distance matrix (vectorized haversine)
- Variables created: nb_pharmacies_concurrentes_{isochrone}, distance_pharmacie_plus_proche
- 7 variables total (6 isochrones + 1 distance)

---

### **ML-3. ml_03_prepare_population_isochrones.py**
**Description:** Calculates population accessible per isochrone by intersecting with IRIS zones

**INPUTS:**
- data/input/data_cleaning/pharmacies_final.csv
- data/input/age_profession.CSV (population by IRIS)
- data/input/geo/contours_iris.gpkg (IRIS geometries)
- data/processed/isochrones/{6 types}/*.geojson

**OUTPUTS:**
- intermediaire/output/pharmacies_avec_population_isochrones.csv
- intermediaire/output/checkpoint_population.csv (checkpoint)
- intermediaire/output/backups_population/pharmacies_population_{timestamp}.csv (backup)

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1)

**NOTES:**
- Converts INSEE P22_XXX codes to target age groups (65-74, 75-84, 85+)
- Weighted by IRIS surface intersection
- Variables created (15 vars × 6 isochrones = 90 columns): pop_totale, pop_65_plus, pop_65_74, pop_75_84, pop_85_plus, pop_{hommes/femmes}_{age groups}, taux_retraites, taux_cadres

---

### **ML-4. ml_04_integration_complete.py**
**Description:** Merges ALL feature files into master file + creates derived features (ratios, densities)

**INPUTS:**
- data/input/data_cleaning/pharmacies_final.csv
- intermediaire/output/pharmacies_avec_hubs.csv
- intermediaire/output/pharmacies_avec_concurrence.csv
- intermediaire/output/pharmacies_avec_population_isochrones.csv
- data/output/pharmacies_final_avec_variables_touristiques.csv

**OUTPUTS:**
- intermediaire/output/pharmacies_features_complet_clean.csv

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1)

**NOTES:**
- Creates derived features:
  * Population ratios (65+ share, gender ratios, age group shares)
  * Health service densities (hubs per 1000 seniors)
  * Competition metrics (competitors per senior)
- Total ~100-120 variables

---

### **ML-5. ml_05_score_attractivite_lightgbm.py**
**Description:** Trains LightGBM models with GridSearch to predict CA (total, ethique, conseil) and generates attractiveness scores

**INPUTS:**
- intermediaire/output/pharmacies_features_complet_clean.csv

**OUTPUTS:**
- intermediaire/output/pharmacies_avec_scores_attractivite.csv
- intermediaire/output/modeles_lightgbm/model_ca_total.pkl
- intermediaire/output/modeles_lightgbm/model_ca_ethique.pkl
- intermediaire/output/modeles_lightgbm/model_ca_conseil.pkl
- intermediaire/output/rapport_gridsearch_attractivite.txt

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1)

**NOTES:**
- GridSearchCV for hyperparameter optimization
- Features: ALL hubs, population, competition, tourism, derived variables across 6 isochrones
- Excludes 'delta' to avoid data leakage (delta = total - ethique - conseil)

---

### **ML-6. ml_06_estimation_clients_65plus_FINAL.py**
**Description:** Final model - estimates 65+ client counts using Huff gravity model with EXACT w_IRIS weighting

**INPUTS:**
- intermediaire/output/pharmacies_avec_scores_attractivite.csv
- (Or directly from ml_04 output if ml_05 not run)
- IRIS-pharmacy correspondence with w_IRIS weights

**OUTPUTS:**
- intermediaire/output/estimations_clients_65plus_FINAL.csv
- intermediaire/output/modeles_lightgbm/model_delta.pkl (if training delta model)

**STATUS:** ✓ Valid (CRITICAL ML script - phase 1 - FINAL OUTPUT)

**NOTES:**
- Implements Huff gravity model with attractiveness scores from ML-5
- Uses EXACT w_IRIS weights from isochrone-IRIS intersections
- Most accurate population allocation method

---

### **ML-7. config_ml.py**
**Description:** Central configuration file for entire ML pipeline

**INPUTS:** None (config file)

**OUTPUTS:** None (config file)

**STATUS:** ✓ Valid (utility - CRITICAL configuration)

**NOTES:**
- Defines all file paths (INPUT_FILES, INTERMEDIATE_FILES, OUTPUT_FILES)
- Configures hub deduplication (epsilon=50m, hierarchies, collocalization weights)
- Configures hub aggregations (families: sante_generale, sante_specialisee, services_seniors, accessibilite)
- Defines 6 isochrone types: walk_5min, walk_10min, drive_5min, drive_10min, drive_15min, drive_20min
- ML config: LightGBM hyperparameters, GridSearch settings

---

### **ML-8. data_quality_check.py**
**Description:** Validates intermediate ML pipeline outputs

**INPUTS:**
- intermediaire/output/pharmacies_features_complet_clean.csv

**OUTPUTS:**
- intermediaire/output/data_quality_report.txt

**STATUS:** ✓ Valid (utility - quality validation)

---

### **ML-9-13. Analysis Scripts**
- analyse_correlation_avancee.py: ✓ Valid (correlation analysis)
- analyse_correlation_sig_p20.py: ✓ Valid (SIG vs P20 correlation)
- analyse_proximite_hubs_medicaux.py: ✓ Valid (medical hub proximity)

---

### **ML-14-24. Experimental/Alternative Scripts (in git status)**
These scripts appear in git status as untracked, indicating they are experimental or alternative approaches:

- analyse_double_comptage_population.py: ⚠ Check (population double-counting analysis)
- analyse_perte_population_huff.py: ⚠ Check (Huff model population loss analysis)
- analyse_perte_population_huff_extended.py: ⚠ Check (extended Huff analysis)
- clean_ml_06_outliers.py: ⚠ Check (outlier cleaning for ML-6)
- creer_correspondance_iris_code_postal.py: ⚠ Check (IRIS-postal code mapping)
- diagnostic_perte_31pct.py: ⚠ Check (31% population loss diagnostic)
- etendre_couverture_100_pourcent.py: ⚠ Check (100% coverage extension)
- etendre_couverture_iris.py: ⚠ Check (IRIS coverage extension)
- ml_06_HUFF_EXACT.py: ⚠ Check (alternative Huff implementation)
- ml_06_HUFF_EXACT_IRIS.py: ⚠ Check (IRIS-based Huff)
- ml_06_HUFF_EXACT_IRIS_FIXED.py: ⚠ Check (fixed IRIS Huff - likely superseded by FINAL)
- normaliser_w_iris.py: ⚠ Check (w_IRIS normalization)
- recalculer_w_iris_avec_isochrones.py: ⚠ Check (recalculate w_IRIS with isochrones)
- recalculer_w_iris_complet.py: ⚠ Check (complete w_IRIS recalculation)
- recalculer_w_iris_depuis_geojson.py: ⚠ Check (w_IRIS from geojson)
- validation_complete_ml_06.py: ⚠ Check (ML-6 validation)
- validation_ml_06.py: ⚠ Check (ML-6 validation)
- verif_conservation_population.py: ⚠ Check (population conservation check)
- nettoyer_matrice_iris_sans_pop.py: ⚠ Check (clean IRIS matrix without population)
- nettoyer_matrice_iris_ET_pharmacies.py: ⚠ Check (clean IRIS matrix + pharmacies)

**STATUS:** ⚠ Check all - These scripts are experiments/diagnostics, likely candidates for archiving

---

## ROOT LEVEL CHECK SCRIPTS

These scripts in the project root are simple data quality checks:

- check_categories.py: Reads intermediaire/output/pharmacies_features_selected.csv
- check_missing_coords.py: Reads pharmacies_final.csv and pharmacies_avec_hubs.csv
- check_ratios.py: Reads pharmacies_features_engineered.csv
- check_segmentation_complete.py: Reads pharmacies_features_complet.csv

**STATUS:** ⚠ Check (utility scripts - one-off checks, can be deleted or archived)

---

## CRITICAL PIPELINE SUMMARY

### **PHASE 0 - Data Preparation (Required Order)**

1. **create_pharmacies_final.py** → pharmacies_final.csv
2. **create_hubs_file.py** → hubs.csv (or use existing)
3. **corriger_bonus.py** → HUBS_unified_corriges.csv
4. **corriger_dedoublonner.py** → HUBS_unified_final.csv (CRITICAL)
5. **enrichir_pharmacies_optimise.py** → pharmacies_enrichies_insee.csv (CRITICAL)
6. **calcul_variables_touristiques.py** → pharmacies_final_avec_variables_touristiques.csv
7. **Isochrone generation scripts** → isochrones/{6 types}/*.geojson

### **PHASE 1 - ML Pipeline (Required Order)**

1. **ml_01_prepare_hubs_par_isochrone.py** → pharmacies_avec_hubs.csv (90 variables)
2. **ml_02_prepare_concurrence.py** → pharmacies_avec_concurrence.csv (7 variables)
3. **ml_03_prepare_population_isochrones.py** → pharmacies_avec_population_isochrones.csv (90 variables)
4. **ml_04_integration_complete.py** → pharmacies_features_complet_clean.csv (~120 variables)
5. **ml_05_score_attractivite_lightgbm.py** → pharmacies_avec_scores_attractivite.csv + models
6. **ml_06_estimation_clients_65plus_FINAL.py** → estimations_clients_65plus_FINAL.csv (FINAL OUTPUT)

---

## ORPHANED DATA FILES TO CHECK

Based on the script analysis, these data files should be checked for orphan status:

**Potential Orphans (no script generates them):**
- data/input/enrichissement/pharmacie_iris_pond.csv (required by enrichir_pharmacies_optimise.py)
  * STATUS: Check if this is manually created or generated by missing script
- data/input/iris_insee/*.csv files
  * STATUS: External data sources (INSEE), not generated

**Cache/Temporary Files (can be deleted):**
- data/cache/*.csv (all checkpoint/temp files)
- intermediaire/output/checkpoint_*.csv
- intermediaire/output/backups_*/*

---

## SCRIPTS TO DELETE/ARCHIVE

### **Candidates for Deletion (Low Priority/Redundant)**

**scripts/**
- test_geocode_10.py (test script)
- create_hubs_file_OSM.py (alternative to create_hubs_file.py)
- create_hubs_finess_only.py (alternative extractor)
- merge_rpps_add_weights.py (check if still used)
- merge_missing_clean.py (cleanup utility)
- generate_simple_isochrones.py (alternative generator)
- generate_drive_short_isochrones.py (specific use case)

**intermediaire/scripts/** (all untracked experimental scripts)
- All 17 untracked scripts listed above under ML-14-24
- These are experiments/diagnostics for debugging population loss issues

**Root level**
- check_*.py (4 scripts - one-off quality checks)

### **Archive Recommendation**
Create archive/ folder and move:
1. All experimental ml_06 variants
2. All w_IRIS recalculation variants
3. All population loss diagnostic scripts
4. Root level check scripts

---

## NOTES

**Isochrones:** 6 types used throughout pipeline
- walk_5min, walk_10min (pedestrian access)
- drive_5min, drive_10min, drive_15min, drive_20min (car access)

**Critical Deduplication:** 50m threshold using DBSCAN spatial clustering

**w_IRIS Weighting:** Population allocation weighted by isochrone-IRIS intersection surface

**LightGBM Models:** 4 models trained
- model_ca_total.pkl
- model_ca_ethique.pkl
- model_ca_conseil.pkl
- model_delta.pkl

**Modified Files (git status):**
- model pkl files (models updated)
- rapport_gridsearch_attractivite.txt (GridSearch results)
- ml_06_estimation_clients_65plus_FINAL.py (latest version)

---

**END OF MAPPING**