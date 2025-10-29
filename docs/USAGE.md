# Guide d'Utilisation

## Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation des dépendances

```bash
pip install -r requirements.txt
```

## Préparation des Données

1. Placez vos fichiers de données dans le répertoire `data/`
2. Respectez la structure décrite dans `data/README.md`
3. Les fichiers attendus sont :
   - `pharmacies.csv`
   - `demographics.csv`
   - `economic.csv`

Des exemples sont fournis avec le préfixe `example_` :
- `data/example_pharmacies.csv`
- `data/example_demographics.csv`
- `data/example_economic.csv`

## Utilisation Basique

### Exécution du script principal

```bash
python main.py
```

Ce script va :
1. Charger toutes les données disponibles
2. Calculer les scores pour chaque pharmacie
3. Générer un rapport de synthèse
4. Exporter les résultats dans `output/`
5. Créer des visualisations

### Utilisation Programmatique

```python
from scoring_pharma import ScoringEngine, DataLoader
from scoring_pharma.visualizer import Visualizer

# Charger les données
loader = DataLoader(data_dir='data')
data = loader.load_all()

# Calculer les scores
engine = ScoringEngine()
scores = engine.calculate_total_score(
    data['pharmacies'],
    data['demographics'],
    data['economic']
)

# Afficher les meilleures pharmacies
top_10 = engine.get_top_pharmacies(10)
print(top_10)

# Créer des visualisations
viz = Visualizer()
viz.plot_score_distribution(scores)
viz.plot_category_distribution(scores)
```

## Résultats

Les résultats sont exportés dans le répertoire `output/` :
- `scores_pharmacies.csv` : Scores détaillés de toutes les pharmacies
- `distribution_scores.png` : Histogramme de distribution des scores
- `distribution_categories.png` : Répartition par catégories
- `composantes_scores.png` : Détail des composantes du score
- `top_pharmacies.png` : Top 10 des meilleures pharmacies

## Tests

Pour exécuter les tests unitaires :

```bash
pytest tests/ -v
```

Pour exécuter les tests avec couverture :

```bash
pytest tests/ --cov=src/scoring_pharma --cov-report=html
```

## Personnalisation

### Modifier les poids du scoring

Éditez le fichier `src/scoring_pharma/scoring_engine.py` :

```python
WEIGHTS = {
    'demographic': 0.35,  # Poids démographie
    'geographic': 0.25,   # Poids géographie
    'economic': 0.25,     # Poids économie
    'service': 0.15       # Poids services
}
```

### Modifier les catégories

Dans le même fichier :

```python
CATEGORIES = {
    'A+': (90, 100),
    'A': (80, 89),
    'B': (65, 79),
    'C': (50, 64),
    'D': (0, 49)
}
```

## Notebooks Jupyter

Vous pouvez créer des notebooks dans le répertoire `notebooks/` pour :
- Explorer les données de manière interactive
- Créer des analyses personnalisées
- Expérimenter avec différents paramètres

Exemple de démarrage :

```bash
jupyter notebook notebooks/
```

## Support

Pour toute question ou problème :
1. Consultez la documentation dans `docs/METHODOLOGIE.md`
2. Vérifiez les logs d'exécution
3. Examinez les exemples de données fournis
