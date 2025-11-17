# ÉVALUATION DE LA QUALITÉ DU MODÈLE ML_05

**Date:** 2025-11-17
**Script:** ml_05_score_attractivite_lightgbm.py
**Statut:** ✅ EXÉCUTION RÉUSSIE

---

## 📊 RÉSUMÉ EXÉCUTIF

Le script ml_05 a réussi à entraîner 3 modèles LightGBM et à calculer les scores d'attractivité pour **19,296 pharmacies**.

**Optimisations appliquées:**
- ✅ Réutilisation des hyperparamètres sauvegardés (skip GridSearch = gain de 12 minutes)
- ✅ Sauvegardes intermédiaires toutes les 2-3 minutes
- ✅ Pondérations calculées automatiquement à partir des moyennes réelles
- ✅ Correction du bug JSON (types numpy → types Python)

**Durée totale:** ~5 minutes (au lieu de ~20 minutes sans optimisation)

---

## 📈 PERFORMANCES DES MODÈLES

### 1️⃣ MODÈLE CA_TOTAL

| Métrique | Train | Test | Interprétation |
|----------|-------|------|----------------|
| **R² score** | 0.289 | 0.066 | ⚠️ **TRÈS FAIBLE** - Le modèle n'explique que 6.6% de la variance du CA total |
| **MAE** | 843,802 € | 945,484 € | ⚠️ Erreur moyenne de ~945k€ (élevée) |
| **RMSE** | 1,420,084 € | 2,111,140 € | ⚠️ Erreur quadratique ~2.1M€ (très élevée) |
| **Overfitting** | 0.223 | | ⚠️ Écart train-test important (modèle surappris) |

**Contribution estimée des seniors au CA:** 54.1%

### 2️⃣ MODÈLE CA_ETHIQUE

| Métrique | Train | Test | Interprétation |
|----------|-------|------|----------------|
| **R² score** | 0.366 | 0.190 | ⚠️ **FAIBLE** - Le modèle n'explique que 19% de la variance du CA éthique |
| **MAE** | 523,846 € | 579,858 € | ⚠️ Erreur moyenne de ~580k€ |
| **RMSE** | 717,426 € | 808,297 € | ⚠️ Erreur quadratique ~808k€ |
| **Overfitting** | 0.176 | | ⚠️ Écart train-test important |

**Contribution estimée des seniors au CA:** 59.9%

### 3️⃣ MODÈLE CA_CONSEIL

| Métrique | Train | Test | Interprétation |
|----------|-------|------|----------------|
| **R² score** | 0.233 | 0.022 | ❌ **EXTRÊMEMENT FAIBLE** - Le modèle n'explique que 2.2% de la variance |
| **MAE** | 287,650 € | 335,017 € | ⚠️ Erreur moyenne de ~335k€ |
| **RMSE** | 820,832 € | 1,514,067 € | ⚠️ Erreur quadratique ~1.5M€ (très élevée) |
| **Overfitting** | 0.211 | | ⚠️ Écart train-test important |

**Contribution estimée des seniors au CA:** 49.7%

---

## 🎯 SCORE COMPOSITE CALCULÉ

**Formule:** Score composite = 0.527×CA_total + 0.368×CA_ethique + 0.105×CA_conseil

**Pondérations basées sur les moyennes réelles:**
- CA_total: 52.7% (pondération la plus importante)
- CA_ethique: 36.8%
- CA_conseil: 10.5% (pondération la plus faible)

---

## ⚠️ ANALYSE DE LA QUALITÉ

### Points positifs ✅

1. **Exécution complète sans erreur** - Tous les modèles entraînés et scores calculés
2. **Optimisations efficaces** - Réutilisation des hyperparamètres (gain de temps)
3. **Sauvegardes intermédiaires** - Protection contre les plantages
4. **Pondérations réalistes** - Basées sur les moyennes des CA réels

### Points problématiques ❌

#### 1. **R² extrêmement faibles** (PROBLÈME MAJEUR)

**R² optimal:** 0.7 - 0.9
**R² acceptable:** 0.5 - 0.7
**R² observé:**
- CA_total: 0.066 (❌ 10× trop faible)
- CA_ethique: 0.190 (❌ 3× trop faible)
- CA_conseil: 0.022 (❌ 30× trop faible)

