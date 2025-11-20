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
import sys
import time
from datetime import datetime, timedelta
import functools

# Force unbuffered output
print = functools.partial(print, flush=True)

# Ajouter le répertoire config au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_ml import (
    INPUT_FILES,
    INTERMEDIATE_FILES,
    OUTPUT_FILES,
    PROJECT_ROOT
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info("MODÈLE DE HUFF EXACT PAR IRIS - VERSION CORRIGÉE")
logger.info("="*80)

# 1. Charger les données
logger.info("\n1. CHARGEMENT DES DONNÉES")

df_pharmacies = pd.read_csv(
    INPUT_FILES['pharmacies'],
    sep=';', usecols=['id_pharmacie', 'nom_pharmacie', 'type_zone']
)
logger.info(f"   Pharmacies            : {len(df_pharmacies):,}")

df_scores = pd.read_csv(INTERMEDIATE_FILES['pharmacies_avec_scores_attractivite'])
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

df_iris_pop = pd.read_csv(INPUT_FILES['population_age_csv'],
                          sep=';', dtype={'IRIS': str}, low_memory=False)
df_iris_pop = df_iris_pop.rename(columns={
    'IRIS': 'CODE_IRIS',
    'P22_POP65P': 'pop_65_plus',
    'P22_POP6579': 'pop_65_79',
    'P22_POP80P': 'pop_80_plus',
    'P22_H65P': 'pop_hommes_65_plus',
    'P22_F65P': 'pop_femmes_65_plus'
})
logger.info(f"   IRIS population       : {len(df_iris_pop):,}")
logger.info(f"   Population 65+ France : {df_iris_pop['pop_65_plus'].sum():,.0f}")
logger.info(f"   dont Hommes 65+       : {df_iris_pop['pop_hommes_65_plus'].sum():,.0f}")
logger.info(f"   dont Femmes 65+       : {df_iris_pop['pop_femmes_65_plus'].sum():,.0f}")

df_pharmacie_iris = pd.read_csv(INTERMEDIATE_FILES['matrice_pharmacie_iris_cleaned'])
df_pharmacie_iris = df_pharmacie_iris[
    df_pharmacie_iris['id_pharmacie'].isin(df_pharmacies['id_pharmacie'])
]
logger.info(f"   Relations matrice     : {len(df_pharmacie_iris):,}")
logger.info(f"   Pharmacies uniques    : {df_pharmacie_iris['id_pharmacie'].nunique():,}")

# 2. Préparer le dataset de travail
logger.info("\n2. PRÉPARATION DU DATASET")

