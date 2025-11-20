# Méthode de Calcul de la Matrice w_IRIS

## 📋 Vue d'ensemble

La **matrice w_IRIS** est un fichier central du projet qui établit les relations géographiques entre les pharmacies et les zones IRIS (Ilots Regroupés pour l'Information Statistique), avec des pondérations reflétant l'accessibilité spatiale.

**Fichier final** : `1_data_prep/output/matrice_w_iris.csv`

---

## 🎯 Objectif

Créer une table de correspondance pharmacie-IRIS avec un coefficient de pondération `w_IRIS` ∈ [0, 1] qui représente :
- **Pour une pharmacie donnée** : la fraction d'un IRIS accessible via ses isochrones
- **Pour le modèle de Huff** : le poids utilisé pour distribuer la population d'un IRIS entre pharmacies concurrentes

---

## 📊 Structure de la Matrice

### Format du fichier

```csv
id_pharmacie,CODE_IRIS,w_IRIS,source
PHA001,751050101,0.85,isochrones
PHA001,751050102,1.00,isochrones
PHA001,751050103,0.42,isochrones
PHA002,751050101,0.15,isochrones
...
```

### Colonnes

| Colonne | Type | Description |
|---------|------|-------------|
| `id_pharmacie` | string | Identifiant unique de la pharmacie |
| `CODE_IRIS` | string | Code IRIS (9 caractères) |
| `w_IRIS` | float | Pondération [0, 1] = fraction de l'IRIS accessible |
| `source` | string | Méthode d'association (`isochrones`, `geoloc`, `nearest_neighbor`) |

---

## 🔄 Pipeline de Calcul

### Étape 1 : Génération des Isochrones (a, b)

**Scripts** :
- `a_generate_isochrones.py` : Génère les isochrones pour toutes les pharmacies
- `b_generate_missing_isochrones.py` : Complète les isochrones manquants

**Types d'isochrones générés** :
- `walk_5min` : Marche 5 minutes
- `walk_10min` : Marche 10 minutes
- `drive_5min` : Voiture 5 minutes
- `drive_10min` : Voiture 10 minutes
- `drive_15min` : Voiture 15 minutes
- `drive_20min` : Voiture 20 minutes

**Sortie** : Fichiers GeoJSON dans `1_data_prep/output/isochrones/{type}/`

---

### Étape 2 : Calcul des w_IRIS par intersection géométrique (c)

**Script** : `c_calculate_w_iris.py`

**Méthode** :

Pour chaque pharmacie :
1. **Charger l'isochrone** (priorité : drive_20min > drive_15min > ... > walk_5min)
2. **Intersection spatiale** avec les polygones IRIS
3. **Calcul de w_IRIS** :

```python
w_IRIS = Surface(Isochrone ∩ IRIS) / Surface(IRIS)
```

**Illustration** :

```
┌─────────────────────────────────┐
│         IRIS A                   │
│  ┌──────────────────┐           │
│  │  Isochrone       │           │
│  │  Pharmacie 1     │           │
│  │                  │           │
│  └──────────────────┘           │
│                                  │
└─────────────────────────────────┘

w_IRIS = Surface(zone grisée) / Surface(IRIS A)
       = 60% (exemple)
```

**Cas particuliers** :
- Si `w_IRIS < 0.01` → Éliminé (seuil de bruit)
- Si l'IRIS est entièrement dans l'isochrone → `w_IRIS = 1.0`
- Si plusieurs isochrones (différentes pharmacies) couvrent le même IRIS → **plusieurs lignes** dans la matrice

**Sortie** : `matrice_w_iris.csv` (~19,000 pharmacies × ~5 IRIS/pharmacie en moyenne = ~95,000 relations)

---

### Étape 3 : Enrichissement par géolocalisation (d)

**Script** : `d_associate_pharmacies_to_iris.py`

**Objectif** : Ajouter les pharmacies sans isochrones (~1,000 pharmacies)

**Méthode** :
1. Identifier les pharmacies absentes de la matrice (pas d'isochrones générés)
2. **Spatial join** : Trouver l'IRIS contenant les coordonnées GPS de la pharmacie
3. Ajouter la relation avec `w_IRIS = 1.0` (on suppose que la pharmacie dessert entièrement son IRIS local)

**Sortie** : `matrice_w_iris_enriched.csv`

---

### Étape 4 : Couverture 100% par plus proche voisin (e)

**Script** : `e_associate_uncovered_iris.py`

**Objectif** : Couvrir les IRIS restants (DOM-TOM, zones isolées)

**Méthode** :
1. Identifier les IRIS non couverts (absents de la matrice)
2. **KDTree** : Trouver la pharmacie la plus proche (distance euclidienne)
3. **Calcul de w_IRIS par distance** :

```python
w_IRIS = exp(-distance_km / λ)

où λ = 20 km (distance caractéristique)
```

**Exemples** :
- Distance 5 km → `w_IRIS = 0.779`
- Distance 10 km → `w_IRIS = 0.607`
- Distance 20 km → `w_IRIS = 0.368`
- Distance 50 km → `w_IRIS = 0.082`

**Sortie** : `matrice_w_iris_100pct.csv` (couverture exhaustive)

---

## 📐 Formules Mathématiques

### Intersection Géométrique

Pour une pharmacie *i* et un IRIS *j* :

```
w_ij = A(Iso_i ∩ IRIS_j) / A(IRIS_j)

où :
- Iso_i = polygone de l'isochrone de la pharmacie i
- IRIS_j = polygone de l'IRIS j
- A() = fonction surface (en m²)
- ∩ = intersection géométrique
```

### Distance Exponential Decay

Pour les IRIS sans isochrone :

```
w_ij = exp(-d_ij / λ)

où :
- d_ij = distance euclidienne entre pharmacie i et centroïde IRIS j
- λ = 20 km (paramètre de décroissance)
```

---

## 🔢 Statistiques de la Matrice

### Répartition par source

| Source | Nombre de relations | Description |
|--------|---------------------|-------------|
| `isochrones` | ~95,000 | Calcul géométrique (étape 2) |
| `geoloc` | ~1,000 | Géolocalisation GPS (étape 3) |
| `nearest_neighbor` | ~500 | Plus proche voisin (étape 4) |
| **TOTAL** | **~96,500** | - |

### Couverture

- **Pharmacies** : ~19,000
- **IRIS** : ~51,000 (France métropolitaine + DOM-TOM)
- **Relations/pharmacie** : ~5.1 en moyenne
- **Conservation population** : 97.7% (13.5M clients / 13.8M population 65+)

### Distribution de w_IRIS

```
w_IRIS ∈ [0.0, 0.1[ : ~15% des relations (bordures d'isochrones)
w_IRIS ∈ [0.1, 0.5[ : ~25% des relations (couverture partielle)
w_IRIS ∈ [0.5, 0.9[ : ~20% des relations (couverture importante)
w_IRIS ∈ [0.9, 1.0] : ~40% des relations (couverture totale)
```

---

## 🧮 Utilisation dans le Modèle de Huff

### Principe

Le modèle de gravité de Huff distribue la population d'un IRIS entre les pharmacies concurrentes selon leur attractivité.

### Formule de Distribution

Pour une pharmacie *i* et un IRIS *j* :

```
P_ij = (A_i × w_ij^β) / Σ_k(A_k × w_kj^β)

où :
- P_ij = probabilité qu'un habitant de l'IRIS j fréquente la pharmacie i
- A_i = score d'attractivité de la pharmacie i (calculé par LightGBM)
- w_ij = pondération IRIS (notre matrice !)
- β = exposant de distance (calibré, typiquement β ∈ [1.5, 2.5])
- Σ_k = somme sur toutes les pharmacies k accessibles depuis l'IRIS j
```

### Distribution des Clients

```
Clients_i = Σ_j (Pop65+_j × P_ij × w_ij)

où :
- Clients_i = nombre de clients 65+ estimés pour la pharmacie i
- Pop65+_j = population 65+ de l'IRIS j
- P_ij = probabilité de Huff
- w_ij = pondération (pour éviter double comptage sur bordures)
```

---

## 🔍 Validation et Contrôle Qualité

### Conservation de la Population

**Test** : Vérifier que la somme des clients distribués ≈ population totale

```python
Total_clients = Σ_i Clients_i
Total_pop = Σ_j Pop65+_j

Taux_conservation = Total_clients / Total_pop
# Attendu : ~97-100%
```

**Résultat actuel** : 97.7% ✅

### Couverture des IRIS

**Test** : Tous les IRIS avec population > 0 doivent être dans la matrice

```python
IRIS_couverts = matrice['CODE_IRIS'].unique()
IRIS_avec_pop = population[population['pop_65_plus'] > 0]['CODE_IRIS']

Taux_couverture = len(IRIS_couverts) / len(IRIS_avec_pop)
# Attendu : 100%
```

### Cohérence Géographique

**Test** : Les pharmacies ne doivent pas desservir des IRIS à > 100 km

```python
distances = calcul_distances(pharmacies, IRIS)
relations_aberrantes = matrice[(distances > 100_000) & (w_IRIS > 0.5)]
# Attendu : 0 relations aberrantes
```

---

## 🛠️ Paramètres de Configuration

### `config_prep.py`

```python
ISOCHRONES_CONFIG = {
    'types': [
        ('walk', 5), ('walk', 10),
        ('drive', 5), ('drive', 10), ('drive', 15), ('drive', 20)
    ],
    'api_provider': 'valhalla',
    'api_url': 'http://localhost:8002',
}

# Seuils de calcul w_IRIS
SEUIL_W_IRIS_MIN = 0.01  # Éliminer les relations négligeables
LAMBDA_DISTANCE_KM = 20.0  # Paramètre de décroissance exponentielle
```

---

## 📈 Performance et Optimisation

### Temps de Calcul

| Étape | Temps (optimisé) | Nb pharmacies traitées |
|-------|------------------|------------------------|
| a. Génération isochrones | ~8 heures | 19,000 |
| b. Isochrones manquants | ~30 min | ~500 |
| c. Calcul w_IRIS | ~3-4 min | 19,000 |
| d. Enrichissement géoloc | ~10 sec | ~1,000 |
| e. Couverture 100% | ~5 sec | ~500 IRIS |

### Optimisations Appliquées

1. **Pré-groupement des données** (étape c)
   ```python
   # Grouper avant la boucle évite des opérations répétées
   iris_grouped = gdf_iris.groupby('CODE_IRIS')
   ```

2. **Checkpoints réguliers** (étape c)
   - Sauvegarde toutes les 1,000 pharmacies
   - Reprise automatique en cas d'interruption

3. **Index spatial** (étape c)
   ```python
   sindex = gdf_iris.sindex  # R-tree pour recherche rapide
   ```

4. **KDTree** (étape e)
   ```python
   tree = cKDTree(coords)  # Recherche O(log n)
   ```

---

## 📂 Arborescence des Fichiers

```
1_data_prep/
├── input/
│   ├── 1_sources_brutes/
│   │   └── contours_iris.gpkg          # Polygones IRIS
│   └── 2_insee_brutes/
│       └── age_profession.CSV          # Population 65+ par IRIS
│
├── output/
│   ├── isochrones/                     # Isochrones générés
│   │   ├── walk_5min/
│   │   ├── walk_10min/
│   │   ├── drive_5min/
│   │   ├── drive_10min/
│   │   ├── drive_15min/
│   │   └── drive_20min/
│   │
│   ├── pharmacies_final.csv            # Liste des pharmacies
│   ├── matrice_w_iris.csv             # Matrice principale ✨
│   ├── matrice_w_iris_enriched.csv    # + géolocalisation
│   └── matrice_w_iris_100pct.csv      # + couverture 100%
│
└── scripts/
    └── 3_isochrones/
        ├── a_generate_isochrones.py
        ├── b_generate_missing_isochrones.py
        ├── c_calculate_w_iris.py          # Calcul principal
        ├── d_associate_pharmacies_to_iris.py
        └── e_associate_uncovered_iris.py
```

---

## 🔬 Exemples Concrets

### Exemple 1 : Pharmacie en centre-ville

```
Pharmacie PHA001 - Paris 75001
Isochrone drive_10min couvre 8 IRIS partiellement

Matrice générée :
PHA001, 750101201, 1.00  # IRIS entièrement couvert
PHA001, 750101202, 0.95  # Couverture quasi-totale
PHA001, 750101203, 0.65  # Couverture partielle (bordure)
PHA001, 750101204, 0.42  # Couverture faible (extrémité)
...

→ Cette pharmacie dessert ~8 IRIS avec pondérations variables
```

### Exemple 2 : Pharmacie rurale

```
Pharmacie PHA500 - Lozère
Isochrone drive_20min couvre 2 IRIS totalement

Matrice générée :
PHA500, 481200001, 1.00
PHA500, 481200002, 1.00

→ Cette pharmacie dessert entièrement 2 IRIS isolés
```

### Exemple 3 : Concurrence urbaine

```
IRIS 750101201 (Paris centre)
Couvert par 12 pharmacies concurrentes

Matrice (extrait) :
PHA001, 750101201, 1.00
PHA002, 750101201, 0.95
PHA003, 750101201, 0.88
...
PHA012, 750101201, 0.35

→ Le modèle de Huff distribuera la population entre ces 12 pharmacies
→ Taux de capture moyen : ~5% par pharmacie (1/20 concurrents)
```

---

## ⚠️ Limites et Précautions

### Limites Méthodologiques

1. **Isochrones théoriques** : Ne tiennent pas compte du trafic réel, des obstacles, etc.
2. **Seuil de 0.01** : Élimine des relations faibles qui pourraient être pertinentes en zone très rurale
3. **Décroissance exponentielle** : Modèle simplifié pour nearest_neighbor (λ fixe)

### Cas Particuliers

1. **DOM-TOM** : Isochrones parfois indisponibles → Utilisation de nearest_neighbor
2. **Zones frontalières** : Isochrones peuvent dépasser la frontière → w_IRIS sous-estimé
3. **IRIS sans population** : Exclus de la matrice (pas de clients potentiels)

### Recommandations

- **Validation régulière** : Vérifier le taux de conservation à chaque exécution
- **Analyse des outliers** : Identifier les relations avec distance > 50 km
- **Calibration de β** : Ajuster l'exposant de distance selon les zones (urbain vs rural)

---

## 📚 Références

### Modèle de Huff

Huff, D. L. (1963). "A Probabilistic Analysis of Shopping Center Trade Areas". *Land Economics*, 39(1), 81-90.

### Isochrones

- API Valhalla : https://github.com/valhalla/valhalla
- Documentation isochrones : https://valhalla.readthedocs.io/en/latest/api/isochrone/

### Données INSEE

- Contours IRIS : https://geoservices.ign.fr/contoursiris
- Population par IRIS : https://www.insee.fr/

---

**Document créé le** : 2025-11-20
**Version** : 1.0
**Auteur** : Pipeline Data Prep - Phase 1