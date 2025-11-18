#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ULTRA-OPTIMISÉ : Dédoublonnage structures vs médecins

OPTIMISATIONS :
- KDTree spatial pour recherche rapide O(log n)
- Traitement par batch de 1000
- Sauvegarde incrémentale tous les 10,000 hubs
- Reprise automatique si interruption
- Progression détaillée en temps réel

LOGIQUE :
- Si structure générique < 50m d'un médecin RPPS → SUPPRIMER structure
- Garder TOUS les médecins RPPS
- Ne JAMAIS toucher aux pharmacies

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys
import time
from scipy.spatial import cKDTree
import pickle

warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
OUTPUT_DIR = BASE_DIR / "data" / "output"
CACHE_DIR = BASE_DIR / "data" / "cache"

DEDUPLICATE_DISTANCE = 50  # 50 mètres
BATCH_SIZE = 1000  # Traiter par batch
SAVE_EVERY = 10000  # Sauvegarder tous les 10,000

# Structures génériques à supprimer si médecin proche
# Objectif: Supprimer les structures où on trouve des médecins, garder uniquement les médecins RPPS
STRUCTURES_GENERIQUES = {
    # OSM - Structures médicales génériques
    'Hôpital',                          # OSM - contient des médecins RPPS individuels
    'Cabinet médical',                  # OSM - médecin non identifié, probablement dans RPPS
    
    # FINESS - Hôpitaux et cliniques (contiennent des médecins)
    'Centre Hospitalier',               # Hôpital général, médecins listés dans RPPS
    'CHR',                              # Centre Hospitalier Régional
    'Hôpital local',                    # Hôpital de proximité
    'Hôpital militaire',                # Hôpital militaire
    'Clinique chirurgicale',            # Clinique privée, chirurgiens dans RPPS
    'Clinique médicale',                # Clinique privée, médecins dans RPPS
    'Clinique SSR',                     # Soins de suite et réadaptation
    'Établissement pluridisciplinaire', # Multi-spécialités, médecins dans RPPS
    'Autre établissement',              # Établissement non catégorisé
    
    # FINESS - Centres de santé collectifs (regroupent des médecins)
    'Centre de santé',                  # Maison de santé, médecins dans RPPS
    'Maison de santé',                  # Maison de santé pluriprofessionnelle, médecins dans RPPS
    'Maison médicale garde',            # Garde médicale, médecins dans RPPS
    'CPTS',                             # Communauté Professionnelle Territoriale de Santé
    
    # Note: Les laboratoires, EHPAD, dialyse, etc. sont GARDÉS car ce ne sont pas des médecins
}


def load_hubs():
    """Charge le fichier hubs unifié"""
    print(f"\n📥 CHARGEMENT DES HUBS...")

    # Chercher le fichier hubs unifié
    hubs_file = BASE_DIR / "data" / "processed" / "HUBS_unified.csv"
    
    if not hubs_file.exists():
        print(f"   ❌ Fichier non trouvé: {hubs_file}")
        return pd.DataFrame()
    
    print(f"   📁 {hubs_file.name}")
    
    df = pd.read_csv(hubs_file, encoding='utf-8', low_memory=False)
    print(f"   ✓ {len(df):,} hubs chargés")
    
    # Renommer hub_categorie en categorie si nécessaire
    if 'hub_categorie' in df.columns and 'categorie' not in df.columns:
        df = df.rename(columns={'hub_categorie': 'categorie'})
    
    # Vérifier colonnes nécessaires
    required = ['latitude', 'longitude', 'source', 'categorie']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"   ❌ Colonnes manquantes: {missing}")
        return pd.DataFrame()
    
    geocoded = df['latitude'].notna().sum()
    print(f"   ✓ Géocodés: {geocoded:,} ({geocoded/len(df)*100:.1f}%)")
    
    return df


def load_checkpoint():
    """Charge le checkpoint si existe"""
    checkpoint_file = CACHE_DIR / "deduplicate_checkpoint.pkl"
    
    if checkpoint_file.exists():
        print(f"\n💾 CHECKPOINT TROUVÉ!")
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
            
            print(f"   ✓ Progression: {checkpoint['processed']}/{checkpoint['total']}")
            print(f"   ✓ Supprimés jusqu'ici: {len(checkpoint['to_remove']):,}")
            
            response = input(f"\n   Reprendre depuis le checkpoint ? (o/n) : ")
            if response.lower() == 'o':
                return checkpoint
        except Exception as e:
            print(f"   ⚠️  Checkpoint corrompu: {e}")
    
    return None


def save_checkpoint(checkpoint):
    """Sauvegarde le checkpoint"""
    checkpoint_file = CACHE_DIR / "deduplicate_checkpoint.pkl"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(checkpoint, f)


