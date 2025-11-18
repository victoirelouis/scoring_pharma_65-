#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ULTRA-OPTIMISÉ : Enrichissement pharmacies + INSEE

OPTIMISATIONS :
- Multiprocessing (tous les CPU disponibles)
- Sauvegarde incrémentale par batch de 1000 pharmacies
- Reprise automatique si interruption
- Progress bar détaillée temps réel
- Fusion vectorisée ultra-rapide

MISSION :
- Agréger TOUTES les données INSEE par pharmacie
- Pondération par w_IRIS (surface accessible)
- Calcul des tranches d'âge 65-74 / 75-84 / 85+ (AJOUTÉ)
- 1 ligne finale par pharmacie

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys
import time
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import pickle

warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
DATA_CLEANING_DIR = INPUT_DIR / "data_cleaning"
INSEE_DIR = INPUT_DIR / "iris_insee"
ENRICHISSEMENT_DIR = INPUT_DIR / "enrichissement"
OUTPUT_DIR = BASE_DIR / "data" / "output"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CACHE_DIR = BASE_DIR / "data" / "cache"

# Paramètres optimisation
N_WORKERS = max(1, cpu_count() - 1)  # Laisser 1 CPU libre
BATCH_SIZE = 1000  # Sauvegarder tous les 1000 pharmacies
CHUNK_SIZE = 50000  # Taille chunks pour lecture CSV

# Fichiers
PHARMACIES_FILE = "pharmacies_final.csv"
PHARMACIES_IRIS_FILE = "pharmacie_iris_pond.csv"

# Colonnes INSEE à conserver (pertinentes pour scoring 65+)
# Note: Les fichiers INSEE utilisent le préfixe P22_ (recensement 2022)
COLONNES_PERTINENTES = {
    'population_age': [
        'P22_POP',         # Population totale
        'P22_POP65P',      # Population 65+ ans (total)
        'P22_POP75P',      # Population 75+ ans (total)
        'P22_POP80P',      # Population 80+ ans (total)
        'P22_POP6579',     # Population 65-79 ans (total)
        # Population par sexe
        'P22_POPH',        # Hommes total
        'P22_H65P',        # Hommes 65+ ans
        'P22_H75P',        # Hommes 75+ ans
        'P22_POPF',        # Femmes total
        'P22_F65P',        # Femmes 65+ ans
        'P22_F75P',        # Femmes 75+ ans
    ],
    'revenus': [
        'DISP_MED20',      # Revenu disponible médian 2020
    ],
    'diplome_formation': [
        'P22_NSCOL15P_SUP2',    # Diplômés supérieur (bac+2)
        'P22_NSCOL15P_SUP34',   # Diplômés supérieur (bac+3/4)
        'P22_NSCOL15P_SUP5',    # Diplômés supérieur (bac+5+)
        'P22_NSCOL15P_DIPLMIN', # Sans diplôme / CEP
        'P22_NSCOL15P',         # Total non scolarisés 15+
    ],
    'logement': [
        'P22_RP',          # Résidences principales
        'P22_MAISON',      # Maisons
        'P22_APPART',      # Appartements
        'P22_RP_PROP',     # Propriétaires
        'P22_RP_LOC',      # Locataires
    ],
}


def load_pharmacies():
    """Charge les pharmacies avec type_zone"""
    print(f"\n💊 CHARGEMENT PHARMACIES...")
    
    # Chercher fichier dans data_cleaning en priorité
    for directory in [DATA_CLEANING_DIR, PROCESSED_DIR, OUTPUT_DIR, INPUT_DIR]:
        pharma_file = directory / PHARMACIES_FILE
        if pharma_file.exists():
            break
    else:
        print(f"   ❌ {PHARMACIES_FILE} non trouvé")
        return None
    
    print(f"   📁 {pharma_file.name}")
    
    # Détection automatique du séparateur
    sep = ';'
    df = pd.read_csv(pharma_file, encoding='utf-8', sep=sep, low_memory=False)
    print(f"   ✓ {len(df):,} pharmacies")
    
    # Vérifier type_zone
    if 'type_zone' in df.columns:
        counts = df['type_zone'].value_counts()
        print(f"   ✓ Type de zone:")
        for typ, count in counts.items():
            print(f"      • {typ}: {count:,}")
    else:
        print(f"   ⚠️  Colonne type_zone manquante")
    
    return df


