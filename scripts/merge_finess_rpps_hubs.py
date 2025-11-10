#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fusion des fichiers OSM + FINESS + RPPS pour créer un fichier unifié de HUBS
(transports + établissements + professionnels de santé) avec coordonnées et poids d'attractivité

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Fichiers d'entrée
OSM_HUBS_FILE = PROCESSED_DIR / "hubs.csv"
FINESS_FILE = PROCESSED_DIR / "FINESS_with_weights.csv"
RPPS_FILE = PROCESSED_DIR / "RPPS_merged_with_weights.csv"

# Fichier de sortie
OUTPUT_FILE = PROCESSED_DIR / "HUBS_unified.csv"


def main():
    print("=" * 80)
    print("FUSION OSM + FINESS + RPPS → HUBS UNIFIÉS")
    print("=" * 80)
    
    # 1. Charger OSM HUBS
    print(f"\n📖 Lecture OSM HUBS...")
    df_osm = pd.read_csv(OSM_HUBS_FILE)
    print(f"✓ {len(df_osm):,} hubs OSM chargés")
    print(f"  Colonnes: {list(df_osm.columns)}")
    
    # 2. Charger FINESS
    print(f"\n📖 Lecture FINESS...")
    df_finess = pd.read_csv(FINESS_FILE)
    print(f"✓ {len(df_finess):,} établissements FINESS chargés")
    print(f"  Colonnes: {list(df_finess.columns)}")
    
    # 3. Charger RPPS
    print(f"\n📖 Lecture RPPS...")
    df_rpps = pd.read_csv(RPPS_FILE)
    print(f"✓ {len(df_rpps):,} professionnels RPPS chargés")
    print(f"  Colonnes: {list(df_rpps.columns)}")
    
    # 4. Harmoniser les structures
    print(f"\n🔧 Harmonisation des structures...")
    
    # OSM → format unifié
    df_osm_unified = pd.DataFrame({
        'hub_id': df_osm['id_hub'],
        'hub_type': 'transport_commerce',  # Transports et commerces
        'hub_nom': df_osm['nom'],
        'hub_categorie': df_osm['categorie'],
        'hub_type_detail': df_osm['type_hub'],
        'hub_adresse': df_osm['adresse'],
        'hub_departement': None,  # Pas disponible dans OSM
        'hub_commune': df_osm['commune'],
        'latitude': df_osm['latitude'],
        'longitude': df_osm['longitude'],
        'bonus_attractivite': df_osm['bonus_attractivite'],
        'source': df_osm['source']
    })
    
    # FINESS → format unifié
    df_finess_unified = pd.DataFrame({
        'hub_id': 'FINESS_' + df_finess['nofinesset'].astype(str),
        'hub_type': 'etablissement',
        'hub_nom': df_finess['rs'],
        'hub_categorie': df_finess['categorie_simplifiee'],
        'hub_type_detail': df_finess['type_etablissement'],
        'hub_adresse': df_finess['ligneacheminement'],
        'hub_departement': df_finess['departement'],
        'hub_commune': df_finess['commune'],
        'latitude': df_finess['latitude'],
        'longitude': df_finess['longitude'],
        'bonus_attractivite': df_finess['bonus_attractivite'],
        'source': 'FINESS'
    })
    
    # RPPS → format unifié
    df_rpps_unified = pd.DataFrame({
        'hub_id': 'RPPS_' + df_rpps['CodeRPPS'].astype(str),
        'hub_type': 'professionnel',
        'hub_nom': df_rpps['Nom'].fillna('') + ' ' + df_rpps['Prenom'].fillna(''),
        'hub_categorie': df_rpps['NomSpecialiteGers'],
        'hub_type_detail': 'medecin',  # Tous sont des professionnels médicaux
        'hub_adresse': None,  # Pas d'adresse dans le fichier merged
        'hub_departement': None,  # Pas disponible
        'hub_commune': None,  # Pas disponible
        'latitude': df_rpps['latitude'],
        'longitude': df_rpps['longitude'],
        'bonus_attractivite': df_rpps['bonus_attractivite'],
        'source': 'RPPS'
    })
    
    print(f"✓ OSM harmonisé: {len(df_osm_unified):,} lignes")
    print(f"✓ FINESS harmonisé: {len(df_finess_unified):,} lignes")
    print(f"✓ RPPS harmonisé: {len(df_rpps_unified):,} lignes")
    
    # 5. Fusionner
    print(f"\n🔗 Fusion des datasets...")
    df_hubs = pd.concat([df_osm_unified, df_finess_unified, df_rpps_unified], ignore_index=True)
    print(f"✓ {len(df_hubs):,} HUBS totaux")
    
    # 6. Nettoyer et filtrer
    print(f"\n🧹 Nettoyage...")
    
    # Garder seulement les hubs avec coordonnées valides
    avant_coords = len(df_hubs)
    df_hubs = df_hubs[
        df_hubs['latitude'].notna() & 
        df_hubs['longitude'].notna()
    ]
    apres_coords = len(df_hubs)
    print(f"  • Hubs avec coordonnées: {apres_coords:,} (retiré: {avant_coords - apres_coords:,})")
    
    # Garder seulement les hubs avec bonus > 0 (pertinents pour scoring)
    avant_bonus = len(df_hubs)
    df_hubs = df_hubs[df_hubs['bonus_attractivite'] > 0]
    apres_bonus = len(df_hubs)
    print(f"  • Hubs avec bonus > 0: {apres_bonus:,} (retiré: {avant_bonus - apres_bonus:,})")
    
    # 7. Statistiques
    print(f"\n{'='*80}")
    print(f"STATISTIQUES HUBS UNIFIÉS")
    print(f"{'='*80}")
    
    # Par source
    print(f"\nPar source:")
    source_stats = df_hubs.groupby('source').agg({
        'hub_id': 'count',
        'bonus_attractivite': 'mean'
    }).round(3)
    source_stats.columns = ['Nombre', 'Bonus moyen']
    print(source_stats.to_string())
    
    # Par type
    print(f"\nPar type de hub:")
    type_stats = df_hubs.groupby('hub_type').agg({
        'hub_id': 'count',
        'bonus_attractivite': 'mean'
    }).round(3)
    type_stats.columns = ['Nombre', 'Bonus moyen']
    print(type_stats.to_string())
    
    # Top catégories OSM
    print(f"\nTop 15 catégories (OSM - transports & commerces):")
    if len(df_hubs[df_hubs['source'] == 'OSM']) > 0:
        top_osm = df_hubs[df_hubs['source'] == 'OSM'].groupby('hub_categorie').agg({
            'hub_id': 'count',
            'bonus_attractivite': 'mean'
        }).round(3)
        top_osm.columns = ['Nombre', 'Bonus moyen']
        top_osm = top_osm.sort_values('Nombre', ascending=False).head(15)
        for idx, row in top_osm.iterrows():
            print(f"  {idx:40s} | N={row['Nombre']:>6,.0f} | Bonus={row['Bonus moyen']:.3f}")
    
    # Top 20 catégories
    print(f"\nTop 20 catégories (établissements):")
    top_etab = df_hubs[df_hubs['hub_type'] == 'etablissement'].groupby('hub_categorie').agg({
        'hub_id': 'count',
        'bonus_attractivite': 'mean'
    }).round(3)
    top_etab.columns = ['Nombre', 'Bonus moyen']
    top_etab = top_etab.sort_values('Nombre', ascending=False).head(20)
    for idx, row in top_etab.iterrows():
        print(f"  {idx:40s} | N={row['Nombre']:>6,.0f} | Bonus={row['Bonus moyen']:.3f}")
    
    print(f"\nTop 20 spécialités (professionnels):")
    top_prof = df_hubs[df_hubs['hub_type'] == 'professionnel'].groupby('hub_categorie').agg({
        'hub_id': 'count',
        'bonus_attractivite': 'mean'
    }).round(3)
    top_prof.columns = ['Nombre', 'Bonus moyen']
    top_prof = top_prof.sort_values('Nombre', ascending=False).head(20)
    for idx, row in top_prof.iterrows():
        print(f"  {idx:40s} | N={row['Nombre']:>6,.0f} | Bonus={row['Bonus moyen']:.3f}")
    
    # Distribution des bonus
    print(f"\nDistribution des bonus d'attractivité:")
    bonus_dist = df_hubs['bonus_attractivite'].value_counts().sort_index(ascending=False)
    for bonus, count in bonus_dist.head(15).items():
        print(f"  Bonus {bonus:.2f}: {count:>8,} hubs ({count/len(df_hubs)*100:>5.1f}%)")
    
    # 7. Sauvegarder
    print(f"\n💾 Sauvegarde...")
    df_hubs.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"✓ Fichier sauvegardé: {OUTPUT_FILE}")
    print(f"  {len(df_hubs):,} hubs × {len(df_hubs.columns)} colonnes")
    
    # Résumé final
    print(f"\n{'='*80}")
    print(f"✅ FUSION TERMINÉE !")
    print(f"{'='*80}")
    print(f"  • Total HUBS: {len(df_hubs):,}")
    print(f"  • OSM (transports & commerces): {len(df_hubs[df_hubs['source'] == 'OSM']):,}")
    print(f"  • Établissements FINESS: {len(df_hubs[df_hubs['source'] == 'FINESS']):,}")
    print(f"  • Professionnels RPPS: {len(df_hubs[df_hubs['source'] == 'RPPS']):,}")
    print(f"  • Avec coordonnées: {len(df_hubs[df_hubs['latitude'].notna()]):,} (100%)")
    print(f"  • Avec bonus > 0: {len(df_hubs[df_hubs['bonus_attractivite'] > 0]):,} (100%)")
    print(f"  • Bonus moyen: {df_hubs['bonus_attractivite'].mean():.3f}")
    
    return df_hubs


if __name__ == "__main__":
    df = main()
