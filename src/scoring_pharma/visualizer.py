"""
Module de visualisation des résultats
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration du style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


class Visualizer:
    """Classe pour créer des visualisations des scores"""
    
    def __init__(self):
        """Initialise le visualiseur"""
        pass
    
    @staticmethod
    def plot_score_distribution(scores: pd.DataFrame, save_path: Optional[str] = None):
        """
        Crée un histogramme de la distribution des scores totaux
        
        Args:
            scores: DataFrame contenant les scores
            save_path: Chemin pour sauvegarder la figure (optionnel)
        """
        logger.info("Création de la distribution des scores")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(scores['score_total'], bins=20, edgecolor='black', alpha=0.7)
        ax.set_xlabel('Score Total', fontsize=12)
        ax.set_ylabel('Nombre de Pharmacies', fontsize=12)
        ax.set_title('Distribution des Scores de Potentiel', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure sauvegardée : {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_category_distribution(scores: pd.DataFrame, save_path: Optional[str] = None):
        """
        Crée un graphique en barres de la distribution par catégorie
        
        Args:
            scores: DataFrame contenant les scores
            save_path: Chemin pour sauvegarder la figure (optionnel)
        """
        logger.info("Création de la distribution par catégorie")
        
        category_counts = scores['category'].value_counts().sort_index()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = {'A+': '#2ecc71', 'A': '#3498db', 'B': '#f39c12', 'C': '#e67e22', 'D': '#e74c3c'}
        bars = ax.bar(category_counts.index, category_counts.values, 
                     color=[colors.get(cat, '#95a5a6') for cat in category_counts.index],
                     edgecolor='black', alpha=0.8)
        
        ax.set_xlabel('Catégorie', fontsize=12)
        ax.set_ylabel('Nombre de Pharmacies', fontsize=12)
        ax.set_title('Répartition des Pharmacies par Catégorie', fontsize=14, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Ajout des valeurs au-dessus des barres
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure sauvegardée : {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_score_components(scores: pd.DataFrame, pharmacy_id: Optional[str] = None, 
                            save_path: Optional[str] = None):
        """
        Crée un graphique radar des composantes du score
        
        Args:
            scores: DataFrame contenant les scores
            pharmacy_id: ID de la pharmacie (si None, prend la moyenne)
            save_path: Chemin pour sauvegarder la figure (optionnel)
        """
        logger.info("Création du graphique des composantes")
        
        components = ['score_demographic', 'score_geographic', 'score_economic', 'score_service']
        labels = ['Démographique', 'Géographique', 'Économique', 'Services']
        
        if pharmacy_id:
            values = scores[scores['id_pharmacie'] == pharmacy_id][components].values[0]
            title = f'Composantes du Score - Pharmacie {pharmacy_id}'
        else:
            values = scores[components].mean().values
            title = 'Composantes du Score - Moyenne'
        
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(labels))
        bars = ax.barh(labels, values, color='steelblue', edgecolor='black', alpha=0.8)
        
        ax.set_xlabel('Score', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(True, axis='x', alpha=0.3)
        
        # Ajout des valeurs
        for i, (bar, val) in enumerate(zip(bars, values)):
            ax.text(val + 2, i, f'{val:.1f}', 
                   va='center', fontsize=10, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure sauvegardée : {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_top_pharmacies(scores: pd.DataFrame, n: int = 10, 
                          save_path: Optional[str] = None):
        """
        Crée un graphique des n meilleures pharmacies
        
        Args:
            scores: DataFrame contenant les scores
            n: Nombre de pharmacies à afficher
            save_path: Chemin pour sauvegarder la figure (optionnel)
        """
        logger.info(f"Création du graphique des top {n} pharmacies")
        
        top = scores.nlargest(n, 'score_total')
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        pharmacy_labels = top['nom'] if 'nom' in top.columns else top['id_pharmacie']
        colors = top['category'].map({
            'A+': '#2ecc71', 'A': '#3498db', 'B': '#f39c12', 
            'C': '#e67e22', 'D': '#e74c3c'
        })
        
        bars = ax.barh(range(n), top['score_total'], color=colors, 
                      edgecolor='black', alpha=0.8)
        ax.set_yticks(range(n))
        ax.set_yticklabels(pharmacy_labels)
        ax.set_xlabel('Score Total', fontsize=12)
        ax.set_title(f'Top {n} Pharmacies par Score', fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        ax.grid(True, axis='x', alpha=0.3)
        
        # Ajout des valeurs et catégories
        for i, (bar, score, cat) in enumerate(zip(bars, top['score_total'], top['category'])):
            ax.text(score + 1, i, f'{score:.1f} ({cat})', 
                   va='center', fontsize=9, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Figure sauvegardée : {save_path}")
        
        plt.show()