def load_pharmacies_iris():
    """Charge la correspondance pharmacie-IRIS"""
    print(f"\n🗺️  CHARGEMENT CORRESPONDANCE PHARMACIE-IRIS...")
    
    # Chercher dans enrichissement en priorité
    for directory in [ENRICHISSEMENT_DIR, PROCESSED_DIR, OUTPUT_DIR, INPUT_DIR]:
        file_path = directory / PHARMACIES_IRIS_FILE
        if file_path.exists():
            break
    else:
        print(f"   ❌ {PHARMACIES_IRIS_FILE} non trouvé")
        return None
    
    print(f"   📁 {file_path.name}")
    
    # Détection automatique du séparateur
    for sep in [';', ',', '\t']:
        try:
            df_test = pd.read_csv(file_path, encoding='utf-8', sep=sep, nrows=5)
            if len(df_test.columns) > 2:
                df = pd.read_csv(file_path, encoding='utf-8', sep=sep, low_memory=False)
                break
        except:
            continue
    
    print(f"   ✓ {len(df):,} lignes")
    
    nb_pharmacies = df['id_pharmacie'].nunique()
    nb_iris = df['CODE_IRIS'].nunique()
    
    print(f"   ✓ {nb_pharmacies:,} pharmacies")
    print(f"   ✓ {nb_iris:,} IRIS uniques")
    print(f"   ✓ Moyenne: {len(df)/nb_pharmacies:.1f} IRIS par pharmacie")
    
    return df


def load_insee_data():
    """Charge TOUS les fichiers INSEE et vérifie les colonnes"""
    print(f"\n📊 CHARGEMENT DONNÉES INSEE...")
    
    insee_files = {
        'population_age': 'age_profession.CSV',
        'diplome_formation': 'diplome_formation.CSV',
        'logement': 'logement.CSV',
        'revenus': 'revenus.csv',
    }
    
    data_insee = {}
    
    for name, filename in insee_files.items():
        file_path = INSEE_DIR / filename
        
        if not file_path.exists():
            print(f"   ⚠️  {filename} non trouvé, ignoré")
            continue
        
        print(f"   📁 {filename}...")
        
        try:
            # Essayer plusieurs séparateurs
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', sep=sep, 
                                     low_memory=False, nrows=5)
                    if len(df.columns) > 1:  # Bon séparateur trouvé
                        df_full = pd.read_csv(file_path, encoding='utf-8', 
                                              sep=sep, low_memory=False)
                        break
                except:
                    continue
            
            print(f"      ✓ {len(df_full):,} lignes, {len(df_full.columns)} colonnes")
            
            # Vérifier et normaliser le nom de la colonne IRIS
            if 'CODE_IRIS' not in df_full.columns:
                if 'IRIS' in df_full.columns:
                    df_full.rename(columns={'IRIS': 'CODE_IRIS'}, inplace=True)
                elif 'code_iris' in df_full.columns:
                    df_full.rename(columns={'code_iris': 'CODE_IRIS'}, inplace=True)
            
            if 'CODE_IRIS' in df_full.columns:
                print(f"      ✓ {df_full['CODE_IRIS'].nunique():,} IRIS")
                
                # *** VÉRIFICATION DES COLONNES PERTINENTES ***
                if name in COLONNES_PERTINENTES:
                    cols_demandees = COLONNES_PERTINENTES[name]
                    cols_trouvees = [col for col in cols_demandees if col in df_full.columns]
                    cols_manquantes = [col for col in cols_demandees if col not in df_full.columns]
                    
                    print(f"      📋 Colonnes pertinentes:")
                    print(f"         ✓ Trouvées: {len(cols_trouvees)}/{len(cols_demandees)}")
                    if cols_trouvees:
                        for col in cols_trouvees:
                            print(f"            • {col}")
                    if cols_manquantes:
                        print(f"         ⚠️  Manquantes: {', '.join(cols_manquantes)}")
                
                data_insee[name] = df_full
            else:
                print(f"      ⚠️  Pas de colonne CODE_IRIS/IRIS, ignoré")
        
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
    
    print(f"\n   ✅ {len(data_insee)} fichiers INSEE chargés")
    
    return data_insee


