"""
Analyse de corrélation entre données df_bas_annee et estimations clients 65+
"""
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import sys

# Ajouter le répertoire config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_ml import (
    INPUT_FILES,
    OUTPUT_FILES,
    PROJECT_ROOT
)

print("="*80)
print("ANALYSE CORRELATION DF_BAS_ANNEE vs CLIENTS 65+")
print("="*80)

# 1. Charger df_bas_annee
print("\n1. CHARGEMENT DF_BAS_ANNEE")

# Chercher le fichier df_bas_annee dans les inputs
df_bas_path = PROJECT_ROOT / "1_data_prep/input/5_validation/df_bas_annee.csv"

if not df_bas_path.exists():
    # Essayer avec séparateur point-virgule
    print(f"   ERREUR: Fichier non trouvé: {df_bas_path}")
    print(f"   Recherche d'alternatives...")

    # Lister les fichiers disponibles
    insee_dir = PROJECT_ROOT / "1_data_prep/input/5_validation"
    if insee_dir.exists():
        print(f"   Fichiers disponibles dans {insee_dir.name}:")
        for f in insee_dir.glob("*.csv"):
            print(f"     - {f.name}")

    sys.exit(1)

# Charger avec différents séparateurs possibles
try:
    df_bas = pd.read_csv(df_bas_path, sep=',', encoding='utf-8-sig', low_memory=False)
    print(f"   Fichier chargé (sep=',')")
except:
    try:
        df_bas = pd.read_csv(df_bas_path, sep=';', encoding='latin1', low_memory=False)
        print(f"   Fichier chargé (sep=';')")
    except Exception as e:
        print(f"   ERREUR chargement: {e}")
        sys.exit(1)

print(f"   Lignes totales        : {len(df_bas):,}")
print(f"   Colonnes              : {len(df_bas.columns)}")
print(f"   Colonnes disponibles  :")
for i, col in enumerate(df_bas.columns[:20]):
    print(f"     {i+1:2d}. {col}")
if len(df_bas.columns) > 20:
    print(f"     ... et {len(df_bas.columns)-20} autres colonnes")

# Identifier la colonne ID pharmacie
id_col = None
for col in df_bas.columns:
    if 'id' in col.lower() or 'code' in col.lower():
        id_col = col
        break

if id_col is None:
    print(f"\n   ERREUR: Impossible de trouver la colonne ID pharmacie")
    print(f"   Colonnes disponibles: {list(df_bas.columns[:10])}")
    sys.exit(1)

print(f"\n   Colonne ID identifiée : {id_col}")
print(f"   Pharmacies uniques    : {df_bas[id_col].nunique():,}")

# 2. Charger les estimations clients 65+
print("\n2. CHARGEMENT CLIENTS 65+")
df_clients = pd.read_csv(OUTPUT_FILES['pharmacies_clients_65plus_huff'])

print(f"   Pharmacies            : {len(df_clients):,}")
print(f"   Colonnes              : {list(df_clients.columns)}")

# 3. Fusionner les deux datasets
print("\n3. FUSION DES DONNÉES")

# Renommer la colonne ID pour correspondre
df_bas_renamed = df_bas.rename(columns={id_col: 'id_pharmacie'})

df_merged = df_clients.merge(
    df_bas_renamed,
    on='id_pharmacie',
    how='inner'
)

print(f"   Pharmacies communes   : {len(df_merged):,}")
print(f"   Pharmacies clients seules : {len(df_clients) - len(df_merged):,}")
print(f"   Pharmacies df_bas seules : {df_bas_renamed['id_pharmacie'].nunique() - len(df_merged):,}")

if len(df_merged) == 0:
    print(f"\n   ERREUR: Aucune pharmacie commune entre les deux datasets")
    print(f"   Exemples IDs df_clients : {df_clients['id_pharmacie'].head(5).tolist()}")
    print(f"   Exemples IDs df_bas     : {df_bas_renamed['id_pharmacie'].head(5).tolist()}")
    sys.exit(1)

# 4. Identifier les colonnes numériques pertinentes dans df_bas
print("\n4. IDENTIFICATION DES COLONNES NUMÉRIQUES")

numeric_cols = []
for col in df_merged.columns:
    if col in ['id_pharmacie', 'nom_pharmacie', 'attractivite_huff',
               'clients_65_79', 'clients_80_plus', 'clients_65_plus_total',
               'visites_annuelles_65plus', 'decile_clients_65plus']:
        continue

    if pd.api.types.is_numeric_dtype(df_merged[col]):
        # Vérifier qu'il y a de la variance
        if df_merged[col].std() > 0:
            numeric_cols.append(col)

