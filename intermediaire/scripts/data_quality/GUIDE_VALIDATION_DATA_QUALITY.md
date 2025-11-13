# Guide d'utilisation - Validation Data Quality

## 📋 Vue d'ensemble

Ce script valide automatiquement la qualité des données à chaque étape du pipeline de scoring des pharmacies 65+.

### Philosophie de validation

**Scripts 1-3 : Validations CRITIQUES**
- Ces scripts traitent les données brutes (639k hubs, intersections géométriques, etc.)
- ⚠️ Si les données sont mauvaises ici, TOUT le pipeline est compromis
- Les tests sont stricts et bloquants

**Scripts 4-7 : Validations de TRANSFORMATION**
- Feature engineering, intégration, sélection
- Risque plus faible car transformations déterministes
- Les tests vérifient la cohérence des transformations

**Scripts 8-14 : MONITORING ML**
- Modèles ML, prédictions finales
- Validation via métriques (MAE, R², overfitting)
- Tests informatifs plutôt que bloquants

---

## 🚀 Utilisation

### Lancer la validation complète

```python
python validation_data_quality_complete.py
```

Le script :
1. ✅ Valide chaque étape (Scripts 1-7)
2. 📊 Monitore les métriques ML (Scripts 8-14)
3. 📄 Génère un rapport JSON avec tous les résultats
4. 🎯 Donne un verdict final : `✅ RÉUSSI` ou `❌ ÉCHOUÉ`

### Lire le rapport

Le rapport JSON est sauvegardé dans :
```
N:\...\scoring_pharma_65-\data\intermediaire\output\validation_report_YYYYMMDD_HHMMSS.json
```

Structure du rapport :
```json
{
  "timestamp": "2025-11-12T10:30:00",
  "summary": {
    "total_tests": 45,
    "passed": 43,
    "failed": 2,
    "critical_errors": 1
  },
  "results": {
    "S1_count_pharmacies": {
      "passed": true,
      "message": "Nombre de pharmacies : 20,134 (attendu : ~20,000)",
      "critical": true
    },
    ...
  },
  "errors": [
    "❌ CRITIQUE - S3_missing_coordinates: 5 pharmacies sans coordonnées"
  ],
  "warnings": [
    "⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent"
  ]
}
```

---

## 🧪 Tests par script

### Script 1 : Variables Hubs

| Test | Description | Critique |
|------|-------------|----------|
| `S1_count_pharmacies` | Vérifie ~20,000 pharmacies | ✅ Oui |
| `S1_required_columns` | Colonnes `finess`, `latitude`, `longitude` présentes | ✅ Oui |
| `S1_hub_variables` | Toutes les variables hubs créées (48 variables) | ✅ Oui |
| `S1_no_negative_values` | Pas de comptages négatifs | ✅ Oui |
| `S1_hub_distribution` | Chaque pharmacie a des hubs en drive_20min | ⚠️ Non |
| `S1_missing_coordinates` | Toutes les pharmacies géocodées | ✅ Oui |

### Script 2 : Variables Concurrence

| Test | Description | Critique |
|------|-------------|----------|
| `S2_same_pharmacy_count` | Même nombre de pharmacies que Script 1 | ✅ Oui |
| `S2_competition_variables` | Variables concurrence créées (6 variables) | ✅ Oui |
| `S2_isolation_check` | Moins de 5% pharmacies isolées | ⚠️ Non |
| `S2_isochrone_coherence` | drive_5min ≤ drive_10min ≤ ... | ⚠️ Non |

### Script 3 : Variables Population

| Test | Description | Critique |
|------|-------------|----------|
| `S3_same_pharmacy_count` | Même nombre de pharmacies | ✅ Oui |
| `S3_population_variables` | Variables population créées (18 variables) | ✅ Oui |
| `S3_no_negative_population` | Pas de population négative | ✅ Oui |
| `S3_population_coverage` | Chaque pharmacie a une population 65+ | ✅ Oui* |
| `S3_population_coherence` | Population croissante avec isochrone | ⚠️ Non |
| `S3_outliers_check` | Moins de 1% valeurs aberrantes | ⚠️ Non |

*Critique si > 50 pharmacies sans population

### Script 4 : Intégration

| Test | Description | Critique |
|------|-------------|----------|
| `S4_all_features_integrated` | Toutes les variables des scripts 1-3 | ✅ Oui |
| `S4_no_pharmacy_loss` | Pas de perte lors du merge | ✅ Oui |
| `S4_target_variables` | Variables CA présentes | ✅ Oui |
| `S4_missing_values` | Moins de 20% valeurs manquantes par colonne | ⚠️ Non |