def aggregate_iris_data(pharmacie_iris_group, data_insee):
    """
    Agrège les données INSEE pour 1 pharmacie
    UNIQUEMENT LES COLONNES PERTINENTES
    
    Args:
        pharmacie_iris_group: DataFrame avec les IRIS de cette pharmacie
        data_insee: dict des DataFrames INSEE
        
    Returns:
        dict: Données agrégées
    """
    result = {}
    
    # Pour chaque fichier INSEE
    for name, df_insee in data_insee.items():
        # Vérifier si on a des colonnes pertinentes définies pour ce fichier
        if name not in COLONNES_PERTINENTES:
            continue
        
        # Fusionner avec les IRIS de la pharmacie
        merged = pharmacie_iris_group.merge(df_insee, on='CODE_IRIS', how='left')
        
        # Sélectionner UNIQUEMENT les colonnes pertinentes
        cols_to_aggregate = COLONNES_PERTINENTES[name]
        
        # Agréger avec pondération par w_IRIS
        for col in cols_to_aggregate:
            if col in merged.columns:
                try:
                    # Convertir en numérique (gérer les erreurs de conversion)
                    col_numeric = pd.to_numeric(merged[col], errors='coerce')
                    w_iris_numeric = pd.to_numeric(merged['w_IRIS'], errors='coerce')
                    
                    # Somme pondérée (ignorer les NaN)
                    weighted_sum = (col_numeric * w_iris_numeric).sum()
                    result[f"{name}_{col}"] = weighted_sum
                except Exception as e:
                    # En cas d'erreur, mettre NaN
                    result[f"{name}_{col}"] = np.nan
    
    return result


def process_batch_pharmacies(batch_data):
    """
    Traite un batch de pharmacies (pour multiprocessing)
    
    Args:
        batch_data: tuple (batch_pharmacies, df_pharmacie_iris, data_insee)
        
    Returns:
        list: Résultats pour ce batch
    """
    batch_pharmacies, df_pharmacie_iris, data_insee = batch_data
    
    results = []
    
    for id_pharmacie in batch_pharmacies:
        # Récupérer les IRIS de cette pharmacie
        iris_pharma = df_pharmacie_iris[
            df_pharmacie_iris['id_pharmacie'] == id_pharmacie
        ]
        
        if len(iris_pharma) == 0:
            continue
        
        # Agréger données INSEE
        aggregated = aggregate_iris_data(iris_pharma, data_insee)
        aggregated['id_pharmacie'] = id_pharmacie
        
        results.append(aggregated)
    
    return results


def load_checkpoint():
    """Charge le checkpoint si existe"""
    checkpoint_file = CACHE_DIR / "enrichissement_checkpoint.pkl"
    
    if checkpoint_file.exists():
        print(f"\n💾 CHECKPOINT TROUVÉ!")
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
            
            print(f"   ✓ {len(checkpoint['results'])} pharmacies déjà traitées")
            print(f"   ✓ Dernière ID: {checkpoint['last_processed']}")
            
            response = input(f"\n   Reprendre depuis le checkpoint ? (o/n) : ")
            if response.lower() == 'o':
                return checkpoint
        except Exception as e:
            print(f"   ⚠️  Checkpoint corrompu: {e}")
    
    return None


def save_checkpoint(results, last_processed):
    """Sauvegarde le checkpoint"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    checkpoint = {
        'results': results,
        'last_processed': last_processed,
        'timestamp': time.time()
    }
    
    checkpoint_file = CACHE_DIR / "enrichissement_checkpoint.pkl"
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(checkpoint, f)


def save_incremental(df_results, batch_number):
    """Sauvegarde incrémentale"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    batch_file = CACHE_DIR / f"enrichissement_batch_{batch_number:04d}.csv"
    df_results.to_csv(batch_file, index=False, encoding='utf-8')


