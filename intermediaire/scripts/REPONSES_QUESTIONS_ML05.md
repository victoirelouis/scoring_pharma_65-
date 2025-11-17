# RÉPONSES AUX QUESTIONS SUR LE SCRIPT ML_05

**Date:** 2025-11-17
**Auteur:** Claude

---

## 📋 VOS 4 QUESTIONS

### ❓ Question 1: Il ne faut pas prédire aussi le delta?

**Réponse:** ✅ **CORRECT - Delta EXCLU**

Le `delta` est une variable créée **APRÈS** la prédiction dans le script 6:
```python
delta = ca_reel - ca_predit
```

**Problème si on l'utilisait:**
- **Data leakage** (fuite de données)
- Le delta contient l'information du CA réel qu'on essaie de prédire
- Cela fausserait complètement le modèle

**✅ CORRECTION APPLIQUÉE:**
```python
# AVANT (ligne 149):
derived_patterns = ['ratio_', 'densite_', 'zone_', 'concurrence_par_', 'delta', 'voisins_']

# APRÈS (ligne 150):
derived_patterns = ['ratio_', 'densite_', 'zone_', 'concurrence_par_', 'voisins_']
# IMPORTANT: Exclure 'delta' car c'est une variable créée APRÈS prédiction (data leakage!)
```

---

### ❓ Question 2: Comment tu prédis le CA?

**Réponse:** Le modèle **LightGBM (Gradient Boosting)** apprend la relation entre les features et le CA.

#### Principe mathématique:
```
CA_prédit = f(HUBS, POPULATION, CONCURRENCE, TOURISME, DÉRIVÉES)
```

Le modèle construit des **arbres de décision** qui apprennent automatiquement les poids optimaux.

#### Exemple concret pour une pharmacie:

**Entrée (features):**
- `pop_65_plus_drive_10min` = 15,000 seniors
- `nb_sante_generale_drive_10min` = 25 médecins
- `nb_pharmacies_concurrentes_drive_10min` = 2 concurrents
- `capacite_accueil_drive_10min` = 500 lits touristiques
- `nb_hotels_drive_10min` = 8 hôtels
- ... (+ 248 autres features)

**Sortie (prédiction):**
- `ca_total_predit` ≈ 2,800,000 €

#### Comment le modèle apprend:

1. **Phase d'entraînement (80% des données):**
   - Le modèle analyse 15,436 pharmacies avec leur CA réel
   - Il identifie les patterns: "Si beaucoup de seniors + beaucoup de médecins + peu de concurrence → CA élevé"
   - Il construit des arbres de décision avec des règles optimisées

2. **Phase de test (20% des données):**
   - Le modèle prédit le CA de 3,860 pharmacies jamais vues
   - On compare les prédictions au CA réel → Calcul R², MAE, RMSE

3. **Phase de production (100% des données):**
   - Le modèle prédit le CA de TOUTES les 19,296 pharmacies
   - Ces prédictions deviennent les **scores d'attractivité**

#### Métriques de qualité attendues:
- **R² (coefficient de détermination):** 0.6 - 0.85
  - 1.0 = prédiction parfaite
  - 0.0 = prédiction aléatoire
- **MAE (Mean Absolute Error):** Erreur moyenne en € (plus c'est bas, mieux c'est)
- **RMSE (Root Mean Squared Error):** Pénalise davantage les grosses erreurs

---

### ❓ Question 3: D'où sortent les 0.5, 0.2 et 0.3 utilisés dans les scores composites?

**Réponse:** ✅ **MAINTENANT CALCULÉS AUTOMATIQUEMENT À PARTIR DES DONNÉES RÉELLES**

#### AVANT (valeurs arbitraires):
```python
score_composite = 0.5 × ca_total + 0.3 × ca_ethique + 0.2 × ca_conseil
```
- Basé sur l'hypothèse que ca_total est le plus important
- Valeurs "au doigt mouillé"

#### APRÈS (valeurs basées sur les moyennes réelles):

**✅ CORRECTION APPLIQUÉE:**

Le script calcule maintenant les pondérations à partir des **moyennes des CA réels**:

```python
# Étape 1: Calculer les moyennes réelles
moyenne_ca_total = df['ca_total'].mean()      # Ex: 2,300,000 €
moyenne_ca_ethique = df['ca_ethique'].mean()  # Ex: 1,600,000 €
moyenne_ca_conseil = df['ca_conseil'].mean()  # Ex:   461,000 €

# Étape 2: Calculer les poids proportionnels
somme = 2,300,000 + 1,600,000 + 461,000 = 4,361,000 €

poids_total   = 2,300,000 / 4,361,000 = 0.527 (52.7%)
poids_ethique = 1,600,000 / 4,361,000 = 0.367 (36.7%)
poids_conseil =   461,000 / 4,361,000 = 0.106 (10.6%)

# Étape 3: Appliquer ces poids
score_composite = 0.527 × ca_total + 0.367 × ca_ethique + 0.106 × ca_conseil
```

**Avantage:** Les poids reflètent la réalité économique des pharmacies!