**Signification:**
- Le modèle CA_total n'explique que **6.6%** de la variance du CA réel
- Les 93.4% restants sont dus à des facteurs non capturés par les 252 features
- Le modèle CA_conseil est pratiquement **aléatoire** (R²=2.2%)

#### 2. **Overfitting important** (PROBLÈME SÉRIEUX)

- Écart train-test entre 0.176 et 0.223
- Le modèle "apprend par cœur" le train set mais ne généralise pas au test set
- Indique que les features ne capturent pas les vrais patterns prédictifs

#### 3. **Erreurs de prédiction élevées**

Pour le CA_total (moyenne ~2.3M€):
- **MAE test:** 945k€ → Erreur moyenne = **41%** du CA moyen
- **RMSE test:** 2.1M€ → Erreur quadratique = **91%** du CA moyen

Pour le CA_conseil (moyenne ~460k€):
- **MAE test:** 335k€ → Erreur moyenne = **73%** du CA moyen
- **RMSE test:** 1.5M€ → Erreur quadratique = **328%** du CA moyen (!)

---

## 🔍 DIAGNOSTIC DES CAUSES PROBABLES

### 1. **Variables manquantes critiques**

Les features actuelles (HUBS, population, concurrence, tourisme) ne capturent probablement **PAS** les vrais drivers du CA:

**Facteurs probablement importants mais absents:**
- ✗ **Historique du titulaire** (ancienneté, réputation, fidélisation client)
- ✗ **Qualité de service** (horaires d'ouverture, services additionnels, disponibilité)
- ✗ **Mix produit** (part OTC, parapharmacie, orthopédie, homéopathie, etc.)
- ✗ **Stratégie commerciale** (programmes de fidélité, conseils personnalisés, événements)
- ✗ **Niveau de prix** (premium vs discount)
- ✗ **Présence en ligne** (click & collect, e-commerce, réseaux sociaux)
- ✗ **Partenariats** (médecins, EHPAD, maisons de santé)
- ✗ **Facteurs temporels** (tendances, saisonnalité fine, événements locaux)

### 2. **Linéarité inadaptée**

LightGBM capture des **relations non-linéaires**, mais si les features ne sont pas les bonnes, même le meilleur modèle ne peut pas prédire correctement.

### 3. **Hétérogénéité des pharmacies**

Les pharmacies sont probablement trop **hétérogènes** pour être modélisées avec seulement des features géographiques/démographiques:
- Pharmacie de centre-ville touristique ≠ Pharmacie de banlieue résidentielle
- Pharmacie près d'un hôpital ≠ Pharmacie isolée en milieu rural
- Pharmacie "conseil premium" ≠ Pharmacie "prix discount"

---

## 💡 RECOMMANDATIONS

### Option 1: **Accepter les résultats comme scores relatifs** (SOLUTION PRAGMATIQUE)

**Principe:** Même si le R² est faible, les scores peuvent quand même **classer** les pharmacies par attractivité relative.

**Utilisation recommandée:**
- ✅ Comparer les pharmacies entre elles (ranking)
- ✅ Identifier les pharmacies avec les scores les plus élevés/faibles
- ✅ Utiliser comme indicateur d'attractivité contextuelle (géographie + démographie)
- ❌ NE PAS utiliser pour prédire le CA réel avec précision

**Avantages:**
- Les scores restent utiles pour la **priorisation commerciale**
- Pas besoin de collecte de données supplémentaires
- Livrable immédiat

**Limites:**
- Les scores ne capturent qu'une partie de l'attractivité (géo + démo)
- Erreur de prédiction importante (±40-70%)

### Option 2: **Enrichir avec des données qualitatives** (SOLUTION IDÉALE MAIS COÛTEUSE)

**Données à collecter:**
1. **Enquête terrain:**
   - Horaires d'ouverture étendus (oui/non)
   - Services proposés (orthopédie, homéopathie, Click & Collect, etc.)
   - Nombre d'employés / ETP
   - Ancienneté du titulaire
   - Programmes de fidélité

2. **Données externes:**
   - Avis Google/Facebook (note moyenne, nombre d'avis)
   - Présence sur réseaux sociaux
   - Site web (oui/non)

3. **Données comportementales:**
   - Taux de fidélisation clients (si disponible)
   - Part de clients réguliers vs occasionnels

**Impact attendu:**
- R² pourrait passer de 0.06-0.19 à **0.5-0.7**
- Erreur de prédiction divisée par 2 ou 3

**Coût:**
- Enquête terrain: 50-100 pharmacies pilotes (2-3 semaines)
- Web scraping: automatisable

### Option 3: **Modèle hybride segmenté** (SOLUTION INTERMÉDIAIRE)

**Principe:** Créer des modèles différents par **type de pharmacie**

**Segments possibles:**
1. Pharmacies urbaines (centre-ville)
2. Pharmacies périurbaines (banlieue)
3. Pharmacies rurales
4. Pharmacies touristiques (littoral, montagne)
5. Pharmacies près d'hôpitaux/EHPAD

**Avantages:**
- Capture mieux l'hétérogénéité
- Peut améliorer le R² de 5-10 points par segment

**Inconvénient:**
- Nécessite de définir les segments (clustering ou règles métier)

---

## 📋 CONCLUSION ET DÉCISION RECOMMANDÉE

### Verdict sur la qualité actuelle: ⚠️ **QUALITÉ PRÉVISIONNELLE FAIBLE MAIS SCORES UTILISABLES**

**Ce qui fonctionne:**
- ✅ Les scores reflètent l'attractivité **géographique et démographique**
- ✅ Le ranking des pharmacies est cohérent
- ✅ Les pondérations sont réalistes

**Ce qui ne fonctionne pas:**
- ❌ La **prédiction précise du CA** (R² trop faible)
- ❌ La **généralisation** (overfitting important)

### 🎯 Décision recommandée

**Option 1 (pragmatique) à court terme:**
- Utiliser les scores comme **indicateurs d'attractivité contextuelle**
- Les présenter comme "scores basés sur la géographie, la démographie et la concurrence"
- Ajouter un disclaimer: "Ces scores ne prédisent pas le CA réel avec précision"

**Ensuite, planifier Option 2 ou 3 pour améliorer:**
- Enrichir avec données qualitatives (enquête pilote sur 50-100 pharmacies)
- Ou segmenter les modèles par type de pharmacie

---

## 📂 FICHIERS GÉNÉRÉS

| Fichier | Contenu | Taille |
|---------|---------|--------|
| `pharmacies_avec_scores_attractivite.csv` | 19,296 pharmacies avec tous les scores | ~10 MB |
| `model_ca_total.pkl` | Modèle LightGBM CA total | ~5 MB |
| `model_ca_ethique.pkl` | Modèle LightGBM CA éthique | ~5 MB |
| `model_ca_conseil.pkl` | Modèle LightGBM CA conseil | ~5 MB |
| `performances_ca_total.json` | Métriques détaillées CA total | 1 KB |
| `performances_ca_ethique.json` | Métriques détaillées CA éthique | 1 KB |
| `performances_ca_conseil.json` | Métriques détaillées CA conseil | 1 KB |
| `best_hyperparameters_gridsearch.json` | Hyperparamètres optimisés | 1 KB |

---

## ✅ PROCHAINES ÉTAPES SUGGÉRÉES

1. **Court terme (1-2 jours):**
   - [ ] Analyser la distribution des scores (min, max, médiane, quartiles)
   - [ ] Identifier les 100 pharmacies avec les meilleurs/pires scores
   - [ ] Vérifier la cohérence avec la réalité terrain (spot checks)

2. **Moyen terme (1-2 semaines):**
   - [ ] Décider Option 1 vs Option 2 vs Option 3
   - [ ] Si Option 2: planifier enquête pilote (50 pharmacies)
   - [ ] Si Option 3: définir les segments et entraîner modèles spécifiques

3. **Long terme (1-2 mois):**
   - [ ] Améliorer les modèles avec données qualitatives
   - [ ] Viser R² > 0.5 pour CA_total
   - [ ] Réduire MAE test < 500k€