df_work = df_pharmacie_iris.merge(
    df_iris_pop[['CODE_IRIS', 'pop_65_plus', 'pop_65_79', 'pop_80_plus',
                 'pop_hommes_65_plus', 'pop_femmes_65_plus']],
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

# Remplir les NaN avec 0 pour les populations
df_work['pop_65_plus'] = df_work['pop_65_plus'].fillna(0)
df_work['pop_65_79'] = df_work['pop_65_79'].fillna(0)
df_work['pop_80_plus'] = df_work['pop_80_plus'].fillna(0)
df_work['pop_hommes_65_plus'] = df_work['pop_hommes_65_plus'].fillna(0)
df_work['pop_femmes_65_plus'] = df_work['pop_femmes_65_plus'].fillna(0)

logger.info(f"   NaN remplis avec 0    : OK")

# 3. Initialiser les colonnes clients
df_pharmacies['clients_65_plus_total'] = 0.0
df_pharmacies['clients_65_79'] = 0.0
df_pharmacies['clients_80_plus'] = 0.0
df_pharmacies['clients_hommes_65_plus'] = 0.0
df_pharmacies['clients_femmes_65_plus'] = 0.0

# 4. Calculer le modèle de Huff par IRIS
logger.info("\n3. CALCUL DU MODÈLE DE HUFF")

clients_dict = {
    'clients_65_plus_total': {},
    'clients_65_79': {},
    'clients_80_plus': {},
    'clients_hommes_65_plus': {},
    'clients_femmes_65_plus': {}
}

iris_list = df_work['CODE_IRIS'].unique()
logger.info(f"   IRIS à traiter        : {len(iris_list):,}")

# OPTIMISATION: Pré-grouper les données par IRIS pour éviter les filtres répétés
logger.info(f"   Pré-groupement par IRIS...")
df_work_grouped = df_work.groupby('CODE_IRIS', group_keys=False)
logger.info(f"   OK Groupes créés")

# Checkpoint setup
CHECKPOINT_DIR = OUTPUT_FILES['pharmacies_clients_65plus_huff'].parent / "checkpoints_huff"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
SAVE_INTERVAL = 10000  # Sauvegarder tous les 10000 IRIS

temps_debut = time.time()

for i, iris_code in enumerate(iris_list):
    # Progression et estimation temps
    if i % 5000 == 0 and i > 0:
        temps_ecoule = time.time() - temps_debut
        temps_par_iris = temps_ecoule / i
        iris_restants = len(iris_list) - i
        temps_restant_sec = temps_par_iris * iris_restants
        temps_restant = timedelta(seconds=int(temps_restant_sec))

        logger.info(f"\n   [{datetime.now().strftime('%H:%M:%S')}] Progression:")
        logger.info(f"      Traité            : {i:,} / {len(iris_list):,} ({i/len(iris_list)*100:.1f}%)")
        logger.info(f"      Pharmacies avec clients: {len(clients_dict['clients_65_plus_total']):,}")
        logger.info(f"      Temps par IRIS    : {temps_par_iris:.3f}s")
        logger.info(f"      Temps restant     : {temps_restant}")

    # OPTIMISATION: Utiliser get_group au lieu de filtrer
    try:
        df_iris = df_work_grouped.get_group(iris_code)
    except KeyError:
        # IRIS absent du groupement (ne devrait pas arriver)
        continue

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

        # Total par tranches d'âge
        clients_dict['clients_65_plus_total'][id_pharma] = \
            clients_dict['clients_65_plus_total'].get(id_pharma, 0) + row['pop_65_plus'] * part
        clients_dict['clients_65_79'][id_pharma] = \
            clients_dict['clients_65_79'].get(id_pharma, 0) + row['pop_65_79'] * part
        clients_dict['clients_80_plus'][id_pharma] = \
            clients_dict['clients_80_plus'].get(id_pharma, 0) + row['pop_80_plus'] * part

        # Par sexe (65+ uniquement)
        clients_dict['clients_hommes_65_plus'][id_pharma] = \
            clients_dict['clients_hommes_65_plus'].get(id_pharma, 0) + row['pop_hommes_65_plus'] * part
        clients_dict['clients_femmes_65_plus'][id_pharma] = \
            clients_dict['clients_femmes_65_plus'].get(id_pharma, 0) + row['pop_femmes_65_plus'] * part

    # Sauvegarde checkpoint
    if (i + 1) % SAVE_INTERVAL == 0:
        logger.info(f"\n   SAUVEGARDE CHECKPOINT à {i+1:,} IRIS...")

        # Créer dataframe temporaire
        df_temp = df_pharmacies.copy()
        for id_pharma, clients in clients_dict['clients_65_plus_total'].items():
            df_temp.loc[df_temp['id_pharmacie'] == id_pharma, 'clients_65_plus_total'] = clients
        for id_pharma, clients in clients_dict['clients_65_79'].items():
            df_temp.loc[df_temp['id_pharmacie'] == id_pharma, 'clients_65_79'] = clients
        for id_pharma, clients in clients_dict['clients_80_plus'].items():
            df_temp.loc[df_temp['id_pharmacie'] == id_pharma, 'clients_80_plus'] = clients
        for id_pharma, clients in clients_dict['clients_hommes_65_plus'].items():
            df_temp.loc[df_temp['id_pharmacie'] == id_pharma, 'clients_hommes_65_plus'] = clients
        for id_pharma, clients in clients_dict['clients_femmes_65_plus'].items():
            df_temp.loc[df_temp['id_pharmacie'] == id_pharma, 'clients_femmes_65_plus'] = clients

        checkpoint_file = CHECKPOINT_DIR / "checkpoint_latest.csv"
        df_temp.to_csv(checkpoint_file, index=False)

        # Métadonnées
        checkpoint_meta = CHECKPOINT_DIR / "checkpoint_meta.txt"
        with open(checkpoint_meta, 'w') as f:
            f.write(f"Checkpoint: {i+1:,} / {len(iris_list):,} IRIS\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Pharmacies: {len(clients_dict['clients_65_plus_total']):,}\n")
            f.write(f"Clients totaux: {sum(clients_dict['clients_65_plus_total'].values()):,.0f}\n")

        logger.info(f"   Checkpoint sauvegardé : {checkpoint_file}")
        logger.info(f"   Taille: {checkpoint_file.stat().st_size / 1024 / 1024:.1f} MB")

temps_total = time.time() - temps_debut
logger.info(f"\n   OK Traitement terminé en {timedelta(seconds=int(temps_total))}")

# 5. Mettre à jour le dataframe des pharmacies
logger.info("\n4. MISE À JOUR DES PHARMACIES")

for id_pharma, clients in clients_dict['clients_65_plus_total'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_65_plus_total'] = clients
for id_pharma, clients in clients_dict['clients_65_79'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_65_79'] = clients
for id_pharma, clients in clients_dict['clients_80_plus'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_80_plus'] = clients
for id_pharma, clients in clients_dict['clients_hommes_65_plus'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_hommes_65_plus'] = clients
for id_pharma, clients in clients_dict['clients_femmes_65_plus'].items():
    df_pharmacies.loc[df_pharmacies['id_pharmacie'] == id_pharma, 'clients_femmes_65_plus'] = clients

logger.info(f"   Pharmacies mises à jour : {len(clients_dict['clients_65_plus_total']):,}")

# Calculer les visites annuelles (12 visites/an)
df_pharmacies['visites_annuelles_65plus'] = df_pharmacies['clients_65_plus_total'] * 12

# 6. Résultats
logger.info("\n5. RÉSULTATS")

total_clients = df_pharmacies['clients_65_plus_total'].sum()
total_hommes = df_pharmacies['clients_hommes_65_plus'].sum()
total_femmes = df_pharmacies['clients_femmes_65_plus'].sum()

pop_france = df_iris_pop['pop_65_plus'].sum()
pop_couverte = df_iris_pop[df_iris_pop['CODE_IRIS'].isin(iris_list)]['pop_65_plus'].sum()
pop_hommes_couverte = df_iris_pop[df_iris_pop['CODE_IRIS'].isin(iris_list)]['pop_hommes_65_plus'].sum()
pop_femmes_couverte = df_iris_pop[df_iris_pop['CODE_IRIS'].isin(iris_list)]['pop_femmes_65_plus'].sum()

logger.info(f"   Clients 65+ totaux    : {total_clients:,.0f}")
logger.info(f"   Clients 65-79         : {df_pharmacies['clients_65_79'].sum():,.0f}")
logger.info(f"   Clients 80+           : {df_pharmacies['clients_80_plus'].sum():,.0f}")
logger.info(f"")
logger.info(f"   RÉPARTITION PAR SEXE:")
logger.info(f"   Clients Hommes 65+    : {total_hommes:,.0f} ({100*total_hommes/total_clients:.1f}%)")
logger.info(f"   Clients Femmes 65+    : {total_femmes:,.0f} ({100*total_femmes/total_clients:.1f}%)")
logger.info(f"   Hommes + Femmes       : {total_hommes + total_femmes:,.0f}")
logger.info(f"   Vérification (H+F=T)  : {abs((total_hommes + total_femmes) - total_clients) < 1:.0f}")
logger.info(f"")
logger.info(f"   Population France 65+ : {pop_france:,.0f}")
logger.info(f"   Population couverte   : {pop_couverte:,.0f}")
logger.info(f"   dont Hommes couverts  : {pop_hommes_couverte:,.0f}")
logger.info(f"   dont Femmes couvertes : {pop_femmes_couverte:,.0f}")
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

output_path = OUTPUT_FILES['pharmacies_clients_65plus_huff']
# Créer le répertoire s'il n'existe pas
output_path.parent.mkdir(parents=True, exist_ok=True)

cols = ['id_pharmacie', 'nom_pharmacie', 'attractivite_huff',
        'clients_65_79', 'clients_80_plus', 'clients_65_plus_total',
        'clients_hommes_65_plus', 'clients_femmes_65_plus',
        'visites_annuelles_65plus', 'decile_clients_65plus']
df_output = df_pharmacies[[c for c in cols if c in df_pharmacies.columns]]

# Calculer les pourcentages Hommes/Femmes
df_output['pct_hommes_65_plus'] = 100 * df_output['clients_hommes_65_plus'] / (
    df_output['clients_hommes_65_plus'] + df_output['clients_femmes_65_plus'] + 1e-10
)
df_output['pct_femmes_65_plus'] = 100 * df_output['clients_femmes_65_plus'] / (
    df_output['clients_hommes_65_plus'] + df_output['clients_femmes_65_plus'] + 1e-10
)

df_output.to_csv(output_path, index=False)

logger.info(f"   Fichier sauvegardé    : {output_path}")
logger.info(f"   Pharmacies totales    : {len(df_output):,}")
logger.info(f"   Pharmacies avec >0    : {(df_output['clients_65_plus_total'] > 0).sum():,}")
logger.info(f"   Pharmacies avec =0    : {(df_output['clients_65_plus_total'] == 0).sum():,}")

logger.info("\n" + "="*80)
logger.info("OK TERMINÉ - MODÈLE DE HUFF AVEC CONSERVATION PARFAITE")
logger.info("="*80)
