"""
Script de validation data quality pour le pipeline de scoring pharmacies 65+
=============================================================================

Ce script valide la qualité des données à chaque étape critique du pipeline :
- Scripts 1-3 : Validations critiques (données brutes → features)
- Scripts 4-7 : Validations de transformation (feature engineering → ML)
- Scripts 8-14 : Monitoring des métriques ML

Auteur : Victoire LOUIS
Date : Novembre 2025
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import json
from datetime import datetime
import warnings
import argparse
warnings.filterwarnings('ignore')

# =============================================================================
# FONCTION HELPER POUR LIRE LES CSV
# =============================================================================

def read_csv_auto_sep(filepath):
    """
    Lit un CSV en détectant automatiquement le séparateur (virgule ou point-virgule)
    
    Args:
        filepath: Chemin du fichier CSV
    
    Returns:
        DataFrame pandas
    """
    try:
        # Essayer d'abord avec point-virgule (format standard du projet)
        df = pd.read_csv(filepath, sep=';', nrows=5)
        # Si ça a créé une seule colonne, c'est le mauvais séparateur
        if len(df.columns) == 1:
            df = pd.read_csv(filepath, sep=',')
        else:
            df = pd.read_csv(filepath, sep=';')
        return df
    except:
        # Fallback sur virgule
        return pd.read_csv(filepath, sep=',')

# =============================================================================
# CONFIGURATION DES CHEMINS
# =============================================================================

BASE_PATH = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
OUTPUT_PATH = BASE_PATH / "intermediaire" / "output"
SCRIPT_PATH = BASE_PATH / "intermediaire" / "scripts"

# Fichiers à valider
FILES = {
    # Script 1 : Variables hubs par isochrone
    "script1_hubs": OUTPUT_PATH / "pharmacies_avec_hubs.csv",
    
    # Script 2 : Variables concurrence
    "script2_competition": OUTPUT_PATH / "pharmacies_avec_concurrence.csv",
    
    # Script 3 : Variables population isochrones
    "script3_population": OUTPUT_PATH / "pharmacies_avec_population_isochrones.csv",
    
    # Script 4 : Intégration complète
    "script4_integration": OUTPUT_PATH / "pharmacies_features_complet.csv",
    
    # Script 5 : Feature engineering
    "script5_features": OUTPUT_PATH / "pharmacies_features_engineered.csv",
    
    # Script 6 : Sélection features
    "script6_selection": OUTPUT_PATH / "pharmacies_features_selected.csv",
    
    # Script 7 : Split train/test
    "script7_train": OUTPUT_PATH / "train.csv",
    "script7_test": OUTPUT_PATH / "test.csv",
    
    # Script 8 : Baseline models
    "script8_models": OUTPUT_PATH / "baseline_model_results.json",
    
    # Script 9 : LightGBM optimized
    "script9_lightgbm": OUTPUT_PATH / "lightgbm_model_results.json",
    
    # Script 10 : Évaluation finale
    "script10_evaluation": OUTPUT_PATH / "evaluation_results.json",
    
    # Script 11 : Interprétabilité SHAP
    "script11_shap": OUTPUT_PATH / "shap_values.csv",
    
    # Script 12 : Prédictions finales
    "script12_predictions": OUTPUT_PATH / "predictions_finales.csv",
    
    # Script 13 : Analyse segmentée
    "script13_analyse": OUTPUT_PATH / "analyse_segmentee.csv",
    
    # Script 14 : Rapport final
    "script14_rapport": OUTPUT_PATH / "rapport_final.json"
}

# Noms réels des scripts (pour référence)
SCRIPT_NAMES = {
    1: "ml_01_prepare_hubs_par_isochrone",
    2: "ml_02_prepare_concurrence",
    3: "ml_03_prepare_population_isochrones",
    4: "ml_04_integration_complete",
    5: "ml_05_feature_engineering",
    6: "ml_06_selection_features",
    7: "ml_07_split_train_test",
    8: "ml_08_baseline_models",
    9: "ml_09_lightgbm_optimized",
    10: "ml_10_evaluation_finale",
    11: "ml_11_interpretabilite_shap",
    12: "ml_12_predictions_finales",
    13: "ml_13_analyse_segmentee",
    14: "ml_14_rapport_final"
}

# =============================================================================
# CLASSE DE VALIDATION
# =============================================================================

class DataQualityValidator:
    """Classe pour valider la qualité des données du pipeline"""
    
    def __init__(self):
        """Initialise le validateur"""
        self.results = {}  # Stocke les résultats de validation
        self.errors = []   # Stocke les erreurs critiques
        self.warnings = [] # Stocke les avertissements
        
    def log_result(self, test_name, passed, message="", is_critical=False):
        """
        Enregistre le résultat d'un test
        
        Args:
            test_name: Nom du test
            passed: True si le test est passé, False sinon
            message: Message descriptif
            is_critical: True si l'échec est critique
        """
        result = {
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "critical": is_critical
        }
        
        self.results[test_name] = result
        
        # Ajoute aux erreurs ou warnings
        if not passed:
            if is_critical:
                self.errors.append(f"❌ CRITIQUE - {test_name}: {message}")
            else:
                self.warnings.append(f"⚠️ WARNING - {test_name}: {message}")
        else:
            print(f"✅ {test_name}")
    
    # =========================================================================
    # VALIDATIONS SCRIPT 1 : VARIABLES HUBS
    # =========================================================================
    
    def validate_script1_hubs(self):
        """Valide la sortie du Script 1 (variables hubs)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 1 : VARIABLES HUBS")
        print("="*80)
        
        try:
            # Charge le fichier
            df = read_csv_auto_sep(FILES["script1_hubs"])
            
            # Test 1 : Nombre de pharmacies (doit être ~20,000)
            n_pharmacies = len(df)
            passed = 19000 <= n_pharmacies <= 21000
            self.log_result(
                "S1_count_pharmacies",
                passed,
                f"Nombre de pharmacies : {n_pharmacies:,} (attendu : ~20,000)",
                is_critical=True
            )
            
            # Test 2 : Colonnes obligatoires présentes
            required_cols = ["id_pharmacie", "latitude", "longitude"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            passed = len(missing_cols) == 0
            self.log_result(
                "S1_required_columns",
                passed,
                f"Colonnes manquantes : {missing_cols}" if not passed else "Toutes les colonnes requises présentes",
                is_critical=True
            )
            
            # Test 3 : Variables hubs créées (par type d'isochrone)
            # Le script 1 crée des variables par FAMILLE de hubs et par catégorie détaillée
            isochrone_types = ["walk_5min", "drive_10min"]
            
            # Familles de hubs
            hub_families = ["sante_generale", "sante_specialisee", "services_seniors", "accessibilite"]
            
            # Catégories détaillées
            hub_details = ["medecin", "ehpad", "hopital", "laboratoire", "supermarche", "bus"]
            
            # Métriques
            hub_metrics = ["nb_hubs_brut", "nb_hubs_deduplique", "taux_colocalisation"]
            
            expected_hub_cols = []
            for iso in isochrone_types:
                # Familles
                for family in hub_families:
                    expected_hub_cols.append(f"nb_{family}_{iso}")
                # Détails
                for detail in hub_details:
                    expected_hub_cols.append(f"nb_{detail}_{iso}")
                # Métriques
                for metric in hub_metrics:
                    expected_hub_cols.append(f"{metric}_{iso}")
            
            missing_hub_cols = [col for col in expected_hub_cols if col not in df.columns]
            passed = len(missing_hub_cols) == 0
            self.log_result(
                "S1_hub_variables",
                passed,
                f"{len(expected_hub_cols) - len(missing_hub_cols)}/{len(expected_hub_cols)} variables hubs créées" + 
                (f" - Manquantes: {missing_hub_cols[:5]}" if not passed else ""),
                is_critical=True
            )
            
            # Test 4 : Pas de valeurs négatives dans les comptages
            hub_cols = [col for col in df.columns if col.startswith("nb_")]
            negative_values = (df[hub_cols] < 0).any().any()
            passed = not negative_values
            self.log_result(
                "S1_no_negative_values",
                passed,
                "Valeurs négatives détectées dans les comptages de hubs" if not passed else "Pas de valeurs négatives",
                is_critical=True
            )
            
            # Test 5 : Distribution des valeurs (sanity check)
            # Par exemple, chaque pharmacie devrait avoir au moins quelques hubs dans drive_10min
            df_check = df[[col for col in df.columns if "drive_10min" in col and col.startswith("nb_") and "brut" not in col and "deduplique" not in col]]
            total_hubs_10min = df_check.sum(axis=1)
            pharmacies_sans_hubs = (total_hubs_10min == 0).sum()
            passed = pharmacies_sans_hubs < 100  # Moins de 100 pharmacies sans aucun hub en 10min
            self.log_result(
                "S1_hub_distribution",
                passed,
                f"{pharmacies_sans_hubs} pharmacies sans hubs en drive_10min (suspect si > 100)",
                is_critical=False
            )
            
            # Test 6 : Valeurs manquantes dans les coordonnées
            missing_coords = df[["latitude", "longitude"]].isna().any(axis=1).sum()
            passed = missing_coords == 0
            self.log_result(
                "S1_missing_coordinates",
                passed,
                f"{missing_coords} pharmacies sans coordonnées" if not passed else "Toutes les pharmacies géocodées",
                is_critical=True
            )
            
        except FileNotFoundError:
            self.log_result(
                "S1_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script1_hubs']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S1_general_error",
                False,
                f"Erreur lors de la validation : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 2 : VARIABLES CONCURRENCE
    # =========================================================================
    
    def validate_script2_competition(self):
        """Valide la sortie du Script 2 (variables concurrence)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 2 : VARIABLES CONCURRENCE")
        print("="*80)
        
        try:
            df = read_csv_auto_sep(FILES["script2_competition"])
            
            # Test 1 : Même nombre de pharmacies que Script 1
            if "script1_hubs" in self.results and self.results["script1_hubs"]["passed"]:
                df1 = pd.read_csv(FILES["script1_hubs"])
                passed = len(df) == len(df1)
                self.log_result(
                    "S2_same_pharmacy_count",
                    passed,
                    f"Script 2 : {len(df)} pharmacies vs Script 1 : {len(df1)} pharmacies",
                    is_critical=True
                )
            
            # Test 2 : Variables concurrence créées
            isochrone_types = ["walk_5min", "drive_10min"]
            expected_comp_cols = [f"nb_pharmacies_concurrentes_{iso}" for iso in isochrone_types]
            expected_comp_cols.append("distance_pharmacie_plus_proche")
            
            missing_comp_cols = [col for col in expected_comp_cols if col not in df.columns]
            passed = len(missing_comp_cols) == 0
            self.log_result(
                "S2_competition_variables",
                passed,
                f"{len(expected_comp_cols) - len(missing_comp_cols)}/{len(expected_comp_cols)} variables concurrence créées",
                is_critical=True
            )
            
            # Test 3 : Distribution de la concurrence (sanity check)
            # La plupart des pharmacies devraient avoir des concurrents en drive_10min
            if "nb_pharmacies_concurrentes_drive_10min" in df.columns:
                pharmacies_isolees = (df["nb_pharmacies_concurrentes_drive_10min"] == 0).sum()
                pct_isolees = (pharmacies_isolees / len(df)) * 100
                passed = pct_isolees < 10  # Moins de 10% de pharmacies totalement isolées
                self.log_result(
                    "S2_isolation_check",
                    passed,
                    f"{pct_isolees:.1f}% pharmacies sans concurrent en drive_10min (attendu < 10%)",
                    is_critical=False
                )
            
            # Test 4 : Cohérence des isochrones (walk_5min <= drive_10min)
            walk_col = "nb_pharmacies_concurrentes_walk_5min"
            drive_col = "nb_pharmacies_concurrentes_drive_10min"
            
            if walk_col in df.columns and drive_col in df.columns:
                # Vérifie que drive_10min contient au moins autant de concurrents que walk_5min
                coherent = (df[walk_col] <= df[drive_col]).all()
                
                passed = coherent
                self.log_result(
                    "S2_isochrone_coherence",
                    passed,
                    "Incohérence détectée : walk_5min > drive_10min" if not passed else "Cohérence des isochrones OK",
                    is_critical=False
                )
            
        except FileNotFoundError:
            self.log_result(
                "S2_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script2_competition']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S2_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 3 : VARIABLES POPULATION
    # =========================================================================
    
    def validate_script3_population(self):
        """Valide la sortie du Script 3 (variables population)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 3 : VARIABLES POPULATION")
        print("="*80)
        
        try:
            df = pd.read_csv(FILES["script3_population"])
            
            # Test 1 : Même nombre de pharmacies
            if "script1_hubs" in self.results and self.results["script1_hubs"]["passed"]:
                df1 = pd.read_csv(FILES["script1_hubs"])
                passed = len(df) == len(df1)
                self.log_result(
                    "S3_same_pharmacy_count",
                    passed,
                    f"Script 3 : {len(df)} pharmacies",
                    is_critical=True
                )
            
            # Test 2 : Variables population créées
            isochrone_types = ["walk_5min", "drive_10min"]
            # Variables par isochrone: pop_totale, pop_65_74, pop_75_84, pop_85_plus, pop_65_plus,
            # pop_hommes_65_74, pop_hommes_75_84, pop_hommes_85_plus, pop_hommes_65_plus,
            # pop_femmes_65_74, pop_femmes_75_84, pop_femmes_85_plus, pop_femmes_65_plus,
            # taux_retraites, taux_cadres
            # Total: 15 variables x 2 isochrones = 30 variables
            
            expected_pop_cols = []
            for iso in isochrone_types:
                expected_pop_cols.extend([
                    f"pop_totale_{iso}",
                    f"pop_65_74_{iso}",
                    f"pop_75_84_{iso}",
                    f"pop_85_plus_{iso}",
                    f"pop_65_plus_{iso}",
                    f"pop_hommes_65_74_{iso}",
                    f"pop_hommes_75_84_{iso}",
                    f"pop_hommes_85_plus_{iso}",
                    f"pop_hommes_65_plus_{iso}",
                    f"pop_femmes_65_74_{iso}",
                    f"pop_femmes_75_84_{iso}",
                    f"pop_femmes_85_plus_{iso}",
                    f"pop_femmes_65_plus_{iso}",
                    f"taux_retraites_{iso}",
                    f"taux_cadres_{iso}"
                ])
            
            missing_pop_cols = [col for col in expected_pop_cols if col not in df.columns]
            passed = len(missing_pop_cols) == 0
            self.log_result(
                "S3_population_variables",
                passed,
                f"{len(expected_pop_cols) - len(missing_pop_cols)}/{len(expected_pop_cols)} variables population créées",
                is_critical=True
            )
            
            # Test 3 : Pas de valeurs négatives
            pop_cols = [col for col in df.columns if col.startswith("pop_")]
            negative_values = (df[pop_cols] < 0).any().any()
            passed = not negative_values
            self.log_result(
                "S3_no_negative_population",
                passed,
                "Valeurs négatives dans la population" if not passed else "Pas de valeurs négatives",
                is_critical=True
            )
            
            # Test 4 : Distribution de la population (sanity check)
            # Note: Avec age_profession.CSV, seulement 8170 IRIS sur 48512 ont des donnees
            # Donc ~80% des pharmacies peuvent avoir 0 population (normal avec donnees partielles)
            if "pop_65_plus_drive_10min" in df.columns:
                pharmacies_avec_pop = (df["pop_65_plus_drive_10min"] > 0).sum()
                pct_avec_pop = pharmacies_avec_pop / len(df) * 100
                
                passed = pct_avec_pop >= 10  # Au moins 10% avec population
                self.log_result(
                    "S3_population_coverage",
                    passed,
                    f"{pharmacies_avec_pop} pharmacies avec population 65+ en drive_10min ({pct_avec_pop:.1f}%)",
                    is_critical=False  # Non critique car dependant de la couverture IRIS source
                )
            
            # Test 5 : Cohérence des isochrones (population croissante: walk_5min <= drive_10min)
            if "pop_65_plus_walk_5min" in df.columns and "pop_65_plus_drive_10min" in df.columns:
                coherent = (df["pop_65_plus_walk_5min"] <= df["pop_65_plus_drive_10min"]).sum()
                pct_coherent = coherent / len(df) * 100
                
                passed = pct_coherent >= 95  # Au moins 95% coherent
                self.log_result(
                    "S3_population_coherence",
                    passed,
                    f"{pct_coherent:.1f}% des pharmacies ont walk_5min <= drive_10min" if passed else "Population walk_5min > drive_10min pour certaines pharmacies",
                    is_critical=False
                )
            
            # Test 6 : Valeurs aberrantes (outliers)
            if "pop_65plus_drive_20min" in df.columns:
                Q1 = df["pop_65plus_drive_20min"].quantile(0.25)
                Q3 = df["pop_65plus_drive_20min"].quantile(0.75)
                IQR = Q3 - Q1
                outliers = ((df["pop_65plus_drive_20min"] < (Q1 - 3*IQR)) | 
                           (df["pop_65plus_drive_20min"] > (Q3 + 3*IQR))).sum()
                
                pct_outliers = (outliers / len(df)) * 100
                passed = pct_outliers < 1  # Moins de 1% d'outliers extrêmes
                self.log_result(
                    "S3_outliers_check",
                    passed,
                    f"{pct_outliers:.2f}% pharmacies avec population aberrante (>3 IQR)",
                    is_critical=False
                )
                
        except FileNotFoundError:
            self.log_result(
                "S3_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script3_population']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S3_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 4 : INTÉGRATION
    # =========================================================================
    
    def validate_script4_integration(self):
        """Valide la sortie du Script 4 (intégration des features)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 4 : INTÉGRATION")
        print("="*80)
        
        try:
            df = pd.read_csv(FILES["script4_integration"])
            
            # Test 1 : Toutes les variables des scripts 1-3 sont présentes
            # Charge les 3 fichiers précédents
            df1 = pd.read_csv(FILES["script1_hubs"])
            df2 = pd.read_csv(FILES["script2_competition"])
            df3 = pd.read_csv(FILES["script3_population"])
            
            # Variables attendues (toutes sauf les colonnes clés dupliquées)
            expected_cols = set(df1.columns) | set(df2.columns) | set(df3.columns)
            actual_cols = set(df.columns)
            
            missing_cols = expected_cols - actual_cols
            passed = len(missing_cols) == 0
            self.log_result(
                "S4_all_features_integrated",
                passed,
                f"{len(actual_cols)} variables présentes, {len(missing_cols)} manquantes" if not passed else "Toutes les features intégrées",
                is_critical=True
            )
            
            # Test 2 : Pas de perte de pharmacies lors du merge
            n_pharmacies = len(df)
            n_expected = len(df1)
            passed = n_pharmacies == n_expected
            self.log_result(
                "S4_no_pharmacy_loss",
                passed,
                f"{n_pharmacies} pharmacies (attendu {n_expected})",
                is_critical=True
            )
            
            # Test 3 : Variables target présentes (ca_total, ca_ethique, ca_conseil, delta)
            target_vars = ["ca_total", "ca_ethique", "ca_conseil", "delta"]
            missing_targets = [var for var in target_vars if var not in df.columns]
            passed = len(missing_targets) == 0
            self.log_result(
                "S4_target_variables",
                passed,
                f"Variables target manquantes : {missing_targets}" if not passed else "Variables target OK",
                is_critical=True
            )
            
            # Test 4 : Pas de valeurs manquantes excessives
            missing_pct = (df.isna().sum() / len(df)) * 100
            cols_with_high_missing = missing_pct[missing_pct > 20].index.tolist()
            passed = len(cols_with_high_missing) == 0
            self.log_result(
                "S4_missing_values",
                passed,
                f"{len(cols_with_high_missing)} colonnes avec >20% valeurs manquantes" if not passed else "Taux de complétion OK",
                is_critical=False
            )
            
        except FileNotFoundError:
            self.log_result(
                "S4_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script4_integration']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S4_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 5 : FEATURE ENGINEERING
    # =========================================================================
    
    def validate_script5_features(self):
        """Valide la sortie du Script 5 (feature engineering)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 5 : FEATURE ENGINEERING")
        print("="*80)
        
        try:
            df = pd.read_csv(FILES["script5_features"])
            df_before = pd.read_csv(FILES["script4_integration"])
            
            # Test 1 : Nouvelles features créées
            new_cols = set(df.columns) - set(df_before.columns)
            passed = len(new_cols) > 0
            self.log_result(
                "S5_new_features_created",
                passed,
                f"{len(new_cols)} nouvelles features créées",
                is_critical=True
            )
            
            # Test 2 : Pas de features infinies ou NaN suite aux transformations
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            has_inf = np.isinf(df[numeric_cols]).any().any()
            passed = not has_inf
            self.log_result(
                "S5_no_infinite_values",
                passed,
                "Valeurs infinies détectées (division par zéro?)" if not passed else "Pas de valeurs infinies",
                is_critical=True
            )
            
            # Test 3 : Features de ratio cohérentes (entre 0 et 1 si c'est des pourcentages)
            ratio_cols = [col for col in df.columns if "ratio" in col.lower() or "pct" in col.lower()]
            if len(ratio_cols) > 0:
                ratios_valides = ((df[ratio_cols] >= 0) & (df[ratio_cols] <= 1)).all().all()
                passed = ratios_valides
                self.log_result(
                    "S5_ratio_coherence",
                    passed,
                    "Ratios hors limites [0,1] détectés" if not passed else f"{len(ratio_cols)} ratios cohérents",
                    is_critical=False
                )
            
            # Test 4 : Variance non nulle (pas de colonnes constantes)
            zero_variance_cols = df[numeric_cols].var() == 0
            n_zero_var = zero_variance_cols.sum()
            passed = n_zero_var == 0
            self.log_result(
                "S5_non_zero_variance",
                passed,
                f"{n_zero_var} colonnes avec variance nulle (inutiles pour ML)" if not passed else "Toutes les features ont de la variance",
                is_critical=False
            )
            
        except FileNotFoundError:
            self.log_result(
                "S5_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script5_features']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S5_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 6 : SÉLECTION FEATURES
    # =========================================================================
    
    def validate_script6_selection(self):
        """Valide la sortie du Script 6 (sélection de features)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 6 : SÉLECTION FEATURES")
        print("="*80)
        
        try:
            df = pd.read_csv(FILES["script6_selection"])
            df_before = pd.read_csv(FILES["script5_features"])
            
            # Test 1 : Réduction du nombre de features
            n_features_before = len(df_before.columns)
            n_features_after = len(df.columns)
            reduction_pct = ((n_features_before - n_features_after) / n_features_before) * 100
            
            passed = n_features_after < n_features_before
            self.log_result(
                "S6_feature_reduction",
                passed,
                f"Features : {n_features_before} → {n_features_after} (-{reduction_pct:.1f}%)",
                is_critical=False
            )
            
            # Test 2 : Variables target toujours présentes
            target_vars = ["ca_total", "ca_ethique", "ca_conseil", "delta"]
            missing_targets = [var for var in target_vars if var not in df.columns]
            passed = len(missing_targets) == 0
            self.log_result(
                "S6_targets_preserved",
                passed,
                f"Variables target perdues : {missing_targets}" if not passed else "Variables target préservées",
                is_critical=True
            )
            
            # Test 3 : Pas de multicolinéarité excessive dans les features sélectionnées
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col not in target_vars]
            
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr().abs()
                # Masque la diagonale
                np.fill_diagonal(corr_matrix.values, 0)
                # Compte les paires avec corrélation > 0.95
                high_corr = (corr_matrix > 0.95).sum().sum() / 2  # Divise par 2 car symétrique
                
                passed = high_corr < 5  # Moins de 5 paires hautement corrélées
                self.log_result(
                    "S6_multicollinearity",
                    passed,
                    f"{int(high_corr)} paires de features avec corrélation > 0.95",
                    is_critical=False
                )
            
        except FileNotFoundError:
            self.log_result(
                "S6_file_exists",
                False,
                f"Fichier non trouvé : {FILES['script6_selection']}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S6_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # VALIDATIONS SCRIPT 7 : SPLIT TRAIN/TEST
    # =========================================================================
    
    def validate_script7_split(self):
        """Valide la sortie du Script 7 (split train/test)"""
        print("\n" + "="*80)
        print("VALIDATION SCRIPT 7 : SPLIT TRAIN/TEST")
        print("="*80)
        
        try:
            df_train = pd.read_csv(FILES["script7_train"])
            df_test = pd.read_csv(FILES["script7_test"])
            df_full = pd.read_csv(FILES["script6_selection"])
            
            # Test 1 : Pas de perte de données
            n_total = len(df_train) + len(df_test)
            n_expected = len(df_full)
            passed = n_total == n_expected
            self.log_result(
                "S7_no_data_loss",
                passed,
                f"Total : {n_total} (attendu {n_expected})",
                is_critical=True
            )
            
            # Test 2 : Ratio train/test cohérent (attendu ~80/20)
            pct_train = (len(df_train) / n_total) * 100
            pct_test = (len(df_test) / n_total) * 100
            passed = 70 <= pct_train <= 85  # Tolérance de 70-85% pour train
            self.log_result(
                "S7_split_ratio",
                passed,
                f"Train : {pct_train:.1f}% / Test : {pct_test:.1f}%",
                is_critical=False
            )
            
            # Test 3 : Pas de fuite de données (pas d'intersection entre train et test)
            if "finess" in df_train.columns and "finess" in df_test.columns:
                train_ids = set(df_train["finess"])
                test_ids = set(df_test["finess"])
                overlap = train_ids & test_ids
                
                passed = len(overlap) == 0
                self.log_result(
                    "S7_no_data_leakage",
                    passed,
                    f"{len(overlap)} pharmacies présentes dans train ET test" if not passed else "Pas de fuite de données",
                    is_critical=True
                )
            
            # Test 4 : Distribution des targets similaire entre train et test
            target_vars = ["CA_total", "CA_ethique", "CA_conseil", "CA_delta"]
            distributions_ok = True
            
            for target in target_vars:
                if target in df_train.columns and target in df_test.columns:
                    mean_train = df_train[target].mean()
                    mean_test = df_test[target].mean()
                    # Vérifie que les moyennes sont dans une marge de 20%
                    diff_pct = abs((mean_test - mean_train) / mean_train) * 100
                    if diff_pct > 20:
                        distributions_ok = False
                        break
            
            passed = distributions_ok
            self.log_result(
                "S7_target_distribution",
                passed,
                "Distribution des targets trop différente entre train/test" if not passed else "Distribution similaire",
                is_critical=False
            )
            
        except FileNotFoundError as e:
            self.log_result(
                "S7_file_exists",
                False,
                f"Fichier non trouvé : {e.filename}",
                is_critical=True
            )
        except Exception as e:
            self.log_result(
                "S7_general_error",
                False,
                f"Erreur : {str(e)}",
                is_critical=True
            )
    
    # =========================================================================
    # MONITORING SCRIPTS ML (8-14)
    # =========================================================================
    
    def monitor_ml_metrics(self):
        """Monitore les métriques ML des scripts 8-14"""
        print("\n" + "="*80)
        print("MONITORING SCRIPTS ML (8-14)")
        print("="*80)
        
        try:
            # Charge les résultats du modèle (Script 8)
            with open(FILES["script8_models"], "r") as f:
                results = json.load(f)
            
            # Test 1 : MAE raisonnable (< 30% de la moyenne du CA)
            if "mae_test" in results:
                mae = results["mae_test"]
                # Estime la moyenne du CA (à adapter selon vos données)
                mean_ca = results.get("mean_ca_total", 500000)  # Valeur par défaut
                mae_pct = (mae / mean_ca) * 100
                
                passed = mae_pct < 30
                self.log_result(
                    "ML_mae_reasonable",
                    passed,
                    f"MAE = {mae:,.0f}€ ({mae_pct:.1f}% du CA moyen)",
                    is_critical=False
                )
            
            # Test 2 : R² acceptable (> 0.6)
            if "r2_test" in results:
                r2 = results["r2_test"]
                passed = r2 > 0.6
                self.log_result(
                    "ML_r2_acceptable",
                    passed,
                    f"R² = {r2:.3f} (attendu > 0.60)",
                    is_critical=False
                )
            
            # Test 3 : Pas d'overfitting (écart train/test < 10%)
            if "mae_train" in results and "mae_test" in results:
                mae_train = results["mae_train"]
                mae_test = results["mae_test"]
                gap_pct = ((mae_test - mae_train) / mae_train) * 100
                
                passed = gap_pct < 10
                self.log_result(
                    "ML_no_overfitting",
                    passed,
                    f"Écart MAE train/test : {gap_pct:.1f}% (attendu < 10%)",
                    is_critical=False
                )
            
            print("\n📊 Métriques ML enregistrées - Voir fichier JSON pour détails complets")
            
        except FileNotFoundError:
            print("⚠️ Fichier résultats ML non trouvé (normal si modèle pas encore entraîné)")
        except Exception as e:
            print(f"⚠️ Erreur lors du monitoring ML : {str(e)}")
    
    # =========================================================================
    # GÉNÉRATION DU RAPPORT
    # =========================================================================
    
    def generate_report(self):
        """Génère un rapport de validation complet"""
        print("\n" + "="*80)
        print("RAPPORT DE VALIDATION DATA QUALITY")
        print("="*80)
        
        # Compte les résultats
        n_total = len(self.results)
        n_passed = sum(1 for r in self.results.values() if r["passed"])
        n_failed = n_total - n_passed
        n_critical_failed = len(self.errors)
        
        print(f"\n📊 RÉSUMÉ")
        print(f"  Total tests : {n_total}")
        print(f"  ✅ Réussis : {n_passed} ({(n_passed/n_total)*100:.1f}%)")
        print(f"  ❌ Échoués : {n_failed} ({(n_failed/n_total)*100:.1f}%)")
        print(f"  🚨 Erreurs critiques : {n_critical_failed}")
        
        # Affiche les erreurs
        if len(self.errors) > 0:
            print(f"\n🚨 ERREURS CRITIQUES ({len(self.errors)})")
            print("-" * 80)
            for error in self.errors:
                print(f"  {error}")
        
        # Affiche les warnings
        if len(self.warnings) > 0:
            print(f"\n⚠️ AVERTISSEMENTS ({len(self.warnings)})")
            print("-" * 80)
            for warning in self.warnings:
                print(f"  {warning}")
        
        # Verdict final
        print("\n" + "="*80)
        if n_critical_failed == 0:
            print("✅ VALIDATION RÉUSSIE - Pipeline prêt pour ML")
        else:
            print("❌ VALIDATION ÉCHOUÉE - Corriger les erreurs critiques avant de continuer")
        print("="*80)
        
        # Sauvegarde le rapport en JSON
        report_path = OUTPUT_PATH / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convertir les types numpy en types Python natifs pour JSON
        def convert_numpy(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": int(n_total),
                    "passed": int(n_passed),
                    "failed": int(n_failed),
                    "critical_errors": int(n_critical_failed)
                },
                "results": convert_numpy(self.results),
                "errors": self.errors,
                "warnings": self.warnings
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Rapport sauvegardé : {report_path}")
        
        return n_critical_failed == 0

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main(steps=None):
    """
    Fonction principale d'exécution de la validation
    
    Args:
        steps: Liste des étapes à valider (ex: [1, 2, 3])
               Si None, valide toutes les étapes
    """
    print("\n" + "="*80)
    print("VALIDATION DATA QUALITY - PIPELINE SCORING PHARMACIES 65+")
    print("="*80)
    print(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Chemin base : {BASE_PATH}")
    
    # Si aucune étape spécifiée, valide tout
    if steps is None:
        steps = list(range(1, 15))  # Scripts 1-14
        print("Mode : VALIDATION COMPLÈTE (tous les scripts)")
    else:
        print(f"Mode : VALIDATION CIBLÉE (scripts {', '.join(map(str, steps))})")
    
    # Crée le validateur
    validator = DataQualityValidator()
    
    # Exécute les validations selon les étapes demandées
    if 1 in steps:
        validator.validate_script1_hubs()
    
    if 2 in steps:
        validator.validate_script2_competition()
    
    if 3 in steps:
        validator.validate_script3_population()
    
    if 4 in steps:
        validator.validate_script4_integration()
    
    if 5 in steps:
        validator.validate_script5_features()
    
    if 6 in steps:
        validator.validate_script6_selection()
    
    if 7 in steps:
        validator.validate_script7_split()
    
    # Monitoring ML (scripts 8-14 groupés)
    if any(step in steps for step in range(8, 15)):
        validator.monitor_ml_metrics()
    
    # Génère le rapport final
    success = validator.generate_report()
    
    return success

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    # Parse les arguments de ligne de commande
    parser = argparse.ArgumentParser(
        description="Validation data quality pour le pipeline scoring pharmacies 65+",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python validation_data_quality_complete.py                    # Valide TOUT
  python validation_data_quality_complete.py --step 1           # Valide Script 1 uniquement
  python validation_data_quality_complete.py --step 1 2 3       # Valide Scripts 1, 2 et 3
  python validation_data_quality_complete.py --step 1-3         # Valide Scripts 1 à 3
  python validation_data_quality_complete.py --step 1-3 5 7     # Valide Scripts 1-3, 5 et 7
  python validation_data_quality_complete.py --step ml          # Valide uniquement ML (8-14)
        """
    )
    
    parser.add_argument(
        '--step', '--steps',
        nargs='+',
        help='Numéros des scripts à valider (ex: 1, 2, 3 ou 1-3 ou ml pour 8-14)'
    )
    
    args = parser.parse_args()
    
    # Parse les étapes demandées
    steps_to_validate = None
    
    if args.step:
        steps_to_validate = []
        for item in args.step:
            # Gère les alias
            if item.lower() == 'ml':
                steps_to_validate.extend(range(8, 15))  # Scripts 8-14
            elif item.lower() == 'all':
                steps_to_validate = None  # Valide tout
                break
            # Gère les ranges (ex: 1-3)
            elif '-' in item:
                try:
                    start, end = map(int, item.split('-'))
                    steps_to_validate.extend(range(start, end + 1))
                except ValueError:
                    print(f"⚠️ Format invalide pour range: {item}")
                    exit(1)
            # Gère les nombres simples
            else:
                try:
                    steps_to_validate.append(int(item))
                except ValueError:
                    print(f"⚠️ Valeur invalide: {item}")
                    exit(1)
        
        # Enlève les doublons et trie
        if steps_to_validate:
            steps_to_validate = sorted(set(steps_to_validate))
    
    # Exécute la validation
    success = main(steps=steps_to_validate)
    exit(0 if success else 1)
