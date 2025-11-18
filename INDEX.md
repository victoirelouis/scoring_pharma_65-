# Index de la Documentation - Projet Scoring Pharmacies 65+

## Documents de Référence

### 📘 Méthodologie et Théorie
- **[README.md](README.md)** - Méthodologie détaillée complète (400 lignes)
  - Principe général du modèle gravitaire
  - Phase 1 : Calcul d'attractivité (composantes S, F, H, M, β)
  - Phase 2 : Modèle de Huff et répartition population
  - Phase 3 : Projection du CA 65+
  - Données d'entrée et paramètres
  - Glossaire des termes techniques

### 🛠️ Implémentation Pratique
- **[GUIDE_IMPLEMENTATION.md](GUIDE_IMPLEMENTATION.md)** - Guide d'implémentation complet
  - Architecture des dossiers
  - Phase 0 : Préparation données de base (25 scripts)
  - Phase 1 : Pipeline ML et analyses (13 scripts)
  - Ordre d'exécution des scripts
  - Fichiers de sortie essentiels

### 📊 Pipeline ML (Phase 1)
- **[intermediaire/README_PIPELINE.md](intermediaire/README_PIPELINE.md)** - Documentation Pipeline ML
  - 6 scripts du pipeline principal (ml_01 à ml_06)
  - 3 scripts d'analyse des corrélations
  - Résultats clés et métriques
  - Notes techniques sur le modèle de Huff

---

## Structure du Projet

```
scoring_pharma_65-/
│
├── INDEX.md                    # Ce fichier (point d'entrée documentation)
├── README.md                   # Méthodologie complète (théorique)
├── GUIDE_IMPLEMENTATION.md     # Guide implémentation (pratique)
│
├── scripts/                    # PHASE 0 : Préparation données (25 scripts)
│   ├── geocode_rpps_optimise.py
│   ├── fusion_hubs_complet.py
│   ├── generate_isochrones.py
│   └── ... (22 autres scripts)
│
├── data/
│   ├── input/                  # Données sources
│   │   ├── FINESS.csv
│   │   ├── data_cleaning/pharmacies_final.csv
│   │   ├── enrichissement/pharmacie_iris_pond_cleaned.csv
│   │   └── iris_insee/population_age.csv
│   │
│   └── output/                 # Résultats Phase 0
│       ├── HUBS_unified_final.csv (71 MB) ⭐
│       └── pharmacies_final_avec_variables_touristiques.csv
│
├── intermediaire/              # PHASE 1 : Pipeline ML
│   ├── README_PIPELINE.md      # Documentation Phase 1
│   │
│   ├── scripts/                # Scripts ML (13 scripts)
│   │   ├── ml_01_prepare_hubs_par_isochrone.py
│   │   ├── ml_02_prepare_concurrence.py
│   │   ├── ml_03_prepare_population_isochrones.py
│   │   ├── ml_04_integration_complete.py
│   │   ├── ml_05_score_attractivite_lightgbm.py
│   │   ├── ml_06_HUFF_EXACT_IRIS_FIXED.py ⭐
│   │   ├── analyse_correlation_sig_p20.py
│   │   ├── analyse_correlation_avancee.py
│   │   └── analyse_proximite_hubs_medicaux.py
│   │
│   └── output/
│       ├── pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv ⭐ FINAL
│       ├── modeles_lightgbm/ (4 modèles)
│       └── correlation_*.csv (résultats analyses)
│
└── src/                        # Code source (vide)
```

---

## Parcours de Lecture Recommandé

### Pour comprendre la méthodologie
1. Lire [README.md](README.md) sections 1-3 (Introduction, Principe, Phase 1-2-3)
2. Consulter le glossaire à la fin de README.md si termes inconnus

### Pour exécuter le projet
1. Lire [GUIDE_IMPLEMENTATION.md](GUIDE_IMPLEMENTATION.md)
2. Suivre l'ordre d'exécution des scripts Phase 0 puis Phase 1
3. Consulter [intermediaire/README_PIPELINE.md](intermediaire/README_PIPELINE.md) pour détails Phase 1

### Pour analyser les résultats
1. Fichier final : `intermediaire/output/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv`
2. Résultats corrélations : `intermediaire/output/correlation_*.csv`
3. Consulter les sections "Résultats" dans GUIDE_IMPLEMENTATION.md

---

## Fichiers de Sortie Essentiels

| Fichier | Taille | Description |
|---------|--------|-------------|
| `data/output/HUBS_unified_final.csv` | 71 MB | HUBS médicaux/touristiques finaux |
| `intermediaire/output/pharmacies_avec_scores_attractivite.csv` | 8.5 MB | Scores LightGBM |
| `intermediaire/output/pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv` | 2.3 MB | **RÉSULTAT FINAL** ⭐ |

---

## Résultats Clés

### Modèle de Huff
- Population France 65+ : 14,125,725
- Population couverte : 13,302,521 (94.2%)
- **Conservation : 100.0%** ✓
- Pharmacies avec clients : 18,208 / 19,307

### Corrélations SIG_P20 vs Clients 65+
- Global : 0.150 (UN), 0.210 (CAHT)
- Urbain dense : 0.342 (meilleure)
- Zones touristiques : 0.220 (vs 0.113)
- 4-10 hubs médicaux à 1km : 0.320 (meilleure)

---

## Contact

**Projet** : Scoring Pharmacies 65+  
**Organisation** : GERS  
**Responsable** : Victoire LOUIS  
**Date** : Novembre 2025  
**Version** : 1.0 (après nettoyage)
