# 📋 Correspondance Scripts - Pipeline Scoring Pharmacies 65+

## 🎯 Noms réels de vos scripts

Voici la correspondance entre les numéros utilisés dans la validation et les noms réels de vos fichiers Python.

### Scripts de préparation des données (1-3)

| N° | Nom du fichier | Description | Validation |
|----|----------------|-------------|------------|
| **1** | `ml_01_prepare_hubs_par_isochrone.py` | Calcul des variables hubs par isochrone (médecins, infirmiers, EHPAD, etc.) | ✅ Critique |
| **2** | `ml_02_prepare_concurrence.py` | Calcul des variables de concurrence (pharmacies concurrentes par isochrone) | ✅ Critique |
| **3** | `ml_03_prepare_population_isochrones.py` | Calcul des variables de population 65+ par intersection IRIS/isochrones | ✅ Critique |

**⚠️ Ces 3 scripts sont CRITIQUES** : si les données sont mauvaises ici, tout le pipeline est compromis.

### Scripts de transformation (4-7)

| N° | Nom du fichier | Description | Validation |
|----|----------------|-------------|------------|
| **4** | `ml_04_integration_complete.py` | Intégration de toutes les features (hubs + concurrence + population) | ✅ Transformation |
| **5** | `ml_05_feature_engineering.py` | Feature engineering (ratios, log, interactions, etc.) | ✅ Transformation |
| **6** | `ml_06_selection_features.py` | Sélection des features les plus importantes | ✅ Transformation |
| **7** | `ml_07_split_train_test.py` | Split train/test stratifié | ✅ Transformation |

### Scripts ML (8-14)

| N° | Nom du fichier | Description | Validation |
|----|----------------|-------------|------------|
| **8** | `ml_08_baseline_models.py` | Entraînement des modèles baseline (régression linéaire, etc.) | 📊 Monitoring |
| **9** | `ml_09_lightgbm_optimized.py` | Entraînement LightGBM avec optimisation hyperparamètres | 📊 Monitoring |
| **10** | `ml_10_evaluation_finale.py` | Évaluation finale des modèles (MAE, RMSE, R²) | 📊 Monitoring |
| **11** | `ml_11_interpretabilite_shap.py` | Analyse SHAP pour l'interprétabilité | 📊 Monitoring |
| **12** | `ml_12_predictions_finales.py` | Génération des prédictions finales | 📊 Monitoring |
| **13** | `ml_13_analyse_segmentee.py` | Analyse par segments (urbain/rural, régions, etc.) | 📊 Monitoring |
| **14** | `ml_14_rapport_final.py` | Génération du rapport final avec visualisations | 📊 Monitoring |

---

## 💻 Commandes de validation correspondantes

### Valider après chaque script

```bash
# Après ml_01_prepare_hubs_par_isochrone.py
python validation_data_quality_complete.py --step 1

# Après ml_02_prepare_concurrence.py
python validation_data_quality_complete.py --step 2

# Après ml_03_prepare_population_isochrones.py
python validation_data_quality_complete.py --step 3

# Après ml_04_integration_complete.py
python validation_data_quality_complete.py --step 4

# Après ml_05_feature_engineering.py
python validation_data_quality_complete.py --step 5

# Après ml_06_selection_features.py
python validation_data_quality_complete.py --step 6

# Après ml_07_split_train_test.py
python validation_data_quality_complete.py --step 7

# Après les scripts ML (8-14)
python validation_data_quality_complete.py --step ml
```

### Valider par groupe

```bash
# Scripts critiques (préparation données)
python validation_data_quality_complete.py --step 1-3

# Scripts transformation (feature engineering)
python validation_data_quality_complete.py --step 4-7

# Avant ML (toute la préparation)
python validation_data_quality_complete.py --step 1-7

# Scripts ML uniquement
python validation_data_quality_complete.py --step ml
# ou
python validation_data_quality_complete.py --step 8-14

# TOUT le pipeline
python validation_data_quality_complete.py
```

---

## 📂 Fichiers de sortie attendus

### Sorties des scripts de préparation (1-3)

| Script | Fichier de sortie |
|--------|-------------------|
| Script 1 | `pharmacies_avec_variables_hubs.csv` |
| Script 2 | `pharmacies_avec_variables_competition.csv` |
| Script 3 | `pharmacies_avec_variables_population.csv` |

### Sorties des scripts de transformation (4-7)

| Script | Fichier(s) de sortie |
|--------|----------------------|
| Script 4 | `pharmacies_features_complet.csv` |
| Script 5 | `pharmacies_features_engineered.csv` |
| Script 6 | `pharmacies_features_selected.csv` |
| Script 7 | `train_data.csv` + `test_data.csv` |