def deduplicate_intelligent(df):
    """
    Dédoublonnage optimisé avec sauvegarde incrémentale
    """
    print(f"\n🚀 DÉDOUBLONNAGE INTELLIGENT (OPTIMISÉ)...")
    print(f"   Distance: {DEDUPLICATE_DISTANCE}m")
    print(f"   Batch: {BATCH_SIZE} structures")
    print(f"   Sauvegarde: tous les {SAVE_EVERY:,} hubs")
    
    start_time = time.time()
    
    # Filtrer géocodés
    df_valid = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    print(f"\n   ✓ {len(df_valid):,} hubs géocodés")
    
    # Séparer médecins RPPS et structures
    df_medecins = df_valid[df_valid['source'] == 'RPPS'].copy()
    df_structures = df_valid[df_valid['source'] != 'RPPS'].copy()
    
    print(f"   • Médecins RPPS: {len(df_medecins):,}")
    print(f"   • Structures: {len(df_structures):,}")
    
    if len(df_medecins) == 0:
        print(f"\n   ⚠️  Pas de médecins RPPS, pas de dédoublonnage")
        return df_valid
    
    # Filtrer structures génériques uniquement
    df_structures_generiques = df_structures[
        df_structures['categorie'].isin(STRUCTURES_GENERIQUES)
    ].copy()
    
    df_structures_specifiques = df_structures[
        ~df_structures['categorie'].isin(STRUCTURES_GENERIQUES)
    ].copy()
    
    print(f"   • Structures génériques (à vérifier): {len(df_structures_generiques):,}")
    print(f"   • Structures spécifiques (à garder): {len(df_structures_specifiques):,}")
    
    # Construire KDTree pour médecins
    print(f"\n   🏗️  Construction KDTree...")
    coords_medecins = df_medecins[['latitude', 'longitude']].values
    coords_medecins_rad = np.radians(coords_medecins)
    tree = cKDTree(coords_medecins_rad)
    print(f"   ✓ KDTree créé ({len(coords_medecins):,} médecins)")
    
    # Charger checkpoint si existe
    checkpoint = load_checkpoint()
    
    if checkpoint:
        to_remove = set(checkpoint['to_remove'])
        start_idx = checkpoint['processed']
    else:
        to_remove = set()
        start_idx = 0
    
    # Traiter structures génériques par batch
    total_structures = len(df_structures_generiques)
    distance_rad = DEDUPLICATE_DISTANCE / 6371000  # 50m en radians
    
    print(f"\n   🔍 RECHERCHE DES DOUBLONS...")
    print(f"   Distance seuil: {DEDUPLICATE_DISTANCE}m")
    
    structures_array = df_structures_generiques.reset_index()
    
    for batch_start in range(start_idx, total_structures, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_structures)
        batch = structures_array.iloc[batch_start:batch_end]
        
        # Progression
        pct = (batch_start / total_structures) * 100
        elapsed = time.time() - start_time
        
        if batch_start > 0:
            speed = batch_start / elapsed
            remaining = total_structures - batch_start
            eta = remaining / speed if speed > 0 else 0
            eta_min = eta / 60
            
            print(f"      [{batch_start:>7,}/{total_structures:<7,}] {pct:>5.1f}% | "
                  f"Supprimés: {len(to_remove):>6,} | "
                  f"Vitesse: {speed:>6.0f}/s | "
                  f"ETA: {eta_min:>5.1f}min", end='\r')
        
        # Traiter le batch
        for _, row in batch.iterrows():
            idx = row['index']
            lat, lon = row['latitude'], row['longitude']
            
            # Chercher médecins proches
            point_rad = np.radians([lat, lon])
            indices = tree.query_ball_point(point_rad, distance_rad)
            
            # Si au moins 1 médecin proche, marquer pour suppression
            if len(indices) > 0:
                to_remove.add(idx)
        
        # Sauvegarde incrémentale
        if (batch_end % SAVE_EVERY == 0) or (batch_end == total_structures):
            checkpoint = {
                'processed': batch_end,
                'total': total_structures,
                'to_remove': list(to_remove),
            }
            save_checkpoint(checkpoint)
    
    print()  # Nouvelle ligne après progression
    
    # Créer DataFrame final
    print(f"\n   🔨 Création du DataFrame final...")
    
    # Indices à garder
    indices_to_keep = set(df_valid.index) - to_remove
    df_final = df_valid.loc[list(indices_to_keep)].copy()
    
    # Statistiques
    removed_count = len(to_remove)
    removed_pct = (removed_count / len(df_valid)) * 100
    
    elapsed_total = time.time() - start_time
    
    print(f"\n   ✅ DÉDOUBLONNAGE TERMINÉ !")
    print(f"      • Temps: {elapsed_total/60:.1f} minutes")
    print(f"      • Avant: {len(df_valid):,} hubs")
    print(f"      • Après: {len(df_final):,} hubs")
    print(f"      • Supprimés: {removed_count:,} ({removed_pct:.1f}%)")
    
    # Détail par source
    print(f"\n   📊 SUPPRIMÉS PAR SOURCE:")
    for source in df_valid['source'].unique():
        before = len(df_valid[df_valid['source'] == source])
        after = len(df_final[df_final['source'] == source])
        removed = before - after
        if before > 0:
            pct = (removed / before) * 100
            print(f"      • {source:<10} : -{removed:>6,} ({pct:>5.1f}%)")
    
    # Détail par catégorie supprimée
    if removed_count > 0:
        print(f"\n   🗑️  TOP 10 CATÉGORIES SUPPRIMÉES:")
        df_removed = df_valid.loc[list(to_remove)]
        for cat, count in df_removed['categorie'].value_counts().head(10).items():
            print(f"      • {cat:<30} : {count:>6,}")
    
    return df_final


