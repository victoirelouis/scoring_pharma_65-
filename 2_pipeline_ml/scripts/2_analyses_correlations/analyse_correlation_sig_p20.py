"""
Analyse de corrélation entre données SIG_P20 et estimations clients 65+
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
print("ANALYSE CORRELATION SIG_P20 vs CLIENTS 65+")
print("="*80)

# 1. Charger SIG_P20
print("\n1. CHARGEMENT SIG_P20")
df_sig = pd.read_csv(
    INPUT_FILES['sig_p20'],
    sep=';',
    decimal=','  # Les montants utilisent la virgule comme séparateur décimal
)

print(f"   Lignes totales        : {len(df_sig):,}")
print(f"   Colonnes              : {list(df_sig.columns)}")
print(f"   Pharmacies uniques    : {df_sig['Pvactif'].nunique():,}")
print(f"   Mois uniques          : {df_sig['CleMoisAnnee'].nunique():,}")

# 2. Groupby par Pvactif (somme de UN et CAHT)
print("\n2. GROUPBY PAR PHARMACIE")
df_sig_agg = df_sig.groupby('Pvactif').agg({
    'UN': 'sum',
    'CAHT': 'sum'
}).reset_index()

df_sig_agg = df_sig_agg.rename(columns={'Pvactif': 'id_pharmacie'})

print(f"   Pharmacies après agg  : {len(df_sig_agg):,}")
print(f"   UN total              : {df_sig_agg['UN'].sum():,.0f}")
print(f"   CAHT total            : {df_sig_agg['CAHT'].sum():,.2f} €")
print(f"\n   Statistiques UN :")
print(f"     Moyenne             : {df_sig_agg['UN'].mean():,.0f}")
print(f"     Médiane             : {df_sig_agg['UN'].median():,.0f}")
print(f"     Min                 : {df_sig_agg['UN'].min():,.0f}")
print(f"     Max                 : {df_sig_agg['UN'].max():,.0f}")
print(f"\n   Statistiques CAHT :")
print(f"     Moyenne             : {df_sig_agg['CAHT'].mean():,.2f} €")
print(f"     Médiane             : {df_sig_agg['CAHT'].median():,.2f} €")
print(f"     Min                 : {df_sig_agg['CAHT'].min():,.2f} €")
print(f"     Max                 : {df_sig_agg['CAHT'].max():,.2f} €")

# 3. Charger les estimations clients 65+
print("\n3. CHARGEMENT CLIENTS 65+")
df_clients = pd.read_csv(
    OUTPUT_FILES['pharmacies_clients_65plus_huff']
)

print(f"   Pharmacies            : {len(df_clients):,}")
print(f"   Colonnes              : {list(df_clients.columns)}")

# 4. Fusionner les deux datasets
print("\n4. FUSION DES DONNÉES")
df_merged = df_sig_agg.merge(
    df_clients[['id_pharmacie', 'clients_65_plus_total', 'visites_annuelles_65plus']],
    on='id_pharmacie',
    how='inner'
)

print(f"   Pharmacies communes   : {len(df_merged):,}")
print(f"   Pharmacies SIG seules : {len(df_sig_agg) - len(df_merged):,}")
print(f"   Pharmacies clients seules : {len(df_clients) - len(df_merged):,}")

# Filtrer les pharmacies avec des données valides (>0)
df_merged_valide = df_merged[
    (df_merged['UN'] > 0) &
    (df_merged['CAHT'] > 0) &
    (df_merged['clients_65_plus_total'] > 0)
].copy()

print(f"   Pharmacies valides    : {len(df_merged_valide):,}")

# 5. Calculer les corrélations
print("\n5. CORRÉLATIONS")

# Corrélation UN vs clients_65_plus_total
corr_un_clients = df_merged_valide['UN'].corr(df_merged_valide['clients_65_plus_total'])
print(f"   UN vs Clients 65+     : {corr_un_clients:.4f}")

# Corrélation UN vs visites_annuelles_65plus
corr_un_visites = df_merged_valide['UN'].corr(df_merged_valide['visites_annuelles_65plus'])
print(f"   UN vs Visites 65+     : {corr_un_visites:.4f}")

# Corrélation CAHT vs clients_65_plus_total
corr_caht_clients = df_merged_valide['CAHT'].corr(df_merged_valide['clients_65_plus_total'])
print(f"   CAHT vs Clients 65+   : {corr_caht_clients:.4f}")

# Corrélation CAHT vs visites_annuelles_65plus
corr_caht_visites = df_merged_valide['CAHT'].corr(df_merged_valide['visites_annuelles_65plus'])
print(f"   CAHT vs Visites 65+   : {corr_caht_visites:.4f}")

# 6. Matrice de corrélation complète
print("\n6. MATRICE DE CORRÉLATION")
corr_matrix = df_merged_valide[['UN', 'CAHT', 'clients_65_plus_total', 'visites_annuelles_65plus']].corr()
print(corr_matrix)

# 7. Statistiques descriptives
print("\n7. STATISTIQUES DESCRIPTIVES (pharmacies valides)")
print(df_merged_valide[['UN', 'CAHT', 'clients_65_plus_total', 'visites_annuelles_65plus']].describe())

# 8. Ratios
print("\n8. RATIOS MOYENS")
df_merged_valide['ratio_un_clients'] = df_merged_valide['UN'] / df_merged_valide['clients_65_plus_total']
df_merged_valide['ratio_caht_clients'] = df_merged_valide['CAHT'] / df_merged_valide['clients_65_plus_total']

print(f"   UN / Clients 65+      : {df_merged_valide['ratio_un_clients'].mean():.2f} (médiane: {df_merged_valide['ratio_un_clients'].median():.2f})")
print(f"   CAHT / Clients 65+    : {df_merged_valide['ratio_caht_clients'].mean():.2f} € (médiane: {df_merged_valide['ratio_caht_clients'].median():.2f} €)")

# 9. Sauvegarder les résultats
print("\n9. SAUVEGARDE")
output_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_sig_p20_clients65.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
df_merged_valide.to_csv(output_path, index=False)
print(f"   Fichier sauvegardé    : {output_path}")

# 10. Créer des graphiques de corrélation
print("\n10. CRÉATION DES GRAPHIQUES")

try:
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # UN vs Clients 65+
    axes[0, 0].scatter(df_merged_valide['clients_65_plus_total'], df_merged_valide['UN'], alpha=0.5)
    axes[0, 0].set_xlabel('Clients 65+')
    axes[0, 0].set_ylabel('UN')
    axes[0, 0].set_title(f'UN vs Clients 65+ (corr={corr_un_clients:.3f})')

    # UN vs Visites
    axes[0, 1].scatter(df_merged_valide['visites_annuelles_65plus'], df_merged_valide['UN'], alpha=0.5)
    axes[0, 1].set_xlabel('Visites annuelles 65+')
    axes[0, 1].set_ylabel('UN')
    axes[0, 1].set_title(f'UN vs Visites 65+ (corr={corr_un_visites:.3f})')

    # CAHT vs Clients 65+
    axes[1, 0].scatter(df_merged_valide['clients_65_plus_total'], df_merged_valide['CAHT'], alpha=0.5)
    axes[1, 0].set_xlabel('Clients 65+')
    axes[1, 0].set_ylabel('CAHT (€)')
    axes[1, 0].set_title(f'CAHT vs Clients 65+ (corr={corr_caht_clients:.3f})')

    # CAHT vs Visites
    axes[1, 1].scatter(df_merged_valide['visites_annuelles_65plus'], df_merged_valide['CAHT'], alpha=0.5)
    axes[1, 1].set_xlabel('Visites annuelles 65+')
    axes[1, 1].set_ylabel('CAHT (€)')
    axes[1, 1].set_title(f'CAHT vs Visites 65+ (corr={corr_caht_visites:.3f})')

    plt.tight_layout()

    graph_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_sig_p20_graphs.png"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(graph_path, dpi=150)
    print(f"   Graphique sauvegardé  : {graph_path}")

except Exception as e:
    print(f"   Erreur graphique      : {e}")

print("\n" + "="*80)
print("OK ANALYSE TERMINÉE")
print("="*80)
