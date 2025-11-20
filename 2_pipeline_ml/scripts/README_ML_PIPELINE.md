# Pipeline ML - Prédiction CA Pharmacies 65+

## 📁 Structure des dossiers

Voici comment organiser vos fichiers :

```
N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\
│
├── data/
│   ├── output/
│   │   ├── pharmacies_final.csv                                    ✅ (VOTRE FICHIER)
│   │   ├── HUBS_unified_corriges.csv                              ✅ (VOTRE FICHIER)
│   │   └── pharmacies_final_avec_variables_touristiques.csv       ✅ (VOTRE FICHIER)
│   │
│   ├── enrichi_INSEE.csv                                          ✅ (VOTRE FICHIER)
│   │
│   └── isochrones/
│       ├── walk_5min/
│       │   ├── 2040918.geojson
│       │   ├── 2050549.geojson
│       │   └── ... (20 000 fichiers)
│       │
│       └── drive_10min/
│           ├── 2040918.geojson
│           ├── 2050549.geojson
│           └── ... (20 000 fichiers)
│
├── 2_pipeline_ml/
│   ├── script/                          ← Mettez les scripts Python ici
│   │   ├── config_ml.py
│   │   ├── ml_01_prepare_hubs_par_isochrone.py
│   │   ├── ml_02_prepare_concurrence.py
│   │   ├── ... (autres scripts)
│   │   └── requirements.txt
│   │
│   └── output/                          ← Les résultats intermédiaires iront ici
│       ├── pharmacies_avec_hubs.csv         (généré par script 1)
│       ├── pharmacies_avec_concurrence.csv  (généré par script 2)
│       ├── rapport_deduplication_hubs.txt   (généré par script 1)
│       ├── pipeline_ml.log                  (fichier de log)
│       ├── models/                          (modèles ML)
│       └── reports/                         (graphiques et rapports)
│
└── README_ML_PIPELINE.md                    (ce fichier)
```

---

## ⚙️ Installation

### 1. Vérifier Python

Assurez-vous d'avoir **Python 3.8+** installé :

```bash
python --version
```

### 2. Installer les dépendances

Dans le dossier `2_pipeline_ml/script/`, créez un fichier `requirements.txt` avec :

```txt
pandas>=2.0.0
numpy>=1.24.0
geopandas>=0.14.0
shapely>=2.0.0
scikit-learn>=1.3.0
lightgbm>=4.0.0
shap>=0.42.0
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.14.0
tqdm>=4.65.0
optuna>=3.2.0
statsmodels>=0.14.0
folium>=0.14.0
```

Puis installez :

```bash
cd N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\script
pip install -r requirements.txt
```

---

## 🚀 Exécution des scripts

### Étape préliminaire : Vérifier les chemins

Avant d'exécuter, ouvrez `config_ml.py` et vérifiez que tous les chemins correspondent à vos fichiers.

**Points à vérifier** :

1. **Noms de fichiers** :
   - ✅ `pharmacies_final.csv`
   - ✅ `HUBS_unified_corriges.csv`
   - ⚠️ `enrichi_INSEE.csv` → Où est ce fichier exactement ?
   - ⚠️ Fichier variables touristiques → Quel est son nom exact ?

2. **Colonnes importantes** :
   - Dans `pharmacies_final.csv`, quelle colonne contient l'ID pharmacie ?
     → Modifiez `ISOCHRONES_CONFIG['colonne_id_pharmacie']` si ce n'est pas `'id_pharmacie'`
   
   - Dans `HUBS_unified_corriges.csv`, vérifiez :
     → `hub_type_detail` existe bien
     → `latitude` et `longitude` existent bien

3. **Structure isochrones** :
   - Les fichiers GeoJSON sont bien nommés comme `{id_pharmacie}.geojson` ?
   - Exemple : `2040918.geojson`, `2050549.geojson`, etc.

---

### Script 1 : Préparation hubs par isochrone

**Ce qu'il fait** :
- Charge les 639k hubs
- Pour chaque pharmacie, filtre les hubs dans ses isochrones (walk_5min, drive_10min)
- Applique déduplication spatiale (clustering 50m)
- Crée ~24 variables hubs par pharmacie

**Exécution** :

```bash
cd N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\script
python ml_01_prepare_hubs_par_isochrone.py
```

**Durée estimée** : 25-35 minutes

**Sortie** :
- `2_pipeline_ml/output/pharmacies_avec_hubs.csv`
- `2_pipeline_ml/output/rapport_deduplication_hubs.txt`