### Sorties des scripts ML (8-14)

| Script | Fichier(s) de sortie |
|--------|----------------------|
| Script 8 | `baseline_model_results.json` |
| Script 9 | `lightgbm_model_results.json` |
| Script 10 | `evaluation_results.json` |
| Script 11 | `shap_values.csv` |
| Script 12 | `predictions_finales.csv` |
| Script 13 | `analyse_segmentee.csv` |
| Script 14 | `rapport_final.json` |

**💡 Tous ces fichiers doivent être dans :**
```
N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\data\intermediaire\output\
```

---

## 🔄 Workflow complet avec noms réels

### Méthode 1 : Validation après chaque script (recommandé)

```bash
# Exécute et valide script par script
python ml_01_prepare_hubs_par_isochrone.py
python validation_data_quality_complete.py --step 1

python ml_02_prepare_concurrence.py
python validation_data_quality_complete.py --step 2

python ml_03_prepare_population_isochrones.py
python validation_data_quality_complete.py --step 3

python ml_04_integration_complete.py
python validation_data_quality_complete.py --step 4

python ml_05_feature_engineering.py
python validation_data_quality_complete.py --step 5

python ml_06_selection_features.py
python validation_data_quality_complete.py --step 6

python ml_07_split_train_test.py
python validation_data_quality_complete.py --step 7

# Scripts ML
python ml_08_baseline_models.py
python ml_09_lightgbm_optimized.py
python ml_10_evaluation_finale.py
python ml_11_interpretabilite_shap.py
python ml_12_predictions_finales.py
python ml_13_analyse_segmentee.py
python ml_14_rapport_final.py

# Validation finale ML
python validation_data_quality_complete.py --step ml
```

### Méthode 2 : Validation groupée

```bash
# Exécute tous les scripts de préparation
python ml_01_prepare_hubs_par_isochrone.py
python ml_02_prepare_concurrence.py
python ml_03_prepare_population_isochrones.py

# Valide les 3 d'un coup
python validation_data_quality_complete.py --step 1-3
```

### Méthode 3 : Automatisation bash

Crée un fichier `run_pipeline.sh` :

```bash
#!/bin/bash

# Définit les scripts dans l'ordre
SCRIPTS=(
    "ml_01_prepare_hubs_par_isochrone.py"
    "ml_02_prepare_concurrence.py"
    "ml_03_prepare_population_isochrones.py"
    "ml_04_integration_complete.py"
    "ml_05_feature_engineering.py"
    "ml_06_selection_features.py"
    "ml_07_split_train_test.py"
)

# Boucle sur chaque script
for i in "${!SCRIPTS[@]}"; do
    SCRIPT="${SCRIPTS[$i]}"
    STEP=$((i + 1))
    
    echo "=================================="
    echo "🔄 Exécution : $SCRIPT"
    echo "=================================="
    
    python "$SCRIPT"
    
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de l'exécution de $SCRIPT"
        exit 1
    fi
    
    echo ""
    echo "🔍 Validation Script $STEP..."
    python validation_data_quality_complete.py --step $STEP
    
    if [ $? -ne 0 ]; then
        echo "❌ Validation échouée pour Script $STEP"
        exit 1
    fi
    
    echo "✅ Script $STEP validé avec succès"
    echo ""
done

echo "🎉 Pipeline complet validé avec succès !"
```

Puis exécute :
```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

---

## 🎯 Résumé rapide

| Tu viens d'exécuter... | Utilise cette commande |
|------------------------|------------------------|
| `ml_01_prepare_hubs_par_isochrone.py` | `python validation_data_quality_complete.py --step 1` |
| `ml_02_prepare_concurrence.py` | `python validation_data_quality_complete.py --step 2` |
| `ml_03_prepare_population_isochrones.py` | `python validation_data_quality_complete.py --step 3` |
| Scripts 1-3 en bloc | `python validation_data_quality_complete.py --step 1-3` |
| Scripts 4-7 en bloc | `python validation_data_quality_complete.py --step 4-7` |
| Tout avant ML (1-7) | `python validation_data_quality_complete.py --step 1-7` |
| Scripts ML (8-14) | `python validation_data_quality_complete.py --step ml` |
| TOUT | `python validation_data_quality_complete.py` |

---

**🎓 Note importante :** Les numéros (1-14) dans la commande `--step` correspondent à l'**ordre logique** des scripts, pas aux noms de fichiers. La validation utilise ces numéros pour savoir quels tests exécuter.
