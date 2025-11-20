"""
Script 5 : Calcul du score d'attractivité 65+ via PCA (100% data-driven)

MÉTHODOLOGIE :
1. Sélection automatique des features pertinentes (population, HUBS, concurrence, tourisme)
2. Standardisation des features (mean=0, std=1)
3. PCA (Principal Component Analysis) pour réduction de dimensionnalité
4. Sélection automatique des composantes par variance expliquée (seuil 95%)
5. Score composite = moyenne pondérée des composantes par variance expliquée

AVANTAGES :
- Aucun paramètre codé en dur (sauf seuils mathématiques standards)
- Auto-adaptatif aux données
- Orthogonalité des composantes (pas de redondance)
- Explicable via variance expliquée
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import sys
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

# Ajouter le répertoire config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
    OUTPUT_FILES
)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AttractivityScorePCA:
    """
    Calcule le score d'attractivité via PCA
    """

    def __init__(self, variance_threshold=0.95):
        """
        Args:
            variance_threshold: Seuil de variance expliquée cumulée (défaut: 95%)
        """
        self.variance_threshold = variance_threshold
        self.df = None
        self.features_selected = []
        self.pca = None
        self.scaler = None
        self.imputer = None
        self.n_components = None
        self.variance_explained = None

    def load_data(self):
        """Charge les données"""
        logger.info("="*80)
        logger.info("CHARGEMENT DES DONNÉES")
        logger.info("="*80)

        # Essayer d'abord le fichier enrichi avec CA, sinon SIG_P20, sinon standard
        enriched_ca_file = INTERMEDIATE_FILES['pharmacies_features_complet'].parent / 'pharmacies_features_complet_ca_enriched.csv'
        enriched_sig_file = INTERMEDIATE_FILES['pharmacies_features_complet'].parent / 'pharmacies_features_complet_sig_enriched.csv'

        if enriched_ca_file.exists():
            logger.info(f"   Utilisation du fichier enrichi CA + SIG_P20")
            self.df = pd.read_csv(enriched_ca_file)
        elif enriched_sig_file.exists():
            logger.info(f"   Utilisation du fichier enrichi SIG_P20")
            self.df = pd.read_csv(enriched_sig_file)
        else:
            logger.info(f"   Fichier enrichi non trouvé, utilisation du fichier standard")
            self.df = pd.read_csv(INTERMEDIATE_FILES['pharmacies_features_complet'])

        logger.info(f"   Dataset chargé        : {len(self.df):,} pharmacies")
        logger.info(f"   Features totales      : {len(self.df.columns):,}")

    def select_features(self):
        """
        Sélectionne automatiquement les features pertinentes pour 65+

        Critères de sélection (basés sur le domaine métier) :
        - Population 65+ par isochrone
        - HUBS médicaux par isochrone
        - Concurrence par isochrone
        - Tourisme (hébergements)
        - Variables géographiques/démographiques
        """
        logger.info("\n" + "="*80)
        logger.info("SÉLECTION AUTOMATIQUE DES FEATURES")
        logger.info("="*80)

        # Patterns de features pertinentes
        patterns = [
            'pop_65',           # Population 65+
            'pop_75',           # Population 75+
            'pop_80',           # Population 80+
            'pop_85',           # Population 85+
            'nb_sante',         # HUBS santé
            'nb_ehpad',         # EHPAD
            'nb_hopital',       # Hôpitaux
            'nb_medecin',       # Médecins
            'nb_pharmacies_concurrentes',  # Concurrence
            'hebergements',     # Tourisme
            'capacite_accueil', # Tourisme
            'un_sig_norm',      # Activité réelle (unités) - SIG_P20
            'ca_ethique_norm',  # CA médicaments prescrits normalisé
            'ca_conseil_norm',  # CA OTC + parapharmacie normalisé
            'ca_delta_norm',    # CA résiduel normalisé (total - ethique - conseil)
        ]

        # Sélectionner les colonnes qui matchent les patterns
        selected_cols = []
        for col in self.df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in patterns):
                # Vérifier que c'est une colonne numérique
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    selected_cols.append(col)

        # Ajouter variables géographiques si disponibles
        geo_vars = ['latitude', 'longitude', 'densite_population']
        for var in geo_vars:
            if var in self.df.columns and pd.api.types.is_numeric_dtype(self.df[var]):
                selected_cols.append(var)

        self.features_selected = selected_cols

        logger.info(f"\n  Features sélectionnées : {len(self.features_selected)}")
        logger.info(f"\n  Répartition par type :")

        # Compter par type
        counts = {
            'Population 65+': sum(1 for c in selected_cols if 'pop_6' in c.lower() or 'pop_7' in c.lower() or 'pop_8' in c.lower()),
            'HUBS médicaux': sum(1 for c in selected_cols if any(x in c.lower() for x in ['sante', 'ehpad', 'hopital', 'medecin'])),
            'Concurrence': sum(1 for c in selected_cols if 'concurrente' in c.lower()),
            'Tourisme': sum(1 for c in selected_cols if 'hebergement' in c.lower() or 'capacite' in c.lower()),
            'Activité SIG_P20': sum(1 for c in selected_cols if 'sig_norm' in c.lower()),
            'Activité CA': sum(1 for c in selected_cols if 'ca_' in c.lower() and '_norm' in c.lower()),
            'Géographiques': sum(1 for c in selected_cols if c in geo_vars)
        }

        for type_feat, count in counts.items():
            logger.info(f"     {type_feat:20s} : {count:3d} features")

    def prepare_data(self):
        """
        Prépare les données pour la PCA :
        1. Imputation des valeurs manquantes
        2. Standardisation (mean=0, std=1)
        """
        logger.info("\n" + "="*80)
        logger.info("PRÉPARATION DES DONNÉES")
        logger.info("="*80)

        # Extraire les features sélectionnées
        X = self.df[self.features_selected].copy()

        # 1. Imputation des valeurs manquantes (médiane)
        logger.info(f"\n  1. Imputation des valeurs manquantes")
        logger.info(f"     NaN avant imputation  : {X.isna().sum().sum():,}")

        self.imputer = SimpleImputer(strategy='median')
        X_imputed = self.imputer.fit_transform(X)

        logger.info(f"     NaN après imputation  : 0")

        # 2. Standardisation (mean=0, std=1)
        logger.info(f"\n  2. Standardisation (Z-score)")

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_imputed)

        logger.info(f"     Mean après scaling    : {X_scaled.mean():.6f}")
        logger.info(f"     Std après scaling     : {X_scaled.std():.6f}")

        return X_scaled

    def apply_pca(self, X_scaled):
        """
        Applique la PCA et sélectionne automatiquement le nombre de composantes

        Args:
            X_scaled: Données standardisées

        Returns:
            Composantes principales transformées
        """
        logger.info("\n" + "="*80)
        logger.info("ANALYSE EN COMPOSANTES PRINCIPALES (PCA)")
        logger.info("="*80)

        # Appliquer PCA sur toutes les composantes possibles
        n_features = X_scaled.shape[1]
        self.pca = PCA(n_components=n_features)
        X_pca_full = self.pca.fit_transform(X_scaled)

        # Calculer la variance expliquée cumulée
        cumsum_variance = np.cumsum(self.pca.explained_variance_ratio_)

        # Sélectionner le nombre de composantes pour atteindre le seuil
        self.n_components = np.argmax(cumsum_variance >= self.variance_threshold) + 1

        logger.info(f"\n  Variance expliquée cumulée :")
        logger.info(f"     Seuil cible           : {self.variance_threshold*100:.1f}%")
        logger.info(f"     Composantes retenues  : {self.n_components} / {n_features}")
        logger.info(f"     Variance atteinte     : {cumsum_variance[self.n_components-1]*100:.2f}%")

        # Afficher le détail des 10 premières composantes
        logger.info(f"\n  Détail des composantes principales :")
        logger.info(f"     {'Composante':12s} | {'Variance':>10s} | {'Cumul':>10s}")
        logger.info(f"     {'-'*12:12s} | {'-'*10:10s} | {'-'*10:10s}")

        for i in range(min(10, len(self.pca.explained_variance_ratio_))):
            var = self.pca.explained_variance_ratio_[i]
            cum = cumsum_variance[i]
            marker = " ✓" if i < self.n_components else ""
            logger.info(f"     PC{i+1:2d}          | {var*100:9.2f}% | {cum*100:9.2f}%{marker}")

        # Conserver uniquement les composantes retenues
        X_pca = X_pca_full[:, :self.n_components]
        self.variance_explained = self.pca.explained_variance_ratio_[:self.n_components]

        return X_pca

    def calculate_composite_score(self, X_pca):
        """
        Calcule le score composite comme moyenne pondérée des composantes

        Pondération = variance expliquée de chaque composante

        Args:
            X_pca: Composantes principales

        Returns:
            Score composite normalisé [0, 1]
        """
        logger.info("\n" + "="*80)
        logger.info("CALCUL DU SCORE COMPOSITE")
        logger.info("="*80)

        # Normaliser chaque composante entre 0 et 1
        X_pca_norm = np.zeros_like(X_pca)
        for i in range(self.n_components):
            pc = X_pca[:, i]
            # Normalisation robuste avec percentiles
            q01, q99 = np.percentile(pc, [1, 99])
            pc_clipped = np.clip(pc, q01, q99)
            pc_norm = (pc_clipped - q01) / (q99 - q01 + 1e-10)
            X_pca_norm[:, i] = pc_norm

        # Pondération par variance expliquée
        weights = self.variance_explained / self.variance_explained.sum()

        logger.info(f"\n  Pondérations par composante (variance expliquée) :")
        for i, w in enumerate(weights):
            logger.info(f"     PC{i+1:2d} : {w:.4f} ({w*100:.1f}%)")

        # Score composite = moyenne pondérée
        score_composite = (X_pca_norm * weights).sum(axis=1)

        # Normalisation finale entre 0.1 et 1.0 (éviter 0 pour modèle de Huff)
        score_composite_norm = 0.1 + 0.9 * score_composite

        logger.info(f"\n  Score composite calculé :")
        logger.info(f"     Min   : {score_composite_norm.min():.3f}")
        logger.info(f"     Max   : {score_composite_norm.max():.3f}")
        logger.info(f"     Mean  : {score_composite_norm.mean():.3f}")
        logger.info(f"     Std   : {score_composite_norm.std():.3f}")
        logger.info(f"     Median: {np.median(score_composite_norm):.3f}")

        return score_composite_norm

    def analyze_feature_importance(self):
        """
        Analyse l'importance des features originales dans les composantes principales
        """
        logger.info("\n" + "="*80)
        logger.info("ANALYSE D'IMPORTANCE DES FEATURES")
        logger.info("="*80)

        # Matrice de composantes (features × PC)
        components = self.pca.components_[:self.n_components, :]

        # Calculer l'importance absolue de chaque feature (somme sur toutes les PC pondérée par variance)
        feature_importance = np.zeros(len(self.features_selected))

        for i, var in enumerate(self.variance_explained):
            feature_importance += np.abs(components[i, :]) * var

        # Normaliser
        feature_importance = feature_importance / feature_importance.sum()

        # Créer un dataframe d'importance
        importance_df = pd.DataFrame({
            'feature': self.features_selected,
            'importance': feature_importance
        }).sort_values('importance', ascending=False)

        # Afficher les 20 features les plus importantes
        logger.info(f"\n  Top 20 features les plus importantes :")
        logger.info(f"     {'Rang':4s} | {'Feature':50s} | {'Importance':>10s}")
        logger.info(f"     {'-'*4:4s} | {'-'*50:50s} | {'-'*10:10s}")

        for idx, row in importance_df.head(20).iterrows():
            logger.info(f"     {importance_df.index.get_loc(idx)+1:4d} | {row['feature']:50s} | {row['importance']:9.4f}")

        # Sauvegarder l'importance complète
        importance_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / 'feature_importance_pca.csv'
        importance_path.parent.mkdir(parents=True, exist_ok=True)
        importance_df.to_csv(importance_path, index=False)
        logger.info(f"\n  Importance complète sauvegardée : {importance_path}")

    def save_results(self, score):
        """
        Sauvegarde les résultats

        Args:
            score: Score composite calculé
        """
        logger.info("\n" + "="*80)
        logger.info("SAUVEGARDE DES RÉSULTATS")
        logger.info("="*80)

        # Ajouter le score au dataframe
        self.df['score_attractivite_65plus_composite'] = score

        # Calculer les déciles
        self.df['decile_attractivite'] = pd.qcut(
            score,
            q=10,
            labels=False,
            duplicates='drop'
        ) + 1

        # Sélectionner les colonnes à sauvegarder
        cols_to_save = ['id_pharmacie', 'score_attractivite_65plus_composite', 'decile_attractivite']

        # Ajouter nom pharmacie si disponible
        if 'nom_pharmacie' in self.df.columns:
            cols_to_save.insert(1, 'nom_pharmacie')

        # Ajouter type_zone si disponible
        if 'type_zone' in self.df.columns:
            cols_to_save.append('type_zone')

        df_output = self.df[cols_to_save].copy()

        # Sauvegarder
        output_path = INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite']
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_output.to_csv(output_path, index=False)

        logger.info(f"\n  Fichier sauvegardé    : {output_path}")
        logger.info(f"  Pharmacies totales    : {len(df_output):,}")
        logger.info(f"  Colonnes sauvegardées : {len(cols_to_save)}")

        # Statistiques par décile
        logger.info(f"\n  Distribution par décile :")
        for decile in range(1, 11):
            df_decile = self.df[self.df['decile_attractivite'] == decile]
            score_mean = df_decile['score_attractivite_65plus_composite'].mean()
            logger.info(f"     Décile {decile:2d} : {len(df_decile):5,} pharmacies | Score moyen: {score_mean:.3f}")

    def run(self):
        """Exécute le pipeline complet"""
        logger.info("="*80)
        logger.info("PIPELINE PCA - SCORE D'ATTRACTIVITÉ 65+")
        logger.info("="*80)
        logger.info(f"\nMÉTHODE : 100% data-driven via PCA")
        logger.info(f"  - Aucun paramètre codé en dur (sauf seuils statistiques standards)")
        logger.info(f"  - Auto-adaptatif aux données")
        logger.info(f"  - Composantes orthogonales (pas de redondance)")
        logger.info(f"  - Pondération par variance expliquée")

        # 1. Chargement
        self.load_data()

        # 2. Sélection des features
        self.select_features()

        # 3. Préparation des données
        X_scaled = self.prepare_data()

        # 4. PCA
        X_pca = self.apply_pca(X_scaled)

        # 5. Score composite
        score = self.calculate_composite_score(X_pca)

        # 6. Analyse d'importance
        self.analyze_feature_importance()

        # 7. Sauvegarde
        self.save_results(score)

        logger.info("\n" + "="*80)
        logger.info("OK - PIPELINE TERMINÉ")
        logger.info("="*80)


if __name__ == "__main__":
    # Créer l'instance et exécuter
    scorer = AttractivityScorePCA(variance_threshold=0.95)
    scorer.run()