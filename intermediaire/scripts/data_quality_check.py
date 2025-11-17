"""
Script de vérification de la qualité des données
Vérifie le fichier master pharmacies_features_complet.csv

Auteur: Claude
Date: 2025-11-17
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Chemins
FICHIER_MASTER = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-\intermediaire\output\pharmacies_features_complet.csv")

def check_data_quality():
    """Vérifie la qualité des données du fichier master"""

    print("="*80)
    print("VERIFICATION DATA QUALITY - FICHIER MASTER")
    print("="*80)

    # Charger le fichier
    print(f"\n[LOAD] Chargement du fichier...")
    df = pd.read_csv(FICHIER_MASTER)
    print(f"   OK {len(df):,} lignes x {len(df.columns)} colonnes")

    # ===================================================================
    # 1. VERIFICATION DES DIMENSIONS
    # ===================================================================
    print(f"\n" + "="*80)
    print("1. VERIFICATION DES DIMENSIONS")
    print("="*80)

    print(f"   Nombre de pharmacies: {len(df):,}")
    print(f"   Nombre de variables: {len(df.columns)}")
    print(f"   Nombre de doublons (id_pharmacie): {df['id_pharmacie'].duplicated().sum()}")

    # ===================================================================
    # 2. VALEURS MANQUANTES
    # ===================================================================
    print(f"\n" + "="*80)
    print("2. VALEURS MANQUANTES")
    print("="*80)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    missing_df = pd.DataFrame({
        'column': missing.index,
        'missing_count': missing.values,
        'missing_pct': missing_pct.values
    })
    missing_df = missing_df[missing_df['missing_count'] > 0].sort_values('missing_count', ascending=False)

    print(f"\n   Colonnes avec valeurs manquantes: {len(missing_df)}")
    if len(missing_df) > 0:
        print(f"\n   TOP 20 colonnes avec le plus de valeurs manquantes:")
        for _, row in missing_df.head(20).iterrows():
            print(f"      {row['column']:50s} : {row['missing_count']:6.0f} ({row['missing_pct']:5.1f}%)")
    else:
        print(f"   OK Aucune valeur manquante")

    # ===================================================================
    # 3. VALEURS INFINIES
    # ===================================================================
    print(f"\n" + "="*80)
    print("3. VALEURS INFINIES")
    print("="*80)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_count = 0
    inf_cols = []

    for col in numeric_cols:
        n_inf = np.isinf(df[col]).sum()
        if n_inf > 0:
            inf_count += n_inf
            inf_cols.append((col, n_inf))

    if inf_count > 0:
        print(f"   ATTENTION {inf_count} valeurs infinies trouvées dans {len(inf_cols)} colonnes:")
        for col, count in sorted(inf_cols, key=lambda x: x[1], reverse=True)[:20]:
            print(f"      {col:50s} : {count:6d}")
    else:
        print(f"   OK Aucune valeur infinie")

    # ===================================================================
    # 4. VALEURS NEGATIVES (pour variables de comptage)
    # ===================================================================
    print(f"\n" + "="*80)
    print("4. VALEURS NEGATIVES (variables de comptage)")
    print("="*80)

    # Variables qui ne devraient jamais être négatives
    count_patterns = ['nb_', 'pop_', 'capacite_', 'distance_']
    count_cols = [col for col in df.columns if any(pattern in col for pattern in count_patterns)]

    negative_found = False
    for col in count_cols:
        if col in df.columns and df[col].dtype in [np.int64, np.float64]:
            n_neg = (df[col] < 0).sum()
            if n_neg > 0:
                negative_found = True
                print(f"   ATTENTION {col:50s} : {n_neg:6d} valeurs négatives")

    if not negative_found:
        print(f"   OK Aucune valeur négative dans les variables de comptage")

    # ===================================================================
    # 5. STATISTIQUES PAR CATEGORIE
    # ===================================================================
    print(f"\n" + "="*80)
    print("5. STATISTIQUES PAR CATEGORIE DE VARIABLES")
    print("="*80)

    categories = {
        'Hubs': ['nb_sante', 'nb_medecin', 'nb_laboratoire', 'nb_ehpad', 'taux_colocalisation'],
        'Concurrence': ['nb_pharmacies_concurrentes', 'distance_pharmacie'],
        'Population': ['pop_', 'ratio_0_64', 'ratio_65_plus', 'ratio_femmes'],
        'Tourisme': ['nb_hotels', 'nb_campings', 'capacite_accueil', 'flag_commune'],
        'Features derivees': ['densite_', 'zone_isolee', 'zone_tres_senior'],
    }

    for cat_name, patterns in categories.items():
        cat_cols = [col for col in df.columns if any(pattern in col for pattern in patterns)]
        if len(cat_cols) > 0:
            print(f"\n   {cat_name} ({len(cat_cols)} variables)")

            # Exemple de quelques colonnes
            for col in cat_cols[:5]:
                if col in df.columns and df[col].dtype in [np.int64, np.float64]:
                    print(f"      {col:50s} : mean={df[col].mean():8.2f} | median={df[col].median():8.2f} | min={df[col].min():8.2f} | max={df[col].max():8.2f}")

    # ===================================================================
    # 6. COHERENCE DES ISOCHRONES
    # ===================================================================
    print(f"\n" + "="*80)
    print("6. COHERENCE DES ISOCHRONES")
    print("="*80)

    # Vérifier que walk_5min <= drive_10min pour population
    if 'pop_totale_walk_5min' in df.columns and 'pop_totale_drive_10min' in df.columns:
        incoherent = (df['pop_totale_walk_5min'] > df['pop_totale_drive_10min']).sum()
        print(f"   Pop walk_5min > drive_10min: {incoherent} cas ({incoherent/len(df)*100:.1f}%)")
        if incoherent > 0:
            print(f"      ATTENTION: Incohérence détectée")

    # Vérifier que nb_pharmacies walk <= drive
    if 'nb_pharmacies_concurrentes_walk_5min' in df.columns and 'nb_pharmacies_concurrentes_drive_10min' in df.columns:
        incoherent = (df['nb_pharmacies_concurrentes_walk_5min'] > df['nb_pharmacies_concurrentes_drive_10min']).sum()
        print(f"   Pharmacies walk_5min > drive_10min: {incoherent} cas ({incoherent/len(df)*100:.1f}%)")
        if incoherent > 0:
            print(f"      ATTENTION: Incohérence détectée")

    # ===================================================================
    # 7. OUTLIERS
    # ===================================================================
    print(f"\n" + "="*80)
    print("7. DETECTION D'OUTLIERS (variables clés)")
    print("="*80)

    key_vars = [
        'pop_65_plus_drive_10min',
        'nb_sante_generale_drive_10min',
        'nb_pharmacies_concurrentes_drive_10min',
        'distance_pharmacie_plus_proche'
    ]

    for var in key_vars:
        if var in df.columns:
            Q1 = df[var].quantile(0.25)
            Q3 = df[var].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR

            n_outliers = ((df[var] < lower_bound) | (df[var] > upper_bound)).sum()
            print(f"   {var:50s} : {n_outliers:5d} outliers ({n_outliers/len(df)*100:4.1f}%)")

    # ===================================================================
    # 8. VERIFICATION VARIABLES TOURISTIQUES
    # ===================================================================
    print(f"\n" + "="*80)
    print("8. VERIFICATION VARIABLES TOURISTIQUES")
    print("="*80)

    tourisme_cols = [col for col in df.columns if any(x in col for x in ['hotel', 'camping', 'residence', 'capacite_accueil', 'flag_commune'])]

    if len(tourisme_cols) > 0:
        print(f"   Variables touristiques trouvées: {len(tourisme_cols)}")

        # Quelques stats
        for col in tourisme_cols[:10]:
            if col in df.columns:
                if df[col].dtype in [np.int64, np.float64]:
                    non_zero = (df[col] > 0).sum()
                    print(f"      {col:50s} : {non_zero:6d} pharmacies avec valeur > 0 ({non_zero/len(df)*100:4.1f}%)")
    else:
        print(f"   ATTENTION: Aucune variable touristique trouvée")

    # ===================================================================
    # 9. RESUME FINAL
    # ===================================================================
    print(f"\n" + "="*80)
    print("9. RESUME DATA QUALITY")
    print("="*80)

    issues = []

    if len(missing_df) > 0:
        issues.append(f"- {len(missing_df)} colonnes avec valeurs manquantes")

    if inf_count > 0:
        issues.append(f"- {inf_count} valeurs infinies détectées")

    if negative_found:
        issues.append(f"- Valeurs négatives dans variables de comptage")

    if len(tourisme_cols) == 0:
        issues.append(f"- Variables touristiques manquantes")

    if len(issues) > 0:
        print(f"\n   PROBLEMES DETECTES:")
        for issue in issues:
            print(f"      {issue}")
    else:
        print(f"\n   OK Aucun problème majeur détecté")

    print(f"\n" + "="*80)
    print("VERIFICATION TERMINEE")
    print("="*80)

    return df

if __name__ == "__main__":
    df = check_data_quality()
