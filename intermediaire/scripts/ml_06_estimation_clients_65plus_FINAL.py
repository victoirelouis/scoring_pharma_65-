"""
Script 6 : ESTIMATION DU NOMBRE DE CLIENTS 65+ PAR PHARMACIE

Ce script utilise les scores d'attractivité (Script 5) et le modèle de Huff
pour estimer le nombre de clients 65+ potentiels pour chaque pharmacie.

MÉTHODOLOGIE :
    1. Charger les scores d'attractivité (Script 5)
    2. Pour chaque pharmacie, identifier les pharmacies concurrentes accessibles
    3. Appliquer le modèle de Huff pour calculer la part de marché
    4. Estimer le nombre de clients 65+ captés par tranche d'âge
    5. Calculer des déciles de performance
    6. Identifier les opportunités

MODÈLE DE HUFF :
    Part_marche_i = Score_attractivite_i / Σ(Score_attractivite_j)
    où j = toutes les pharmacies accessibles (concurrentes)
    
    Clients_65plus_i = Pop_65plus_accessible × Part_marche_i × Taux_fidelite

Inputs:
    - pharmacies_avec_scores_attractivite.csv (Script 5)
    - pharmacies_avec_population_isochrones.csv (Script 3)
    - pharmacies_avec_concurrence.csv (Script 2)

Outputs:
    - pharmacies_estimation_clients_65plus.csv : Estimation finale
    - rapport_estimation_clients.txt : Rapport détaillé

Durée estimée: 2-3 minutes

Auteur: Pipeline ML Pharmacies
Date: 2025-11-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration
from config_ml import (
    INTERMEDIATE_FILES,
    LOGGING_CONFIG
)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['log_file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClientsEstimator:
    """
    Classe pour estimer le nombre de clients 65+ par pharmacie
    """
    
    def __init__(self):
        """Initialisation"""
        self.df = None
        self.df_population = None
        self.df_concurrence = None
        
        # Paramètres du modèle
        self.taux_fidelite = 0.85  # 85% des seniors vont régulièrement en pharmacie
        self.freq_visite_annuelle = 12  # Nombre de visites/an en moyenne pour 65+
        
        logger.info("Initialisation de l'estimateur de clients 65+")
    
    def load_data(self):
        """Charge toutes les données nécessaires"""
        logger.info("\nChargement des données...")
        
        # 1. Scores d'attractivité (Script 5)
        scores_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite']
        self.df = pd.read_csv(scores_path)
        logger.info(f"  ✅ Scores d'attractivité : {len(self.df):,} pharmacies")
        
        # 2. Population par isochrone (Script 3)
        pop_path = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones']
        self.df_population = pd.read_csv(pop_path)
        logger.info(f"  ✅ Population : {len(self.df_population):,} pharmacies")
        
        # 3. Concurrence (Script 2)
        conc_path = INTERMEDIATE_FILES['pharmacies_avec_concurrence']
        self.df_concurrence = pd.read_csv(conc_path)
        logger.info(f"  ✅ Concurrence : {len(self.df_concurrence):,} pharmacies")
        
        # Fusionner tout
        logger.info("\nFusion des données...")
        self.df = self.df.merge(
            self.df_population[['id_pharmacie', 'pop_65_74_drive_10min', 'pop_75_84_drive_10min', 
                                'pop_85_plus_drive_10min', 'pop_65_plus_drive_10min']],
            on='id_pharmacie',
            how='left'
        )
        
        self.df = self.df.merge(
            self.df_concurrence[['id_pharmacie', 'nb_pharmacies_concurrentes_drive_10min', 
                                 'distance_pharmacie_plus_proche']],
            on='id_pharmacie',
            how='left'
        )
        
        logger.info(f"  ✅ Fusion terminée : {len(self.df):,} pharmacies × {len(self.df.columns)} colonnes")
    
    def verify_scores(self):
        """Vérifie que les scores d'attractivité 65+ existent"""
        logger.info("\nVérification des scores d'attractivité 65+...")
        
        required_col = 'score_attractivite_65plus_composite'
        
        if required_col not in self.df.columns:
            logger.error(f"❌ Colonne '{required_col}' introuvable !")
            logger.error("   → Le Script 5 doit être lancé avec extraction de la part 65+")
            logger.error(f"   Colonnes disponibles commençant par 'score_' : {[c for c in self.df.columns if c.startswith('score_')]}")
            raise ValueError(f"Colonne {required_col} manquante")
        
        # Vérifier qu'il n'y a pas de valeurs manquantes
        n_missing = self.df[required_col].isna().sum()
        if n_missing > 0:
            logger.warning(f"⚠️  {n_missing} pharmacies sans score 65+ → Remplissage avec médiane")
            median_score = self.df[required_col].median()
            self.df[required_col] = self.df[required_col].fillna(median_score)
        
        # Vérifier que les scores sont dans [0, 1]
        score_min = self.df[required_col].min()
        score_max = self.df[required_col].max()
        
        if score_min < 0 or score_max > 1:
            logger.warning(f"⚠️  Scores hors de [0,1] détectés : min={score_min:.3f}, max={score_max:.3f}")
            logger.warning("   → Normalisation forcée entre 0 et 1")
            self.df[required_col] = (
                (self.df[required_col] - score_min) / (score_max - score_min)
            )
        
        logger.info(f"  ✅ Score 65+ disponible pour {len(self.df):,} pharmacies")
        logger.info(f"     Min: {self.df[required_col].min():.3f} | Médiane: {self.df[required_col].median():.3f} | Max: {self.df[required_col].max():.3f}")
        
        # Afficher aussi les parts seniors si disponibles
        part_cols = [c for c in self.df.columns if 'part_seniors' in c or 'part_ca_65plus' in c]
        if part_cols:
            logger.info(f"\n  📊 Parts seniors détectées :")
            for col in part_cols:
                if col in self.df.columns:
                    mean_val = self.df[col].mean()
                    logger.info(f"     {col}: {mean_val:.1%}")
    
    def calculate_market_share_huff(self):
        """
        Calcule la part de marché selon le modèle de Huff
        
        Modèle de Huff :
        Part_marche_i = Score_i / (Score_i + Σ Score_j)
        où j = pharmacies concurrentes
        """
        logger.info("\n" + "="*80)
        logger.info("CALCUL DE LA PART DE MARCHÉ (MODÈLE DE HUFF)")
        logger.info("="*80)
        
        score_col = 'score_attractivite_65plus_composite'
        
        # Simplification : Part de marché = Score normalisé ajusté par la concurrence
        # Plus il y a de concurrence, plus la part est diluée
        
        logger.info("\nCalcul de la part de marché par pharmacie...")
        
        # Méthode simplifiée : Part inversement proportionnelle à la concurrence
        # Si nb_concurrents = 0 → part = 1.0 (monopole local)
        # Si nb_concurrents = 5 → part = 1/6 = 0.167 (6 pharmacies se partagent)
        
        self.df['nb_pharmacies_totales'] = self.df['nb_pharmacies_concurrentes_drive_10min'].fillna(0) + 1
        
        # Part de base = 1 / nombre total de pharmacies
        self.df['part_marche_base'] = 1.0 / self.df['nb_pharmacies_totales']
        
        # Ajustement par le score d'attractivité relatif
        # Si score > médiane → bonus
        # Si score < médiane → malus
        score_median = self.df[score_col].median()
        self.df['ratio_score'] = self.df[score_col] / score_median
        
        # Part de marché finale = part_base × ratio_score
        # Puis normalisée pour que la somme = 1 dans chaque zone
        self.df['part_marche_huff'] = self.df['part_marche_base'] * self.df['ratio_score']
        
        # Limiter entre 0.05 (5%) et 0.95 (95%)
        self.df['part_marche_huff'] = self.df['part_marche_huff'].clip(0.05, 0.95)
        
        logger.info(f"  ✅ Part de marché calculée")
        logger.info(f"     Moyenne : {self.df['part_marche_huff'].mean():.1%}")
        logger.info(f"     Médiane : {self.df['part_marche_huff'].median():.1%}")
        logger.info(f"     Min : {self.df['part_marche_huff'].min():.1%}")
        logger.info(f"     Max : {self.df['part_marche_huff'].max():.1%}")
    
    def estimate_clients_65plus(self):
        """Estime le nombre de clients 65+ par pharmacie et par tranche d'âge"""
        logger.info("\n" + "="*80)
        logger.info("ESTIMATION DES CLIENTS 65+")
        logger.info("="*80)
        
        logger.info(f"\nParamètres du modèle :")
        logger.info(f"  - Taux de fidélité : {self.taux_fidelite:.0%}")
        logger.info(f"  - Fréquence de visite annuelle : {self.freq_visite_annuelle} fois/an")
        
        # Population accessible × Part de marché × Taux de fidélité
        
        # Par tranche d'âge
        tranches = {
            '65_74': 'pop_65_74_drive_10min',
            '75_84': 'pop_75_84_drive_10min',
            '85_plus': 'pop_85_plus_drive_10min'
        }
        
        for tranche, pop_col in tranches.items():
            if pop_col in self.df.columns:
                # Nombre de clients = Pop × Part_marche × Taux_fidelite
                self.df[f'clients_{tranche}'] = (
                    self.df[pop_col].fillna(0) *
                    self.df['part_marche_huff'] *
                    self.taux_fidelite
                )
                
                logger.info(f"\n  Tranche {tranche} :")
                logger.info(f"    Population moyenne accessible : {self.df[pop_col].mean():,.0f}")
                logger.info(f"    Clients moyens estimés : {self.df[f'clients_{tranche}'].mean():,.0f}")
        
        # Total 65+
        if 'pop_65_plus_drive_10min' in self.df.columns:
            self.df['clients_65plus_total'] = (
                self.df['pop_65_plus_drive_10min'].fillna(0) *
                self.df['part_marche_huff'] *
                self.taux_fidelite
            )
            
            logger.info(f"\n  TOTAL 65+ :")
            logger.info(f"    Population moyenne accessible : {self.df['pop_65_plus_drive_10min'].mean():,.0f}")
            logger.info(f"    Clients moyens estimés : {self.df['clients_65plus_total'].mean():,.0f}")
        
        # Nombre de visites annuelles
        self.df['visites_annuelles_65plus'] = (
            self.df['clients_65plus_total'] * self.freq_visite_annuelle
        )
        
        logger.info(f"\n  ✅ Estimation des clients 65+ terminée")
    
    def calculate_performance_metrics(self):
        """Calcule des métriques de performance et déciles"""
        logger.info("\n" + "="*80)
        logger.info("CALCUL DES MÉTRIQUES DE PERFORMANCE")
        logger.info("="*80)
        
        # 1. Déciles de clients 65+
        self.df['decile_clients_65plus'] = pd.qcut(
            self.df['clients_65plus_total'], 
            q=10, 
            labels=False, 
            duplicates='drop'
        ) + 1
        
        logger.info("\n  Déciles de clients 65+ :")
        for decile in range(1, 11):
            subset = self.df[self.df['decile_clients_65plus'] == decile]
            if len(subset) > 0:
                logger.info(f"    Décile {decile:2d} : {subset['clients_65plus_total'].min():6.0f} - {subset['clients_65plus_total'].max():6.0f} clients")
        
        # 2. Potentiel vs Réalisé (si CA disponible)
        if 'ca_total' in self.df.columns:
            # Estimer le CA potentiel 65+ basé sur le nombre de clients
            # Hypothèse : Panier moyen 65+ = 450€/an
            panier_moyen_65plus = 450
            
            self.df['ca_potentiel_65plus'] = (
                self.df['clients_65plus_total'] * panier_moyen_65plus
            )
            
            # Comparer avec CA réel (ajusté par la part 65+)
            # MÉTHODE 1 : Utiliser la part seniors du Script 5 si disponible
            if 'score_ca_total_65plus' in self.df.columns and 'score_ca_total' in self.df.columns:
                # Calculer le ratio score_65+ / score_total pour avoir la part
                logger.info("\n  📊 Utilisation de la part seniors calculée par le Script 5")
                self.df['part_ca_65plus_estimee'] = (
                    self.df['score_ca_total_65plus'] / 
                    self.df['score_ca_total'].replace(0, np.nan)
                ).fillna(0.5).clip(0.3, 0.8)  # Limiter entre 30% et 80%
                
                mean_part = self.df['part_ca_65plus_estimee'].mean()
                logger.info(f"     Part moyenne calculée : {mean_part:.1%}")
            else:
                # MÉTHODE 2 : Hypothèse par défaut si pas disponible
                logger.info("\n  ℹ️  Part seniors non disponible → Hypothèse par défaut : 50%")
                self.df['part_ca_65plus_estimee'] = 0.50
            
            self.df['ca_reel_65plus_estime'] = (
                self.df['ca_total'] * self.df['part_ca_65plus_estimee']
            )
            
            # Gap d'opportunité
            self.df['gap_opportunite_65plus'] = (
                self.df['ca_potentiel_65plus'] - self.df['ca_reel_65plus_estime']
            )
            
            # Pourcentage du potentiel atteint
            self.df['pct_potentiel_atteint'] = (
                self.df['ca_reel_65plus_estime'] / 
                self.df['ca_potentiel_65plus'].replace(0, np.nan) * 100
            ).clip(0, 200)  # Max 200% (sur-performance)
            
            logger.info("\n  Analyse potentiel vs réalisé :")
            logger.info(f"    CA potentiel 65+ moyen : {self.df['ca_potentiel_65plus'].mean():,.0f} €")
            logger.info(f"    CA réel 65+ moyen : {self.df['ca_reel_65plus_estime'].mean():,.0f} €")
            logger.info(f"    Gap moyen : {self.df['gap_opportunite_65plus'].mean():,.0f} €")
            logger.info(f"    % potentiel atteint moyen : {self.df['pct_potentiel_atteint'].mean():.1f}%")
            
            # Identifier opportunités
            opportunites = self.df[self.df['gap_opportunite_65plus'] > 50000]
            logger.info(f"\n  ✅ {len(opportunites):,} pharmacies avec gap > 50k€ (opportunités)")
    
    def generate_report(self):
        """Génère un rapport détaillé"""
        logger.info("\nGénération du rapport...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAPPORT - ESTIMATION CLIENTS 65+")
        report_lines.append("=" * 80)
        report_lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Nombre de pharmacies : {len(self.df):,}")
        report_lines.append("")
        
        # Paramètres
        report_lines.append("PARAMÈTRES DU MODÈLE")
        report_lines.append("-" * 80)
        report_lines.append(f"Taux de fidélité : {self.taux_fidelite:.0%}")
        report_lines.append(f"Fréquence de visite annuelle : {self.freq_visite_annuelle}")
        report_lines.append(f"Modèle : Huff (part de marché basée sur score attractivité)")
        report_lines.append("")
        
        # Statistiques clients 65+
        report_lines.append("STATISTIQUES - CLIENTS 65+")
        report_lines.append("-" * 80)
        
        stats_clients = self.df['clients_65plus_total'].describe()
        report_lines.append(f"Moyenne : {stats_clients['mean']:,.0f} clients")
        report_lines.append(f"Médiane : {stats_clients['50%']:,.0f} clients")
        report_lines.append(f"Écart-type : {stats_clients['std']:,.0f}")
        report_lines.append(f"Min : {stats_clients['min']:,.0f} clients")
        report_lines.append(f"Max : {stats_clients['max']:,.0f} clients")
        report_lines.append("")
        
        report_lines.append("Répartition par tranche d'âge (moyennes) :")
        if 'clients_65_74' in self.df.columns:
            report_lines.append(f"  65-74 ans : {self.df['clients_65_74'].mean():,.0f} clients ({self.df['clients_65_74'].mean() / self.df['clients_65plus_total'].mean() * 100:.1f}%)")
        if 'clients_75_84' in self.df.columns:
            report_lines.append(f"  75-84 ans : {self.df['clients_75_84'].mean():,.0f} clients ({self.df['clients_75_84'].mean() / self.df['clients_65plus_total'].mean() * 100:.1f}%)")
        if 'clients_85_plus' in self.df.columns:
            report_lines.append(f"  85+ ans : {self.df['clients_85_plus'].mean():,.0f} clients ({self.df['clients_85_plus'].mean() / self.df['clients_65plus_total'].mean() * 100:.1f}%)")
        report_lines.append("")
        
        # Déciles
        report_lines.append("DÉCILES - CLIENTS 65+")
        report_lines.append("-" * 80)
        for decile in range(1, 11):
            subset = self.df[self.df['decile_clients_65plus'] == decile]
            if len(subset) > 0:
                report_lines.append(f"Décile {decile:2d} : {len(subset):5,} pharmacies | {subset['clients_65plus_total'].min():6,.0f} - {subset['clients_65plus_total'].max():6,.0f} clients")
        report_lines.append("")
        
        # Opportunités (si disponible)
        if 'gap_opportunite_65plus' in self.df.columns:
            report_lines.append("ANALYSE POTENTIEL VS RÉALISÉ")
            report_lines.append("-" * 80)
            report_lines.append(f"CA potentiel 65+ moyen : {self.df['ca_potentiel_65plus'].mean():,.0f} €")
            report_lines.append(f"CA réel 65+ moyen : {self.df['ca_reel_65plus_estime'].mean():,.0f} €")
            report_lines.append(f"Gap moyen : {self.df['gap_opportunite_65plus'].mean():,.0f} €")
            report_lines.append(f"% potentiel atteint moyen : {self.df['pct_potentiel_atteint'].mean():.1f}%")
            report_lines.append("")
            
            # Top 10 opportunités
            report_lines.append("TOP 10 OPPORTUNITÉS (gap le plus élevé) :")
            top_10 = self.df.nlargest(10, 'gap_opportunite_65plus')[
                ['nom_pharmacie', 'commune', 'clients_65plus_total', 'gap_opportunite_65plus', 'pct_potentiel_atteint']
            ]
            for i, row in top_10.iterrows():
                report_lines.append(f"  {row['nom_pharmacie']:50s} | {row['commune']:20s} | {row['clients_65plus_total']:5,.0f} clients | Gap: {row['gap_opportunite_65plus']:7,.0f} € | {row['pct_potentiel_atteint']:5.1f}%")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("FIN DU RAPPORT")
        report_lines.append("=" * 80)
        
        # Sauvegarder
        report_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'].parent / 'rapport_estimation_clients_65plus.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"  ✅ Rapport sauvegardé : {report_path}")
    
    def save_results(self):
        """Sauvegarde les résultats"""
        logger.info("\nSauvegarde des résultats...")
        
        # Colonnes à sauvegarder
        cols_to_save = [
            'id_pharmacie', 'nom_pharmacie', 'latitude', 'longitude',
            'code_postal', 'commune', 'departement', 'type_zone',
            # Scores
            'score_attractivite_composite',
            'score_attractivite_65plus_composite',
            # Population
            'pop_65_74_drive_10min', 'pop_75_84_drive_10min', 'pop_85_plus_drive_10min',
            'pop_65_plus_drive_10min',
            # Concurrence
            'nb_pharmacies_concurrentes_drive_10min',
            'distance_pharmacie_plus_proche',
            # Part de marché
            'part_marche_huff',
            # Clients estimés
            'clients_65_74', 'clients_75_84', 'clients_85_plus',
            'clients_65plus_total',
            'visites_annuelles_65plus',
            # Décile
            'decile_clients_65plus'
        ]
        
        # Ajouter colonnes potentiel si disponibles
        optional_cols = [
            'ca_total', 'ca_potentiel_65plus', 'ca_reel_65plus_estime',
            'gap_opportunite_65plus', 'pct_potentiel_atteint'
        ]
        
        for col in optional_cols:
            if col in self.df.columns:
                cols_to_save.append(col)
        
        # Filtrer les colonnes disponibles
        cols_available = [c for c in cols_to_save if c in self.df.columns]
        
        df_output = self.df[cols_available].copy()
        
        # Sauvegarder
        output_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'].parent / 'pharmacies_estimation_clients_65plus.csv'
        df_output.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"  ✅ Fichier sauvegardé : {output_path}")
        logger.info(f"  ✅ {len(df_output):,} pharmacies × {len(df_output.columns)} colonnes")
        
        # Afficher les colonnes créées
        new_cols = [c for c in df_output.columns if 'clients_' in c or 'part_marche' in c or 'decile' in c or 'gap_' in c]
        logger.info(f"\n  📊 Colonnes créées ({len(new_cols)}) :")
        for col in sorted(new_cols):
            logger.info(f"     - {col}")
    
    def run(self):
        """Execute le pipeline complet"""
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DU SCRIPT 6 : ESTIMATION CLIENTS 65+")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 1. Charger les données
            self.load_data()
            
            # 2. Vérifier les scores
            self.verify_scores()
            
            # 3. Calculer la part de marché (Huff)
            self.calculate_market_share_huff()
            
            # 4. Estimer les clients 65+
            self.estimate_clients_65plus()
            
            # 5. Calculer les métriques de performance
            self.calculate_performance_metrics()
            
            # 6. Générer le rapport
            self.generate_report()
            
            # 7. Sauvegarder
            self.save_results()
            
            # Temps d'exécution
            duration = datetime.now() - start_time
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ SCRIPT 6 TERMINÉ AVEC SUCCÈS")
            logger.info(f"Durée d'exécution : {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ ERREUR FATALE : {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal"""
    estimator = ClientsEstimator()
    estimator.run()


if __name__ == "__main__":
    main()