print(f"   Colonnes numériques   : {len(numeric_cols)}")
print(f"   Top 20 colonnes:")
for i, col in enumerate(numeric_cols[:20]):
    mean_val = df_merged[col].mean()
    print(f"     {i+1:2d}. {col:40s} (mean={mean_val:.2f})")

if len(numeric_cols) > 20:
    print(f"     ... et {len(numeric_cols)-20} autres colonnes")

# 5. Calculer les corrélations avec clients 65+
print("\n5. CORRÉLATIONS AVEC CLIENTS 65+")

correlations = []
for col in numeric_cols:
    corr = df_merged[col].corr(df_merged['clients_65_plus_total'])
    if not np.isnan(corr):
        correlations.append({
            'variable': col,
            'correlation': corr,
            'abs_correlation': abs(corr)
        })

df_corr = pd.DataFrame(correlations)
df_corr = df_corr.sort_values('abs_correlation', ascending=False)

print(f"\n   Top 20 corrélations (valeur absolue):")
print(f"   {'Variable':50s} | {'Corrélation':>12s}")
print(f"   {'-'*50:50s} | {'-'*12:12s}")
for idx, row in df_corr.head(20).iterrows():
    print(f"   {row['variable']:50s} | {row['correlation']:12.4f}")

# 6. Statistiques descriptives des variables les plus corrélées
print("\n6. STATISTIQUES DES VARIABLES TOP CORRÉLÉES")

top_vars = df_corr.head(10)['variable'].tolist()
top_vars_with_clients = ['clients_65_plus_total'] + top_vars

print(f"\n   Statistiques descriptives:")
print(df_merged[top_vars_with_clients].describe())

# 7. Sauvegarder les résultats
print("\n7. SAUVEGARDE")

output_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_df_bas_annee_clients65.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
df_corr.to_csv(output_path, index=False)
print(f"   Corrélations          : {output_path}")

# Sauvegarder aussi le dataset fusionné (échantillon)
output_merged_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "merged_df_bas_clients65.csv"
df_merged[top_vars_with_clients + ['id_pharmacie', 'nom_pharmacie']].to_csv(output_merged_path, index=False)
print(f"   Dataset fusionné      : {output_merged_path}")

# 8. Créer des graphiques de corrélation
print("\n8. CRÉATION DES GRAPHIQUES")

try:
    # Sélectionner les 6 variables les plus corrélées
    top_6_vars = df_corr.head(6)['variable'].tolist()

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    for i, var in enumerate(top_6_vars):
        ax = axes[i]

        # Scatter plot
        ax.scatter(df_merged[var], df_merged['clients_65_plus_total'], alpha=0.5)
        ax.set_xlabel(var)
        ax.set_ylabel('Clients 65+')

        # Corrélation
        corr = df_merged[var].corr(df_merged['clients_65_plus_total'])
        ax.set_title(f'{var}\n(R={corr:.3f})')

        # Ligne de tendance
        z = np.polyfit(df_merged[var].fillna(0), df_merged['clients_65_plus_total'], 1)
        p = np.poly1d(z)
        x_range = np.linspace(df_merged[var].min(), df_merged[var].max(), 100)
        ax.plot(x_range, p(x_range), "r--", alpha=0.8)

    plt.tight_layout()

    graph_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_df_bas_annee_graphs.png"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(graph_path, dpi=150)
    print(f"   Graphique sauvegardé  : {graph_path}")

except Exception as e:
    print(f"   Erreur graphique      : {e}")
    import traceback
    traceback.print_exc()

# 9. Matrice de corrélation (top variables)
print("\n9. MATRICE DE CORRÉLATION")

try:
    top_10_vars = df_corr.head(10)['variable'].tolist()
    corr_matrix_vars = ['clients_65_plus_total'] + top_10_vars

    corr_matrix = df_merged[corr_matrix_vars].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=ax)
    ax.set_title('Matrice de Corrélation - Top 10 Variables vs Clients 65+')

    plt.tight_layout()

    heatmap_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_df_bas_annee_heatmap.png"
    plt.savefig(heatmap_path, dpi=150)
    print(f"   Heatmap sauvegardée   : {heatmap_path}")

except Exception as e:
    print(f"   Erreur heatmap        : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("OK ANALYSE TERMINÉE")
print("="*80)