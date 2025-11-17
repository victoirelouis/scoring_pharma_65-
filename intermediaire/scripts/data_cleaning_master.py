"""
Script de nettoyage du fichier master
Traite les valeurs manquantes et les incohérences

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Chemins
FICHIER_INPUT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet.csv")
FICHIER_OUTPUT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet_clean.csv")
FICHIER_RAPPORT = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\rapport_nettoyage.txt")


def nettoyer_donnees():
    """Nettoie les données du fichier master"""

    print("="*80)
    print("NETTOYAGE DU FICHIER MASTER")
    print("="*80)

    rapport = []
    rapport.append("="*80)
    rapport.append("RAPPORT DE NETTOYAGE DES DONNEES")
    rapport.append("="*80)
    rapport.append("")

    # Charger le fichier
    print(f"\n[LOAD] Chargement du fichier...")
    df = pd.read_csv(FICHIER_INPUT)
    nb_initial = len(df)
    print(f"   OK {nb_initial:,} lignes x {len(df.columns)} colonnes")

    rapport.append(f"Données initiales: {nb_initial:,} pharmacies x {len(df.columns)} colonnes")
    rapport.append("")

    # ===================================================================
    # 1. TRAITEMENT DES VALEURS MANQUANTES (latitude/longitude)
    # ===================================================================
    print(f"\n" + "="*80)
    print("1. TRAITEMENT VALEURS MANQUANTES (latitude/longitude)")
    print("="*80)

    rapport.append("1. VALEURS MANQUANTES")
    rapport.append("-"*80)

    nb_missing_coords = df[['latitude', 'longitude']].isnull().any(axis=1).sum()
    print(f"   Pharmacies avec coordonnées manquantes: {nb_missing_coords}")
    rapport.append(f"   Pharmacies avec coordonnées manquantes: {nb_missing_coords}")

    if nb_missing_coords > 0:
        # Option 1: Supprimer les lignes sans coordonnées
        print(f"   -> SUPPRESSION de {nb_missing_coords} pharmacies sans coordonnées")
        rapport.append(f"   -> SUPPRESSION de {nb_missing_coords} pharmacies sans coordonnées")

        df_clean = df.dropna(subset=['latitude', 'longitude']).copy()
        nb_supprimes = nb_initial - len(df_clean)
        print(f"   OK {nb_supprimes} lignes supprimées")
        rapport.append(f"   OK {nb_supprimes} lignes supprimées")
    else:
        df_clean = df.copy()
        print(f"   OK Aucune suppression nécessaire")
        rapport.append(f"   OK Aucune suppression nécessaire")

    rapport.append("")

    # ===================================================================
    # 2. TRAITEMENT DES INCOHERENCES D'ISOCHRONES
    # ===================================================================
    print(f"\n" + "="*80)
    print("2. TRAITEMENT INCOHERENCES ISOCHRONES")
    print("="*80)

    rapport.append("2. INCOHERENCES ISOCHRONES")
    rapport.append("-"*80)

    # Identifier les incohérences pop_walk_5min > pop_drive_10min
    if 'pop_totale_walk_5min' in df_clean.columns and 'pop_totale_drive_10min' in df_clean.columns:
        incoherent_mask = df_clean['pop_totale_walk_5min'] > df_clean['pop_totale_drive_10min']
        nb_incoherent = incoherent_mask.sum()

        print(f"   Cas où pop_walk_5min > pop_drive_10min: {nb_incoherent}")
        rapport.append(f"   Cas où pop_walk_5min > pop_drive_10min: {nb_incoherent}")

        if nb_incoherent > 0:
            # Option: Corriger en prenant le max des deux valeurs pour drive_10min
            print(f"   -> CORRECTION: drive_10min = max(walk_5min, drive_10min)")
            rapport.append(f"   -> CORRECTION: drive_10min = max(walk_5min, drive_10min)")

            # Colonnes population à corriger
            pop_cols = [col for col in df_clean.columns if col.startswith('pop_') and 'walk_5min' in col]

            nb_corrections = 0
            for col_walk in pop_cols:
                col_drive = col_walk.replace('walk_5min', 'drive_10min')
                if col_drive in df_clean.columns:
                    # Correction: drive_10min doit être au moins égal à walk_5min
                    mask = df_clean[col_walk] > df_clean[col_drive]
                    if mask.any():
                        df_clean.loc[mask, col_drive] = df_clean.loc[mask, col_walk]
                        nb_corrections += mask.sum()

            print(f"   OK {nb_corrections} valeurs corrigées")
            rapport.append(f"   OK {nb_corrections} valeurs corrigées")
    else:
        print(f"   Colonnes pop_totale non trouvées, pas de correction")
        rapport.append(f"   Colonnes pop_totale non trouvées, pas de correction")

    rapport.append("")

    # ===================================================================
    # 3. VERIFICATION VALEURS NEGATIVES
    # ===================================================================
    print(f"\n" + "="*80)
    print("3. VERIFICATION VALEURS NEGATIVES")
    print("="*80)

    rapport.append("3. VALEURS NEGATIVES")
    rapport.append("-"*80)

    # Variables qui ne devraient jamais être négatives
    count_patterns = ['nb_', 'pop_', 'capacite_', 'distance_']
    count_cols = [col for col in df_clean.columns if any(pattern in col for pattern in count_patterns)]

    negative_found = False
    nb_corrections_neg = 0

    for col in count_cols:
        if col in df_clean.columns and df_clean[col].dtype in [np.int64, np.float64]:
            n_neg = (df_clean[col] < 0).sum()
            if n_neg > 0:
                negative_found = True
                print(f"   CORRECTION {col}: {n_neg} valeurs négatives -> 0")
                rapport.append(f"   CORRECTION {col}: {n_neg} valeurs négatives -> 0")
                df_clean.loc[df_clean[col] < 0, col] = 0
                nb_corrections_neg += n_neg

    if not negative_found:
        print(f"   OK Aucune valeur négative détectée")
        rapport.append(f"   OK Aucune valeur négative détectée")
    else:
        print(f"   OK {nb_corrections_neg} valeurs négatives corrigées")
        rapport.append(f"   OK {nb_corrections_neg} valeurs négatives corrigées")

    rapport.append("")

    # ===================================================================
    # 4. VERIFICATION VALEURS INFINIES
    # ===================================================================
    print(f"\n" + "="*80)
    print("4. VERIFICATION VALEURS INFINIES")
    print("="*80)

    rapport.append("4. VALEURS INFINIES")
    rapport.append("-"*80)

    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    inf_count = 0

    for col in numeric_cols:
        n_inf = np.isinf(df_clean[col]).sum()
        if n_inf > 0:
            print(f"   CORRECTION {col}: {n_inf} valeurs infinies -> NaN puis 0")
            rapport.append(f"   CORRECTION {col}: {n_inf} valeurs infinies -> 0")
            df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
            df_clean[col] = df_clean[col].fillna(0)
            inf_count += n_inf

    if inf_count == 0:
        print(f"   OK Aucune valeur infinie détectée")
        rapport.append(f"   OK Aucune valeur infinie détectée")
    else:
        print(f"   OK {inf_count} valeurs infinies corrigées")
        rapport.append(f"   OK {inf_count} valeurs infinies corrigées")

    rapport.append("")

    # ===================================================================
    # 5. IMPUTATION DES NaN RESTANTS
    # ===================================================================
    print(f"\n" + "="*80)
    print("5. IMPUTATION DES NaN RESTANTS")
    print("="*80)

    rapport.append("5. IMPUTATION DES NaN")
    rapport.append("-"*80)

    # Compter les NaN restants
    nan_counts = df_clean.isnull().sum()
    nan_cols = nan_counts[nan_counts > 0]

    if len(nan_cols) > 0:
        print(f"   Colonnes avec NaN: {len(nan_cols)}")
        rapport.append(f"   Colonnes avec NaN: {len(nan_cols)}")

        # Pour les colonnes numériques, imputer avec 0 (sauf latitude/longitude déjà traitées)
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ['latitude', 'longitude'] and df_clean[col].isnull().any():
                n_nan = df_clean[col].isnull().sum()
                print(f"   -> {col}: {n_nan} NaN -> 0")
                rapport.append(f"   -> {col}: {n_nan} NaN -> 0")
                df_clean[col] = df_clean[col].fillna(0)
    else:
        print(f"   OK Aucun NaN détecté")
        rapport.append(f"   OK Aucun NaN détecté")

    rapport.append("")

    # ===================================================================
    # 6. VERIFICATION DOUBLONS
    # ===================================================================
    print(f"\n" + "="*80)
    print("6. VERIFICATION DOUBLONS")
    print("="*80)

    rapport.append("6. DOUBLONS")
    rapport.append("-"*80)

    nb_doublons = df_clean['id_pharmacie'].duplicated().sum()
    print(f"   Doublons sur id_pharmacie: {nb_doublons}")
    rapport.append(f"   Doublons sur id_pharmacie: {nb_doublons}")

    if nb_doublons > 0:
        print(f"   -> SUPPRESSION des doublons")
        rapport.append(f"   -> SUPPRESSION des doublons")
        df_clean = df_clean.drop_duplicates(subset=['id_pharmacie'], keep='first')
        print(f"   OK {nb_doublons} doublons supprimés")
        rapport.append(f"   OK {nb_doublons} doublons supprimés")
    else:
        print(f"   OK Aucun doublon")
        rapport.append(f"   OK Aucun doublon")

    rapport.append("")

    # ===================================================================
    # 7. STATISTIQUES FINALES
    # ===================================================================
    print(f"\n" + "="*80)
    print("7. STATISTIQUES FINALES")
    print("="*80)

    rapport.append("7. STATISTIQUES FINALES")
    rapport.append("-"*80)

    nb_final = len(df_clean)
    nb_supprimes_total = nb_initial - nb_final

    print(f"   Pharmacies initiales: {nb_initial:,}")
    print(f"   Pharmacies après nettoyage: {nb_final:,}")
    print(f"   Pharmacies supprimées: {nb_supprimes_total} ({nb_supprimes_total/nb_initial*100:.2f}%)")
    print(f"   Variables: {len(df_clean.columns)}")

    rapport.append(f"   Pharmacies initiales: {nb_initial:,}")
    rapport.append(f"   Pharmacies après nettoyage: {nb_final:,}")
    rapport.append(f"   Pharmacies supprimées: {nb_supprimes_total} ({nb_supprimes_total/nb_initial*100:.2f}%)")
    rapport.append(f"   Variables: {len(df_clean.columns)}")

    # Vérification finale
    print(f"\n   Vérification finale:")
    print(f"   - Valeurs manquantes: {df_clean.isnull().sum().sum()}")
    print(f"   - Valeurs infinies: {np.isinf(df_clean.select_dtypes(include=[np.number])).sum().sum()}")
    print(f"   - Doublons: {df_clean['id_pharmacie'].duplicated().sum()}")

    rapport.append(f"\n   Vérification finale:")
    rapport.append(f"   - Valeurs manquantes: {df_clean.isnull().sum().sum()}")
    rapport.append(f"   - Valeurs infinies: {np.isinf(df_clean.select_dtypes(include=[np.number])).sum().sum()}")
    rapport.append(f"   - Doublons: {df_clean['id_pharmacie'].duplicated().sum()}")

    rapport.append("")
    rapport.append("="*80)
    rapport.append("NETTOYAGE TERMINE")
    rapport.append("="*80)

    # ===================================================================
    # SAUVEGARDE
    # ===================================================================
    print(f"\n" + "="*80)
    print("8. SAUVEGARDE")
    print("="*80)

    print(f"\n[SAVE] Sauvegarde du fichier nettoyé...")
    df_clean.to_csv(FICHIER_OUTPUT, index=False, encoding='utf-8')
    print(f"   OK Fichier sauvegardé: {FICHIER_OUTPUT}")
    print(f"   -> {nb_final:,} lignes x {len(df_clean.columns)} colonnes")

    # Sauvegarder le rapport
    print(f"\n[SAVE] Sauvegarde du rapport...")
    with open(FICHIER_RAPPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rapport))
    print(f"   OK Rapport sauvegardé: {FICHIER_RAPPORT}")

    print(f"\n" + "="*80)
    print("NETTOYAGE TERMINE AVEC SUCCES")
    print("="*80)

    return df_clean


if __name__ == "__main__":
    df_clean = nettoyer_donnees()
