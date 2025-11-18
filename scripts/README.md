# Scripts Phase 0 - Préparation des Données

Ce dossier contient tous les scripts de **préparation des données de base** organisés par pipeline de génération.

## Structure

```
scripts/
├── 1_pharmacies/       → pharmacies_final.csv
├── 2_hubs/             → HUBS_unified_final.csv
├── 3_isochrones/       → 115k fichiers geojson
├── 4_enrichissement/   → pharmacies enrichies INSEE + tourisme
└── 5_validation/       → contrôles qualité
```

---

## 1. Pipeline Pharmacies

**Objectif** : Créer `data/input/data_cleaning/pharmacies_final.csv`

### Scripts (1)

#### create_pharmacies_final.py
Transforme les données sources UGA en fichier pharmacies propre.

**Input** :
- `N:\...\DATA\DONNEES_PHARMACIES\points_ventes_202509 - RETRAVAILLE.geocoded.csv`
- `data/input/pharmacies.csv` (optionnel, pour CA)

**Output** :
- `data/input/data_cleaning/pharmacies_final.csv`

**Variables créées** :
- id_pharmacie, nom_pharmacie, latitude, longitude
- code_postal, commune, departement
- type_zone (urbain_dense, urbain, periurbain, rural)
- ca_total, ca_ethique, ca_conseil, delta (si disponibles)
- voisins_5km (nombre de pharmacies dans rayon 5km)

**Exécution** :
```bash
cd scripts/1_pharmacies
python create_pharmacies_final.py
```

---

## 2. Pipeline HUBS

**Objectif** : Créer `data/output/HUBS_unified_final.csv`

### Ordre d'exécution (8 scripts)

#### 2.1 Génération Sources

**create_hubs_file.py**
Extrait hubs depuis sources multiples (FINESS, RPPS, SNCF, RATP, OSM).
- **Output** : `data/processed/hubs.csv`

**geocode_rpps_optimise.py**
Géocode les médecins RPPS via API BAN.
- **Input** : `data/input/*rpps*.txt`
- **Output** : `data/processed/rpps_geocoded.csv`

**process_finess_with_weights.py**
Traite FINESS avec poids seniors.
- **Input** : `data/input/FINESS.csv`
- **Output** : `data/processed/FINESS_with_weights.csv`

**finess_categories_weights_seniors_only.py**
Config des poids/bonus par catégorie FINESS (focus seniors).

#### 2.2 Fusion

**merge_finess_rpps_hubs.py**
Merge FINESS + RPPS.

**fusion_hubs_complet.py**
Fusion complète toutes sources → `data/processed/HUBS_unified.csv`

#### 2.3 Corrections

**corriger_bonus.py** ⭐
Recalcule bonus_attractivite (focus structures seniors).
- **Input** : `data/processed/HUBS_unified.csv`
- **Output** : `data/output/HUBS_unified_corriges.csv`
- **Modifications** :
  - ↓ Transport/commercial (bus: 0.15→0.02, marchés: 0.20→0.03)
  - ↑ Structures seniors (EHPAD, dialyse, etc.)

**corriger_dedoublonner.py** ⭐
Déduplique structures génériques vs médecins RPPS (seuil 50m, KDTree spatial).
- **Input** : `data/output/HUBS_unified_corriges.csv`
- **Output** : `data/output/HUBS_unified_final.csv` (fichier final)
- **Règles** :
  - Supprime structures génériques si médecin < 50m
  - Garde TOUS les médecins RPPS

**Exécution complète** :
```bash
cd scripts/2_hubs
# Génération initiale (une seule fois)
python create_hubs_file.py
python geocode_rpps_optimise.py
python process_finess_with_weights.py
python merge_finess_rpps_hubs.py
python fusion_hubs_complet.py

# Corrections (réexécutable)
python corriger_bonus.py
python corriger_dedoublonner.py
```

---

## 3. Pipeline Isochrones

**Objectif** : Générer isochrones pour 19k pharmacies (6 types)

### Types d'isochrones

- **walk_5min** : Piéton 5 minutes
- **walk_10min** : Piéton 10 minutes
- **drive_5min** : Voiture 5 minutes
- **drive_10min** : Voiture 10 minutes
- **drive_15min** : Voiture 15 minutes
- **drive_20min** : Voiture 20 minutes

### Scripts (7)

#### generate_isochrones.py ⭐
Générateur principal d'isochrones (API routing).
- **Input** : `data/input/data_cleaning/pharmacies_final.csv`
- **Output** : `data/processed/isochrones/{type}/*.geojson`

#### generate_isochrones_backup.py
Générateur backup en cas de problème.

#### generate_missing_isochrones.py
Remplit les gaps pour pharmacies sans isochrones.
- **Input** : `data/input/pharmacies_missing.csv`

#### generate_geometric_fallback.py
Crée buffers géométriques si API échoue (fallback).

#### manage_isochrone_batches.py
Gestion par batch avec sauvegarde incrémentale.

#### monitor_isochrones.py
Monitoring progression (OK/manquant/erreur).

#### prepare_pharmacies_for_isochrones.py
Prépare fichier pharmacies pour génération.

**Exécution** :
```bash
cd scripts/3_isochrones
# Génération principale
python generate_isochrones.py

# Si gaps détectés
python generate_missing_isochrones.py

# Monitoring
python monitor_isochrones.py
```

**Résultat** : 115,767 fichiers geojson générés

---

## 4. Pipeline Enrichissement

