# Scoring Pharma 65+

Système de scoring du potentiel de ventes des pharmacies pour la population des 65 ans et plus.

## 📋 Description

Ce projet propose une méthodologie complète pour évaluer le potentiel commercial des pharmacies ciblant la clientèle senior (65+). Le système prend en compte plusieurs dimensions :

- **Démographique** (35%) : Densité de la population 65+, structure d'âge, croissance
- **Géographique** (25%) : Accessibilité, zone de chalandise, concurrence
- **Économique** (25%) : Pouvoir d'achat, équipements seniors, dynamisme
- **Services** (15%) : Offre adaptée aux seniors

## 🚀 Démarrage Rapide

### Installation

```bash
# Cloner le repository
git clone https://github.com/victoirelouis/scoring_pharma_65-.git
cd scoring_pharma_65-

# Installer les dépendances
pip install -r requirements.txt
```

### Utilisation

```bash
# Exécuter l'analyse avec les données d'exemple
python main.py
```

Les résultats seront disponibles dans le répertoire `output/`.

## 📁 Structure du Projet

```
scoring_pharma_65-/
├── data/                      # Données d'entrée
│   ├── README.md             # Description des données attendues
│   ├── example_*.csv         # Exemples de données
│   └── .gitkeep
├── src/scoring_pharma/       # Code source principal
│   ├── __init__.py
│   ├── data_loader.py        # Chargement des données
│   ├── scoring_engine.py     # Calcul des scores
│   ├── visualizer.py         # Visualisations
│   └── utils.py              # Utilitaires
├── tests/                    # Tests unitaires
│   ├── test_data_loader.py
│   ├── test_scoring_engine.py
│   └── test_utils.py
├── docs/                     # Documentation
│   ├── METHODOLOGIE.md       # Détails de la méthodologie
│   └── USAGE.md              # Guide d'utilisation
├── notebooks/                # Notebooks Jupyter (analyses)
├── main.py                   # Script principal
├── requirements.txt          # Dépendances Python
└── README.md
```

## 📊 Méthodologie

Le score final est calculé selon la formule :

```
Score = 0.35×Démo + 0.25×Géo + 0.25×Éco + 0.15×Services
```

Les pharmacies sont ensuite classées en 5 catégories (A+, A, B, C, D) selon leur score.

Pour plus de détails, consultez [docs/METHODOLOGIE.md](docs/METHODOLOGIE.md).

## 📚 Documentation

- **[Guide d'utilisation](docs/USAGE.md)** : Installation et utilisation détaillée
- **[Méthodologie](docs/METHODOLOGIE.md)** : Explication complète du système de scoring
- **[README des données](data/README.md)** : Structure des fichiers de données

## 🧪 Tests

```bash
# Exécuter tous les tests
pytest tests/ -v

# Avec couverture de code
pytest tests/ --cov=src/scoring_pharma --cov-report=html
```

## 🔧 Configuration

Les paramètres du scoring peuvent être ajustés dans `src/scoring_pharma/scoring_engine.py` :

- Poids des différentes composantes
- Seuils des catégories
- Méthodes de normalisation

## 📈 Exemples de Résultats

Le système génère automatiquement :
- Scores individuels par pharmacie
- Distribution des scores
- Répartition par catégories
- Top N des meilleures pharmacies
- Analyse des composantes du score

## 🤝 Contribution

Ce projet a été développé avec Claude Code pour automatiser et standardiser le processus d'évaluation du potentiel des pharmacies.

## 📝 Licence

Ce projet est sous licence MIT.

## 👤 Auteur

Victoire Louis

## 🔗 Liens Utiles

- [Documentation Python Pandas](https://pandas.pydata.org/)
- [Scikit-learn](https://scikit-learn.org/)
- [Matplotlib](https://matplotlib.org/)
