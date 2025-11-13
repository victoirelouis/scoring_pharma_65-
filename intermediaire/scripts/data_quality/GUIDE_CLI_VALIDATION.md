# Guide rapide - Validation par étape

## 🚀 Utilisation en ligne de commande

### Validation COMPLÈTE (tous les scripts)

```bash
python validation_data_quality_complete.py
```

Valide tous les scripts 1-14 d'un coup.

---

## 🎯 Validation CIBLÉE (script par script)

### Valider UN SEUL script

```bash
# Valide uniquement le Script 1
python validation_data_quality_complete.py --step 1

# Valide uniquement le Script 2
python validation_data_quality_complete.py --step 2

# Valide uniquement le Script 3
python validation_data_quality_complete.py --step 3

# Etc.
python validation_data_quality_complete.py --step 4
python validation_data_quality_complete.py --step 5
python validation_data_quality_complete.py --step 6
python validation_data_quality_complete.py --step 7
```

### Valider PLUSIEURS scripts spécifiques

```bash
# Valide Scripts 1, 2 et 3
python validation_data_quality_complete.py --step 1 2 3

# Valide Scripts 1, 3 et 5
python validation_data_quality_complete.py --step 1 3 5

# Valide Scripts 4, 5, 6 et 7
python validation_data_quality_complete.py --step 4 5 6 7
```

### Valider une PLAGE de scripts

```bash
# Valide Scripts 1 à 3 (1, 2, 3)
python validation_data_quality_complete.py --step 1-3

# Valide Scripts 1 à 5 (1, 2, 3, 4, 5)
python validation_data_quality_complete.py --step 1-5

# Valide Scripts 4 à 7 (4, 5, 6, 7)
python validation_data_quality_complete.py --step 4-7
```

### Combiner plages et numéros spécifiques

```bash
# Valide Scripts 1 à 3 + Script 5 + Script 7
python validation_data_quality_complete.py --step 1-3 5 7

# Valide Scripts 1, 2, 3, 5, 6, 7
python validation_data_quality_complete.py --step 1-3 5-7
```

### Valider UNIQUEMENT les scripts ML (8-14)

```bash
# Raccourci pour valider tous les scripts ML
python validation_data_quality_complete.py --step ml

# Équivalent à :
python validation_data_quality_complete.py --step 8-14
```

---

## 📊 Exemples de workflow

### Workflow 1 : Développement (valider après chaque script)

```bash
# Développe et exécute Script 1
python script_1_hubs.py

# Valide immédiatement
python validation_data_quality_complete.py --step 1
# ✅ Si OK, continue

# Développe et exécute Script 2
python script_2_competition.py

# Valide immédiatement
python validation_data_quality_complete.py --step 2
# ✅ Si OK, continue

# Développe et exécute Script 3
python script_3_population.py

# Valide immédiatement
python validation_data_quality_complete.py --step 3
# ✅ Si OK, continue

# Etc.
```

### Workflow 2 : Validation des scripts critiques (1-3)

```bash
# Après avoir exécuté les scripts 1, 2 et 3
python validation_data_quality_complete.py --step 1-3
```

**Résultat :**
```
================================================================================
VALIDATION DATA QUALITY - PIPELINE SCORING PHARMACIES 65+
================================================================================
Date : 2025-11-12 11:30:00
Chemin base : N:\...\scoring_pharma_65-
Mode : VALIDATION CIBLÉE (scripts 1, 2, 3)

================================================================================
VALIDATION SCRIPT 1 : VARIABLES HUBS
================================================================================
✅ S1_count_pharmacies
✅ S1_required_columns
✅ S1_hub_variables
...

================================================================================
VALIDATION SCRIPT 2 : VARIABLES CONCURRENCE
================================================================================
✅ S2_same_pharmacy_count
...

================================================================================
VALIDATION SCRIPT 3 : VARIABLES POPULATION
================================================================================
✅ S3_same_pharmacy_count
...

📊 RÉSUMÉ
  Total tests : 16
  ✅ Réussis : 16 (100.0%)
  ❌ Échoués : 0 (0.0%)
  🚨 Erreurs critiques : 0

✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML
```

### Workflow 3 : Validation avant ML (scripts 1-7)

```bash
# Avant de lancer l'entraînement ML
python validation_data_quality_complete.py --step 1-7
```

Valide toute la préparation de données d'un coup.

### Workflow 4 : Vérifier seulement un script problématique

```bash
# Script 3 a échoué hier, tu l'as corrigé, vérifie uniquement celui-là
python validation_data_quality_complete.py --step 3
```

---

## 🔧 Options avancées

### Obtenir de l'aide

```bash
python validation_data_quality_complete.py --help
```