def save_results(df):
    """Sauvegarde le fichier final"""
    print(f"\n💾 SAUVEGARDE...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fichier final
    output_file = OUTPUT_DIR / "HUBS_unified_final.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ {output_file.name} ({size_mb:.1f} MB)")
    
    # Backup ancien
    old_file = OUTPUT_DIR / "HUBS_unified_corriges.csv"
    if old_file.exists():
        backup_file = OUTPUT_DIR / "HUBS_unified_corriges_backup.csv"
        import shutil
        shutil.copy2(old_file, backup_file)
        print(f"   💾 Backup: {backup_file.name}")
    
    # Supprimer checkpoint
    checkpoint_file = CACHE_DIR / "deduplicate_checkpoint.pkl"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print(f"   🗑️  Checkpoint supprimé")


def display_summary(df):
    """Affiche le résumé"""
    print(f"\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 70)
    
    total = len(df)
    geocoded = df['latitude'].notna().sum()
    
    print(f"\n✅ HUBS FINAUX:")
    print(f"   Total: {total:,} hubs")
    print(f"   Géocodés: {geocoded:,} ({geocoded/total*100:.1f}%)")
    
    # Par source
    if 'source' in df.columns:
        print(f"\n📋 PAR SOURCE:")
        for source in sorted(df['source'].unique()):
            count = len(df[df['source'] == source])
            pct = (count / total) * 100
            print(f"   • {source:<10} : {count:>7,} ({pct:>5.1f}%)")
    
    # Bonus
    if 'bonus_attractivite' in df.columns:
        print(f"\n💰 BONUS:")
        print(f"   Minimum: {df['bonus_attractivite'].min():.3f}")
        print(f"   Moyen: {df['bonus_attractivite'].mean():.3f}")
        print(f"   Médiane: {df['bonus_attractivite'].median():.3f}")
        print(f"   Maximum: {df['bonus_attractivite'].max():.3f}")
    
    # Top catégories
    print(f"\n🏆 TOP 15 CATÉGORIES:")
    for idx, (cat, count) in enumerate(df['categorie'].value_counts().head(15).items(), 1):
        pct = (count / total) * 100
        bonus = df[df['categorie']==cat]['bonus_attractivite'].mean()
        print(f"   {idx:>2}. {cat:<35} : {count:>7,} ({pct:>4.1f}%) | {bonus:.3f}")
    
    print(f"\n📁 FICHIER CRÉÉ:")
    print(f"   • data/output/HUBS_unified_final.csv")
    
    print(f"\n💡 PRÊT POUR LE SCORING !")
    print(f"   • Structures vs médecins dédoublonnés ✅")
    print(f"   • Tous les médecins RPPS gardés ✅")
    print(f"   • Structures spécifiques gardées ✅")
    
    print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🚀 DÉDOUBLONNAGE INTELLIGENT - VERSION OPTIMISÉE")
    print("=" * 70)
    print(f"📋 Optimisations:")
    print(f"   • KDTree spatial (recherche rapide)")
    print(f"   • Traitement par batch de {BATCH_SIZE}")
    print(f"   • Sauvegarde tous les {SAVE_EVERY:,} hubs")
    print(f"   • Reprise automatique si interruption")
    print(f"   • Progression en temps réel avec ETA")
    print(f"\n📐 Logique:")
    print(f"   • Structure générique + Médecin < 50m → Supprimer structure")
    print(f"   • Garder TOUS les médecins RPPS")
    print(f"   • Garder structures spécifiques (EHPAD, dialyse, etc.)")
    print("=" * 70)
    
    try:
        # Charger
        df = load_hubs()
        
        if df.empty:
            print("\n❌ Aucune donnée")
            return False
        
        # Dédoublonner
        df_final = deduplicate_intelligent(df)
        
        if df_final.empty:
            print("\n❌ Échec")
            return False
        
        # Sauvegarder
        save_results(df_final)
        
        # Résumé
        display_summary(df_final)
        
        print(f"\n✅ TERMINÉ AVEC SUCCÈS!")
        
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