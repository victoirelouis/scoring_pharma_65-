"""
Analyse avancée des corrélations :
- Par type de zone (rural/urbain/etc.)
- Avec proxies touristiques (départements côtiers, montagne, delta CA saisonnier)
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
    INTERMEDIATE_FILES,
    OUTPUT_FILES,
    PROJECT_ROOT
)

print("="*80)
print("ANALYSE AVANCÉE : TYPE DE ZONE & TOURISME")
print("="*80)

# 1. Charger toutes les données
print("\n1. CHARGEMENT DES DONNÉES")

# SIG_P20
df_sig = pd.read_csv(
    INPUT_FILES['sig_p20'],
    sep=';',
    decimal=','
)
df_sig_agg = df_sig.groupby('Pvactif').agg({
    'UN': 'sum',
    'CAHT': 'sum'
}).reset_index()
df_sig_agg = df_sig_agg.rename(columns={'Pvactif': 'id_pharmacie'})

# Clients 65+
df_clients = pd.read_csv(
    OUTPUT_FILES['pharmacies_clients_65plus_huff']
)

# Pharmacies avec scores et type_zone
df_pharmacies_scores = pd.read_csv(
    INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite']
)

# Pharmacies avec infos complètes
df_pharmacies_full = pd.read_csv(
    INPUT_FILES['pharmacies'],
    sep=';'
)

print(f"   SIG_P20               : {len(df_sig_agg):,} pharmacies")
print(f"   Clients 65+           : {len(df_clients):,} pharmacies")
print(f"   Pharmacies scores     : {len(df_pharmacies_scores):,} pharmacies")
print(f"   Pharmacies complètes  : {len(df_pharmacies_full):,} pharmacies")

# 2. Fusion complète
print("\n2. FUSION DES DONNÉES")

df_merged = df_sig_agg.merge(
    df_clients[['id_pharmacie', 'clients_65_plus_total', 'visites_annuelles_65plus']],
    on='id_pharmacie',
    how='inner'
)

df_merged = df_merged.merge(
    df_pharmacies_scores[['id_pharmacie', 'type_zone', 'score_attractivite_65plus_composite']],
    on='id_pharmacie',
    how='left'
)

# Ajouter infos département depuis pharmacies_full
df_merged = df_merged.merge(
    df_pharmacies_full[['id_pharmacie', 'departement']],
    on='id_pharmacie',
    how='left'
)

# Filtrer données valides
df_merged = df_merged[
    (df_merged['UN'] > 0) &
    (df_merged['CAHT'] > 0) &
    (df_merged['clients_65_plus_total'] > 0)
].copy()

print(f"   Données fusionnées    : {len(df_merged):,} pharmacies")
print(f"   Avec type_zone        : {df_merged['type_zone'].notna().sum():,}")

# 3. Identifier zones touristiques (proxy)
print("\n3. IDENTIFICATION ZONES TOURISTIQUES")

# Départements côtiers
depts_cotiers = ['06', '13', '83', '2A', '2B', '34', '11', '66', '64', '40', '33', '17',
                 '85', '44', '56', '29', '22', '35', '50', '14', '76', '80', '62', '59']

# Départements montagne
depts_montagne = ['73', '74', '38', '05', '04', '06', '2A', '2B', '64', '65', '09', '31',
                  '66', '48', '07', '26', '88', '68', '25', '39', '01']

df_merged['est_cotier'] = df_merged['departement'].astype(str).isin(depts_cotiers)
df_merged['est_montagne'] = df_merged['departement'].astype(str).isin(depts_montagne)
df_merged['zone_touristique'] = df_merged['est_cotier'] | df_merged['est_montagne']

print(f"   Pharmacies côtières   : {df_merged['est_cotier'].sum():,} ({100*df_merged['est_cotier'].mean():.1f}%)")
print(f"   Pharmacies montagne   : {df_merged['est_montagne'].sum():,} ({100*df_merged['est_montagne'].mean():.1f}%)")
print(f"   Zones touristiques    : {df_merged['zone_touristique'].sum():,} ({100*df_merged['zone_touristique'].mean():.1f}%)")

# 4. Analyse par TYPE DE ZONE
print("\n4. ANALYSE PAR TYPE DE ZONE")
print(f"\n   Répartition des pharmacies par type de zone :")

for zone in df_merged['type_zone'].dropna().unique():
    df_zone = df_merged[df_merged['type_zone'] == zone]
    corr_un = df_zone['UN'].corr(df_zone['clients_65_plus_total'])
    corr_caht = df_zone['CAHT'].corr(df_zone['clients_65_plus_total'])

    print(f"\n   {zone.upper()} ({len(df_zone):,} pharmacies)")
    print(f"     Clients 65+ moyen   : {df_zone['clients_65_plus_total'].mean():,.0f}")
    print(f"     UN moyen            : {df_zone['UN'].mean():,.0f}")
    print(f"     CAHT moyen          : {df_zone['CAHT'].mean():,.0f} €")
    print(f"     Corr UN-Clients     : {corr_un:.3f}")
    print(f"     Corr CAHT-Clients   : {corr_caht:.3f}")

# 5. Statistiques par type de zone
print("\n5. STATISTIQUES DÉTAILLÉES PAR TYPE DE ZONE")

stats_zone = df_merged.groupby('type_zone').agg({
    'clients_65_plus_total': ['count', 'mean', 'median', 'std'],
    'UN': ['mean', 'median', 'std'],
    'CAHT': ['mean', 'median', 'std']
}).round(2)

print(stats_zone)

# 6. Analyse zones TOURISTIQUES vs NON-TOURISTIQUES
print("\n6. ZONES TOURISTIQUES vs NON-TOURISTIQUES")

for is_tourist, label in [(True, 'TOURISTIQUES'), (False, 'NON-TOURISTIQUES')]:
    df_subset = df_merged[df_merged['zone_touristique'] == is_tourist]

    print(f"\n   {label} ({len(df_subset):,} pharmacies)")
    print(f"     Clients 65+ moyen   : {df_subset['clients_65_plus_total'].mean():,.0f}")
    print(f"     UN moyen            : {df_subset['UN'].mean():,.0f}")
    print(f"     CAHT moyen          : {df_subset['CAHT'].mean():,.0f} €")
    print(f"     Corr UN-Clients     : {df_subset['UN'].corr(df_subset['clients_65_plus_total']):.3f}")
    print(f"     Corr CAHT-Clients   : {df_subset['CAHT'].corr(df_subset['clients_65_plus_total']):.3f}")

# 7. Analyse CÔTIER vs MONTAGNE
print("\n7. ZONES CÔTIÈRES vs MONTAGNE")

for condition, label in [
    (df_merged['est_cotier'], 'CÔTIÈRES'),
    (df_merged['est_montagne'], 'MONTAGNE')
]:
    df_subset = df_merged[condition]

    if len(df_subset) > 0:
        print(f"\n   {label} ({len(df_subset):,} pharmacies)")
        print(f"     Clients 65+ moyen   : {df_subset['clients_65_plus_total'].mean():,.0f}")
        print(f"     UN moyen            : {df_subset['UN'].mean():,.0f}")
        print(f"     CAHT moyen          : {df_subset['CAHT'].mean():,.0f} €")
        print(f"     Corr UN-Clients     : {df_subset['UN'].corr(df_subset['clients_65_plus_total']):.3f}")
        print(f"     Corr CAHT-Clients   : {df_subset['CAHT'].corr(df_subset['clients_65_plus_total']):.3f}")

# 8. Matrice de corrélation par sous-groupe
print("\n8. MATRICES DE CORRÉLATION")

print("\n   GLOBAL :")
corr_global = df_merged[['UN', 'CAHT', 'clients_65_plus_total']].corr()
print(corr_global.round(3))

if df_merged['type_zone'].notna().sum() > 0:
    for zone in ['rural', 'urbain']:
        df_zone = df_merged[df_merged['type_zone'] == zone]
        if len(df_zone) > 10:
            print(f"\n   {zone.upper()} :")
            corr_zone = df_zone[['UN', 'CAHT', 'clients_65_plus_total']].corr()
            print(corr_zone.round(3))

# 9. Créer graphiques
print("\n9. CRÉATION DES GRAPHIQUES")

try:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Graphique 1 : UN vs Clients par type de zone
    if df_merged['type_zone'].notna().sum() > 0:
        for zone in df_merged['type_zone'].dropna().unique():
            df_zone = df_merged[df_merged['type_zone'] == zone]
            axes[0, 0].scatter(df_zone['clients_65_plus_total'], df_zone['UN'],
                             alpha=0.5, label=zone)
        axes[0, 0].set_xlabel('Clients 65+')
        axes[0, 0].set_ylabel('UN')
        axes[0, 0].set_title('UN vs Clients 65+ par type de zone')
        axes[0, 0].legend()

    # Graphique 2 : CAHT vs Clients par type de zone
    if df_merged['type_zone'].notna().sum() > 0:
        for zone in df_merged['type_zone'].dropna().unique():
            df_zone = df_merged[df_merged['type_zone'] == zone]
            axes[0, 1].scatter(df_zone['clients_65_plus_total'], df_zone['CAHT'],
                             alpha=0.5, label=zone)
        axes[0, 1].set_xlabel('Clients 65+')
        axes[0, 1].set_ylabel('CAHT (€)')
        axes[0, 1].set_title('CAHT vs Clients 65+ par type de zone')
        axes[0, 1].legend()

    # Graphique 3 : Boxplot Clients par type de zone
    if df_merged['type_zone'].notna().sum() > 0:
        df_merged.boxplot(column='clients_65_plus_total', by='type_zone', ax=axes[0, 2])
        axes[0, 2].set_title('Clients 65+ par type de zone')
        axes[0, 2].set_xlabel('Type de zone')
        axes[0, 2].set_ylabel('Clients 65+')

    # Graphique 4 : Touristique vs Non-touristique UN
    df_merged.boxplot(column='UN', by='zone_touristique', ax=axes[1, 0])
    axes[1, 0].set_title('UN : Touristique vs Non-touristique')
    axes[1, 0].set_xticklabels(['Non-touristique', 'Touristique'])

    # Graphique 5 : Touristique vs Non-touristique CAHT
    df_merged.boxplot(column='CAHT', by='zone_touristique', ax=axes[1, 1])
    axes[1, 1].set_title('CAHT : Touristique vs Non-touristique')
    axes[1, 1].set_xticklabels(['Non-touristique', 'Touristique'])

    # Graphique 6 : Touristique vs Non-touristique Clients
    df_merged.boxplot(column='clients_65_plus_total', by='zone_touristique', ax=axes[1, 2])
    axes[1, 2].set_title('Clients 65+ : Touristique vs Non-touristique')
    axes[1, 2].set_xticklabels(['Non-touristique', 'Touristique'])

    plt.tight_layout()

    graph_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_avancee_graphs.png"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(graph_path, dpi=150)
    print(f"   Graphiques sauvegardés : {graph_path}")

except Exception as e:
    print(f"   Erreur graphique       : {e}")

# 10. Sauvegarder résultats
print("\n10. SAUVEGARDE")

output_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "correlation_avancee_complete.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
df_merged.to_csv(output_path, index=False)
print(f"   Données sauvegardées   : {output_path}")

# Créer résumé statistique
summary_data = []

for zone in df_merged['type_zone'].dropna().unique():
    df_zone = df_merged[df_merged['type_zone'] == zone]
    summary_data.append({
        'type': 'type_zone',
        'categorie': zone,
        'nb_pharmacies': len(df_zone),
        'clients_65_moyen': df_zone['clients_65_plus_total'].mean(),
        'un_moyen': df_zone['UN'].mean(),
        'caht_moyen': df_zone['CAHT'].mean(),
        'corr_un_clients': df_zone['UN'].corr(df_zone['clients_65_plus_total']),
        'corr_caht_clients': df_zone['CAHT'].corr(df_zone['clients_65_plus_total'])
    })

for is_tourist, label in [(True, 'touristique'), (False, 'non_touristique')]:
    df_subset = df_merged[df_merged['zone_touristique'] == is_tourist]
    summary_data.append({
        'type': 'tourisme',
        'categorie': label,
        'nb_pharmacies': len(df_subset),
        'clients_65_moyen': df_subset['clients_65_plus_total'].mean(),
        'un_moyen': df_subset['UN'].mean(),
        'caht_moyen': df_subset['CAHT'].mean(),
        'corr_un_clients': df_subset['UN'].corr(df_subset['clients_65_plus_total']),
        'corr_caht_clients': df_subset['CAHT'].corr(df_subset['clients_65_plus_total'])
    })

df_summary = pd.DataFrame(summary_data)
summary_path = OUTPUT_FILES['correlation_hubs_medicaux'].parent / "summary_correlations_par_categorie.csv"
summary_path.parent.mkdir(parents=True, exist_ok=True)
df_summary.to_csv(summary_path, index=False)
print(f"   Résumé sauvegardé      : {summary_path}")

print("\n" + "="*80)
print("OK ANALYSE AVANCÉE TERMINÉE")
print("="*80)
