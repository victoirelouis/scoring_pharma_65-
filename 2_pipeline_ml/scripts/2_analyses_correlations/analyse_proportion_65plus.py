"""
Analyse de la proportion de personnes 65+ par rapport à la population totale
à différentes mailles : IRIS, isochrones pharmacies, et comparaison avec les estimations clients
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

from config_ml import OUTPUT_FILES

print("=" * 80)
print("ANALYSE PROPORTION 65+ vs POPULATION TOTALE")
print("=" * 80)

# ============================================================================
# 1. CHARGER LES DONNÉES POPULATION PAR ISOCHRONE
# ============================================================================
print("\n1. CHARGEMENT POPULATION PAR ISOCHRONE")
pop_file = PROJECT_ROOT / "2_pipeline_ml/output/1_etapes_pipeline/pharmacies_avec_population_isochrones.csv"
df_pop = pd.read_csv(pop_file)
print(f"   Pharmacies            : {len(df_pop):,}")

# ============================================================================
# 2. CHARGER LES ESTIMATIONS CLIENTS 65+
# ============================================================================
print("\n2. CHARGEMENT ESTIMATIONS CLIENTS 65+")
df_clients = pd.read_csv(OUTPUT_FILES['pharmacies_clients_65plus_huff'])
print(f"   Pharmacies            : {len(df_clients):,}")

# ============================================================================
# 3. FUSIONNER
# ============================================================================
print("\n3. FUSION DES DONNÉES")
df = df_pop.merge(df_clients[['id_pharmacie', 'clients_65_plus_total']],
                  on='id_pharmacie', how='left')
print(f"   Pharmacies fusionnées : {len(df):,}")

# ============================================================================
# 4. CALCULER LES PROPORTIONS PAR ISOCHRONE
# ============================================================================
print("\n4. CALCUL DES PROPORTIONS 65+ PAR ISOCHRONE")

isochrones = [
    ('walk_5min', 'Marche 5min'),
    ('walk_10min', 'Marche 10min'),
    ('drive_5min', 'Voiture 5min'),
    ('drive_10min', 'Voiture 10min'),
    ('drive_15min', 'Voiture 15min'),
    ('drive_20min', 'Voiture 20min')
]

results_by_isochrone = []

for iso_code, iso_label in isochrones:
    pop_total_col = f'pop_totale_{iso_code}'
    pop_65_col = f'pop_65_plus_{iso_code}'

    if pop_total_col not in df.columns or pop_65_col not in df.columns:
        print(f"   WARNING: Colonnes manquantes pour {iso_label}")
        continue

    # Filtrer les pharmacies avec population > 0
    df_iso = df[(df[pop_total_col] > 0) & (df[pop_65_col] > 0)].copy()

    # Calculer la proportion théorique 65+ dans l'isochrone
    df_iso['proportion_65plus_iso'] = df_iso[pop_65_col] / df_iso[pop_total_col]

    # Calculer la proportion estimée dans les clients
    # (clients 65+ / population totale de l'isochrone)
    df_iso['clients_sur_pop_totale'] = df_iso['clients_65_plus_total'] / df_iso[pop_total_col]

    # Calculer le ratio clients / population 65+ (taux de capture)
    df_iso['taux_capture_65plus'] = df_iso['clients_65_plus_total'] / df_iso[pop_65_col]

    stats = {
        'isochrone': iso_label,
        'n_pharmacies': len(df_iso),
        'proportion_65plus_moy': df_iso['proportion_65plus_iso'].mean(),
        'proportion_65plus_med': df_iso['proportion_65plus_iso'].median(),
        'proportion_65plus_std': df_iso['proportion_65plus_iso'].std(),
        'clients_sur_pop_moy': df_iso['clients_sur_pop_totale'].mean(),
        'clients_sur_pop_med': df_iso['clients_sur_pop_totale'].median(),
        'taux_capture_65plus_moy': df_iso['taux_capture_65plus'].mean(),
        'taux_capture_65plus_med': df_iso['taux_capture_65plus'].median(),
    }
    results_by_isochrone.append(stats)

    print(f"\n   {iso_label}:")
    print(f"      Pharmacies                    : {stats['n_pharmacies']:,}")
    print(f"      Proportion 65+ (isochrone)    : {stats['proportion_65plus_moy']:.1%} (médiane: {stats['proportion_65plus_med']:.1%})")
    print(f"      Clients/Pop totale            : {stats['clients_sur_pop_moy']:.1%} (médiane: {stats['clients_sur_pop_med']:.1%})")
    print(f"      Taux capture 65+ (clients/65+): {stats['taux_capture_65plus_moy']:.1%} (médiane: {stats['taux_capture_65plus_med']:.1%})")

df_results = pd.DataFrame(results_by_isochrone)

# ============================================================================
# 5. ANALYSE DÉTAILLÉE POUR DRIVE 10MIN (isochrone principale du modèle)
# ============================================================================
print("\n5. ANALYSE DÉTAILLÉE - DRIVE 10MIN (isochrone du modèle)")

df_main = df[(df['pop_totale_drive_10min'] > 0) & (df['pop_65_plus_drive_10min'] > 0)].copy()
df_main['proportion_65plus'] = df_main['pop_65_plus_drive_10min'] / df_main['pop_totale_drive_10min']
df_main['clients_sur_pop_totale'] = df_main['clients_65_plus_total'] / df_main['pop_totale_drive_10min']
df_main['taux_capture_65plus'] = df_main['clients_65_plus_total'] / df_main['pop_65_plus_drive_10min']

print(f"\n   a) Distribution de la proportion 65+ dans les isochrones:")
print(f"      Min    : {df_main['proportion_65plus'].min():.1%}")
print(f"      Q25    : {df_main['proportion_65plus'].quantile(0.25):.1%}")
print(f"      Médiane: {df_main['proportion_65plus'].median():.1%}")
print(f"      Q75    : {df_main['proportion_65plus'].quantile(0.75):.1%}")
print(f"      Max    : {df_main['proportion_65plus'].max():.1%}")
print(f"      Moyenne: {df_main['proportion_65plus'].mean():.1%}")

print(f"\n   b) Distribution du taux de capture (clients 65+ / population 65+):")
print(f"      Min    : {df_main['taux_capture_65plus'].min():.1%}")
print(f"      Q25    : {df_main['taux_capture_65plus'].quantile(0.25):.1%}")
print(f"      Médiane: {df_main['taux_capture_65plus'].median():.1%}")
print(f"      Q75    : {df_main['taux_capture_65plus'].quantile(0.75):.1%}")
print(f"      Max    : {df_main['taux_capture_65plus'].max():.1%}")
print(f"      Moyenne: {df_main['taux_capture_65plus'].mean():.1%}")

# Analyse par type de zone
print(f"\n   c) Par type de zone:")
for zone_type in df_main['type_zone'].unique():
    df_zone = df_main[df_main['type_zone'] == zone_type]
    print(f"\n      {zone_type.upper()}:")
    print(f"         Pharmacies              : {len(df_zone):,}")
    print(f"         Proportion 65+ moyenne  : {df_zone['proportion_65plus'].mean():.1%}")
    print(f"         Taux capture 65+ moyen  : {df_zone['taux_capture_65plus'].mean():.1%}")

# Analyse par décile de proportion 65+
print(f"\n   d) Par décile de proportion 65+ dans l'isochrone:")
df_main['decile_65plus'] = pd.qcut(df_main['proportion_65plus'], 10, labels=False, duplicates='drop')
for decile in sorted(df_main['decile_65plus'].unique()):
    df_dec = df_main[df_main['decile_65plus'] == decile]
    print(f"\n      Décile {int(decile)+1}:")
    print(f"         Proportion 65+ isochrone: {df_dec['proportion_65plus'].mean():.1%}")
    print(f"         Taux capture 65+ moyen  : {df_dec['taux_capture_65plus'].mean():.1%}")
    print(f"         Pharmacies              : {len(df_dec):,}")

# ============================================================================
# 6. VÉRIFICATION: COHÉRENCE DES PROPORTIONS
# ============================================================================
print("\n6. VÉRIFICATION COHÉRENCE")

# Le taux de capture devrait être autour de 1.0 si le modèle est bien calibré
df_main['deviation_capture'] = abs(df_main['taux_capture_65plus'] - 1.0)

print(f"\n   Écart moyen au taux de capture idéal (1.0):")
print(f"      Moyenne    : {df_main['deviation_capture'].mean():.2%}")
print(f"      Médiane    : {df_main['deviation_capture'].median():.2%}")

# Pharmacies avec bon taux de capture (entre 0.8 et 1.2)
df_good = df_main[(df_main['taux_capture_65plus'] >= 0.8) & (df_main['taux_capture_65plus'] <= 1.2)]
print(f"\n   Pharmacies avec taux capture entre 0.8 et 1.2:")
print(f"      Nombre     : {len(df_good):,} / {len(df_main):,} ({len(df_good)/len(df_main)*100:.1f}%)")

# Pharmacies avec sur-estimation (> 1.2)
df_over = df_main[df_main['taux_capture_65plus'] > 1.2]
print(f"\n   Pharmacies avec sur-estimation (> 1.2):")
print(f"      Nombre     : {len(df_over):,} ({len(df_over)/len(df_main)*100:.1f}%)")
print(f"      Taux moyen : {df_over['taux_capture_65plus'].mean():.2f}")

# Pharmacies avec sous-estimation (< 0.8)
df_under = df_main[df_main['taux_capture_65plus'] < 0.8]
print(f"\n   Pharmacies avec sous-estimation (< 0.8):")
print(f"      Nombre     : {len(df_under):,} ({len(df_under)/len(df_main)*100:.1f}%)")
print(f"      Taux moyen : {df_over['taux_capture_65plus'].mean():.2f}")

# ============================================================================
# 7. SAUVEGARDER LES RÉSULTATS
# ============================================================================
print("\n7. SAUVEGARDE")

output_dir = PROJECT_ROOT / "2_pipeline_ml/output/3_analyses_correlations"
output_dir.mkdir(exist_ok=True, parents=True)

# Synthèse par isochrone
output_file_syn = output_dir / "proportion_65plus_par_isochrone.csv"
df_results.to_csv(output_file_syn, index=False, encoding='utf-8-sig')
print(f"   Synthèse isochrones   : {output_file_syn}")

# Détail par pharmacie (drive 10min)
output_file_det = output_dir / "proportion_65plus_par_pharmacie.csv"
df_main_export = df_main[[
    'id_pharmacie', 'nom_pharmacie', 'type_zone',
    'pop_totale_drive_10min', 'pop_65_plus_drive_10min',
    'clients_65_plus_total', 'proportion_65plus',
    'taux_capture_65plus', 'deviation_capture'
]].copy()
df_main_export.to_csv(output_file_det, index=False, encoding='utf-8-sig')
print(f"   Détail pharmacies     : {output_file_det}")

# ============================================================================
# 8. GRAPHIQUES
# ============================================================================
print("\n8. CRÉATION DES GRAPHIQUES")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Analyse Proportion 65+ et Taux de Capture - Drive 10min', fontsize=16, fontweight='bold')

# 1. Distribution proportion 65+ dans isochrones
ax1 = axes[0, 0]
ax1.hist(df_main['proportion_65plus'], bins=50, edgecolor='black', alpha=0.7)
ax1.axvline(df_main['proportion_65plus'].mean(), color='red', linestyle='--',
            label=f'Moyenne: {df_main["proportion_65plus"].mean():.1%}')
ax1.axvline(df_main['proportion_65plus'].median(), color='green', linestyle='--',
            label=f'Médiane: {df_main["proportion_65plus"].median():.1%}')
ax1.set_xlabel('Proportion 65+ dans isochrone')
ax1.set_ylabel('Nombre de pharmacies')
ax1.set_title('Distribution de la proportion 65+ dans les isochrones')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Distribution taux de capture
ax2 = axes[0, 1]
# Limiter l'axe x pour meilleure lisibilité
df_main_plot = df_main[df_main['taux_capture_65plus'] <= 3.0]
ax2.hist(df_main_plot['taux_capture_65plus'], bins=50, edgecolor='black', alpha=0.7)
ax2.axvline(1.0, color='red', linestyle='--', linewidth=2, label='Idéal: 1.0')
ax2.axvline(df_main_plot['taux_capture_65plus'].mean(), color='orange', linestyle='--',
            label=f'Moyenne: {df_main_plot["taux_capture_65plus"].mean():.2f}')
ax2.axvline(df_main_plot['taux_capture_65plus'].median(), color='green', linestyle='--',
            label=f'Médiane: {df_main_plot["taux_capture_65plus"].median():.2f}')
ax2.set_xlabel('Taux de capture (clients 65+ / pop 65+)')
ax2.set_ylabel('Nombre de pharmacies')
ax2.set_title('Distribution du taux de capture 65+')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Proportion 65+ par type de zone
ax3 = axes[0, 2]
zone_stats = df_main.groupby('type_zone')['proportion_65plus'].agg(['mean', 'median']).reset_index()
x = range(len(zone_stats))
width = 0.35
ax3.bar([i - width/2 for i in x], zone_stats['mean'], width, label='Moyenne', alpha=0.8)
ax3.bar([i + width/2 for i in x], zone_stats['median'], width, label='Médiane', alpha=0.8)
ax3.set_xticks(x)
ax3.set_xticklabels(zone_stats['type_zone'])
ax3.set_ylabel('Proportion 65+')
ax3.set_title('Proportion 65+ par type de zone')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# 4. Taux de capture par type de zone
ax4 = axes[1, 0]
zone_capture = df_main.groupby('type_zone')['taux_capture_65plus'].agg(['mean', 'median']).reset_index()
ax4.bar([i - width/2 for i in x], zone_capture['mean'], width, label='Moyenne', alpha=0.8)
ax4.bar([i + width/2 for i in x], zone_capture['median'], width, label='Médiane', alpha=0.8)
ax4.axhline(1.0, color='red', linestyle='--', linewidth=2, label='Idéal: 1.0')
ax4.set_xticks(x)
ax4.set_xticklabels(zone_capture['type_zone'])
ax4.set_ylabel('Taux de capture')
ax4.set_title('Taux de capture 65+ par type de zone')
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

# 5. Scatter: Proportion 65+ vs Taux de capture
ax5 = axes[1, 1]
scatter = ax5.scatter(df_main['proportion_65plus'], df_main['taux_capture_65plus'],
                     c=df_main['type_zone'].map({'rural': 0, 'urbain': 1, 'urbain_dense': 2}),
                     alpha=0.5, s=10, cmap='viridis')
ax5.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.5)
ax5.set_xlabel('Proportion 65+ dans isochrone')
ax5.set_ylabel('Taux de capture (clients/pop 65+)')
ax5.set_title('Relation proportion 65+ vs taux de capture')
ax5.set_ylim(0, 3)
ax5.grid(True, alpha=0.3)
# Legend for colors
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=plt.cm.viridis(0), label='Rural'),
                  Patch(facecolor=plt.cm.viridis(0.5), label='Urbain'),
                  Patch(facecolor=plt.cm.viridis(1), label='Urbain dense')]
ax5.legend(handles=legend_elements, loc='upper right')

# 6. Taux de capture par décile de proportion 65+
ax6 = axes[1, 2]
decile_stats = df_main.groupby('decile_65plus').agg({
    'proportion_65plus': 'mean',
    'taux_capture_65plus': 'mean'
}).reset_index()
ax6_twin = ax6.twinx()
line1 = ax6.plot(decile_stats['decile_65plus'], decile_stats['proportion_65plus'],
                'o-', color='blue', label='Proportion 65+', linewidth=2, markersize=8)
line2 = ax6_twin.plot(decile_stats['decile_65plus'], decile_stats['taux_capture_65plus'],
                     's-', color='orange', label='Taux capture', linewidth=2, markersize=8)
ax6_twin.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.5)
ax6.set_xlabel('Décile de proportion 65+')
ax6.set_ylabel('Proportion 65+ moyenne', color='blue')
ax6_twin.set_ylabel('Taux capture moyen', color='orange')
ax6.set_title('Taux de capture par décile de proportion 65+')
ax6.tick_params(axis='y', labelcolor='blue')
ax6_twin.tick_params(axis='y', labelcolor='orange')
ax6.grid(True, alpha=0.3)
# Combine legends
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax6.legend(lines, labels, loc='upper left')

plt.tight_layout()
output_graph = output_dir / "analyse_proportion_65plus_graphs.png"
plt.savefig(output_graph, dpi=150, bbox_inches='tight')
print(f"   Graphiques            : {output_graph}")

print("\n" + "=" * 80)
print("OK ANALYSE TERMINÉE")
print("=" * 80)