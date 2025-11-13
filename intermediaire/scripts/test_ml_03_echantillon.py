"""
Script de TEST pour ml_03 sur un petit échantillon
===================================================

Teste le calcul de population pour les 6 isochrones sur 10 pharmacies seulement.
Permet de vérifier que tout fonctionne avant de lancer le calcul complet.

Durée estimée : 2-3 minutes

Auteur : Test ml_03
Date : 2025-11-12
"""

import pandas as pd
from pathlib import Path
import sys

# Ajouter le répertoire des scripts au path pour import
PROJECT_ROOT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
sys.path.insert(0, str(PROJECT_ROOT / "intermediaire" / "scripts"))

# Importer le processeur
from ml_03_prepare_population_isochrones import PopulationProcessor, INTERMEDIATE_FILES, INPUT_FILES

# ============================================================================
# CONFIGURATION TEST
# ============================================================================

N_PHARMACIES_TEST = 10  # Nombre de pharmacies à tester

print("="*80)
print("TEST ML_03 - CALCUL POPULATION SUR ECHANTILLON")
print("="*80)
print(f"\nNombre de pharmacies à tester : {N_PHARMACIES_TEST}")
print("")

# ============================================================================
# PREPARATION ECHANTILLON
# ============================================================================

# Charger le fichier pharmacies
pharmacies_path = INPUT_FILES['pharmacies']
print(f"Chargement pharmacies depuis : {pharmacies_path}")
df_pharmacies_full = pd.read_csv(pharmacies_path, sep=';')
print(f"  -> {len(df_pharmacies_full):,} pharmacies totales")

# Prendre échantillon
df_pharmacies_sample = df_pharmacies_full.head(N_PHARMACIES_TEST).copy()
print(f"  -> Echantillon : {len(df_pharmacies_sample)} pharmacies")
print(f"  -> IDs : {df_pharmacies_sample['id_pharmacie'].tolist()}")

# Sauvegarder l'échantillon temporairement (avec même format que l'original : sep=';')
temp_sample_file = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones'].parent / 'temp_pharmacies_sample.csv'
df_pharmacies_sample.to_csv(temp_sample_file, index=False, sep=';')
print(f"\nEchantillon sauvegarde : {temp_sample_file}")

# ============================================================================
# EXECUTION TEST
# ============================================================================

print("\n" + "="*80)
print("LANCEMENT DU TEST")
print("="*80)
print("")

# Créer le processeur
processor = PopulationProcessor()

# Remplacer temporairement le fichier pharmacies par l'échantillon
original_pharmacies_path = INPUT_FILES['pharmacies']
INPUT_FILES['pharmacies'] = temp_sample_file

try:
    # Charger les données
    processor.load_data()

    print(f"\nPharmacies chargées : {len(processor.pharmacies_df)}")
    print(f"IRIS chargés : {len(processor.iris_data_geo):,}")

    # Traiter toutes les pharmacies de l'échantillon
    output_df = processor.process_all_pharmacies()

    # Afficher résultats
    print("\n" + "="*80)
    print("RESULTATS DU TEST")
    print("="*80)
    print(f"\nPharmacies traitées : {len(output_df)}")
    print(f"Colonnes créées : {len(output_df.columns)}")

    # Compter colonnes par isochrone
    iso_types = ['walk_5min', 'walk_10min', 'drive_5min', 'drive_10min', 'drive_15min', 'drive_20min']
    print("\nColonnes par isochrone :")
    for iso in iso_types:
        cols = [c for c in output_df.columns if iso in c]
        if cols:
            print(f"  {iso:15s} : {len(cols):2d} colonnes")
            # Afficher quelques exemples
            print(f"    Exemples : {cols[:3]}")
        else:
            print(f"  {iso:15s} : AUCUNE colonne (vérifier si isochrones existent)")

    # Vérifier quelques valeurs
    print("\nValeurs exemple pour la 1ère pharmacie :")
    pharma_id = output_df.iloc[0]['id_pharmacie']
    print(f"  ID : {pharma_id}")
    for iso in iso_types:
        col_pop = f'pop_65_plus_{iso}'
        if col_pop in output_df.columns:
            val = output_df.iloc[0][col_pop]
            print(f"  {col_pop:35s} : {val:>10,.0f} seniors")

    # Sauvegarder résultat test
    test_output_file = INTERMEDIATE_FILES['pharmacies_avec_population_isochrones'].parent / 'TEST_population_echantillon.csv'
    output_df.to_csv(test_output_file, index=False)
    print(f"\nRésultats test sauvegardés : {test_output_file}")

    print("\n" + "="*80)
    print("TEST TERMINE AVEC SUCCES")
    print("="*80)
    print("\nSi les résultats sont corrects, vous pouvez lancer le calcul complet avec :")
    print("  python ml_03_prepare_population_isochrones.py")
    print("")

finally:
    # Restaurer le chemin original
    INPUT_FILES['pharmacies'] = original_pharmacies_path

    # Nettoyer fichier temporaire
    if temp_sample_file.exists():
        temp_sample_file.unlink()
        print(f"Fichier temporaire supprimé : {temp_sample_file}")
