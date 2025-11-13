# 🚀 Démarrage rapide - Validation Data Quality

## 📦 Package complet (7 fichiers - 99 KB)

Vous avez maintenant un système complet de validation pour votre pipeline ML !

### 📄 Fichiers inclus

1. **README_VALIDATION.md** (10 KB) ⭐ **COMMENCER ICI**
   - Vue d'ensemble du système
   - Quelle documentation lire selon vos besoins

2. **CORRESPONDANCE_SCRIPTS.md** (8.5 KB) ⭐ **VOS SCRIPTS**
   - Correspondance entre numéros et noms réels de vos fichiers
   - Exemples avec noms réels (`ml_01_prepare_hubs_par_isochrone.py`, etc.)

3. **GUIDE_CLI_VALIDATION.md** (8.5 KB) ⭐ **UTILISATION**
   - Toutes les commandes possibles
   - Workflows recommandés

4. **validation_data_quality_complete.py** (41 KB) 🐍 **SCRIPT PRINCIPAL**
   - 34 tests automatiques
   - Support ligne de commande

5. **run_pipeline_auto.sh** (4.8 KB) 🔧 **AUTOMATISATION**
   - Script bash pour exécuter tout automatiquement

6. **GUIDE_VALIDATION_DATA_QUALITY.md** (13 KB)
   - Détail de tous les tests

7. **ARCHITECTURE_VALIDATION.md** (14 KB)
   - Architecture technique du système

---

## ⚡ Usage immédiat

### Vos scripts réels → Commandes de validation

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
```

### Raccourcis utiles

```bash
# Valider les 3 scripts critiques d'un coup
python validation_data_quality_complete.py --step 1-3

# Valider toute la préparation avant ML
python validation_data_quality_complete.py --step 1-7

# Valider les scripts ML
python validation_data_quality_complete.py --step ml

# Valider TOUT le pipeline
python validation_data_quality_complete.py
```

---

## 🎯 Table de correspondance rapide

| Vos scripts | N° | Commande validation |
|-------------|----|--------------------|
| `ml_01_prepare_hubs_par_isochrone.py` | 1 | `--step 1` |
| `ml_02_prepare_concurrence.py` | 2 | `--step 2` |
| `ml_03_prepare_population_isochrones.py` | 3 | `--step 3` |
| `ml_04_integration_complete.py` | 4 | `--step 4` |
| `ml_05_feature_engineering.py` | 5 | `--step 5` |
| `ml_06_selection_features.py` | 6 | `--step 6` |
| `ml_07_split_train_test.py` | 7 | `--step 7` |
| Scripts ML (8-14) | 8-14 | `--step ml` |

---

## 🔧 Automatisation complète

### Option 1 : Script bash (Linux/Mac/WSL)

```bash
# Rends le script exécutable
chmod +x run_pipeline_auto.sh

# Exécute tout automatiquement
./run_pipeline_auto.sh

# Ou seulement certains scripts
./run_pipeline_auto.sh --steps 1-3    # Scripts 1 à 3
./run_pipeline_auto.sh --step 1       # Script 1 uniquement
```

Le script bash :
- ✅ Exécute chaque script Python
- ✅ Valide immédiatement après
- ❌ S'arrête si erreur critique
- 📊 Affiche la progression

### Option 2 : Intégration Python

Ajoute à la fin de chaque script (ex: `ml_01_prepare_hubs_par_isochrone.py`) :

```python
# À la toute fin du script
if __name__ == "__main__":
    # ... ton code principal ...
    
    # Validation automatique
    import subprocess
    import sys
    
    print("\n🔍 Validation automatique...")
    result = subprocess.run([
        "python", 
        "validation_data_quality_complete.py",
        "--step", "1"  # Change le numéro selon le script
    ])
    
    if result.returncode != 0:
        print("❌ Validation échouée")
        sys.exit(1)
    
    print("✅ Script 1 validé avec succès !")