**Objectif** : Enrichir pharmacies avec données INSEE + tourisme

### Scripts (2)

#### enrichir_pharmacies_optimise.py ⭐
Enrichissement INSEE par IRIS avec pondération w_IRIS.

**Input** :
- `data/input/data_cleaning/pharmacies_final.csv`
- `data/input/enrichissement/pharmacie_iris_pond_cleaned.csv`
- `data/input/iris_insee/population_age.csv`
- `data/input/iris_insee/diplome_formation.csv`
- `data/input/iris_insee/logement.csv`
- `data/input/iris_insee/revenus.csv`

**Output** :
- `data/output/pharmacies_enrichies_insee.csv`

**Variables créées** :
- Population par âge : 65-74, 75-84, 85+ (par genre)
- Revenus, éducation, logement
- Agrégées par zone IRIS avec poids d'intersection

**Caractéristiques** :
- Multiprocessing (N_WORKERS CPUs)
- Checkpoint tous les 1000 pharmacies

#### calcul_variables_touristiques.py ⭐
Calcule variables tourisme par isochrone.

**Input** :
- `data/output/pharmacies_enrichies_insee.csv`
- `data/input/INSEE_hebergements_classes.csv`
- `data/input/INSEE_loi_montagne.xlsx`
- `data/input/INSEE_loi_littorale.xlsx`
- `data/processed/isochrones/{6 types}/*.geojson`

**Output** :
- `data/output/pharmacies_final_avec_variables_touristiques.csv`

**Variables créées** :
- Hébergements (hotels, camping) par isochrone
- Flags zone_littorale, zone_montagne
- Agrégation spatiale via STRtree

**Exécution** :
```bash
cd scripts/4_enrichissement
python enrichir_pharmacies_optimise.py
python calcul_variables_touristiques.py
```

---

## 5. Validation

**Objectif** : Contrôle qualité des données

### Scripts (1)

#### check_data_quality.py
Valide données enrichies.

**Input** :
- `data/output/pharmacies_enrichies_insee.csv`
- `data/output/HUBS_unified_final.csv`
- `data/processed/isochrones/*/*.geojson`

**Output** :
- `data/reports/data_quality_report.txt`

**Vérifications** :
- Complétude des données
- Cohérence coordonnées
- Présence isochrones
- Distribution variables

**Exécution** :
```bash
cd scripts/5_validation
python check_data_quality.py
```

---

## Flux de Données Complet

```
Phase 0 (scripts/)
===================
1. points_ventes_202509.xlsx
   → create_pharmacies_final.py
   → pharmacies_final.csv

2. FINESS + RPPS + OSM + Transport
   → [pipeline 2_hubs/ - 8 scripts]
   → HUBS_unified_final.csv

3. pharmacies_final.csv
   → [pipeline 3_isochrones/ - 7 scripts]
   → 115k fichiers geojson (6 types)

4. pharmacies_final.csv + IRIS INSEE + isochrones
   → enrichir_pharmacies_optimise.py
   → pharmacies_enrichies_insee.csv

5. pharmacies_enrichies_insee.csv + hébergements + isochrones
   → calcul_variables_touristiques.py
   → pharmacies_final_avec_variables_touristiques.csv

6. Toutes données
   → check_data_quality.py
   → Validation ✓

Phase 1 (intermediaire/scripts/)
=================================
7-12. Pipeline ML (6 scripts)
   → estimations_clients_65plus_FINAL.csv
```

---

## Ordre d'Exécution Recommandé

### Génération Initiale (une seule fois)
```bash
# 1. Pharmacies
cd 1_pharmacies && python create_pharmacies_final.py

# 2. HUBS (chaîne complète)
cd ../2_hubs
python create_hubs_file.py
python geocode_rpps_optimise.py
python process_finess_with_weights.py
python merge_finess_rpps_hubs.py
python fusion_hubs_complet.py
python corriger_bonus.py
python corriger_dedoublonner.py

# 3. Isochrones
cd ../3_isochrones && python generate_isochrones.py

# 4. Enrichissement
cd ../4_enrichissement
python enrichir_pharmacies_optimise.py
python calcul_variables_touristiques.py

# 5. Validation
cd ../5_validation && python check_data_quality.py
```

### Mise à Jour (nouvelles pharmacies UGA)
```bash
# Seulement ces 4 scripts
cd 1_pharmacies && python create_pharmacies_final.py
cd ../3_isochrones && python generate_missing_isochrones.py
cd ../4_enrichissement
python enrichir_pharmacies_optimise.py
python calcul_variables_touristiques.py
```

---

## Notes Techniques

### Optimisations
- **KDTree spatial** : Recherche voisins (scipy.spatial.cKDTree)
- **STRtree** : Indexation géométrique (shapely)
- **Multiprocessing** : Enrichissement parallèle
- **Checkpoints** : Sauvegarde incrémentale (tous les 1000 pharmacies)

### Dépendances
- pandas, numpy, geopandas
- shapely, scipy
- requests (API BAN, routing)

### Temps d'Exécution Estimés
- create_pharmacies_final.py : ~2 min
- Pipeline HUBS complet : ~30 min
- generate_isochrones.py : ~48h (19k pharmacies × 6 types)
- enrichir_pharmacies_optimise.py : ~45 min
- calcul_variables_touristiques.py : ~30 min

---

**Total scripts Phase 0 : 19 scripts organisés en 5 pipelines**

Pour la Phase 1 (ML pipeline), voir `../intermediaire/README_PIPELINE.md`