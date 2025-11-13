# 🎯 Système de validation Data Quality - Pipeline Scoring Pharmacies 65+

## 📦 Contenu de ce package

Ce package contient un système complet de validation de la qualité des données pour votre pipeline de machine learning.

### Fichiers inclus

| Fichier | Taille | Description |
|---------|--------|-------------|
| `validation_data_quality_complete.py` | 40 KB | Script Python de validation (34 tests) |
| `GUIDE_CLI_VALIDATION.md` | 8.5 KB | **⭐ COMMENCER ICI** - Guide d'utilisation en ligne de commande |
| `GUIDE_VALIDATION_DATA_QUALITY.md` | 13 KB | Guide détaillé de tous les tests |
| `ARCHITECTURE_VALIDATION.md` | 14 KB | Documentation de l'architecture du système |

---

## 🚀 Démarrage rapide

### 1. Valider TOUT le pipeline

```bash
python validation_data_quality_complete.py
```

### 2. Valider UN SEUL script

```bash
# Après avoir exécuté script_1_hubs.py
python validation_data_quality_complete.py --step 1

# Après avoir exécuté script_2_competition.py
python validation_data_quality_complete.py --step 2

# Après avoir exécuté script_3_population.py
python validation_data_quality_complete.py --step 3
```

### 3. Valider PLUSIEURS scripts

```bash
# Valide les scripts critiques (1, 2, 3)
python validation_data_quality_complete.py --step 1-3

# Valide la préparation complète avant ML (1 à 7)
python validation_data_quality_complete.py --step 1-7

# Valide uniquement les scripts ML (8-14)
python validation_data_quality_complete.py --step ml
```

---

## 📚 Quelle documentation lire ?

### Tu veux juste utiliser le script ?
→ Lis **`GUIDE_CLI_VALIDATION.md`** ⭐

Contient :
- Toutes les commandes possibles
- Exemples de workflows
- Conseils pratiques
- Script bash d'automatisation

### Tu veux comprendre chaque test ?
→ Lis **`GUIDE_VALIDATION_DATA_QUALITY.md`**

Contient :
- Détail des 34 tests (description, seuils, criticité)
- Section dépannage
- Interprétation des résultats
- FAQ

### Tu veux comprendre l'architecture ?
→ Lis **`ARCHITECTURE_VALIDATION.md`**

Contient :
- Pourquoi 3 niveaux de validation (critique/transformation/monitoring)
- Types de tests implémentés
- Principes de conception
- Évolutions futures

---

## 🎯 Ce que le système valide

### Scripts 1-3 : Validations CRITIQUES ⚠️

**34 tests au total**, dont **19 critiques** (bloquants si échec)

| Script | Tests | Description |
|--------|-------|-------------|
| Script 1 | 6 tests | Variables hubs (639k hubs analysés) |
| Script 2 | 4 tests | Variables concurrence |
| Script 3 | 6 tests | Variables population (intersections IRIS) |

**Ces validations sont CRITIQUES car si les données sont mauvaises ici, TOUT le pipeline est compromis.**

### Scripts 4-7 : Validations TRANSFORMATION ✅

| Script | Tests | Description |
|--------|-------|-------------|
| Script 4 | 4 tests | Intégration des features |
| Script 5 | 4 tests | Feature engineering |
| Script 6 | 3 tests | Sélection de features |
| Script 7 | 4 tests | Split train/test |

**Ces validations vérifient la cohérence des transformations (moins critiques).**

### Scripts 8-14 : MONITORING ML 📊

| Métrique | Description |
|----------|-------------|
| MAE | Erreur moyenne acceptable (< 30% du CA moyen) |
| R² | Score de prédiction (> 0.60) |
| Overfitting | Écart train/test (< 10%) |

**Ces validations surveillent la performance des modèles ML.**

---

## 🎓 Exemples d'utilisation

### Workflow développement (recommandé)

```bash
# Développe et exécute chaque script
python script_1_hubs.py
python validation_data_quality_complete.py --step 1  # ✅ Valide immédiatement

python script_2_competition.py
python validation_data_quality_complete.py --step 2  # ✅ Valide immédiatement

python script_3_population.py
python validation_data_quality_complete.py --step 3  # ✅ Valide immédiatement

# Continue pour tous les scripts...
```

**Avantage :** Détecte les problèmes tôt, avant qu'ils se propagent.

### Workflow validation groupée

```bash
# Après avoir exécuté les scripts 1, 2 et 3
python validation_data_quality_complete.py --step 1-3

# Résultat immédiat : ✅ ou ❌
```

### Workflow production (automatisé)

```python
# À la fin de chaque script de préparation
import subprocess

result = subprocess.run([
    "python", 
    "validation_data_quality_complete.py",
    "--step", "1"  # Numéro du script actuel
])

if result.returncode != 0:
    raise Exception("❌ Validation échouée - Pipeline arrêté")
```

---

## 📊 Interprétation des résultats

### ✅ Succès complet

```
📊 RÉSUMÉ
  Total tests : 34
  ✅ Réussis : 34 (100.0%)
  ❌ Échoués : 0 (0.0%)
  🚨 Erreurs critiques : 0

✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

→ **Continue en confiance !** 🚀

### ⚠️ Warnings (non bloquants)

```
📊 RÉSUMÉ
  Total tests : 34
  ✅ Réussis : 32 (94.1%)
  ❌ Échoués : 2 (5.9%)
  🚨 Erreurs critiques : 0

⚠️ AVERTISSEMENTS (2)
  ⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent
  ⚠️ WARNING - S3_outliers_check: 1.2% pharmacies avec population aberrante

✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

→ **Investigate les warnings mais tu peux continuer.**

### ❌ Erreurs critiques (BLOQUANT)

```
📊 RÉSUMÉ
  Total tests : 34
  ✅ Réussis : 30 (88.2%)
  ❌ Échoués : 4 (11.8%)
  🚨 Erreurs critiques : 2

🚨 ERREURS CRITIQUES (2)
  ❌ CRITIQUE - S1_count_pharmacies: Nombre de pharmacies : 15,234 (attendu : ~20,000)
  ❌ CRITIQUE - S3_population_variables: 12/18 variables population créées

❌ VALIDATION ÉCHOUÉE - Corriger les erreurs critiques avant de continuer
```

→ **STOP ❌ Corrige les erreurs avant de continuer !**

---

## 📄 Rapports générés

Chaque exécution génère un rapport JSON daté :

```
N:\...\scoring_pharma_65-\data\intermediaire\output\
    validation_report_20251112_103000.json
```

**Contenu du rapport :**
```json
{
  "timestamp": "2025-11-12T10:30:00",
  "summary": {
    "total_tests": 34,
    "passed": 32,
    "failed": 2,
    "critical_errors": 0
  },
  "results": {
    "S1_count_pharmacies": {
      "passed": true,
      "message": "Nombre de pharmacies : 20,134 (attendu : ~20,000)",
      "timestamp": "2025-11-12T10:30:01",
      "critical": true
    },
    ...
  },
  "errors": [...],
  "warnings": [...]
}
```

**Utilité :**
- Traçabilité complète
- Comparaison entre runs
- Debugging facilité

---

## 🔧 Configuration

### Modifier les chemins

Édite les variables au début du script Python :

```python
# Ligne ~25
BASE_PATH = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\...")
OUTPUT_PATH = BASE_PATH / "data" / "intermediaire" / "output"
SCRIPT_PATH = BASE_PATH / "data" / "intermediaire" / "script"
```

### Modifier les seuils de validation

Exemple : Accepter plus de pharmacies isolées

```python
# Ligne ~250 environ (dans validate_script2_competition)
pharmacies_isolees = (df["nb_concurrents_drive_20min"] == 0).sum()
pct_isolees = (pharmacies_isolees / len(df)) * 100
passed = pct_isolees < 5  # Modifie 5 → 10 pour accepter 10%
```

### Ajouter un nouveau test

```python
# Ajoute dans la méthode validate_scriptX_xxx
def validate_script1_hubs(self):
    ...
    
    # Nouveau test personnalisé
    mon_test = ma_logique_de_validation()
    self.log_result(
        "S1_mon_nouveau_test",
        mon_test,
        "Message descriptif",
        is_critical=True  # ou False
    )
```

---

## 💡 Bonnes pratiques

### ✅ Valide après CHAQUE script

Ne fais pas tous les scripts puis valide à la fin. Valide au fur et à mesure !

```bash
python script_1_hubs.py && python validation_data_quality_complete.py --step 1
python script_2_competition.py && python validation_data_quality_complete.py --step 2
python script_3_population.py && python validation_data_quality_complete.py --step 3
```

### ✅ Garde les rapports JSON

Les rapports sont datés automatiquement. Conserve-les pour :
- Comparer les runs
- Tracer l'évolution de la qualité
- Débugger les régressions

### ✅ Automatise dans un script bash

Crée un fichier `run_pipeline.sh` :

```bash
#!/bin/bash

for i in {1..7}; do
    echo "🔄 Exécution Script $i..."
    python script_${i}_*.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Script $i a échoué"
        exit 1
    fi
    
    echo "🔍 Validation Script $i..."
    python validation_data_quality_complete.py --step $i
    
    if [ $? -ne 0 ]; then
        echo "❌ Validation Script $i échouée"
        exit 1
    fi
    
    echo "✅ Script $i validé avec succès"
done

echo "🎉 Pipeline complet validé !"
```

---

## 🐛 Dépannage rapide

### Erreur : Fichier non trouvé

```
❌ CRITIQUE - S1_file_exists: Fichier non trouvé
```

**Solution :** Vérifie que :
1. Le script précédent a bien été exécuté
2. Le chemin `BASE_PATH` est correct
3. Le fichier est dans `/output/`

### Erreur : Variables manquantes

```
❌ CRITIQUE - S1_hub_variables: 42/48 variables créées
```

**Solution :**
1. Vérifie les logs du script concerné
2. Identifie quelles catégories ont échoué
3. Relance le script avec corrections

### Warning récurrent : Pharmacies isolées

```
⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent
```

**Action :**
- Normal dans les zones rurales
- Si > 10%, investigate (problème d'isochrones ?)
- Sinon, documente et continue

---

## 📞 Support

**Questions sur l'utilisation :** Consulte `GUIDE_CLI_VALIDATION.md`  
**Questions sur les tests :** Consulte `GUIDE_VALIDATION_DATA_QUALITY.md`  
**Questions sur l'architecture :** Consulte `ARCHITECTURE_VALIDATION.md`

---

## 🎯 En résumé

**Pour valider UN script après l'avoir exécuté :**
```bash
python validation_data_quality_complete.py --step 1
```

**Pour valider TOUT le pipeline :**
```bash
python validation_data_quality_complete.py
```

**C'est aussi simple que ça !** 🚀

---

**Auteur :** Victoire LOUIS  
**Date :** Novembre 2025  
**Version :** 1.0  
**Projet :** Pipeline Scoring Pharmacies 65+