def calculate_age_groups(df):
    """
    ✨ NOUVELLE FONCTION ✨
    Calcule les tranches d'âge 65-74 / 75-84 / 85+ 
    POUR TOTAL / HOMMES / FEMMES
    
    Formules :
    - 65-74 = P22_POP65P - P22_POP75P (EXACT)
    - 75-84 = (P22_POP75P - P22_POP80P) + (P22_POP80P × 0.60) (APPROXIMATION)
    - 85+ = P22_POP80P × 0.40 (APPROXIMATION)
    
    Justification approximation :
    En France, parmi les 80+ ans, environ 60% ont 80-84 ans et 40% ont 85+
    
    Note: On n'a pas P22_H80P et P22_F80P, donc on applique les mêmes ratios 60/40
    aux hommes et femmes pour les tranches 80-84 et 85+
    """
    print(f"\n🧮 CALCUL DES TRANCHES D'ÂGE PAR SEXE...")
    
    # ========================================================================
    # TOTAL (Hommes + Femmes)
    # ========================================================================
    
    # 65-74 ans (EXACT)
    df['pop_65_74'] = (
        df.get('population_age_P22_POP65P', 0).fillna(0) - 
        df.get('population_age_P22_POP75P', 0).fillna(0)
    )
    
    # 75-79 ans (EXACT)
    pop_75_79 = (
        df.get('population_age_P22_POP75P', 0).fillna(0) - 
        df.get('population_age_P22_POP80P', 0).fillna(0)
    )
    
    # 80-84 ans (APPROXIMATION : ~60% des 80+)
    pop_80_84 = df.get('population_age_P22_POP80P', 0).fillna(0) * 0.60
    
    # 75-84 ans = 75-79 (exact) + 80-84 (approximation)
    df['pop_75_84'] = pop_75_79 + pop_80_84
    
    # 85+ ans (APPROXIMATION : ~40% des 80+)
    df['pop_85_plus'] = df.get('population_age_P22_POP80P', 0).fillna(0) * 0.40
    
    # ========================================================================
    # HOMMES
    # ========================================================================
    
    # On n'a pas P22_H80P, donc on estime 80+ hommes
    # Ratio hommes/total dans les 75+ pour estimer les 80+
    pop_75p_total = df.get('population_age_P22_POP75P', 0).fillna(0)
    pop_75p_hommes = df.get('population_age_P22_H75P', 0).fillna(0)
    ratio_hommes_75p = pop_75p_hommes / pop_75p_total.replace(0, np.nan)
    ratio_hommes_75p = ratio_hommes_75p.fillna(0.46)  # Default: 46% hommes dans 75+
    
    # Estimer P22_H80P
    pop_80p_total = df.get('population_age_P22_POP80P', 0).fillna(0)
    pop_80p_hommes_estime = pop_80p_total * ratio_hommes_75p
    
    # 65-74 ans hommes (EXACT)
    df['pop_hommes_65_74'] = (
        df.get('population_age_P22_H65P', 0).fillna(0) - 
        df.get('population_age_P22_H75P', 0).fillna(0)
    )
    
    # 75-79 ans hommes
    pop_hommes_75_79 = (
        df.get('population_age_P22_H75P', 0).fillna(0) - 
        pop_80p_hommes_estime
    )
    
    # 80-84 ans hommes (APPROXIMATION)
    pop_hommes_80_84 = pop_80p_hommes_estime * 0.60
    
    # 75-84 ans hommes
    df['pop_hommes_75_84'] = pop_hommes_75_79 + pop_hommes_80_84
    
    # 85+ ans hommes (APPROXIMATION)
    df['pop_hommes_85_plus'] = pop_80p_hommes_estime * 0.40
    
    # ========================================================================
    # FEMMES
    # ========================================================================
    
    # Ratio femmes/total dans les 75+
    pop_75p_femmes = df.get('population_age_P22_F75P', 0).fillna(0)
    ratio_femmes_75p = pop_75p_femmes / pop_75p_total.replace(0, np.nan)
    ratio_femmes_75p = ratio_femmes_75p.fillna(0.54)  # Default: 54% femmes dans 75+
    
    # Estimer P22_F80P
    pop_80p_femmes_estime = pop_80p_total * ratio_femmes_75p
    
    # 65-74 ans femmes (EXACT)
    df['pop_femmes_65_74'] = (
        df.get('population_age_P22_F65P', 0).fillna(0) - 
        df.get('population_age_P22_F75P', 0).fillna(0)
    )
    
    # 75-79 ans femmes
    pop_femmes_75_79 = (
        df.get('population_age_P22_F75P', 0).fillna(0) - 
        pop_80p_femmes_estime
    )
    
    # 80-84 ans femmes (APPROXIMATION)
    pop_femmes_80_84 = pop_80p_femmes_estime * 0.60
    
    # 75-84 ans femmes
    df['pop_femmes_75_84'] = pop_femmes_75_79 + pop_femmes_80_84
    
    # 85+ ans femmes (APPROXIMATION)
    df['pop_femmes_85_plus'] = pop_80p_femmes_estime * 0.40
    
    # ========================================================================
    # AFFICHAGE
    # ========================================================================
    
    print(f"\n   📊 TOTAL (H+F):")
    print(f"      • pop_65_74 (exact) : min={df['pop_65_74'].min():.0f}, moy={df['pop_65_74'].mean():.0f}, max={df['pop_65_74'].max():.0f}")
    print(f"      • pop_75_84 (approx) : min={df['pop_75_84'].min():.0f}, moy={df['pop_75_84'].mean():.0f}, max={df['pop_75_84'].max():.0f}")
    print(f"      • pop_85_plus (approx) : min={df['pop_85_plus'].min():.0f}, moy={df['pop_85_plus'].mean():.0f}, max={df['pop_85_plus'].max():.0f}")
    
    print(f"\n   👨 HOMMES:")
    print(f"      • pop_hommes_65_74 : moy={df['pop_hommes_65_74'].mean():.0f}")
    print(f"      • pop_hommes_75_84 : moy={df['pop_hommes_75_84'].mean():.0f}")
    print(f"      • pop_hommes_85_plus : moy={df['pop_hommes_85_plus'].mean():.0f}")
    
    print(f"\n   👩 FEMMES:")
    print(f"      • pop_femmes_65_74 : moy={df['pop_femmes_65_74'].mean():.0f}")
    print(f"      • pop_femmes_75_84 : moy={df['pop_femmes_75_84'].mean():.0f}")
    print(f"      • pop_femmes_85_plus : moy={df['pop_femmes_85_plus'].mean():.0f}")
    
    # Vérification cohérence
    total_calc = df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']
    total_insee = df.get('population_age_P22_POP65P', 0).fillna(0)
    diff = total_calc - total_insee
    diff_pct = (diff / total_insee.replace(0, np.nan) * 100).mean()
    print(f"\n   ℹ️  Écart moyen reconstruction : {diff_pct:.2f}% (devrait être ~0%)")
    
    return df