### Script 5 : Feature Engineering

| Test | Description | Critique |
|------|-------------|----------|
| `S5_new_features_created` | Nouvelles features créées | ✅ Oui |
| `S5_no_infinite_values` | Pas de division par zéro | ✅ Oui |
| `S5_ratio_coherence` | Ratios entre 0 et 1 | ⚠️ Non |
| `S5_non_zero_variance` | Pas de colonnes constantes | ⚠️ Non |

### Script 6 : Sélection Features

| Test | Description | Critique |
|------|-------------|----------|
| `S6_feature_reduction` | Nombre de features réduit | ⚠️ Non |
| `S6_targets_preserved` | Variables target préservées | ✅ Oui |
| `S6_multicollinearity` | Moins de 5 paires corrélées > 0.95 | ⚠️ Non |

### Script 7 : Split Train/Test

| Test | Description | Critique |
|------|-------------|----------|
| `S7_no_data_loss` | train + test = total | ✅ Oui |
| `S7_split_ratio` | Ratio 70-85% train | ⚠️ Non |
| `S7_no_data_leakage` | Pas de pharmacie en commun | ✅ Oui |
| `S7_target_distribution` | Distribution similaire train/test | ⚠️ Non |

### Scripts 8-14 : Monitoring ML

| Métrique | Description | Critique |
|----------|-------------|----------|
| `ML_mae_reasonable` | MAE < 30% du CA moyen | ⚠️ Non |
| `ML_r2_acceptable` | R² > 0.60 | ⚠️ Non |
| `ML_no_overfitting` | Écart train/test < 10% | ⚠️ Non |

---

## 🔧 Personnalisation

### Modifier les seuils

Pour ajuster les seuils de validation, modifiez les valeurs dans le script :

```python
# Exemple : Script 3, population coverage
passed = pharmacies_sans_pop < 10  # Modifie 10 → 20 si besoin
```

### Ajouter un nouveau test

```python
def validate_scriptX_custom(self):
    """Valide un aspect personnalisé"""
    print("\n" + "="*80)
    print("VALIDATION CUSTOM")
    print("="*80)
    
    try:
        df = pd.read_csv(FILES["scriptX_output"])
        
        # Test personnalisé
        passed = ma_condition_de_test
        self.log_result(
            "SX_mon_test",
            passed,
            "Message descriptif",
            is_critical=True  # ou False
        )
        
    except Exception as e:
        self.log_result(
            "SX_general_error",
            False,
            f"Erreur : {str(e)}",
            is_critical=True
        )
```

Puis ajoute dans `main()` :
```python
validator.validate_scriptX_custom()
```

---

## 🐛 Dépannage

### Erreur : Fichier non trouvé

**Symptôme :**
```
❌ CRITIQUE - S1_file_exists: Fichier non trouvé : ...pharmacies_avec_variables_hubs.csv
```

**Solutions :**
1. Vérifie que le Script 1 a bien été exécuté
2. Vérifie le chemin dans la variable `BASE_PATH`
3. Vérifie que le fichier est bien dans `/output/`

### Erreur : Variables manquantes

**Symptôme :**
```
❌ CRITIQUE - S1_hub_variables: 42/48 variables hubs créées
```

**Solutions :**
1. Vérifie que tous les types d'isochrones sont calculés
2. Vérifie les logs du Script 1 pour voir quelles catégories ont échoué
3. Relance le Script 1 avec les corrections

### Warning : Pharmacies isolées

**Symptôme :**
```
⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent en drive_20min
```

