# Notebooks d'Analyse

Ce répertoire contient les notebooks Jupyter pour l'analyse interactive des données.

## Notebooks Disponibles

À créer selon vos besoins :

- **exploration.ipynb** : Exploration initiale des données
- **analyse_scores.ipynb** : Analyse détaillée des scores
- **comparaisons.ipynb** : Comparaisons géographiques
- **visualisations.ipynb** : Création de visualisations personnalisées

## Lancement

```bash
jupyter notebook notebooks/
```

## Structure Recommandée

Chaque notebook devrait contenir :

1. **Importation des modules**
```python
import sys
sys.path.insert(0, '../src')

from scoring_pharma import ScoringEngine, DataLoader
from scoring_pharma.visualizer import Visualizer
import pandas as pd
import matplotlib.pyplot as plt
```

2. **Chargement des données**
3. **Analyse exploratoire**
4. **Visualisations**
5. **Conclusions**
