"""
Analyse de corrélation en fonction de la proximité des hubs médicaux
(cabinets médicaux, hôpitaux)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
import sys

# Ajouter le répertoire config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_ml import (
    INPUT_FILES,
    OUTPUT_FILES,
    PROJECT_ROOT
)

print("="*80)
print("ANALYSE PROXIMITÉ HUBS MÉDICAUX")
print("="*80)

# 1. Charger les HUBS
print("\n1. CHARGEMENT DES HUBS MÉDICAUX")

df_hubs = pd.read_csv(
    INPUT_FILES['hubs'],
    sep=';'
)

print(f"   Total hubs            : {len(df_hubs):,}")

# Filtrer hubs médicaux
hubs_medicaux = df_hubs[df_hubs['categorie'].isin(['Cabinet médical', 'Hôpital'])].copy()
print(f"   Hubs médicaux         : {len(hubs_medicaux):,}")
print(f"     Cabinets médicaux   : {(hubs_medicaux['categorie'] == 'Cabinet médical').sum():,}")
print(f"     Hôpitaux            : {(hubs_medicaux['categorie'] == 'Hôpital').sum():,}")

# Nettoyer coordonnées NaN
hubs_medicaux = hubs_medicaux.dropna(subset=['latitude', 'longitude'])
print(f"   Avec coordonnées      : {len(hubs_medicaux):,}")

# 2. Charger les pharmacies
print("\n2. CHARGEMENT DES PHARMACIES")

df_pharmacies_base = pd.read_csv(
    INPUT_FILES['pharmacies'],
    sep=';'
)

print(f"   Pharmacies totales    : {len(df_pharmacies_base):,}")

# 3. Charger données SIG et clients
print("\n3. CHARGEMENT DONNÉES COMPLÉMENTAIRES")

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

df_clients = pd.read_csv(
    OUTPUT_FILES['pharmacies_clients_65plus_huff']
)

# Variables touristiques
df_tourisme = pd.read_csv(
    INPUT_FILES['variables_touristiques']
)

print(f"   SIG P20               : {len(df_sig_agg):,} pharmacies")
print(f"   Clients 65+           : {len(df_clients):,} pharmacies")
print(f"   Variables tourisme    : {len(df_tourisme):,} pharmacies")

# 4. Calculer proximité des hubs médicaux
print("\n4. CALCUL DE PROXIMITÉ AUX HUBS MÉDICAUX")

# Nettoyer coordonnées NaN pharmacies
df_pharmacies_base = df_pharmacies_base.dropna(subset=['latitude', 'longitude'])
print(f"   Pharmacies avec coord : {len(df_pharmacies_base):,}")

# Préparer les coordonnées
pharma_coords = df_pharmacies_base[['latitude', 'longitude']].values
hub_coords = hubs_medicaux[['latitude', 'longitude']].values

# Créer KD-Tree pour recherche rapide
tree = cKDTree(hub_coords)

# Calculer distances aux hubs les plus proches
distances_500m, indices_500m = tree.query(pharma_coords, k=50, distance_upper_bound=0.0045)  # ~500m
distances_1km, indices_1km = tree.query(pharma_coords, k=100, distance_upper_bound=0.009)    # ~1km
distances_2km, indices_2km = tree.query(pharma_coords, k=200, distance_upper_bound=0.018)    # ~2km

# Compter hubs dans chaque rayon
df_pharmacies_base['nb_hubs_medicaux_500m'] = np.sum(distances_500m < 0.0045, axis=1)
df_pharmacies_base['nb_hubs_medicaux_1km'] = np.sum(distances_1km < 0.009, axis=1)
df_pharmacies_base['nb_hubs_medicaux_2km'] = np.sum(distances_2km < 0.018, axis=1)

# Distance au hub le plus proche
df_pharmacies_base['distance_hub_plus_proche_km'] = distances_500m[:, 0] * 111  # conversion deg -> km

print(f"   Pharmacies analysées  : {len(df_pharmacies_base):,}")
print(f"\n   Statistiques proximité :")
print(f"     Moy hubs 500m       : {df_pharmacies_base['nb_hubs_medicaux_500m'].mean():.1f}")
print(f"     Moy hubs 1km        : {df_pharmacies_base['nb_hubs_medicaux_1km'].mean():.1f}")
print(f"     Moy hubs 2km        : {df_pharmacies_base['nb_hubs_medicaux_2km'].mean():.1f}")
print(f"     Distance moy hub    : {df_pharmacies_base['distance_hub_plus_proche_km'].mean():.2f} km")

# 5. Fusionner toutes les données
print("\n5. FUSION DES DONNÉES")

df_merged = df_pharmacies_base.merge(
    df_sig_agg,
    on='id_pharmacie',
    how='inner'
)

df_merged = df_merged.merge(
    df_clients[['id_pharmacie', 'clients_65_plus_total', 'visites_annuelles_65plus']],
    on='id_pharmacie',
    how='inner'
)

df_merged = df_merged.merge(
    df_tourisme,
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

# 6. Créer catégories de proximité
print("\n6. CATÉGORISATION PAR PROXIMITÉ")

df_merged['categorie_proximite'] = pd.cut(
    df_merged['nb_hubs_medicaux_1km'],
    bins=[-1, 0, 1, 3, 10, 1000],
    labels=['Aucun hub', '1 hub', '2-3 hubs', '4-10 hubs', '>10 hubs']
)

for cat in df_merged['categorie_proximite'].cat.categories:
    df_cat = df_merged[df_merged['categorie_proximite'] == cat]
    print(f"   {cat:15s} : {len(df_cat):,} pharmacies ({100*len(df_cat)/len(df_merged):.1f}%)")

# 7. Analyse par catégorie de proximité
print("\n7. CORRÉLATIONS PAR PROXIMITÉ AUX HUBS")

for cat in df_merged['categorie_proximite'].cat.categories:
    df_cat = df_merged[df_merged['categorie_proximite'] == cat]

    if len(df_cat) > 10:
        corr_un = df_cat['UN'].corr(df_cat['clients_65_plus_total'])
        corr_caht = df_cat['CAHT'].corr(df_cat['clients_65_plus_total'])

        print(f"\n   {cat.upper()} ({len(df_cat):,} pharmacies)")
        print(f"     Clients 65+ moyen   : {df_cat['clients_65_plus_total'].mean():,.0f}")
        print(f"     UN moyen            : {df_cat['UN'].mean():,.0f}")
        print(f"     CAHT moyen          : {df_cat['CAHT'].mean():,.0f} €")
        print(f"     Corr UN-Clients     : {corr_un:.3f}")
        print(f"     Corr CAHT-Clients   : {corr_caht:.3f}")

# 8. Analyse continue (régression)
print("\n8. CORRÉLATION AVEC NOMBRE DE HUBS (CONTINUE)")

corr_hubs_500m = df_merged['nb_hubs_medicaux_500m'].corr(df_merged['clients_65_plus_total'])
corr_hubs_1km = df_merged['nb_hubs_medicaux_1km'].corr(df_merged['clients_65_plus_total'])
corr_hubs_2km = df_merged['nb_hubs_medicaux_2km'].corr(df_merged['clients_65_plus_total'])
corr_distance = df_merged['distance_hub_plus_proche_km'].corr(df_merged['clients_65_plus_total'])

print(f"   Nb hubs 500m vs Clients 65+  : {corr_hubs_500m:.3f}")
print(f"   Nb hubs 1km vs Clients 65+   : {corr_hubs_1km:.3f}")
print(f"   Nb hubs 2km vs Clients 65+   : {corr_hubs_2km:.3f}")
print(f"   Distance hub vs Clients 65+  : {corr_distance:.3f}")

# 9. Matrice de corrélation étendue
print("\n9. MATRICE DE CORRÉLATION ÉTENDUE")

vars_analyse = ['UN', 'CAHT', 'clients_65_plus_total',
                'nb_hubs_medicaux_500m', 'nb_hubs_medicaux_1km', 'nb_hubs_medicaux_2km',
                'distance_hub_plus_proche_km']

# Ajouter variables touristiques si disponibles
if 'nb_total_hebergements_walk_5min' in df_merged.columns:
    vars_analyse.extend(['nb_total_hebergements_walk_5min', 'capacite_accueil_drive_10min'])

corr_matrix = df_merged[vars_analyse].corr()
print(corr_matrix[['clients_65_plus_total']].round(3))

# 10. Analyse croisée : proximité hubs + type de zone
print("\n10. ANALYSE CROISÉE : PROXIMITÉ + TYPE DE ZONE")

for zone in ['rural', 'urbain', 'urbain_dense']:
    df_zone = df_merged[df_merged['type_zone'] == zone]

    if len(df_zone) > 100:
        print(f"\n   {zone.upper()} ({len(df_zone):,} pharmacies)")

        # Par catégorie de proximité
        for cat in ['Aucun hub', '>10 hubs']:
            df_subset = df_zone[df_zone['categorie_proximite'] == cat]

            if len(df_subset) > 10:
                corr_un = df_subset['UN'].corr(df_subset['clients_65_plus_total'])
                corr_caht = df_subset['CAHT'].corr(df_subset['clients_65_plus_total'])

                print(f"     {cat:15s} : {len(df_subset):4,} pharma | "
                      f"Corr UN={corr_un:.3f} | Corr CAHT={corr_caht:.3f}")

# 11. Créer graphiques
print("\n11. CRÉATION DES GRAPHIQUES")

try:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Graphique 1 : Nb hubs vs Clients
    axes[0, 0].scatter(df_merged['nb_hubs_medicaux_1km'], df_merged['clients_65_plus_total'], alpha=0.3)
    axes[0, 0].set_xlabel('Nb hubs médicaux 1km')
    axes[0, 0].set_ylabel('Clients 65+')
    axes[0, 0].set_title(f'Hubs médicaux vs Clients 65+ (corr={corr_hubs_1km:.3f})')

    # Graphique 2 : Distance hub vs Clients
    axes[0, 1].scatter(df_merged['distance_hub_plus_proche_km'], df_merged['clients_65_plus_total'], alpha=0.3)
    axes[0, 1].set_xlabel('Distance hub plus proche (km)')
    axes[0, 1].set_ylabel('Clients 65+')
    axes[0, 1].set_title(f'Distance hub vs Clients 65+ (corr={corr_distance:.3f})')
    axes[0, 1].set_xlim(0, 5)

    # Graphique 3 : Boxplot par catégorie
    df_merged.boxplot(column='clients_65_plus_total', by='categorie_proximite', ax=axes[0, 2])
    axes[0, 2].set_title('Clients 65+ par proximité hubs')
    axes[0, 2].set_xlabel('Catégorie proximité')
    axes[0, 2].set_ylabel('Clients 65+')
    plt.setp(axes[0, 2].xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Graphique 4 : UN par catégorie
    df_merged.boxplot(column='UN', by='categorie_proximite', ax=axes[1, 0])
    axes[1, 0].set_title('UN par proximité hubs')
    axes[1, 0].set_xlabel('Catégorie proximité')
    plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Graphique 5 : CAHT par catégorie
    df_merged.boxplot(column='CAHT', by='categorie_proximite', ax=axes[1, 1])
    axes[1, 1].set_title('CAHT par proximité hubs')
    axes[1, 1].set_xlabel('Catégorie proximité')
    plt.setp(axes[1, 1].xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Graphique 6 : Heatmap corrélations
    import seaborn as sns
    corr_hubs = df_merged[['nb_hubs_medicaux_500m', 'nb_hubs_medicaux_1km',
                           'nb_hubs_medicaux_2km', 'clients_65_plus_total',
                           'UN', 'CAHT']].corr()
    sns.heatmap(corr_hubs, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=axes[1, 2])
    axes[1, 2].set_title('Corrélations hubs-activité')

    plt.tight_layout()

    graph_path = OUTPUT_FILES['correlation_hubs_medicaux_graphs']
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(graph_path, dpi=150)
    print(f"   Graphiques sauvegardés : {graph_path}")

except Exception as e:
    print(f"   Erreur graphique       : {e}")
    import traceback
    traceback.print_exc()

# 12. Sauvegarder résultats
print("\n12. SAUVEGARDE")

output_path = OUTPUT_FILES['correlation_hubs_medicaux']
output_path.parent.mkdir(parents=True, exist_ok=True)
df_merged.to_csv(output_path, index=False)
print(f"   Données sauvegardées   : {output_path}")

# Résumé par catégorie
summary_data = []
for cat in df_merged['categorie_proximite'].cat.categories:
    df_cat = df_merged[df_merged['categorie_proximite'] == cat]

    if len(df_cat) > 0:
        summary_data.append({
            'categorie': cat,
            'nb_pharmacies': len(df_cat),
            'clients_65_moyen': df_cat['clients_65_plus_total'].mean(),
            'un_moyen': df_cat['UN'].mean(),
            'caht_moyen': df_cat['CAHT'].mean(),
            'corr_un_clients': df_cat['UN'].corr(df_cat['clients_65_plus_total']) if len(df_cat) > 1 else np.nan,
            'corr_caht_clients': df_cat['CAHT'].corr(df_cat['clients_65_plus_total']) if len(df_cat) > 1 else np.nan
        })

df_summary = pd.DataFrame(summary_data)
summary_path = OUTPUT_FILES['summary_hubs_medicaux']
summary_path.parent.mkdir(parents=True, exist_ok=True)
df_summary.to_csv(summary_path, index=False)
print(f"   Résumé sauvegardé      : {summary_path}")

print("\n" + "="*80)
print("OK ANALYSE HUBS MÉDICAUX TERMINÉE")
print("="*80)