```

---

## 📊 Ce qui est validé pour chaque script

### Script 1 : Hubs (6 tests)
- Nombre de pharmacies (~20,000)
- Variables hubs créées (48 variables)
- Pas de valeurs négatives
- Coordonnées complètes

### Script 2 : Concurrence (4 tests)
- Variables concurrence créées (6 variables)
- Cohérence des isochrones
- Pas de pharmacies trop isolées

### Script 3 : Population (6 tests)
- Variables population créées (18 variables)
- Pas de valeurs négatives
- Population cohérente
- Pas d'outliers extrêmes

### Scripts 4-7 : Transformation (15 tests)
- Intégration correcte des features
- Pas de valeurs infinies (division par zéro)
- Split train/test sans fuite de données
- Distribution similaire train/test

### Scripts 8-14 : ML (3 métriques)
- MAE raisonnable (< 30% du CA moyen)
- R² acceptable (> 0.60)
- Pas d'overfitting (écart train/test < 10%)

**Total : 34 tests dont 19 critiques (bloquants)**

---

## 💡 Workflow recommandé (votre cas)

```bash
# 1. Exécute et valide les scripts critiques (1-3)
python ml_01_prepare_hubs_par_isochrone.py
python validation_data_quality_complete.py --step 1

python ml_02_prepare_concurrence.py
python validation_data_quality_complete.py --step 2

python ml_03_prepare_population_isochrones.py
python validation_data_quality_complete.py --step 3

# 2. Validation groupée des scripts critiques
python validation_data_quality_complete.py --step 1-3
# ✅ Si OK, continue

# 3. Exécute les scripts de transformation (4-7)
python ml_04_integration_complete.py
python ml_05_feature_engineering.py
python ml_06_selection_features.py
python ml_07_split_train_test.py

# 4. Validation avant ML
python validation_data_quality_complete.py --step 1-7
# ✅ Si OK, lance le ML

# 5. Scripts ML
python ml_08_baseline_models.py
python ml_09_lightgbm_optimized.py
python ml_10_evaluation_finale.py
python ml_11_interpretabilite_shap.py
python ml_12_predictions_finales.py
python ml_13_analyse_segmentee.py
python ml_14_rapport_final.py

# 6. Validation finale
python validation_data_quality_complete.py --step ml
```

---

## 🚨 Codes de retour

```bash
python validation_data_quality_complete.py --step 1

# Code 0 → ✅ Validation réussie
# Code 1 → ❌ Erreurs critiques détectées
```

Utilise `$?` pour vérifier :
```bash
python validation_data_quality_complete.py --step 1
if [ $? -eq 0 ]; then
    echo "OK, je continue"
else
    echo "Erreur, j'arrête tout"
    exit 1
fi
```

---

## 📂 Emplacement des fichiers

**Scripts Python :**
```
N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\data\intermediaire\script\
```

**Fichiers de sortie :**
```
N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\data\intermediaire\output\
```

**Rapports de validation :**
```
N:\...\output\validation_report_YYYYMMDD_HHMMSS.json
```

---

## 🎓 Premiers pas

### 1. Place le script de validation

Copie `validation_data_quality_complete.py` dans le répertoire de tes scripts :
```
N:\...\scoring_pharma_65-\data\intermediaire\script\
```

### 2. Teste sur un script

```bash
# Va dans le répertoire
cd "N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\data\intermediaire\script"

# Teste la validation sur le script 1
python validation_data_quality_complete.py --step 1
```

### 3. Intègre dans ton workflow

Ajoute la validation après chaque exécution de script.

---

## ❓ Besoin d'aide ?

**Pour l'utilisation :**
→ Lis **GUIDE_CLI_VALIDATION.md**

**Pour comprendre les tests :**
→ Lis **GUIDE_VALIDATION_DATA_QUALITY.md**

**Pour la correspondance scripts :**
→ Lis **CORRESPONDANCE_SCRIPTS.md**

**Pour automatiser :**
→ Utilise **run_pipeline_auto.sh**

---

## 🎯 Résumé en 3 lignes

```bash
# 1. Après chaque script, valide avec son numéro
python validation_data_quality_complete.py --step 1

# 2. Ou valide plusieurs scripts d'un coup
python validation_data_quality_complete.py --step 1-3

# 3. Ou valide tout
python validation_data_quality_complete.py
```

**C'est tout ! 🚀**

---

**Auteur :** Victoire LOUIS  
**Date :** Novembre 2025  
**Version :** 1.0  
**Projet :** Pipeline Scoring Pharmacies 65+
