# Méthodologie Complète - Scoring Pharmacies 65+ 📊

**Modélisation du potentiel commercial des pharmacies françaises auprès de la population 65+**

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Problématique et objectifs](#problématique-et-objectifs)
3. [Données sources](#données-sources)
4. [Architecture du modèle](#architecture-du-modèle)
5. [Phase 1 : Préparation des données](#phase-1--préparation-des-données)
6. [Phase 2 : Modélisation ML et Huff](#phase-2--modélisation-ml-et-huff)
7. [Formules mathématiques](#formules-mathématiques)
8. [Validation et métriques](#validation-et-métriques)
9. [Limites et améliorations](#limites-et-améliorations)
10. [Références](#références)

---

## 🎯 Vue d'ensemble

### Objectif principal

Estimer, pour chaque pharmacie de France métropolitaine, le **nombre de clients seniors potentiels** (65+ ans) en utilisant :
- Données démographiques INSEE par IRIS (~50 000 zones)
- Zones d'accessibilité réelles (isochrones)
- Points d'attractivité (HUBS médicaux, transports, commerces)
- Modèle gravitaire de Huff avec scores d'attractivité ML

### Résultat final

Pour chaque pharmacie :
- **Nombre de clients 65-79 ans**
- **Nombre de clients 80+ ans**
- **Nombre total de clients 65+**
- **Visites annuelles estimées** (clients × 12)
- **Décile de performance** (1-10)

### Chiffres clés

- **19 307 pharmacies** analysées
- **~51 000 IRIS** (zones INSEE)
- **115 767 isochrones** générés
- **350 000 points d'attractivité** (HUBS)
- **300+ features** par pharmacie
- **94%** de la population 65+ couverte
- **100%** conservation de la population distribuée

---

## 🔍 Problématique et objectifs

### Problématique

Les pharmacies ont besoin d'estimer leur **patientèle potentielle** pour :
- Évaluer le potentiel commercial d'une localisation
- Anticiper les besoins en ressources humaines
- Adapter l'offre de services (vaccination, téléconsultation, etc.)
- Négocier avec les fournisseurs
- Valoriser un fonds de commerce

**Difficulté** : Le nombre réel de clients n'est pas accessible. Les estimations doivent se baser uniquement sur :
- Données publiques (INSEE, OpenStreetMap, FINESS, RPPS)
- Caractéristiques géographiques
- Environnement concurrentiel

### Objectifs scientifiques

1. **Modéliser l'accessibilité spatiale** via isochrones (temps de trajet réel)
2. **Quantifier l'attractivité** d'une pharmacie à partir de son environnement
3. **Distribuer la population** de manière conservative (pas de double comptage)
4. **Valider les estimations** via corrélations avec données réelles (SIG_P20)

---

## 📊 Données sources

### Données INSEE

| Fichier | Description | Granularité | Variables clés |
|---------|-------------|-------------|----------------|
| `age_profession.CSV` | Population par âge + professions | IRIS | Pop 65-79, Pop 80+, Taux retraités |
| `diplome_formation.CSV` | Niveau d'éducation | IRIS | Taux supérieur, Bac+2 |
| `logement.CSV` | Caractéristiques logement | IRIS | Résidences secondaires, Propriétaires |
| `revenus.csv` | Revenus fiscaux | IRIS | Revenu médian, Taux pauvreté |

**Couverture** : ~51 000 IRIS, population totale 65+ = 14,1 millions

### Données géographiques

| Source | Description | Format | Volumétrie |
|--------|-------------|--------|------------|
| IGN | Contours IRIS | GeoPackage (.gpkg) | 51k polygones |
| OpenStreetMap | Réseau routier/piétonnier | PBF | 4 GB |
| Correspondances | IRIS ↔ code postal | CSV | 2 tables |

### Données de santé

| Source | Description | Contenu | Volumétrie |
|--------|-------------|---------|------------|
| **FINESS** | Établissements sanitaires | Hôpitaux, EHPAD, centres santé | ~40k établissements |
| **RPPS** | Professionnels de santé | Médecins, dentistes, infirmiers | ~400k professionnels |
| **OSM** | Points d'intérêt | Transports, commerces, marchés | ~100k points |

**Sortie** : `HUBS_unified_final.csv` (~350k points dédoublonnés)

### Données pharmacies

| Source | Variables | Volumétrie |
|--------|-----------|------------|
| UGA (source propriétaire) | Coordonnées GPS, CA, type zone | 19 307 pharmacies |

### Données de validation

| Source | Description | Usage |
|--------|-------------|-------|
| **SIG_P20** | Chiffre d'affaires + unités vendues | Corrélations pour validation |
| **df_bas_annee** | Données historiques pharmacies | Analyses complémentaires |

---

## 🏗️ Architecture du modèle

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                       PHASE 1                                │
│                  Préparation des données                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Pharmacies (19k)                                         │
│  2. HUBS (350k) ← FINESS + RPPS + OSM                       │
│  3. Isochrones (115k) + Matrice w_IRIS                      │
│  4. Enrichissement INSEE + Tourisme                          │
│                                                               │
│  Output: pharmacies_final_avec_variables_touristiques.csv   │
│          matrice_w_iris_100pct.csv                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       PHASE 2                                │
│                  Pipeline ML + Modèle de Huff                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Comptage HUBS par isochrone                              │
│  2. Calcul concurrence (KDTree)                              │
│  3. Agrégation population par isochrone                      │
│  4. Intégration features (300+)                              │
│  5. Score attractivité (LightGBM)                            │
│  6. Modèle de Huff (distribution population)                 │
│                                                               │
│  Output: pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                     Validation
              (Corrélations SIG_P20)
```

### Flux de données

```
DONNÉES BRUTES
    │
    ├─→ INSEE (population, revenus, logement)
    ├─→ FINESS/RPPS (établissements, professionnels santé)
    ├─→ OSM (réseau routier, transports, commerces)
    ├─→ UGA (pharmacies avec coordonnées)
    │
    ↓
PRÉPARATION (Phase 1)
    │
    ├─→ Géocodage + nettoyage
    ├─→ Génération isochrones (Valhalla)
    ├─→ Calcul matrice w_IRIS (intersection géométrique)
    ├─→ Enrichissement démographique
    │
    ↓
FEATURES (300+)
    │
    ├─→ Population accessible (par isochrone)
    ├─→ Concurrence (nb pharmacies à 1/3/5 km)
    ├─→ HUBS proximité (médecins, hôpitaux, transports)
    ├─→ Démographie (âge, revenus, formation, logement)
    ├─→ Tourisme (hébergements, zones montagne/littoral)
    │
    ↓
MODÉLISATION (Phase 2)
    │
    ├─→ PCA → Score attractivité [0.1-1.0]
    ├─→ Modèle de Huff → Distribution population
    │
    ↓
RÉSULTAT FINAL
    │
    └─→ Clients 65+ par pharmacie
```

---

## 📦 Phase 1 : Préparation des données

### 1.1 Création base pharmacies

**Objectif** : Base de données géocodées avec métadonnées de base

**Traitement** :
- Nettoyage coordonnées GPS (validation lat/lon)
- Classification type de zone (urbain_dense, urbain, périurbain, rural)
- Comptage voisins dans rayon 5 km
- Attribution `id_pharmacie` unique

**Output** : `pharmacies_final.csv` (19 307 lignes)

---

### 1.2 Construction base HUBS

**Objectif** : Points d'attractivité qui influencent le trafic en pharmacie

**Sources** :
1. **FINESS** : Établissements sanitaires (hôpitaux, EHPAD, centres de santé)
2. **RPPS** : Professionnels de santé (médecins, dentistes, infirmiers, kinés)
3. **OSM** : Transports (gares, stations métro/bus), commerces, marchés

**Pipeline** :
```
FINESS brut
    ↓
Fusion structure + géolocalisation
    ↓
Catégorisation (hopital, ehpad, laboratoire, etc.)
    ↓
FINESS_merged.csv (40k établissements)
```

```
RPPS bruts (6 professions)
    ↓
Géocodage API BAN (10 workers parallèles)
    ↓
RPPS_merged.csv (400k professionnels)
```

```
OSM France (4 GB PBF)
    ↓
Extraction points d'intérêt (transport, commerce)
    ↓
hubs.csv (100k points)
```

```
FINESS + RPPS + OSM
    ↓
Fusion + harmonisation colonnes
    ↓
Dédoublonnage spatial (KDTree, seuil 50m)
    ↓
HUBS_unified_final.csv (350k points)
```

**Temps** : ~45-60 minutes

---

### 1.3 Génération isochrones + Matrice w_IRIS

**1.3.1 Génération isochrones**

**Objectif** : Zones accessibles depuis chaque pharmacie en temps réel de trajet

**Méthode** : API Valhalla sur réseau OpenStreetMap

**Types générés** :
- `walk_5min`, `walk_10min` : Piéton
- `drive_5min`, `drive_10min`, `drive_15min`, `drive_20min` : Voiture

**Output** : 115 767 fichiers GeoJSON (~12 GB)
- 19 307 pharmacies × 6 types (théorique : 115 842)
- Fichiers manquants : ~75 pharmacies (0.4%) sans réseau accessible

**Temps** : ~48 heures (une seule fois)

**1.3.2 Calcul matrice w_IRIS**

📖 **Documentation complète** : [METHODE_CALCUL_MATRICE_W_IRIS.md](METHODE_CALCUL_MATRICE_W_IRIS.md)

**Objectif** : Coefficients de pondération pharmacie-IRIS pour distribution de population

**Méthode** : Intersection géométrique

```
w_IRIS = Surface(Isochrone ∩ IRIS) / Surface(IRIS)
```

**Pipeline en 5 étapes** :

**a. Génération isochrones** → 115k fichiers GeoJSON

**b. Complétion manquants** → +500 isochrones

**c. Calcul w_IRIS par intersection**
- Pour chaque pharmacie :
  - Charger isochrone (priorité drive_20min > ... > walk_5min)
  - Intersection spatiale avec polygones IRIS
  - Calcul w_IRIS = surface_intersection / surface_IRIS
  - Élimination relations < 0.001 (seuil de bruit)
- Optimisations : index spatial (R-tree), checkpoints /1000 pharmacies
- **Output** : `matrice_w_iris.csv` (~95k relations)
- **Temps** : ~3-4 minutes

**d. Enrichissement géolocalisation**
- Pharmacies sans isochrones (~1k) → spatial join via GPS
- Assigne w_IRIS = 1.0 (couverture totale IRIS local)
- **Output** : `matrice_w_iris_enriched.csv` (+~1k relations)
- **Temps** : ~10 secondes

**e. Couverture 100% par nearest neighbor**
- IRIS non couverts → nearest neighbor + décroissance exponentielle
  - `w_IRIS = exp(-distance_km / 20)`
- **Output** : `matrice_w_iris_100pct.csv` (~96.5k relations)
- **Temps** : ~5 secondes

**Résultat final** :
- **~96 500 relations** pharmacie-IRIS
- **~5.1 relations/pharmacie** en moyenne
- **100% couverture** population

---

### 1.4 Enrichissement INSEE + Tourisme

**Objectif** : Agréger variables démographiques + touristiques par pharmacie

**Méthode** : Agrégation pondérée par w_IRIS

```
valeur_pharma = Σ(valeur_IRIS × w_IRIS × pop_IRIS) / Σ(w_IRIS × pop_IRIS)
```

**Variables agrégées** :
- **Population** : Total, 65-79 ans, 80+ ans, familles, retraités
- **Revenus** : Médian, taux pauvreté, déciles
- **Logement** : Propriétaires, résidences secondaires, logements vacants
- **Formation** : Taux Bac+2, taux supérieur, sans diplôme
- **Tourisme** : Nb hôtels, campings, capacité accueil, flag touristique

**Outputs** :
1. `pharmacies_enrichies_insee.csv` (~5 MB)
2. `pharmacies_final_avec_variables_touristiques.csv` (~6 MB, **300+ features**)

**Temps** : ~5-8 minutes

---

## 🤖 Phase 2 : Modélisation ML et Huff

### 2.1 Comptage HUBS par isochrone

**Objectif** : Quantifier l'environnement médical/commercial de chaque pharmacie

**Méthode** :
- Pour chaque pharmacie :
  - Charger isochrones (6 types)
  - Spatial join avec `HUBS_unified_final.csv`
  - Compter HUBS par catégorie dans chaque zone

**Catégories HUBS** :
- Médecins, hôpitaux, EHPAD, laboratoires
- Transports (gares, stations)
- Commerces, marchés

**Output** : `pharmacies_avec_hubs.csv` (~12 MB)
- Colonnes : `hubs_medecins_drive_10min`, `hubs_hopitaux_walk_5min`, etc.

**Temps** : ~30-45 minutes

---

### 2.2 Calcul concurrence

**Objectif** : Nombre de pharmacies concurrentes à proximité

**Méthode** : KDTree spatial

```python
tree = cKDTree(coords_pharmacies)
neighbors_1km = tree.query_ball_point(coord_pharma, r=1000)
```

**Rayons** : 1 km, 3 km, 5 km

**Output** : `pharmacies_avec_concurrence.csv`
- Colonnes : `nb_concurrents_1km`, `nb_concurrents_3km`, `nb_concurrents_5km`

**Temps** : ~5 minutes

---

### 2.3 Agrégation population par isochrone

**Objectif** : Population accessible dans chaque zone

**Méthode** : Agrégation pondérée via matrice w_IRIS

```python
for pharmacie in pharmacies:
    iris_accessibles = matrice[matrice['id_pharmacie'] == pharmacie]
    for iso_type in ['walk_5min', 'drive_10min', ...]:
        pop_iso = Σ(pop_IRIS × w_IRIS) où IRIS dans iso_type
```

**Output** : `pharmacies_avec_population_isochrones.csv` (~34 MB)
- Colonnes : `pop_65_79_drive_10min`, `pop_80_plus_walk_5min`, etc.

**Temps** : ~15-20 minutes

---

### 2.4 Intégration features

**Objectif** : Dataset ML complet

**Méthode** : Fusion via `id_pharmacie`

**Sources fusionnées** :
- `pharmacies_avec_hubs.csv` (HUBS par isochrone)
- `pharmacies_avec_concurrence.csv` (nb concurrents)
- `pharmacies_avec_population_isochrones.csv` (population accessible)
- `pharmacies_final_avec_variables_touristiques.csv` (INSEE + tourisme)

**Output** : `pharmacies_features_complet.csv` (~52 MB, **300+ features**)

**Temps** : ~2 minutes

---

### 2.5 Calcul score attractivité (PCA)

**Objectif** : Score composite [0.1-1.0] mesurant l'attractivité d'une pharmacie

**Approche** : Réduction de dimensionnalité par Analyse en Composantes Principales (PCA)

#### Méthodologie PCA

La méthode utilise l'**ACP (Analyse en Composantes Principales)** pour synthétiser les 300+ features en un score d'attractivité unique.

**Principe** :
- Les 300+ features capturent différentes dimensions de l'attractivité (population, HUBS, concurrence, démographie, tourisme)
- La PCA identifie les combinaisons linéaires de features qui expliquent le mieux la variance
- Les premières composantes principales représentent les dimensions les plus discriminantes

#### Processus

1. **Sélection des features** :
   - Features de population accessible (par isochrone)
   - HUBS de proximité (médecins, hôpitaux, transports)
   - Variables de concurrence (nb pharmacies à 1/3/5 km)
   - Variables démographiques (revenus, âge, formation)
   - Variables touristiques (hébergements, zone montagne/littoral)

2. **Standardisation** :
   ```python
   scaler = StandardScaler()
   features_scaled = scaler.fit_transform(features)
   ```

3. **Application PCA** :
   ```python
   pca = PCA(n_components='auto')  # Garde les composantes expliquant >1% variance
   components = pca.fit_transform(features_scaled)
   ```

4. **Calcul du score d'attractivité** :
   - Utilisation des premières composantes principales
   - Pondération par variance expliquée
   - Normalisation dans l'intervalle [0.1, 1.0]

5. **Normalisation finale** :
   ```python
   score_normalized = (score - score.min()) / (score.max() - score.min())
   score_attractivite = 0.1 + 0.9 * score_normalized  # [0.1, 1.0]
   ```

**Avantages de la PCA** :
- ✅ Pas de sur-ajustement (contrairement aux modèles supervisés)
- ✅ Prend en compte toutes les pharmacies (pas besoin de données historiques)
- ✅ Capture les dimensions latentes de l'attractivité
- ✅ Robuste aux corrélations entre features

**Output** : `pharmacies_avec_scores_attractivite.csv` (~8.5 MB)
- Colonne : `score_attractivite_65plus_composite`

**Temps** : ~5-10 minutes

---

### 2.6 Modèle de Huff (distribution population)

**Objectif** : Distribuer la population 65+ aux pharmacies proportionnellement à leur attractivité

#### Modèle de Huff

**Principe** : Modèle gravitaire qui répartit la demande (population) entre alternatives (pharmacies) selon leur utilité.

**Formule générale** :
```
P_ij = (A_i × d_ij^-β) / Σ_k (A_k × d_kj^-β)
```

Où :
- `P_ij` : Probabilité qu'un habitant de l'IRIS j fréquente la pharmacie i
- `A_i` : Attractivité de la pharmacie i
- `d_ij` : Distance entre pharmacie i et IRIS j
- `β` : Exposant de friction de distance

**Notre implémentation** :

Nous remplaçons `d_ij^-β` par `w_IRIS_ij` (pondération géométrique) :

```
P_ij = (A_i × w_ij) / Σ_k (A_k × w_kj)
```

Où :
- `A_i` : `score_attractivite_65plus_composite` (calculé par LightGBM)
- `w_ij` : Pondération IRIS (matrice w_IRIS)

#### Algorithme exact par IRIS

```python
# Pour chaque IRIS
for iris in IRIS_avec_population:

    # 1. Récupérer pharmacies accessibles
    pharmas_accessibles = matrice_w_iris[
        matrice_w_iris['CODE_IRIS'] == iris
    ]

    # 2. Calculer utilité
    pharmas_accessibles['utilite'] = (
        pharmas_accessibles['attractivite'] ×
        pharmas_accessibles['w_IRIS']
    )

    # 3. Normaliser (somme = 1)
    sum_utilite = pharmas_accessibles['utilite'].sum()
    pharmas_accessibles['part_marche'] = (
        pharmas_accessibles['utilite'] / sum_utilite
    )

    # 4. Distribuer population
    pop_65_79 = population_iris[iris]['pop_65_79']
    pop_80_plus = population_iris[iris]['pop_80_plus']

    for pharma in pharmas_accessibles:
        clients_65_79[pharma] += pop_65_79 × part_marche
        clients_80_plus[pharma] += pop_80_plus × part_marche
```

#### Garanties mathématiques

✅ **Conservation exacte** : `Σ(clients) = Population couverte`

Preuve :
```
Σ_i clients_i = Σ_i Σ_j (pop_j × P_ij)
              = Σ_j pop_j × Σ_i P_ij
              = Σ_j pop_j × 1        (car Σ_i P_ij = 1 par construction)
              = Population totale
```

✅ **Pas de double comptage** : Chaque habitant est compté une seule fois, distribué proportionnellement.

✅ **Respect accessibilité** : Seules les pharmacies avec `w_IRIS > 0` reçoivent des clients de cet IRIS.

#### Output

**`pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`** (~2.3 MB)

Colonnes :
- `id_pharmacie` : Identifiant unique
- `nom_pharmacie` : Nom
- `attractivite_huff` : Score attractivité normalisé [0.1-1.0]
- `clients_65_79` : Nombre clients 65-79 ans
- `clients_80_plus` : Nombre clients 80+ ans
- `clients_65_plus_total` : Total clients 65+
- `visites_annuelles_65plus` : Visites annuelles (clients × 12)
- `decile_clients_65plus` : Décile performance (1 = faible, 10 = fort)

**Résultats typiques** :
```
Population France 65+      : 14,125,725
Population couverte        : 13,302,521 (94.2%)
Clients distribués         : 13,302,521 (conservation 100.0%)
Pharmacies avec clients    : 18,208 / 19,307 (94.3%)
```

**Temps** : ~5-10 minutes

---

## 📐 Formules mathématiques

### Matrice w_IRIS

**Intersection géométrique** :
```
w_ij = A(Iso_i ∩ IRIS_j) / A(IRIS_j)
```

**Décroissance exponentielle** (nearest neighbor) :
```
w_ij = exp(-d_ij / λ)    où λ = 20 km
```

### Agrégation pondérée

**Valeur démographique agrégée** :
```
V_i = Σ_j (v_j × w_ij × p_j) / Σ_j (w_ij × p_j)
```

Où :
- `V_i` : Valeur agrégée pour la pharmacie i
- `v_j` : Valeur de l'IRIS j (ex: revenu médian)
- `w_ij` : Pondération IRIS
- `p_j` : Population IRIS j

### Modèle de Huff

**Probabilité de fréquentation** :
```
P_ij = (A_i × w_ij) / Σ_k (A_k × w_kj)
```

**Distribution clients** :
```
C_i = Σ_j (Pop_j × P_ij)
```

Où :
- `C_i` : Nombre de clients de la pharmacie i
- `Pop_j` : Population de l'IRIS j
- `P_ij` : Probabilité qu'un habitant de j aille en i

### Score attractivité composite

**Normalisation** :
```
score_norm = 0.1 + 0.9 × (score - min) / (max - min)
```

**Composite** :
```
score_final = 0.4×CA_total + 0.3×CA_éthique + 0.2×CA_conseil + 0.1×Delta
```

---

## ✅ Validation et métriques

### Conservation population

**Test** : Vérifier que Σ(clients) = Population couverte

```python
total_clients = df_resultats['clients_65_plus_total'].sum()
total_pop_couverte = df_population[IRIS_couverts]['pop_65_plus'].sum()

taux_conservation = total_clients / total_pop_couverte
```

**Résultat** : **100.0%** (garantie mathématique)

### Couverture géographique

**Métriques** :
- **Population France 65+** : 14,1 millions
- **Population couverte** : 13,3 millions (**94.2%**)
- **Population non couverte** : 0,8 millions (DOM-TOM, zones isolées)

**Pharmacies** :
- **Total** : 19 307
- **Avec clients** : 18 208 (**94.3%**)
- **Sans clients** : 1 099 (zones très rurales, DOM-TOM)

### Corrélations avec données réelles (SIG_P20)

**Méthode** : Corrélation de Pearson entre variables SIG_P20 et clients 65+ estimés

#### Corrélations globales

| Variable SIG_P20 | Clients 65+ estimés | Corrélation R |
|------------------|---------------------|---------------|
| **UN** (Unités vendues) | clients_65_plus_total | **0.15** |
| **CAHT** (Chiffre d'affaires) | clients_65_plus_total | **0.21** |

#### Corrélations stratifiées

**Par type de zone** :

| Type zone | R (UN vs Clients) | R (CAHT vs Clients) |
|-----------|-------------------|---------------------|
| **Urbain dense** | **0.34** | **0.42** |
| Urbain | 0.23 | 0.29 |
| Périurbain | 0.18 | 0.24 |
| Rural | 0.14 | 0.18 |

**Par profil touristique** :

| Profil | R (UN vs Clients) | R (CAHT vs Clients) |
|--------|-------------------|---------------------|
| **Touristique** | **0.22** | **0.28** |
| Non touristique | 0.13 | 0.19 |

**Par proximité HUBS médicaux** (rayon 1 km) :

| Nb HUBS | R (UN vs Clients) | R (CAHT vs Clients) |
|---------|-------------------|---------------------|
| 0 | 0.19 | 0.24 |
| 1-3 | 0.21 | 0.26 |
| **4-10** | **0.32** | **0.38** |
| 10+ | 0.29 | 0.35 |

#### Interprétation

✅ **Corrélations significatives** : Toutes les corrélations sont statistiquement significatives (p < 0.001)

✅ **Variabilité attendue** : Les corrélations globales (0.15-0.21) sont modérées car :
- Le CA pharmacie dépend de NOMBREUX facteurs (OTC, cosmétiques, services)
- Les clients 65+ ne représentent qu'une **fraction** du CA total
- Variabilité géographique forte (urbain vs rural)

✅ **Meilleures corrélations en urbain dense** (0.34-0.42) : Zones où la population 65+ a un poids relatif plus fort

✅ **Impact des HUBS médicaux** : Proximité de 4-10 hubs améliore significativement la corrélation (0.32-0.38)

### Performance de la PCA

| Métrique | Valeur |
|----------|--------|
| **Variance expliquée** (3 premières composantes) | ~65-75% |
| **Nombre de composantes retenues** | Variable (seuil: variance > 1%) |
| **Features les plus contributives** | pop_drive_10min, nb_concurrents_3km, hubs_medecins, pop_65_plus |

---

## ⚠️ Limites et améliorations

### Limites méthodologiques

1. **Isochrones théoriques**
   - Ne tiennent pas compte du trafic réel en temps réel
   - Supposent un réseau routier statique
   - Pas d'obstacles physiques (fermetures temporaires, travaux)

2. **Modèle de Huff simplifié**
   - Attractivité basée uniquement sur l'environnement (pas de qualité service interne)
   - Pas de prise en compte des habitudes/fidélité client
   - β (friction distance) fixe, pourrait varier selon zone

3. **Score d'attractivité PCA**
   - Approche non supervisée : ne nécessite pas de données historiques
   - Pondération uniforme des dimensions (pas d'apprentissage sur cible connue)
   - Sensible au choix des features et à la standardisation

4. **Couverture limitée**
   - 94% de la population couverte (DOM-TOM sous-représentés)
   - 6% de pharmacies sans clients (zones très isolées)

4. **Données INSEE datées**
   - Recensement 2022, évolution démographique non captée
   - Migrations récentes non prises en compte

### Améliorations possibles

#### Court terme

1. **Calibration β par zone**
   - Estimer β optimal par type de zone (urbain vs rural)
   - Intégrer β dans le modèle de Huff

2. **Intégration temps réel**
   - Isochrones dynamiques selon heure de la journée
   - Prise en compte trafic Google Maps API

3. **Données d'actualité**
   - Mise à jour régulière population INSEE
   - Intégration nouveaux établissements FINESS/RPPS

#### Moyen terme

4. **Features comportementales**
   - Taux de motorisation par IRIS
   - Habitudes mobilité (enquêtes déplacements)
   - Fidélité estimée (clustering profils clients)

5. **Validation terrain**
   - Enquêtes auprès d'un échantillon de pharmacies
   - Comparaison avec comptages réels de clients

6. **Méthodes alternatives pour score attractivité**
   - Modèles supervisés (Random Forest, XGBoost) si données historiques disponibles
   - Autres méthodes de réduction : t-SNE, UMAP
   - Approches Bayésiennes (incertitude sur estimations)

#### Long terme

7. **Prédiction temporelle**
   - Évolution clients 65+ sur 5-10 ans
   - Intégration projections démographiques INSEE

8. **Optimisation localisation**
   - Identification zones sous-desservies
   - Recommandations implantation nouvelles pharmacies

9. **Micro-segmentation clients**
   - Profils détaillés (pathologies, traitements)
   - Estimation par classe thérapeutique

---

## 📚 Références

### Modèles théoriques

**Huff, D. L. (1963).** "A Probabilistic Analysis of Shopping Center Trade Areas." *Land Economics*, 39(1), 81-90.
- Modèle gravitaire de distribution de la demande

**Reilly, W. J. (1931).** "The Law of Retail Gravitation." New York: Knickerbocker Press.
- Loi de gravitation commerciale

**Hansen, W. G. (1959).** "How Accessibility Shapes Land Use." *Journal of the American Institute of Planners*, 25(2), 73-76.
- Mesure d'accessibilité spatiale

### APIs et outils

**Valhalla** : https://github.com/valhalla/valhalla
- Moteur de routage open-source pour calcul isochrones

**Scikit-learn** : https://scikit-learn.org/
- Framework ML incluant PCA pour réduction de dimensionnalité

**GeoPandas** : https://geopandas.org/
- Analyse spatiale en Python

### Données publiques

**INSEE** : https://www.insee.fr/
- Population, revenus, logement par IRIS

**IGN** : https://geoservices.ign.fr/contoursiris
- Contours IRIS France métropolitaine

**OpenStreetMap** : https://www.openstreetmap.org/
- Réseau routier, points d'intérêt

**FINESS** : https://www.data.gouv.fr/fr/datasets/finess/
- Fichier national établissements sanitaires

**RPPS** : https://annuaire.sante.fr/
- Répertoire partagé professionnels santé

---

**Document créé** : Novembre 2025
**Version** : 1.0
**Auteur** : Équipe Data Science - Modélisation Pharmacies 65+
**Projet** : Scoring Pharma 65+