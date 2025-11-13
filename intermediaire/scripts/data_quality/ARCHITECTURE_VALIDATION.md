# Architecture du système de validation Data Quality

## 🎯 Vue d'ensemble

Le système de validation data quality garantit l'intégrité des données à chaque étape du pipeline de scoring des pharmacies 65+.

### Principe de validation en cascade

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PIPELINE SCORING PHARMACIES 65+                  │
└─────────────────────────────────────────────────────────────────────┘

Script 1: Hubs           →  [VALIDATION CRITIQUE] ✅
   ↓
Script 2: Concurrence    →  [VALIDATION CRITIQUE] ✅
   ↓
Script 3: Population     →  [VALIDATION CRITIQUE] ✅
   ↓
Script 4: Intégration    →  [VALIDATION TRANSFORMATION] ✅
   ↓
Script 5: Features       →  [VALIDATION TRANSFORMATION] ✅
   ↓
Script 6: Sélection      →  [VALIDATION TRANSFORMATION] ✅
   ↓
Script 7: Split          →  [VALIDATION TRANSFORMATION] ✅
   ↓
Scripts 8-14: ML         →  [MONITORING MÉTRIQUES] 📊
```

---

## 📊 Niveaux de validation

### Niveau 1 : Validations CRITIQUES (Scripts 1-3)

**Objectif :** Détecter les erreurs qui compromettent TOUT le pipeline

**Caractéristiques :**
- Tests stricts et bloquants
- Pas de tolérance sur les données essentielles
- Erreur = STOP immédiat du pipeline

**Exemples :**
```python
# Script 1 : Toutes les pharmacies doivent avoir des coordonnées
missing_coords = df[["latitude", "longitude"]].isna().any(axis=1).sum()
passed = missing_coords == 0  # Aucune tolérance
```

**Pourquoi critique ?**
- Script 1 traite 639k hubs → Si mal géocodés, toutes les distances sont fausses
- Script 3 fait des intersections géométriques → Si mal calculées, la population est fausse
- Ces erreurs se propagent à TOUS les scripts suivants

### Niveau 2 : Validations de TRANSFORMATION (Scripts 4-7)

**Objectif :** Vérifier la cohérence des transformations de données

**Caractéristiques :**
- Tests de cohérence et intégrité
- Tolérance sur certains aspects (outliers, distribution)
- Erreur = WARNING mais peut continuer

**Exemples :**
```python
# Script 5 : Ratios doivent être entre 0 et 1
ratios_valides = ((df[ratio_cols] >= 0) & (df[ratio_cols] <= 1)).all().all()
passed = ratios_valides  # Warning si échec, pas bloquant
```

**Pourquoi moins critique ?**
- Transformations mathématiques déterministes (log, ratios, etc.)
- Algorithmes sklearn fiables (sélection features, split)
- Erreurs plus faciles à identifier et corriger

### Niveau 3 : MONITORING ML (Scripts 8-14)

**Objectif :** Surveiller la performance des modèles

**Caractéristiques :**
- Métriques de performance (MAE, R², overfitting)
- Tests informatifs, pas bloquants
- Utilisé pour améliorer le modèle

**Exemples :**
```python
# Monitoring : MAE doit être raisonnable
mae_pct = (mae / mean_ca) * 100
passed = mae_pct < 30  # Informatif, pas bloquant
```

**Pourquoi monitoring ?**
- Les modèles ML ont déjà leurs propres métriques intégrées
- Validation se fait via cross-validation, gridsearch, etc.
- Objectif : tracer l'évolution des performances

---

## 🔍 Types de tests implémentés

### 1. Tests de COMPLÉTUDE

Vérifient que toutes les données attendues sont présentes.

```python
# Exemple : Toutes les pharmacies doivent être présentes
n_pharmacies = len(df)
passed = 19000 <= n_pharmacies <= 21000
```

**Où :** Scripts 1-7  
**Criticité :** ✅ Critique

### 2. Tests de COHÉRENCE

Vérifient que les relations entre variables sont logiques.

```python
# Exemple : drive_5min <= drive_10min <= drive_15min <= drive_20min
coherent = (df["drive_5"] <= df["drive_10"]) & (df["drive_10"] <= df["drive_15"])
passed = coherent.all()
```

**Où :** Scripts 2-3, 7  
**Criticité :** ⚠️ Warning (sauf si incohérence massive)

### 3. Tests de VALIDITÉ

Vérifient que les valeurs sont dans les plages attendues.

```python
# Exemple : Pas de valeurs négatives dans les comptages
negative_values = (df[count_cols] < 0).any().any()
passed = not negative_values
```

**Où :** Scripts 1-5  
**Criticité :** ✅ Critique

### 4. Tests de DISTRIBUTION

Vérifient que les distributions sont plausibles.

```python
# Exemple : Moins de 1% de valeurs aberrantes (outliers)
outliers = ((df[col] < Q1 - 3*IQR) | (df[col] > Q3 + 3*IQR)).sum()
pct_outliers = (outliers / len(df)) * 100
passed = pct_outliers < 1
```

**Où :** Scripts 3, 5, 7  
**Criticité :** ⚠️ Warning

### 5. Tests d'INTÉGRITÉ

Vérifient que les opérations de fusion/split sont correctes.

```python
# Exemple : Pas de fuite de données entre train et test
train_ids = set(df_train["finess"])
test_ids = set(df_test["finess"])
overlap = train_ids & test_ids
passed = len(overlap) == 0
```

**Où :** Scripts 4, 7  
**Criticité :** ✅ Critique

### 6. Tests de PERFORMANCE

Vérifient que les métriques ML sont acceptables.

```python
# Exemple : R² doit être > 0.60
r2 = results["r2_test"]
passed = r2 > 0.6
```

**Où :** Scripts 8-14  
**Criticité :** 📊 Informatif

---

## 🏗️ Architecture du code

### Classe `DataQualityValidator`

```python
class DataQualityValidator:
    """Classe centrale de validation"""
    
    def __init__(self):
        self.results = {}    # Stocke tous les résultats
        self.errors = []     # Liste des erreurs critiques
        self.warnings = []   # Liste des avertissements
    
    def log_result(self, test_name, passed, message, is_critical):
        """Enregistre le résultat d'un test"""
        # Logique centralisée pour tous les tests
    
    def validate_scriptX_xxx(self):
        """Méthode de validation pour chaque script"""
        # Tests spécifiques au script
    
    def generate_report(self):
        """Génère le rapport final JSON + console"""
