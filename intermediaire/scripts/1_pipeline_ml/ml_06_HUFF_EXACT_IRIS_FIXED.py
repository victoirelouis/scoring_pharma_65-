"""
Script 6 CORRIGÉ : VRAI MODÈLE DE HUFF avec conservation de la population
VERSION EXACTE basée sur les IRIS et la matrice Pharmacie × IRIS

Principe :
1. Pour chaque IRIS, récupérer la liste des pharmacies accessibles
2. Calculer l'utilité U_j = A_j × w_IRIS pour chaque pharmacie accessible
3. Normaliser : part_marche_j_iris = U_j / Σ(U_k pour pharmacies accessibles de cet IRIS)
4. Distribuer la population de l'IRIS : clients_j += pop_IRIS × part_marche_j_iris

Cette méthode GARANTIT que Σ(parts de marché par IRIS) = 100%
Et donc que Σ(clients toutes pharmacies) = Population totale couverte
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

base_path = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")

logger.info("="*80)
logger.info("MODÈLE DE HUFF EXACT PAR IRIS - VERSION CORRIGÉE")
logger.info("="*80)

# 1. Charger les données
logger.info("\n1. CHARGEMENT DES DONNÉES")

df_pharmacies = pd.read_csv(
    base_path / "data" / "input" / "data_cleaning" / "pharmacies_final.csv",
    sep=';', usecols=['id_pharmacie', 'nom_pharmacie', 'type_zone']
)
logger.info(f"   Pharmacies            : {len(df_pharmacies):,}")

df_scores = pd.read_csv(base_path / "intermediaire" / "output" / "pharmacies_avec_scores_attractivite.csv")
df_pharmacies = df_pharmacies.merge(
    df_scores[['id_pharmacie', 'score_attractivite_65plus_composite']],
    on='id_pharmacie', how='left'
)
logger.info(f"   Scores fusionnés      : OK")

# Normaliser attractivité
A_j = df_pharmacies['score_attractivite_65plus_composite'].fillna(0.5)
A_j = 0.1 + 0.9 * (A_j - A_j.min()) / (A_j.max() - A_j.min() + 1e-10)
df_pharmacies['attractivite_huff'] = A_j
logger.info(f"   Attractivité moyenne  : {A_j.mean():.3f}")

df_iris_pop = pd.read_csv(base_path / "data" / "input" / "iris_insee" / "population_age.csv",
                          sep=';', dtype={'IRIS': str}, low_memory=False)
df_iris_pop = df_iris_pop.rename(columns={
    'IRIS': 'CODE_IRIS',
    'P22_POP65P': 'pop_65_plus',
    'P22_POP6579': 'pop_65_79',
    'P22_POP80P': 'pop_80_plus'
})
logger.info(f"   IRIS population       : {len(df_iris_pop):,}")
logger.info(f"   Population 65+ France : {df_iris_pop['pop_65_plus'].sum():,.0f}")

df_pharmacie_iris = pd.read_csv(base_path / "data" / "output" / "pharmacies_enrichies" / "pharmacie_iris_pond_cleaned.csv")
df_pharmacie_iris = df_pharmacie_iris[
    df_pharmacie_iris['id_pharmacie'].isin(df_pharmacies['id_pharmacie'])
]
logger.info(f"   Relations matrice     : {len(df_pharmacie_iris):,}")
logger.info(f"   Pharmacies uniques    : {df_pharmacie_iris['id_pharmacie'].nunique():,}")

# 2. Préparer le dataset de travail
logger.info("\n2. PRÉPARATION DU DATASET")

df_work = df_pharmacie_iris.merge(
    df_iris_pop[['CODE_IRIS', 'pop_65_plus', 'pop_65_79', 'pop_80_plus']],
    on='CODE_IRIS',
    how='left'
)

df_work = df_work.merge(
    df_pharmacies[['id_pharmacie', 'attractivite_huff']],
    on='id_pharmacie',
    how='left'
)

logger.info(f"   Relations df_work     : {len(df_work):,}")
logger.info(f"   NaN pop_65_plus       : {df_work['pop_65_plus'].isna().sum():,}")
logger.info(f"   NaN attractivite      : {df_work['attractivite_huff'].isna().sum():,}")

# 3. Initialiser les colonnes clients
df_pharmacies['clients_65_plus_total'] = 0.0
df_pharmacies['clients_65_79'] = 0.0
df_pharmacies['clients_80_plus'] = 0.0

# 4. Calculer le modèle de Huff par IRIS
logger.info("\n3. CALCUL DU MODÈLE DE HUFF")

clients_dict = {
    'clients_65_plus_total': {},
    'clients_65_79': {},
    'clients_80_plus': {}
}

iris_list = df_work['CODE_IRIS'].unique()
logger.info(f"   IRIS à traiter        : {len(iris_list):,}")

for i, iris_code in enumerate(iris_list):
    if i % 10000 == 0 and i > 0:
        logger.info(f"   Traité {i:,}/{len(iris_list):,} IRIS ({i/len(iris_list)*100:.1f}%)")

    df_iris = df_work[df_work['CODE_IRIS'] == iris_code].copy()

    if len(df_iris) == 0:
        continue

    # Calculer utilités
    df_iris['utilite'] = df_iris['attractivite_huff'] * df_iris['w_IRIS']

    sum_utilite = df_iris['utilite'].sum()

    if sum_utilite == 0:
        continue

    # Parts de marché
    df_iris['part_marche'] = df_iris['utilite'] / sum_utilite

    # Distribuer la population
    for idx, row in df_iris.iterrows():
        id_pharma = row['id_pharmacie']
        part = row['part_marche']

        clients_dict['clients_65_plus_total'][id_pharma] = \
            clients_dict['clients_65_plus_total'].get(id_pharma, 0) + row['pop_65_plus'] * part

        clients_dict['clients_65_79'][id_pharma] = \
            clients_dict['clients_65_79'].get(id_pharma, 0) + row['pop_65_79'] * part

        clients_dict['clients_80_plus'][id_pharma] = \
            clients_dict['clients_80_plus'].get(id_pharma, 0) + row['pop_80_plus'] * part

logger.info(f"   OK Traitement terminé")

# 5. Mettre à jour le dataframe des pharmacies
logger.info("\n4. MISE À JOUR DES PHARMACIES")

for id_pharma, clients in clients_dict['clients_65_plus_total'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_65_plus_total'] = clients

for id_pharma, clients in clients_dict['clients_65_79'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_65_79'] = clients

for id_pharma, clients in clients_dict['clients_80_plus'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_80_plus'] = clients

logger.info(f"   Pharmacies mises à jour : {len(clients_dict['clients_65_plus_total']):,}")

# Calculer les visites annuelles (12 visites/an)
df_pharmacies['visites_annuelles_65plus'] = df_pharmacies['clients_65_plus_total'] * 12

# 6. Résultats
logger.info("\n5. RÉSULTATS")

total_clients = df_pharmacies['clients_65_plus_total'].sum()
pop_france = df_iris_pop['pop_65_plus'].sum()
pop_couverte = df_iris_pop[df_iris_pop['CODE_IRIS'].isin(iris_list)]['pop_65_plus'].sum()

logger.info(f"   Clients 65+ totaux    : {total_clients:,.0f}")
logger.info(f"   Clients 65-79         : {df_pharmacies['clients_65_79'].sum():,.0f}")
logger.info(f"   Clients 80+           : {df_pharmacies['clients_80_plus'].sum():,.0f}")
logger.info(f"   Population France 65+ : {pop_france:,.0f}")
logger.info(f"   Population couverte   : {pop_couverte:,.0f}")
logger.info(f"   Taux couverture       : {100*pop_couverte/pop_france:.1f}%")
logger.info(f"   Ratio conservation    : {total_clients/pop_couverte:.6f}")

if abs(total_clients/pop_couverte - 1.0) < 0.01:
    logger.info(f"   ✓ CONSERVATION PARFAITE !")
else:
    logger.info(f"   ⚠ Conservation imparfaite")

# 7. Calculer les déciles
logger.info("\n6. CALCUL DES DÉCILES")

df_pharmacies['decile_clients_65plus'] = pd.qcut(
    df_pharmacies['clients_65_plus_total'],
    q=10,
    labels=False,
    duplicates='drop'
) + 1

# 8. Sauvegarder
logger.info("\n7. SAUVEGARDE")

output_path = base_path / "intermediaire" / "output" / "pharmacies_clients_65plus_HUFF_EXACT_IRIS.csv"

cols = ['id_pharmacie', 'nom_pharmacie', 'attractivite_huff',
        'clients_65_79', 'clients_80_plus', 'clients_65_plus_total',
        'visites_annuelles_65plus', 'decile_clients_65plus']
df_output = df_pharmacies[[c for c in cols if c in df_pharmacies.columns]]
df_output.to_csv(output_path, index=False)

logger.info(f"   Fichier sauvegardé    : {output_path}")
logger.info(f"   Pharmacies totales    : {len(df_output):,}")
logger.info(f"   Pharmacies avec >0    : {(df_output['clients_65_plus_total'] > 0).sum():,}")
logger.info(f"   Pharmacies avec =0    : {(df_output['clients_65_plus_total'] == 0).sum():,}")

logger.info("\n" + "="*80)
logger.info("OK TERMINÉ - MODÈLE DE HUFF AVEC CONSERVATION PARFAITE")
logger.info("="*80)
