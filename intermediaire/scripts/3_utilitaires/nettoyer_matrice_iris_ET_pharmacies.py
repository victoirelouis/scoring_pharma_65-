"""
Nettoyer la matrice pour :
1. Supprimer les IRIS sans données de population
2. Supprimer les pharmacies absentes de pharmacies_final.csv
"""
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

base_path = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")

logger.info("="*80)
logger.info("NETTOYAGE MATRICE : IRIS + PHARMACIES")
logger.info("="*80)

# 1. Charger matrice
df_matrix = pd.read_csv(base_path / "data" / "output" / "pharmacies_enrichies" / "pharmacie_iris_pond_100pct_complete.csv")

logger.info(f"\n1. MATRICE AVANT NETTOYAGE")
logger.info(f"   Relations                 : {len(df_matrix):,}")
logger.info(f"   IRIS uniques              : {df_matrix['CODE_IRIS'].nunique():,}")
logger.info(f"   Pharmacies uniques        : {df_matrix['id_pharmacie'].nunique():,}")

# 2. Charger population INSEE
df_pop = pd.read_csv(base_path / "data" / "input" / "iris_insee" / "population_age.csv",
                     sep=';', dtype={'IRIS': str}, low_memory=False)
df_pop = df_pop.rename(columns={'IRIS': 'CODE_IRIS', 'P22_POP65P': 'pop_65_plus'})

iris_avec_pop = set(df_pop['CODE_IRIS'].unique())

logger.info(f"\n2. POPULATION INSEE")
logger.info(f"   IRIS avec données         : {len(iris_avec_pop):,}")

# 3. Charger pharmacies_final.csv
df_pharmacies_final = pd.read_csv(
    base_path / "data" / "input" / "data_cleaning" / "pharmacies_final.csv",
    sep=';'
)

pharma_valides = set(df_pharmacies_final['id_pharmacie'].unique())

logger.info(f"\n3. PHARMACIES VALIDES")
logger.info(f"   Pharmacies dans final.csv : {len(pharma_valides):,}")

# 4. Filtrer matrice (IRIS + PHARMACIES)
df_matrix_clean = df_matrix[
    df_matrix['CODE_IRIS'].isin(iris_avec_pop) &
    df_matrix['id_pharmacie'].isin(pharma_valides)
]

logger.info(f"\n4. APRES NETTOYAGE")
logger.info(f"   Relations                 : {len(df_matrix_clean):,}")
logger.info(f"   Relations supprimees      : {len(df_matrix) - len(df_matrix_clean):,}")
logger.info(f"   IRIS uniques              : {df_matrix_clean['CODE_IRIS'].nunique():,}")
logger.info(f"   Pharmacies uniques        : {df_matrix_clean['id_pharmacie'].nunique():,}")

# 5. Renormaliser les poids w_IRIS (car certaines pharmacies ont été supprimées)
logger.info(f"\n5. RENORMALISATION DES POIDS")

sum_w_avant = df_matrix_clean.groupby('CODE_IRIS')['w_IRIS'].sum()
logger.info(f"   Avant renormalisation :")
logger.info(f"     Moyenne sum(w_IRIS)     : {sum_w_avant.mean():.6f}")
logger.info(f"     Min sum(w_IRIS)         : {sum_w_avant.min():.6f}")
logger.info(f"     Max sum(w_IRIS)         : {sum_w_avant.max():.6f}")

# Renormaliser : diviser chaque w_IRIS par la somme de son IRIS
df_matrix_clean = df_matrix_clean.merge(
    sum_w_avant.rename('sum_w'),
    left_on='CODE_IRIS',
    right_index=True,
    how='left'
)
df_matrix_clean['w_IRIS'] = df_matrix_clean['w_IRIS'] / df_matrix_clean['sum_w']
df_matrix_clean = df_matrix_clean.drop(columns=['sum_w'])

sum_w_apres = df_matrix_clean.groupby('CODE_IRIS')['w_IRIS'].sum()
logger.info(f"   Apres renormalisation :")
logger.info(f"     Moyenne sum(w_IRIS)     : {sum_w_apres.mean():.6f}")
logger.info(f"     Min sum(w_IRIS)         : {sum_w_apres.min():.6f}")
logger.info(f"     Max sum(w_IRIS)         : {sum_w_apres.max():.6f}")

parfait = ((sum_w_apres >= 0.999) & (sum_w_apres <= 1.001)).sum()
logger.info(f"     IRIS avec sum(w) = 1.0  : {parfait:,} ({100*parfait/len(sum_w_apres):.1f}%)")

# 6. Calculer couverture finale
pop_couverte = df_pop[df_pop['CODE_IRIS'].isin(df_matrix_clean['CODE_IRIS'].unique())]['pop_65_plus'].sum()
pop_totale = df_pop['pop_65_plus'].sum()

logger.info(f"\n6. COUVERTURE FINALE")
logger.info(f"   Population 65+ couverte   : {pop_couverte:,.0f}")
logger.info(f"   Population 65+ totale     : {pop_totale:,.0f}")
logger.info(f"   Taux de couverture        : {100*pop_couverte/pop_totale:.1f}%")

# 7. Sauvegarder
output_path = base_path / "data" / "output" / "pharmacies_enrichies" / "pharmacie_iris_pond_cleaned.csv"
df_matrix_clean.to_csv(output_path, index=False)

logger.info(f"\n7. SAUVEGARDE")
logger.info(f"   Fichier sauvegarde        : {output_path}")

logger.info(f"\n" + "="*80)
logger.info("OK NETTOYAGE TERMINE")
logger.info("="*80)