```

### Flux d'exécution

```python
def main():
    # 1. Initialisation
    validator = DataQualityValidator()
    
    # 2. Validations en cascade
    validator.validate_script1_hubs()
    validator.validate_script2_competition()
    validator.validate_script3_population()
    validator.validate_script4_integration()
    validator.validate_script5_features()
    validator.validate_script6_selection()
    validator.validate_script7_split()
    
    # 3. Monitoring ML (optionnel)
    validator.monitor_ml_metrics()
    
    # 4. Rapport final
    success = validator.generate_report()
    
    return success  # True si aucune erreur critique
```

---

## 📈 Évolution du nombre de tests

| Script | Tests | Critiques | Warnings |
|--------|-------|-----------|----------|
| Script 1 | 6 | 5 | 1 |
| Script 2 | 4 | 2 | 2 |
| Script 3 | 6 | 3 | 3 |
| Script 4 | 4 | 3 | 1 |
| Script 5 | 4 | 2 | 2 |
| Script 6 | 3 | 1 | 2 |
| Script 7 | 4 | 3 | 1 |
| Scripts 8-14 | 3 | 0 | 3 |
| **TOTAL** | **34** | **19** | **15** |

---

## 🔄 Workflow d'utilisation

### 1. Développement initial

```bash
# Après chaque script de préparation
python script_1_hubs.py
python validation_data_quality_complete.py  # Vérifie immédiatement

python script_2_competition.py
python validation_data_quality_complete.py  # Vérifie immédiatement

python script_3_population.py
python validation_data_quality_complete.py  # Vérifie immédiatement
```

**Avantage :** Détecte les problèmes tôt, avant qu'ils se propagent

### 2. Production / Automatisation

```python
# Dans chaque script, à la fin
import subprocess

result = subprocess.run([
    "python", 
    "validation_data_quality_complete.py"
])

if result.returncode != 0:
    raise Exception("❌ Validation échouée - Pipeline arrêté")