**Actions :**
1. C'est normal dans les zones très rurales
2. Vérifie quand même les FINESS de ces pharmacies
3. Si > 10%, investigate (problème d'isochrones ?)

### Warning : Distribution targets

**Symptôme :**
```
⚠️ WARNING - S7_target_distribution: Distribution des targets trop différente
```

**Actions :**
1. Vérifie le stratified split (par département ?)
2. Vérifie si outliers dans un seul split
3. Considère un re-split avec meilleure stratification

---

## 📊 Interprétation des résultats

### ✅ Tous les tests passent

```
✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

→ Vous pouvez continuer en toute confiance ! 🚀

### ⚠️ Quelques warnings

```
⚠️ AVERTISSEMENTS (3)
  ⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent
  ⚠️ WARNING - S3_outliers_check: 1.2% pharmacies avec population aberrante
  ⚠️ WARNING - S5_ratio_coherence: Ratios hors limites [0,1] détectés
```

→ Investigate mais pas bloquant. Le pipeline peut continuer.

### ❌ Erreurs critiques

```
🚨 ERREURS CRITIQUES (2)
  ❌ CRITIQUE - S1_count_pharmacies: Nombre de pharmacies : 15,234 (attendu : ~20,000)
  ❌ CRITIQUE - S3_population_variables: 12/18 variables population créées
```

→ **STOP** ❌ Ne pas continuer ! Corriger avant de passer à la suite.

---

## 🎯 Workflow recommandé

### 1. Après chaque script de préparation (1-3)

```bash
python validation_data_quality_complete.py
```

Vérifie immédiatement les erreurs critiques.

### 2. Avant l'entraînement ML (après Script 7)

```bash
python validation_data_quality_complete.py
```

S'assure que toutes les features sont OK.

### 3. Après l'entraînement (Script 8+)

```bash
python validation_data_quality_complete.py
```

Vérifie les métriques ML (MAE, R², overfitting).

---

## 💡 Bonnes pratiques

### 1. Sauvegarde les rapports

Les rapports JSON sont datés automatiquement. Garde-les pour :
- Comparer les runs successifs
- Débugger des régressions
- Documenter la qualité des données

### 2. Automatise la validation

Intègre la validation dans ton workflow :

```python
# À la fin de chaque script de préparation
import subprocess
result = subprocess.run(["python", "validation_data_quality_complete.py"])
if result.returncode != 0:
    raise Exception("Validation échouée - voir rapport")
```

### 3. Attention aux warnings récurrents

Si un warning apparaît systématiquement :
- Soit c'est normal (zones rurales, etc.) → Ajuste le seuil
- Soit c'est un vrai problème → Investigate et corrige

### 4. Versionne les seuils

Si tu modifies les seuils de validation, documente pourquoi :

```python
# Modifié le 2025-11-12 : Zones rurales acceptables
passed = pharmacies_isolees < 100  # Était 50
```

---

## 📞 Support

**En cas de problème :**
1. Consulte la section Dépannage ci-dessus
2. Vérifie le rapport JSON pour le détail des erreurs
3. Vérifie les logs des scripts de préparation (1-7)

**Questions fréquentes :**

**Q : Combien de temps prend la validation ?**
A : ~30 secondes pour valider tous les scripts

**Q : Puis-je valider un seul script ?**
A : Oui, commente les autres dans `main()` :

```python
def main():
    validator = DataQualityValidator()
    # validator.validate_script1_hubs()
    # validator.validate_script2_competition()
    validator.validate_script3_population()  # Seulement celui-ci
    ...
```

**Q : Le script peut-il corriger automatiquement ?**
A : Non, il détecte seulement. La correction reste manuelle pour éviter de modifier les données sans validation humaine.

---

## 🎓 Exemples d'utilisation

### Cas 1 : Validation après Script 1

```bash
$ python validation_data_quality_complete.py

================================================================================
VALIDATION SCRIPT 1 : VARIABLES HUBS
================================================================================
✅ S1_count_pharmacies
✅ S1_required_columns
✅ S1_hub_variables
✅ S1_no_negative_values
⚠️ S1_hub_distribution
✅ S1_missing_coordinates

📊 RÉSUMÉ
  Total tests : 6
  ✅ Réussis : 5 (83.3%)
  ❌ Échoués : 1 (16.7%)
  🚨 Erreurs critiques : 0

⚠️ AVERTISSEMENTS (1)
  ⚠️ WARNING - S1_hub_distribution: 42 pharmacies sans hubs en drive_20min

✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

### Cas 2 : Erreur critique détectée

```bash
$ python validation_data_quality_complete.py

================================================================================
VALIDATION SCRIPT 3 : VARIABLES POPULATION
================================================================================
✅ S3_same_pharmacy_count
❌ S3_population_variables
✅ S3_no_negative_population

🚨 ERREURS CRITIQUES (1)
  ❌ CRITIQUE - S3_population_variables: 12/18 variables population créées

❌ VALIDATION ÉCHOUÉE - Corriger les erreurs critiques avant de continuer
```

→ **Action :** Vérifie les logs du Script 3 pour voir quelles variables n'ont pas été créées

---

## 📝 Changelog

**v1.0 - 2025-11-12**
- Validation complète Scripts 1-7
- Monitoring ML Scripts 8-14
- Rapport JSON automatique
- 45 tests au total

---

**Auteur :** Victoire LOUIS  
**Date :** Novembre 2025  
**Projet :** Scoring Pharmacies 65+
