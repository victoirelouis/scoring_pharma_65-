"""
Script principal d'exécution du scoring des pharmacies
"""

import sys
from pathlib import Path

# Ajout du répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scoring_pharma import ScoringEngine, DataLoader
from scoring_pharma.visualizer import Visualizer
from scoring_pharma.utils import export_results, generate_summary_report
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Fonction principale"""
    logger.info("=" * 60)
    logger.info("Démarrage du calcul de scoring des pharmacies 65+")
    logger.info("=" * 60)
    
    try:
        # 1. Chargement des données
        logger.info("\n1. Chargement des données...")
        loader = DataLoader(data_dir='data')
        data = loader.load_all()
        
        if not data:
            logger.error("Aucune donnée chargée. Veuillez vérifier le répertoire data/")
            logger.info("\nConsultez data/README.md pour la structure des fichiers attendus.")
            return
        
        # Validation des données
        if not loader.validate_data():
            logger.error("Les données ne sont pas valides")
            return
        
        # 2. Calcul des scores
        logger.info("\n2. Calcul des scores...")
        engine = ScoringEngine()
        scores = engine.calculate_total_score(
            data['pharmacies'],
            data.get('demographics', data['pharmacies']),
            data.get('economic', data['pharmacies'])
        )
        
        # 3. Affichage des résultats
        logger.info("\n3. Résultats du scoring")
        logger.info("-" * 60)
        
        # Rapport de synthèse
        report = generate_summary_report(scores)
        logger.info(f"\nNombre total de pharmacies : {report['total_pharmacies']}")
        logger.info(f"Score moyen : {report['score_moyen']:.2f}")
        logger.info(f"Score médian : {report['score_median']:.2f}")
        logger.info(f"Score minimum : {report['score_min']:.2f}")
        logger.info(f"Score maximum : {report['score_max']:.2f}")
        logger.info(f"Écart-type : {report['ecart_type']:.2f}")
        
        logger.info("\nDistribution par catégories :")
        for category, count in sorted(report['distribution_categories'].items()):
            logger.info(f"  {category}: {count} pharmacies")
        
        # Top 10 pharmacies
        logger.info("\n4. Top 10 des pharmacies")
        logger.info("-" * 60)
        top_pharmacies = engine.get_top_pharmacies(10)
        for idx, row in top_pharmacies.iterrows():
            name = row.get('nom', row.get('id_pharmacie', 'N/A'))
            logger.info(f"{name}: {row['score_total']:.2f} (Catégorie {row['category']})")
        
        # 5. Export des résultats
        logger.info("\n5. Export des résultats...")
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        export_results(scores, 'output/scores_pharmacies.csv', format='csv')
        
        # 6. Visualisations
        logger.info("\n6. Génération des visualisations...")
        viz = Visualizer()
        
        try:
            viz.plot_score_distribution(scores, save_path='output/distribution_scores.png')
            viz.plot_category_distribution(scores, save_path='output/distribution_categories.png')
            viz.plot_score_components(scores, save_path='output/composantes_scores.png')
            viz.plot_top_pharmacies(scores, n=10, save_path='output/top_pharmacies.png')
            logger.info("Visualisations sauvegardées dans le répertoire output/")
        except Exception as e:
            logger.warning(f"Impossible de générer les visualisations : {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Calcul terminé avec succès !")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution : {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