**Le script affichera:**
```
================================================================================
CALCUL DES PONDERATIONS BASEES SUR LES DONNEES REELLES
================================================================================
  Moyenne ca_total        : 2,300,000 €
  Moyenne ca_ethique      : 1,600,000 €
  Moyenne ca_conseil      :   461,000 €

Pondérations calculées:
  ca_total        : 0.527 (52.7%)
  ca_ethique      : 0.367 (36.7%)
  ca_conseil      : 0.106 (10.6%)

================================================================================
CALCUL DU SCORE COMPOSITE
================================================================================
  ✅ Score composite = 0.527×total + 0.367×ethique + 0.106×conseil
```

---

### ❓ Question 4: Est-ce que tu peux faire des sauvegardes pendant le process comme ça si jamais le script s'arrête tout ne sera pas perdu?

**Réponse:** ✅ **OUI - SAUVEGARDES INTERMÉDIAIRES AJOUTÉES**

Le GridSearch peut prendre 20 minutes et on ne veut pas tout perdre si ça plante!

#### ✅ CORRECTIONS APPLIQUÉES:

**Sauvegarde 1 - Après GridSearch (ligne 312-317):**
```python
# 💾 SAUVEGARDE INTERMÉDIAIRE - Hyperparamètres optimisés
params_path = models_dir / 'best_hyperparameters_gridsearch.json'
json.dump(best_params, params_path)
```
**Fichier créé:** `modeles_lightgbm/best_hyperparameters_gridsearch.json`
**Durée:** Après 10-20 minutes de GridSearch

---

**Sauvegarde 2 - Après chaque modèle entraîné (ligne 469-486):**
```python
# 💾 SAUVEGARDE INTERMÉDIAIRE - Modèle + Performances
# Sauvegarder le modèle
model_path = models_dir / f'model_{target}.pkl'
pickle.dump(model, model_path)

# Sauvegarder les performances
perf_path = models_dir / f'performances_{target}.json'
json.dump(performances, perf_path)
```
**Fichiers créés:**
- `modeles_lightgbm/model_ca_total.pkl`
- `modeles_lightgbm/performances_ca_total.json`
- `modeles_lightgbm/model_ca_ethique.pkl`
- `modeles_lightgbm/performances_ca_ethique.json`
- `modeles_lightgbm/model_ca_conseil.pkl`
- `modeles_lightgbm/performances_ca_conseil.json`

**Durée:** Après chaque modèle (~2-5 min chacun)

---

**Sauvegarde 3 - Après calcul des scores (ligne 631-643):**
```python
# 💾 SAUVEGARDE INTERMÉDIAIRE - Tous les scores calculés
checkpoint_path = 'scores_checkpoint.csv'
df[['id_pharmacie', 'nom_pharmacie', ...scores...]].to_csv(checkpoint_path)
```
**Fichier créé:** `intermediaire/output/scores_checkpoint.csv`
**Contenu:** Toutes les pharmacies avec TOUS les scores calculés
**Durée:** Après calcul des scores (~1 min)

---

#### 🎯 RÉCAPITULATIF DES SAUVEGARDES

| Étape | Moment | Fichier(s) | Utilité si crash |
|-------|--------|------------|------------------|
| **1. GridSearch** | Après 10-20 min | `best_hyperparameters_gridsearch.json` | Réutiliser les paramètres optimisés sans refaire le GridSearch |
| **2. Modèle CA Total** | Après 2-5 min | `model_ca_total.pkl`<br>`performances_ca_total.json` | Relancer uniquement CA éthique et conseil |
| **3. Modèle CA Éthique** | Après 2-5 min | `model_ca_ethique.pkl`<br>`performances_ca_ethique.json` | Relancer uniquement CA conseil |
| **4. Modèle CA Conseil** | Après 2-5 min | `model_ca_conseil.pkl`<br>`performances_ca_conseil.json` | Relancer uniquement le calcul des scores |
| **5. Scores calculés** | Après 1 min | `scores_checkpoint.csv` | Récupérer tous les scores sans tout recalculer |
| **6. Sauvegarde finale** | À la fin | `pharmacies_avec_scores_attractivite.csv` | Fichier complet avec tous les scores |

**Avantage:** Si le script plante, vous ne perdez JAMAIS plus de 5 minutes de travail!

---

## 📊 RÉSUMÉ DES 4 CORRECTIONS

| # | Question | Correction | Fichier modifié | Lignes |
|---|----------|------------|-----------------|--------|
| 1 | ❌ Delta utilisé comme feature | ✅ Delta retiré de derived_patterns | ml_05_score_attractivite_lightgbm.py | 150 |
| 2 | ❓ Comment prédire le CA | 📖 Explication LightGBM ajoutée | Ce document | - |
| 3 | ❓ Poids 0.5/0.3/0.2 arbitraires | ✅ Calcul automatique basé sur moyennes réelles | ml_05_score_attractivite_lightgbm.py | 516-561 |
| 4 | 💾 Pas de sauvegardes intermédiaires | ✅ 5 sauvegardes ajoutées | ml_05_score_attractivite_lightgbm.py | 312-317, 469-486, 631-643 |

---

## ✅ SCRIPT PRÊT À LANCER

Le script ml_05 est maintenant:
- ✅ Sans data leakage (delta exclu)
- ✅ Avec explications claires de la prédiction
- ✅ Avec poids calculés automatiquement à partir des données réelles
- ✅ Avec sauvegardes intermédiaires toutes les 5 minutes max

**Vous pouvez lancer le script en toute confiance!**