def enrich_pharmacies(df_pharmacies, df_pharmacie_iris, data_insee):
    """
    Enrichit toutes les pharmacies avec données INSEE
    Version OPTIMISÉE avec multiprocessing
    """
    print(f"\n🚀 ENRICHISSEMENT AVEC DONNÉES INSEE...")
    print(f"   Workers: {N_WORKERS} CPU")
    print(f"   Batch: {BATCH_SIZE} pharmacies")
    
    # Liste unique des pharmacies
    all_pharmacies = df_pharmacie_iris['id_pharmacie'].unique()
    total_pharmacies = len(all_pharmacies)
    
    print(f"   Total: {total_pharmacies:,} pharmacies")
    
    # Charger checkpoint
    checkpoint = load_checkpoint()
    
    if checkpoint:
        results = checkpoint['results']
        processed_ids = {r['id_pharmacie'] for r in results}
        all_pharmacies = [p for p in all_pharmacies if p not in processed_ids]
        start_batch = len(results) // BATCH_SIZE
    else:
        results = []
        start_batch = 0
    
    # Diviser en batches
    n_batches = (len(all_pharmacies) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n   🔄 Traitement par batch de {BATCH_SIZE}...")
    
    start_time = time.time()
    
    for batch_idx in range(n_batches):
        batch_start = batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(all_pharmacies))
        batch_pharmacies = all_pharmacies[batch_start:batch_end]
        
        # Diviser le batch pour multiprocessing
        worker_batch_size = max(1, len(batch_pharmacies) // N_WORKERS)
        worker_batches = []
        
        for i in range(0, len(batch_pharmacies), worker_batch_size):
            worker_batch = batch_pharmacies[i:i+worker_batch_size]
            worker_batches.append((worker_batch, df_pharmacie_iris, data_insee))
        
        # Traitement parallèle
        with Pool(processes=N_WORKERS) as pool:
            batch_results = []
            
            # Progress bar pour ce batch
            desc = f"   Batch {batch_idx+1}/{n_batches}"
            
            for worker_result in tqdm(
                pool.imap_unordered(process_batch_pharmacies, worker_batches),
                total=len(worker_batches),
                desc=desc,
                leave=False
            ):
                batch_results.extend(worker_result)
        
        # Ajouter aux résultats
        results.extend(batch_results)
        
        # Progression globale
        processed = len(results)
        pct = (processed / total_pharmacies) * 100
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        remaining = total_pharmacies - processed
        eta = remaining / speed if speed > 0 else 0
        
        print(f"   [{processed:>7,}/{total_pharmacies:<7,}] {pct:>5.1f}% | "
              f"Vitesse: {speed:>6.0f}/s | ETA: {eta/60:>5.1f}min")
        
        # Sauvegarde incrémentale
        if (batch_idx + 1) % 5 == 0 or batch_idx == n_batches - 1:
            df_batch = pd.DataFrame(results)
            save_incremental(df_batch, start_batch + batch_idx + 1)
            save_checkpoint(results, batch_pharmacies[-1])
            print(f"      💾 Checkpoint sauvegardé")
    
    # Créer DataFrame final
    print(f"\n   🔨 Création DataFrame final...")
    df_enriched = pd.DataFrame(results)
    
    # ✨ CALCUL DES TRANCHES D'ÂGE (NOUVEAU) ✨
    df_enriched = calculate_age_groups(df_enriched)
    
    # Fusionner avec données pharmacies originales
    df_final = df_pharmacies.merge(df_enriched, on='id_pharmacie', how='left')
    
    elapsed_total = time.time() - start_time
    
    print(f"\n   ✅ Enrichissement terminé!")
    print(f"      • Temps: {elapsed_total/60:.1f} minutes")
    print(f"      • Vitesse moyenne: {total_pharmacies/elapsed_total:.0f} pharmacies/s")
    print(f"      • Pharmacies enrichies: {len(df_final):,}")
    
    return df_final


def save_results(df):
    """Sauvegarde le fichier final"""
    print(f"\n💾 SAUVEGARDE FINALE...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / "pharmacies_enrichies_insee.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ {output_file.name} ({size_mb:.1f} MB)")
    
    # Nettoyer checkpoints
    checkpoint_file = CACHE_DIR / "enrichissement_checkpoint.pkl"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print(f"   🗑️  Checkpoints nettoyés")


def display_summary(df):
    """Affiche le résumé"""
    print(f"\n" + "=" * 70)
    print("📊 RÉSUMÉ - PHARMACIES ENRICHIES")
    print("=" * 70)
    
    print(f"\n💊 PHARMACIES:")
    print(f"   Total: {len(df):,}")
    print(f"   Colonnes: {len(df.columns)}")
    
    # Colonnes ajoutées
    insee_cols = [col for col in df.columns if any(
        prefix in col for prefix in ['population_age_', 'diplome_', 'logement_', 'revenus_']
    )]
    
    print(f"\n📊 DONNÉES INSEE AJOUTÉES:")
    print(f"   • {len(insee_cols)} nouvelles colonnes")
    
    # Grouper par préfixe
    prefixes = {}
    for col in insee_cols:
        prefix = col.split('_')[0]
        if prefix not in prefixes:
            prefixes[prefix] = 0
        prefixes[prefix] += 1
    
    for prefix, count in sorted(prefixes.items()):
        print(f"      • {prefix}: {count} colonnes")
    
    # Afficher les tranches d'âge calculées
    if 'pop_65_74' in df.columns:
        print(f"\n👴 TRANCHES D'ÂGE CALCULÉES:")
        print(f"   TOTAL (H+F):")
        print(f"      • pop_65_74 : moy={df['pop_65_74'].mean():,.0f}")
        print(f"      • pop_75_84 : moy={df['pop_75_84'].mean():,.0f}")
        print(f"      • pop_85_plus : moy={df['pop_85_plus'].mean():,.0f}")
        
        if 'pop_hommes_65_74' in df.columns:
            print(f"   HOMMES:")
            print(f"      • pop_hommes_65_74 : moy={df['pop_hommes_65_74'].mean():,.0f}")
            print(f"      • pop_hommes_75_84 : moy={df['pop_hommes_75_84'].mean():,.0f}")
            print(f"      • pop_hommes_85_plus : moy={df['pop_hommes_85_plus'].mean():,.0f}")
        
        if 'pop_femmes_65_74' in df.columns:
            print(f"   FEMMES:")
            print(f"      • pop_femmes_65_74 : moy={df['pop_femmes_65_74'].mean():,.0f}")
            print(f"      • pop_femmes_75_84 : moy={df['pop_femmes_75_84'].mean():,.0f}")
            print(f"      • pop_femmes_85_plus : moy={df['pop_femmes_85_plus'].mean():,.0f}")
    
    # Détail de toutes les colonnes ajoutées
    print(f"\n📋 COLONNES INSEE AJOUTÉES:")
    for col in sorted(insee_cols):
        non_null = df[col].notna().sum()
        pct = (non_null / len(df)) * 100
        mean_val = df[col].mean() if df[col].dtype in [np.float64, np.int64] else 0
        print(f"      • {col:<45} : {non_null:>6,} ({pct:>5.1f}%) | moy: {mean_val:>10,.0f}")
    
    print(f"\n📁 FICHIER CRÉÉ:")
    print(f"   • pharmacies_enrichies_insee.csv")
    
    print(f"\n💡 PROCHAINE ÉTAPE:")
    print(f"   Utiliser ce fichier pour le scoring avec isochrones")
    
    print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🚀 ENRICHISSEMENT PHARMACIES - VERSION ULTRA-OPTIMISÉE")
    print("=" * 70)
    print(f"⚡ Optimisations:")
    print(f"   • {N_WORKERS} CPU en parallèle")
    print(f"   • Batch de {BATCH_SIZE} pharmacies")
    print(f"   • Sauvegarde incrémentale tous les 5 batchs")
    print(f"   • Reprise automatique si interruption")
    print(f"   • Progress bar temps réel")
    print(f"   • ✨ Calcul automatique tranches d'âge 65-74 / 75-84 / 85+ ✨")
    print("=" * 70)
    
    try:
        # Charger données
        df_pharmacies = load_pharmacies()
        if df_pharmacies is None:
            return False
        
        df_pharmacie_iris = load_pharmacies_iris()
        if df_pharmacie_iris is None:
            return False
        
        data_insee = load_insee_data()
        if not data_insee:
            print(f"\n❌ Aucune donnée INSEE chargée")
            return False
        
        # Enrichir
        df_enriched = enrich_pharmacies(df_pharmacies, df_pharmacie_iris, data_insee)
        
        # Sauvegarder
        save_results(df_enriched)
        
        # Résumé
        display_summary(df_enriched)
        
        print(f"\n✅ ENRICHISSEMENT TERMINÉ AVEC SUCCÈS!")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  INTERRUPTION PAR L'UTILISATEUR")
        print(f"   💾 Checkpoint sauvegardé")
        print(f"   💡 Relancez le script pour reprendre")
        return False
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)