```

**Avantage :** Arrêt automatique si erreur critique

### 3. Monitoring continu

```bash
# Cron job quotidien / hebdomadaire
0 6 * * 1 python validation_data_quality_complete.py && mail -s "Validation OK" victoire@example.com
```

**Avantage :** Surveillance de la qualité dans le temps

---

## 📊 Format du rapport JSON

```json
{
  "timestamp": "2025-11-12T10:30:00",
  "summary": {
    "total_tests": 34,
    "passed": 32,
    "failed": 2,
    "critical_errors": 1
  },
  "results": {
    "S1_count_pharmacies": {
      "passed": true,
      "message": "Nombre de pharmacies : 20,134 (attendu : ~20,000)",
      "timestamp": "2025-11-12T10:30:01",
      "critical": true
    },
    "S3_population_variables": {
      "passed": false,
      "message": "12/18 variables population créées",
      "timestamp": "2025-11-12T10:30:05",
      "critical": true
    },
    ...
  },
  "errors": [
    "❌ CRITIQUE - S3_population_variables: 12/18 variables population créées"
  ],
  "warnings": [
    "⚠️ WARNING - S2_isolation_check: 6.2% pharmacies sans concurrent",
    "⚠️ WARNING - S3_outliers_check: 1.2% pharmacies avec population aberrante"
  ]
}
```

**Utilisation du rapport :**
- Traçabilité : Garde l'historique des validations
- Debug : Identifie quels tests ont échoué et pourquoi
- Monitoring : Compare les rapports dans le temps

---

## 🎓 Exemples de scénarios

### Scénario 1 : Tout fonctionne parfaitement

```
================================================================================
VALIDATION DATA QUALITY - PIPELINE SCORING PHARMACIES 65+
================================================================================

VALIDATION SCRIPT 1 : VARIABLES HUBS
✅ S1_count_pharmacies
✅ S1_required_columns
✅ S1_hub_variables
✅ S1_no_negative_values
✅ S1_hub_distribution
✅ S1_missing_coordinates

VALIDATION SCRIPT 2 : VARIABLES CONCURRENCE
✅ S2_same_pharmacy_count
✅ S2_competition_variables
✅ S2_isolation_check
✅ S2_isochrone_coherence

... (tous les autres scripts) ...

📊 RÉSUMÉ
  Total tests : 34
  ✅ Réussis : 34 (100.0%)
  ❌ Échoués : 0 (0.0%)
  🚨 Erreurs critiques : 0

✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

**Action :** Continue en confiance ! 🚀

### Scénario 2 : Quelques warnings

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

**Action :**
1. Investigate les warnings (mais pas bloquant)
2. Si normal (zones rurales), documente
3. Si anormal, corrige et re-valide

### Scénario 3 : Erreur critique

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

**Action :**
1. **STOP** ❌ Ne pas continuer le pipeline
2. Investigate S1 : Pourquoi seulement 15k pharmacies ?
3. Investigate S3 : Quelles variables n'ont pas été créées ?
4. Corrige les scripts concernés
5. Re-valide avant de continuer

---

## 💡 Principes de conception

### 1. Fail Fast

```python
# Test critique échoué → Exit immédiatement
if n_critical_failed > 0:
    exit(1)  # Code de retour non-zéro
```

**Avantage :** Évite de propager les erreurs dans le pipeline

### 2. Traçabilité totale

```python
# Chaque test est daté et documenté
result = {
    "passed": passed,
    "message": message,
    "timestamp": datetime.now().isoformat(),
    "critical": is_critical
}
```

**Avantage :** Audit trail complet pour debugging

### 3. Extensibilité

```python
# Ajouter un nouveau test = ajouter une méthode
def validate_scriptX_nouveau_test(self):
    """Nouveau test personnalisé"""
    passed = ma_logique_de_test()
    self.log_result("SX_nouveau_test", passed, "Message", is_critical=False)
```

**Avantage :** Facile d'ajouter de nouveaux tests

### 4. Séparation critique / warning

```python
# Les tests critiques bloquent, les warnings alertent
self.log_result(test_name, passed, message, is_critical=True)  # Bloquant
self.log_result(test_name, passed, message, is_critical=False) # Alerte
```

**Avantage :** Flexibilité selon la sévérité

---

## 🚀 Évolutions futures

### v2.0 : Corrections automatiques

```python
def auto_fix_missing_coordinates(self, df):
    """Géocode automatiquement les pharmacies sans coordonnées"""
    missing = df[df["latitude"].isna()]
    # Appel API géocodage...
    return df_fixed
```

### v2.1 : Alertes email

```python
def send_alert_email(self, errors):
    """Envoie un email si erreurs critiques"""
    import smtplib
    # Logique d'envoi...
```

### v2.2 : Dashboard de monitoring

```python
def export_to_dashboard(self, results):
    """Exporte les résultats vers un dashboard Streamlit/Dash"""
    # Visualisations temps réel...
```

---

## 📞 Support et maintenance

**Mainteneur :** Victoire LOUIS  
**Date création :** Novembre 2025  
**Version :** 1.0  

**Modifications futures :**
- Ajouter dans ce document
- Versionner le script de validation
- Documenter les changements de seuils

---

## 🎯 Conclusion

Ce système de validation garantit :
- ✅ Qualité des données à chaque étape
- 🔍 Détection précoce des erreurs
- 📊 Traçabilité complète
- 🚀 Confiance dans le pipeline

**Principe clé :** Valider tôt, valider souvent, valider bien ! 🎯
