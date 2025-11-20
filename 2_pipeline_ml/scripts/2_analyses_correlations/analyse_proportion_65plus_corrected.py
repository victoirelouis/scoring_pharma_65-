"""
Analyse CORRIGÉE de la proportion de personnes 65+
Utilise la matrice pharmacie-IRIS pour calculer correctement les taux sans duplication
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "2_pipeline_ml/scripts/3_utilitaires"))

from config_ml import INPUT_FILES, INTERMEDIATE_FILES, OUTPUT_FILES

print("=" * 80)
print("ANALYSE PROPORTION 65+ vs POPULATION TOTALE (VERSION CORRIGÉE)")
print("=" * 80)

# ============================================================================
# 1. CHARGER LES DONNÉES
# ============================================================================
print("\n1. CHARGEMENT DES DONNÉES")

# Population IRIS
df_iris_pop = pd.read_csv(INPUT_FILES['population_age_csv'], sep=';', dtype={'IRIS': str})
df_iris_pop = df_iris_pop.rename(columns={
    'IRIS': 'CODE_IRIS',
    'P22_POP': 'pop_totale',
    'P22_POP65P': 'pop_65_plus',
    'P22_POP6579': 'pop_65_79',
    'P22_POP80P': 'pop_80_plus'
})
print(f"   IRIS France           : {len(df_iris_pop):,}")
print(f"   Population totale     : {df_iris_pop['pop_totale'].sum():,.0f}")
print(f"   Population 65+        : {df_iris_pop['pop_65_plus'].sum():,.0f}")
print(f"   Proportion 65+ France : {df_iris_pop['pop_65_plus'].sum() / df_iris_pop['pop_totale'].sum():.1%}")

# Matrice pharmacie-IRIS (avec w_IRIS)
df_matrice = pd.read_csv(INTERMEDIATE_FILES['matrice_pharmacie_iris_cleaned'])
print(f"\n   Matrice pharmacie-IRIS: {len(df_matrice):,} relations")
print(f"   Pharmacies            : {df_matrice['id_pharmacie'].nunique():,}")
print(f"   IRIS couverts         : {df_matrice['CODE_IRIS'].nunique():,}")

# Estimations clients
df_clients = pd.read_csv(OUTPUT_FILES['pharmacies_clients_65plus_huff'])
print(f"\n   Clients estimés       : {len(df_clients):,} pharmacies")
print(f"   Clients 65+ total     : {df_clients['clients_65_plus_total'].sum():,.0f}")

# Infos pharmacies (type_zone)
df_pharma = pd.read_csv(INPUT_FILES['pharmacies'], sep=';',
                        usecols=['id_pharmacie', 'nom_pharmacie', 'type_zone'])

# ============================================================================
# 2. CALCULER POPULATION COUVERTE (SANS DUPLICATION)
# ============================================================================
print("\n2. CALCUL POPULATION COUVERTE (IRIS UNIQUES)")

# IRIS couverts = IRIS qui ont au moins une pharmacie accessible
iris_couverts = df_matrice['CODE_IRIS'].unique()
df_iris_couverts = df_iris_pop[df_iris_pop['CODE_IRIS'].isin(iris_couverts)].copy()

print(f"   IRIS couverts         : {len(df_iris_couverts):,}")
print(f"   Population totale     : {df_iris_couverts['pop_totale'].sum():,.0f}")
print(f"   Population 65+        : {df_iris_couverts['pop_65_plus'].sum():,.0f}")
print(f"   Proportion 65+ couverte: {df_iris_couverts['pop_65_plus'].sum() / df_iris_couverts['pop_totale'].sum():.1%}")

# Taux de conservation global
taux_conservation = df_clients['clients_65_plus_total'].sum() / df_iris_couverts['pop_65_plus'].sum()
print(f"\n   TAUX CONSERVATION GLOBAL: {taux_conservation:.1%}")

# ============================================================================
# 3. ANALYSE PAR PHARMACIE : POPULATION THÉORIQUE vs CLIENTS ESTIMÉS
# ============================================================================
print("\n3. ANALYSE PAR PHARMACIE")

# Pour chaque pharmacie, calculer la population 65+ théorique dans son "bassin"
# Bassin = IRIS accessibles pondérés par w_IRIS

df_bassin = df_matrice.merge(
    df_iris_pop[['CODE_IRIS', 'pop_totale', 'pop_65_plus']],
    on='CODE_IRIS',
    how='left'
)

# Population théorique pondérée par w_IRIS
df_bassin['pop_totale_ponderee'] = df_bassin['pop_totale'] * df_bassin['w_IRIS']
df_bassin['pop_65_plus_ponderee'] = df_bassin['pop_65_plus'] * df_bassin['w_IRIS']

# Agréger par pharmacie
df_pharma_pop = df_bassin.groupby('id_pharmacie').agg({
    'pop_totale_ponderee': 'sum',
    'pop_65_plus_ponderee': 'sum'
}).reset_index()

df_pharma_pop.columns = ['id_pharmacie', 'bassin_pop_totale', 'bassin_pop_65plus']

# Fusionner avec les clients estimés
df_analyse = df_pharma_pop.merge(
    df_clients[['id_pharmacie', 'clients_65_plus_total']],
    on='id_pharmacie',
    how='left'
)

# Ajouter type_zone
df_analyse = df_analyse.merge(
    df_pharma[['id_pharmacie', 'nom_pharmacie', 'type_zone']],
    on='id_pharmacie',
    how='left'
)

# Filtrer les pharmacies avec population > 0
df_analyse = df_analyse[df_analyse['bassin_pop_65plus'] > 0].copy()

# Calculer les métriques
df_analyse['proportion_65plus_bassin'] = df_analyse['bassin_pop_65plus'] / df_analyse['bassin_pop_totale']
df_analyse['taux_capture'] = df_analyse['clients_65_plus_total'] / df_analyse['bassin_pop_65plus']
df_analyse['deviation_capture'] = abs(df_analyse['taux_capture'] - 1.0)

print(f"   Pharmacies analysées  : {len(df_analyse):,}")

# ============================================================================
# 4. STATISTIQUES GLOBALES
# ============================================================================
print("\n4. STATISTIQUES GLOBALES")

print(f"\n   a) Proportion 65+ dans les bassins:")
print(f"      Min    : {df_analyse['proportion_65plus_bassin'].min():.1%}")
print(f"      Q25    : {df_analyse['proportion_65plus_bassin'].quantile(0.25):.1%}")
print(f"      Médiane: {df_analyse['proportion_65plus_bassin'].median():.1%}")
print(f"      Q75    : {df_analyse['proportion_65plus_bassin'].quantile(0.75):.1%}")
print(f"      Max    : {df_analyse['proportion_65plus_bassin'].max():.1%}")
print(f"      Moyenne: {df_analyse['proportion_65plus_bassin'].mean():.1%}")

print(f"\n   b) Taux de capture (clients / population 65+ bassin):")
print(f"      Min    : {df_analyse['taux_capture'].min():.2f}")
print(f"      Q25    : {df_analyse['taux_capture'].quantile(0.25):.2f}")
print(f"      Médiane: {df_analyse['taux_capture'].median():.2f}")
print(f"      Q75    : {df_analyse['taux_capture'].quantile(0.75):.2f}")
print(f"      Max    : {df_analyse['taux_capture'].max():.2f}")
print(f"      Moyenne: {df_analyse['taux_capture'].mean():.2f}")

# ============================================================================
# 5. ANALYSE PAR TYPE DE ZONE
# ============================================================================
print("\n5. ANALYSE PAR TYPE DE ZONE")

for zone_type in sorted(df_analyse['type_zone'].unique()):
    df_zone = df_analyse[df_analyse['type_zone'] == zone_type]
    print(f"\n   {zone_type.upper()}:")
    print(f"      Pharmacies              : {len(df_zone):,}")
    print(f"      Proportion 65+ moyenne  : {df_zone['proportion_65plus_bassin'].mean():.1%}")
    print(f"      Taux capture moyen      : {df_zone['taux_capture'].mean():.2f}")
    print(f"      Taux capture médian     : {df_zone['taux_capture'].median():.2f}")

# ============================================================================
# 6. ANALYSE PAR DÉCILE DE PROPORTION 65+
# ============================================================================
print("\n6. ANALYSE PAR DÉCILE DE PROPORTION 65+")

df_analyse['decile_65plus'] = pd.qcut(df_analyse['proportion_65plus_bassin'], 10,
                                       labels=False, duplicates='drop')

for decile in sorted(df_analyse['decile_65plus'].unique()):
    df_dec = df_analyse[df_analyse['decile_65plus'] == decile]
    print(f"\n   Décile {int(decile)+1}:")
    print(f"      Proportion 65+ moyenne  : {df_dec['proportion_65plus_bassin'].mean():.1%}")
    print(f"      Taux capture moyen      : {df_dec['taux_capture'].mean():.2f}")
    print(f"      Taux capture médian     : {df_dec['taux_capture'].median():.2f}")
    print(f"      Pharmacies              : {len(df_dec):,}")

# ============================================================================
# 7. VÉRIFICATION COHÉRENCE
# ============================================================================
print("\n7. VÉRIFICATION COHÉRENCE")

# Pharmacies avec bon taux de capture (entre 0.8 et 1.2)
df_good = df_analyse[(df_analyse['taux_capture'] >= 0.8) & (df_analyse['taux_capture'] <= 1.2)]
print(f"\n   Pharmacies avec taux capture 0.8-1.2:")
print(f"      Nombre     : {len(df_good):,} / {len(df_analyse):,} ({len(df_good)/len(df_analyse)*100:.1f}%)")

# Pharmacies avec sur-estimation (> 1.2)
df_over = df_analyse[df_analyse['taux_capture'] > 1.2]
print(f"\n   Pharmacies avec sur-estimation (> 1.2):")
print(f"      Nombre     : {len(df_over):,} ({len(df_over)/len(df_analyse)*100:.1f}%)")
print(f"      Taux moyen : {df_over['taux_capture'].mean():.2f}")
print(f"      Taux médian: {df_over['taux_capture'].median():.2f}")

# Pharmacies avec sous-estimation (< 0.8)
df_under = df_analyse[df_analyse['taux_capture'] < 0.8]
print(f"\n   Pharmacies avec sous-estimation (< 0.8):")
print(f"      Nombre     : {len(df_under):,} ({len(df_under)/len(df_analyse)*100:.1f}%)")
print(f"      Taux moyen : {df_under['taux_capture'].mean():.2f}")
print(f"      Taux médian: {df_under['taux_capture'].median():.2f}")

# ============================================================================
# 8. ANALYSE DE LA RELATION ENTRE PROPORTION 65+ ET TAUX DE CAPTURE
# ============================================================================
print("\n8. CORRÉLATION PROPORTION 65+ vs TAUX DE CAPTURE")

corr = df_analyse['proportion_65plus_bassin'].corr(df_analyse['taux_capture'])
print(f"\n   Corrélation Pearson   : {corr:.3f}")

# Par type de zone
for zone_type in sorted(df_analyse['type_zone'].unique()):
    df_zone = df_analyse[df_analyse['type_zone'] == zone_type]
    corr_zone = df_zone['proportion_65plus_bassin'].corr(df_zone['taux_capture'])
    print(f"   Corrélation {zone_type:12s}: {corr_zone:.3f}")

# ============================================================================
# 9. SAUVEGARDER LES RÉSULTATS
# ============================================================================
print("\n9. SAUVEGARDE")

output_dir = PROJECT_ROOT / "2_pipeline_ml/output/3_analyses_correlations"
output_dir.mkdir(exist_ok=True, parents=True)

# Détail par pharmacie
output_file = output_dir / "analyse_proportion_65plus_par_pharmacie_corrected.csv"
df_analyse_export = df_analyse[[
    'id_pharmacie', 'nom_pharmacie', 'type_zone',
    'bassin_pop_totale', 'bassin_pop_65plus',
    'clients_65_plus_total', 'proportion_65plus_bassin',
    'taux_capture', 'deviation_capture'
]].copy()
df_analyse_export.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"   Détail pharmacies     : {output_file}")

# Statistiques par type de zone
zone_stats = df_analyse.groupby('type_zone').agg({
    'id_pharmacie': 'count',
    'proportion_65plus_bassin': ['mean', 'median'],
    'taux_capture': ['mean', 'median'],
    'bassin_pop_65plus': 'sum',
    'clients_65_plus_total': 'sum'
}).reset_index()
zone_stats.columns = ['type_zone', 'n_pharmacies', 'prop_65plus_mean', 'prop_65plus_median',
                     'taux_capture_mean', 'taux_capture_median', 'pop_65plus_sum', 'clients_sum']
zone_stats['taux_conservation'] = zone_stats['clients_sum'] / zone_stats['pop_65plus_sum']

output_zone = output_dir / "analyse_proportion_65plus_par_zone.csv"
zone_stats.to_csv(output_zone, index=False, encoding='utf-8-sig')
print(f"   Stats par zone        : {output_zone}")

# ============================================================================
# 10. GRAPHIQUES
# ============================================================================
print("\n10. CRÉATION DES GRAPHIQUES")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Analyse Proportion 65+ et Taux de Capture (VERSION CORRIGÉE)',
             fontsize=16, fontweight='bold')

# 1. Distribution proportion 65+
ax1 = axes[0, 0]
ax1.hist(df_analyse['proportion_65plus_bassin'], bins=50, edgecolor='black', alpha=0.7)
ax1.axvline(df_analyse['proportion_65plus_bassin'].mean(), color='red', linestyle='--',
            label=f'Moyenne: {df_analyse["proportion_65plus_bassin"].mean():.1%}')
ax1.axvline(df_analyse['proportion_65plus_bassin'].median(), color='green', linestyle='--',
            label=f'Médiane: {df_analyse["proportion_65plus_bassin"].median():.1%}')
ax1.set_xlabel('Proportion 65+ dans le bassin')
ax1.set_ylabel('Nombre de pharmacies')
ax1.set_title('Distribution de la proportion 65+ dans les bassins')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Distribution taux de capture
ax2 = axes[0, 1]
# Limiter pour meilleure lisibilité
df_plot = df_analyse[df_analyse['taux_capture'] <= 3.0]
ax2.hist(df_plot['taux_capture'], bins=50, edgecolor='black', alpha=0.7)
ax2.axvline(1.0, color='red', linestyle='--', linewidth=2, label='Idéal: 1.0')
ax2.axvline(df_plot['taux_capture'].mean(), color='orange', linestyle='--',
            label=f'Moyenne: {df_plot["taux_capture"].mean():.2f}')
ax2.axvline(df_plot['taux_capture'].median(), color='green', linestyle='--',
            label=f'Médiane: {df_plot["taux_capture"].median():.2f}')
ax2.set_xlabel('Taux de capture (clients / pop 65+ bassin)')
ax2.set_ylabel('Nombre de pharmacies')
ax2.set_title('Distribution du taux de capture')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Proportion 65+ par type de zone
ax3 = axes[0, 2]
zone_data = df_analyse.groupby('type_zone')['proportion_65plus_bassin'].agg(['mean', 'median']).reset_index()
x = range(len(zone_data))
width = 0.35
ax3.bar([i - width/2 for i in x], zone_data['mean'], width, label='Moyenne', alpha=0.8)
ax3.bar([i + width/2 for i in x], zone_data['median'], width, label='Médiane', alpha=0.8)
ax3.set_xticks(x)
ax3.set_xticklabels(zone_data['type_zone'], rotation=45, ha='right')
ax3.set_ylabel('Proportion 65+')
ax3.set_title('Proportion 65+ par type de zone')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# 4. Taux de capture par type de zone
ax4 = axes[1, 0]
zone_capture = df_analyse.groupby('type_zone')['taux_capture'].agg(['mean', 'median']).reset_index()
ax4.bar([i - width/2 for i in x], zone_capture['mean'], width, label='Moyenne', alpha=0.8)
ax4.bar([i + width/2 for i in x], zone_capture['median'], width, label='Médiane', alpha=0.8)
ax4.axhline(1.0, color='red', linestyle='--', linewidth=2, label='Idéal: 1.0')
ax4.set_xticks(x)
ax4.set_xticklabels(zone_capture['type_zone'], rotation=45, ha='right')
ax4.set_ylabel('Taux de capture')
ax4.set_title('Taux de capture par type de zone')
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

# 5. Scatter: Proportion 65+ vs Taux de capture
ax5 = axes[1, 1]
zone_colors = {'rural': 0, 'urbain': 1, 'urbain_dense': 2, 'periurbain': 1.5}
colors = df_analyse['type_zone'].map(zone_colors)
scatter = ax5.scatter(df_analyse['proportion_65plus_bassin'],
                     df_analyse['taux_capture'],
                     c=colors, alpha=0.5, s=10, cmap='viridis')
ax5.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Idéal: 1.0')
ax5.set_xlabel('Proportion 65+ dans bassin')
ax5.set_ylabel('Taux de capture')
ax5.set_title(f'Relation proportion 65+ vs taux capture (r={corr:.3f})')
ax5.set_ylim(0, 3)
ax5.legend()
ax5.grid(True, alpha=0.3)

# 6. Taux de capture par décile
ax6 = axes[1, 2]
decile_stats = df_analyse.groupby('decile_65plus').agg({
    'proportion_65plus_bassin': 'mean',
    'taux_capture': 'mean'
}).reset_index()
ax6_twin = ax6.twinx()
line1 = ax6.plot(decile_stats['decile_65plus'], decile_stats['proportion_65plus_bassin'],
                'o-', color='blue', label='Proportion 65+', linewidth=2, markersize=8)
line2 = ax6_twin.plot(decile_stats['decile_65plus'], decile_stats['taux_capture'],
                     's-', color='orange', label='Taux capture', linewidth=2, markersize=8)
ax6_twin.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.5)
ax6.set_xlabel('Décile de proportion 65+')
ax6.set_ylabel('Proportion 65+ moyenne', color='blue')
ax6_twin.set_ylabel('Taux capture moyen', color='orange')
ax6.set_title('Taux de capture par décile')
ax6.tick_params(axis='y', labelcolor='blue')
ax6_twin.tick_params(axis='y', labelcolor='orange')
ax6.grid(True, alpha=0.3)
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax6.legend(lines, labels, loc='upper left')

plt.tight_layout()
output_graph = output_dir / "analyse_proportion_65plus_corrected_graphs.png"
plt.savefig(output_graph, dpi=150, bbox_inches='tight')
print(f"   Graphiques            : {output_graph}")

print("\n" + "=" * 80)
print("OK ANALYSE TERMINÉE")
print("=" * 80)