---

### Script 2 : Préparation concurrence

*(À créer)*

---

### Script 3 : Préparation population par isochrone

*(À créer)*

---

### Script 4-14 : Suite du pipeline

*(À créer)*

---

## 🐛 Dépannage

### Erreur : "FileNotFoundError"

```
FileNotFoundError: [Errno 2] No such file or directory: '...'
```

**Solution** : Vérifiez les chemins dans `config_ml.py`. Assurez-vous que :
- Les fichiers existent bien aux chemins indiqués
- Les noms de fichiers sont corrects (majuscules/minuscules)
- Les répertoires sont créés

---

### Erreur : "KeyError: 'hub_type_detail'"

```
KeyError: 'hub_type_detail'
```

**Solution** : La colonne `hub_type_detail` n'existe pas dans votre fichier hubs.

1. Ouvrez `HUBS_unified_corriges.csv` et vérifiez le nom exact de la colonne type
2. Modifiez dans `config_ml.py` :
   ```python
   HUBS_DEDUPLICATION_CONFIG = {
       'colonne_type': 'votre_nom_de_colonne',  # Modifier ici
       ...
   }
   ```

---

### Erreur : "MemoryError"

```
MemoryError: Unable to allocate ...
```

**Solution** : Pas assez de RAM. Options :
1. Traiter par batch (modifier le script pour traiter 1000 pharmacies à la fois)
2. Utiliser un ordinateur avec plus de RAM
3. Désactiver la déduplication (plus rapide mais moins précis) :
   ```python
   HUBS_DEDUPLICATION_CONFIG = {
       'activer': False,
       ...
   }
   ```

---

### Le script est très lent

**Optimisations possibles** :

1. **Tester sur un échantillon** :
   Modifiez `ml_01_prepare_hubs_par_isochrone.py` ligne ~350 :
   ```python
   # Tester sur 100 pharmacies seulement
   pharmacies_ids = self.pharmacies_df[col_id].head(100).tolist()
   ```

2. **Désactiver les détails** :
   Dans `config_ml.py` :
   ```python
   HUBS_AGREGATIONS_CONFIG = {
       'inclure_details': False,  # Ne garder que les familles agrégées
       ...
   }
   ```

3. **Augmenter epsilon** (moins de clusters) :
   ```python
   HUBS_DEDUPLICATION_CONFIG = {
       'epsilon_metres': 100,  # Au lieu de 50
       ...
   }
   ```

---

## 📊 Vérification des résultats

Après exécution du Script 1, vérifiez :

1. **Fichier créé** :
   ```
   2_pipeline_ml/output/pharmacies_avec_hubs.csv
   ```
   
2. **Nombre de lignes** : 20 000 (même nombre que pharmacies_final.csv)

3. **Colonnes créées** :
   - `nb_sante_generale_walk_5min`
   - `nb_sante_generale_drive_10min`
   - `nb_medecin_walk_5min`
   - `nb_ehpad_drive_10min`
   - `taux_colocalisation_walk_5`
   - ... (~24 nouvelles colonnes)

4. **Rapport de déduplication** :
   ```
   2_pipeline_ml/output/rapport_deduplication_hubs.txt
   ```
   
   Contient des statistiques comme :
   - Total hubs avant/après déduplication
   - Taux de colocalisation par isochrone
   - Moyennes par famille de hubs

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Consultez le fichier de log :
   ```
   2_pipeline_ml/output/pipeline_ml.log
   ```

2. Vérifiez que tous les prérequis sont installés :
   ```bash
   pip list
   ```

3. Testez sur un petit échantillon d'abord (100 pharmacies)

---

## ✅ Checklist avant exécution

- [ ] Python 3.8+ installé
- [ ] Toutes les dépendances installées (`pip install -r requirements.txt`)
- [ ] Fichiers sources présents :
  - [ ] `pharmacies_final.csv`
  - [ ] `HUBS_unified_corriges.csv`
  - [ ] Isochrones walk_5min (20 000 fichiers)
  - [ ] Isochrones drive_10min (20 000 fichiers)
- [ ] Chemins vérifiés dans `config_ml.py`
- [ ] Colonnes vérifiées (id_pharmacie, hub_type_detail, latitude, longitude)
- [ ] Dossiers créés :
  - [ ] `2_pipeline_ml/script/`
  - [ ] `2_pipeline_ml/output/`

---

**Prêt à lancer le Script 1 !** 🚀