**Affiche :**
```
usage: validation_data_quality_complete.py [-h] [--step STEP [STEP ...]]

Validation data quality pour le pipeline scoring pharmacies 65+

optional arguments:
  -h, --help            show this help message and exit
  --step STEP [STEP ...], --steps STEP [STEP ...]
                        Numéros des scripts à valider (ex: 1, 2, 3 ou 1-3 ou ml pour 8-14)

Exemples d'utilisation:
  python validation_data_quality_complete.py                    # Valide TOUT
  python validation_data_quality_complete.py --step 1           # Valide Script 1 uniquement
  python validation_data_quality_complete.py --step 1 2 3       # Valide Scripts 1, 2 et 3
  python validation_data_quality_complete.py --step 1-3         # Valide Scripts 1 à 3
  python validation_data_quality_complete.py --step 1-3 5 7     # Valide Scripts 1-3, 5 et 7
  python validation_data_quality_complete.py --step ml          # Valide uniquement ML (8-14)
```

---

## 🎓 Tableau de correspondance

| Commande | Scripts validés | Cas d'usage |
|----------|----------------|-------------|
| `--step 1` | Script 1 | Après exécution du Script 1 |
| `--step 2` | Script 2 | Après exécution du Script 2 |
| `--step 3` | Script 3 | Après exécution du Script 3 |
| `--step 1-3` | Scripts 1, 2, 3 | Valider les scripts critiques |
| `--step 4-7` | Scripts 4, 5, 6, 7 | Valider le feature engineering |
| `--step 1-7` | Scripts 1 à 7 | Validation complète avant ML |
| `--step ml` | Scripts 8-14 | Monitoring des modèles ML |
| *(aucun)* | Scripts 1-14 | Validation complète du pipeline |

---

## 💡 Conseils pratiques

### ✅ Valide après chaque étape

```bash
# Meilleure pratique
python script_1_hubs.py && python validation_data_quality_complete.py --step 1
```

L'opérateur `&&` n'exécute la validation que si le script réussit.

### ✅ Automatise avec un script bash

```bash
#!/bin/bash
# validate_and_continue.sh

SCRIPT_NUM=$1

echo "🔄 Exécution Script $SCRIPT_NUM..."
python script_${SCRIPT_NUM}_*.py

if [ $? -eq 0 ]; then
    echo "✅ Script $SCRIPT_NUM terminé"
    echo "🔍 Validation en cours..."
    python validation_data_quality_complete.py --step $SCRIPT_NUM
    
    if [ $? -eq 0 ]; then
        echo "✅ Validation réussie pour Script $SCRIPT_NUM"
    else
        echo "❌ Validation échouée pour Script $SCRIPT_NUM"
        exit 1
    fi
else
    echo "❌ Script $SCRIPT_NUM a échoué"
    exit 1
fi
```

**Utilisation :**
```bash
chmod +x validate_and_continue.sh
./validate_and_continue.sh 1  # Exécute et valide Script 1
```

### ✅ Intègre dans tes scripts Python

```python
# À la fin de script_1_hubs.py
import subprocess

print("\n🔍 Lancement de la validation...")
result = subprocess.run([
    "python", 
    "validation_data_quality_complete.py",
    "--step", "1"
])

if result.returncode != 0:
    raise Exception("❌ Validation Script 1 échouée")

print("✅ Script 1 validé avec succès !")
```

---

## 🚨 Codes de retour

Le script utilise des codes de retour standard :

| Code | Signification | Action |
|------|--------------|--------|
| `0` | ✅ Validation réussie | Continue le pipeline |
| `1` | ❌ Erreurs critiques détectées | STOP - Corrige les erreurs |

**Utilisation dans bash :**
```bash
python validation_data_quality_complete.py --step 1

if [ $? -eq 0 ]; then
    echo "OK, on continue !"
else
    echo "Erreur détectée, on arrête tout"
    exit 1
fi
```

**Utilisation dans Python :**
```python
import subprocess

result = subprocess.run([
    "python", 
    "validation_data_quality_complete.py",
    "--step", "1"
])

if result.returncode == 0:
    print("OK, on continue !")
else:
    raise Exception("Erreur détectée, on arrête tout")
```

---

## 🎯 Résumé

**Valider UN script :**
```bash
python validation_data_quality_complete.py --step 1
```

**Valider PLUSIEURS scripts :**
```bash
python validation_data_quality_complete.py --step 1 2 3
```

**Valider une PLAGE :**
```bash
python validation_data_quality_complete.py --step 1-3
```

**Valider TOUT :**
```bash
python validation_data_quality_complete.py
```

C'est simple et flexible ! 🚀
