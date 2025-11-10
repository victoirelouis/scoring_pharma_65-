#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de CORRECTION DES BONUS (RAPIDE)

MISSION :
Réattribuer des bonus cohérents à TOUTES les catégories
Focus sur les VRAIS hubs de santé pour seniors 65+

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys

warnings.filterwarnings('ignore')

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_FILE = BASE_DIR / "data" / "processed" / "HUBS_unified.csv"
OUTPUT_FILE = BASE_DIR / "data" / "output" / "HUBS_unified_corriges.csv"

# ============================================================================
# CONFIGURATION COMPLÈTE DES BONUS PAR CATÉGORIE
# ============================================================================

BONUS_PAR_CATEGORIE = {
    # ========================================================================
    # PRIORITÉ MAXIMALE - STRUCTURES SENIORS (0.26-0.30)
    # ========================================================================
    'EHPAD': 0.30,
    'Résidence autonomie': 0.28,
    'EHPA médicalisé': 0.28,
    'Soins longue durée': 0.26,
    'Centre dialyse': 0.26,
    
    # ========================================================================
    # TRÈS HAUTE PRIORITÉ - SOINS DOMICILE SENIORS (0.22-0.25)
    # ========================================================================
    'EHPA non médicalisé': 0.25,
    'Centre de jour seniors': 0.25,
    'Dialyse alternative': 0.24,
    'SSIAD': 0.24,
    'HAD': 0.24,
    'SAAS': 0.22,
    'Centre cancer': 0.22,
    
    # ========================================================================
    # HAUTE PRIORITÉ - SERVICES SENIORS (0.18-0.20)
    # ========================================================================
    'Service aide seniors': 0.20,
    'Traitement domicile': 0.20,
    'Centre de santé': 0.18,
    'Maison de santé': 0.18,
    'CHS psychiatrie': 0.18,
    'Hôpital local': 0.18,
    'MAS': 0.18,
    'Consultation cancer': 0.18,
    'Équipe soins spécialisés': 0.18,
    
    # ========================================================================
    # MÉDECINS ESSENTIELS SENIORS (0.16-0.18)
    # ========================================================================
    'Médecine Générale': 0.18,
    'Gériatrie Gérontologie': 0.18,
    'Cardiologie': 0.16,
    'Rhumatologie': 0.16,
    
    # ========================================================================
    # MÉDECINS TRÈS FRÉQUENTS SENIORS (0.14-0.15)
    # ========================================================================
    'Ophtalmologie': 0.15,
    'Endocrinologie Diabétologie': 0.15,
    'Néphrologie': 0.15,
    'SAA': 0.15,
    'Laboratoire biologie': 0.15,
    'Laboratoire analyse': 0.15,
    'FAM': 0.15,
    'Centre Hospitalier': 0.15,
    'CHR': 0.15,
    'LHSS': 0.15,
    'LAM': 0.15,
    'CLIC': 0.15,
    'Neurologie': 0.14,
    'Gastro Entérologie': 0.14,
    'Aide ménagère domicile': 0.14,
    'Oxygène domicile': 0.14,
    'Foyer vie handicap': 0.14,
    'Clinique SSR': 0.14,
    
    # ========================================================================
    # MÉDECINS FRÉQUENTS SENIORS (0.12-0.13)
    # ========================================================================
    'Dermatologie': 0.13,
    'Pneumologie': 0.13,
    'Urologie': 0.13,
    'Oncologie Cancérologie': 0.13,
    'Phlébologie Angeiologie': 0.12,
    'Hématologie': 0.12,
    'Médecine Interne': 0.12,
    'CMP': 0.12,
    'CPTS': 0.12,
    'Foyer hébergement handicap': 0.12,
    'Portage repas': 0.12,
    'Mandataire judiciaire': 0.12,
    'Accueil médicalisé handicap': 0.12,
    'ACT': 0.12,
    'CSAPA': 0.12,
    'Centre vaccination': 0.12,
    'Centre soins prévention': 0.12,
    'Clinique chirurgicale': 0.12,
    'Clinique médicale': 0.12,
    'Établissement pluridisciplinaire': 0.12,
    'Hôpital militaire': 0.12,
    'Autre établissement': 0.12,
    'Laboratoire sans FSE': 0.12,
    'MDPH': 0.12,
    
    # ========================================================================
    # MÉDECINS MODÉRÉS (0.10-0.11)
    # ========================================================================
    'Rééducation Fonctionnelle': 0.11,
    'Allergologie': 0.11,
    'Psychiatrie': 0.10,
    'Oto Rhino Laryngologie': 0.10,
    'Chirurgie Orthopédique': 0.10,
    'Radiothérapie': 0.10,
    'CHRS': 0.10,
    'CATTP': 0.10,
    'Thermalisme': 0.10,
    'CeGIDD': 0.10,
    'Examen santé': 0.10,
    'Équipe mobile précarité': 0.10,
    'Accès soins': 0.10,
    'DAC': 0.10,
    'Téléconsultation': 0.10,
    'Transfusion sanguine': 0.10,
    'Maison santé mentale': 0.10,
    'CAARUD': 0.10,
    'CLAT': 0.10,
    
    # ========================================================================
    # CHIRURGIE ET ANESTHÉSIE (0.08)
    # ========================================================================
    'Anesthésiologie Réanimation': 0.08,
    'Chirurgie Générale': 0.08,
    'Stomatologie': 0.08,
    'Maison relais': 0.08,
    
    # ========================================================================
    # GYNÉCO / DENTAIRE (0.05-0.07)
    # ========================================================================
    'Chirurgie Dentaire': 0.07,
    'Gynécologie': 0.05,
    
    # ========================================================================
    # MÉDECINE ESTHÉTIQUE (0.03)
    # ========================================================================
    'Médecine Esthétique': 0.03,
    
    # ========================================================================
    # HUBS OSM - HÔPITAUX ET CABINETS (0.12-0.15)
    # ========================================================================
    'Hôpital': 0.15,  # Aligné avec FINESS
    'Cabinet médical': 0.12,  # Médecin non identifié
    
    # ========================================================================
    # HUBS OSM - MOBILITÉ (0.02-0.03)
    # Utiles pour la mobilité des seniors mais pas hubs de santé
    # ========================================================================
    'Arrêt de bus': 0.02,  # CORRIGÉ de 0.15 → 0.02
    'Station de métro': 0.02,  # CORRIGÉ de 0.08 → 0.02
    'Gare ferroviaire': 0.03,  # CORRIGÉ de 0.10 → 0.03
    
    # ========================================================================
    # HUBS OSM - COMMERCIAL (0.03-0.05)
    # Flux seniors mais pas directement santé
    # ========================================================================
    'Marché': 0.03,  # CORRIGÉ de 0.20 → 0.03
    'Supermarché': 0.05,  # CORRIGÉ de 0.10 → 0.05
    
    # ========================================================================
    # NON PERTINENT POUR SENIORS 65+ (0.00)
    # ========================================================================
    'Pédiatrie': 0.00,
    'Sage Femme': 0.00,
}


def load_hubs():
    """
    Charge le fichier HUBS_unified.csv
    
    Returns:
        pd.DataFrame: Hubs chargés
    """
    print(f"\n📥 CHARGEMENT DES HUBS...")
    
    if not INPUT_FILE.exists():
        print(f"   ❌ Fichier non trouvé: {INPUT_FILE}")
        return pd.DataFrame()
    
    print(f"   📁 {INPUT_FILE.name}")
    
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8', low_memory=False)
        print(f"   ✓ {len(df):,} hubs chargés")
        
        # Renommer hub_categorie en categorie si nécessaire
        if 'hub_categorie' in df.columns:
            df = df.rename(columns={'hub_categorie': 'categorie'})
            print(f"   ✓ Colonne 'hub_categorie' renommée en 'categorie'")
        
        # Statistiques initiales
        if 'categorie' in df.columns:
            nb_categories = df['categorie'].nunique()
            print(f"   ✓ {nb_categories} catégories uniques")
        
        if 'bonus_attractivite' in df.columns:
            bonus_mean = df['bonus_attractivite'].mean()
            bonus_min = df['bonus_attractivite'].min()
            bonus_max = df['bonus_attractivite'].max()
            print(f"   ✓ Bonus actuel: min={bonus_min:.3f}, mean={bonus_mean:.3f}, max={bonus_max:.3f}")
        
        geocoded = df['latitude'].notna().sum()
        print(f"   ✓ Géocodés: {geocoded:,} ({geocoded/len(df)*100:.1f}%)")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return pd.DataFrame()


def reassign_bonus(df):
    """
    Réattribue les bonus cohérents à toutes les catégories
    
    Args:
        df (pd.DataFrame): DataFrame avec colonnes 'categorie' et 'bonus_attractivite'
        
    Returns:
        pd.DataFrame: DataFrame avec bonus corrigés
    """
    print(f"\n🔧 RÉATTRIBUTION DES BONUS...")
    
    if 'categorie' not in df.columns:
        print(f"   ❌ Colonne 'categorie' manquante")
        return df
    
    # Sauvegarder les anciens bonus pour comparaison
    df['bonus_ancien'] = df.get('bonus_attractivite', 0.10)
    
    # Fonction pour attribuer le nouveau bonus
    def get_new_bonus(categorie):
        if pd.isna(categorie):
            return 0.10  # Valeur par défaut
        
        # Chercher correspondance exacte
        if categorie in BONUS_PAR_CATEGORIE:
            return BONUS_PAR_CATEGORIE[categorie]
        
        # Chercher correspondance partielle (pour variantes)
        categorie_lower = str(categorie).lower()
        for cat_ref, bonus in BONUS_PAR_CATEGORIE.items():
            if cat_ref.lower() in categorie_lower or categorie_lower in cat_ref.lower():
                return bonus
        
        # Si pas trouvé, retourner valeur par défaut
        return 0.10
    
    # Appliquer les nouveaux bonus
    print(f"   ⏳ Application des nouveaux bonus...")
    df['bonus_attractivite'] = df['categorie'].apply(get_new_bonus)
    
    # Statistiques
    print(f"   ✓ Bonus réattribués")
    
    # Changements significatifs
    df['bonus_change'] = df['bonus_attractivite'] - df['bonus_ancien']
    
    nb_increases = (df['bonus_change'] > 0.01).sum()
    nb_decreases = (df['bonus_change'] < -0.01).sum()
    nb_unchanged = (df['bonus_change'].abs() <= 0.01).sum()
    
    print(f"\n   📊 Changements:")
    print(f"      • Augmentés: {nb_increases:,} hubs")
    print(f"      • Diminués: {nb_decreases:,} hubs")
    print(f"      • Inchangés: {nb_unchanged:,} hubs")
    
    # Top changements (augmentations)
    if nb_increases > 0:
        print(f"\n   ⬆️  Top 5 augmentations:")
        top_increases = df[df['bonus_change'] > 0].nlargest(5, 'bonus_change')
        for _, row in top_increases.iterrows():
            cat = str(row['categorie'])[:30]
            print(f"      • {cat:<30} : {row['bonus_ancien']:.3f} → {row['bonus_attractivite']:.3f} (+{row['bonus_change']:.3f})")
    
    # Top changements (diminutions)
    if nb_decreases > 0:
        print(f"\n   ⬇️  Top 5 diminutions:")
        top_decreases = df[df['bonus_change'] < 0].nsmallest(5, 'bonus_change')
        for _, row in top_decreases.iterrows():
            cat = str(row['categorie'])[:30]
            print(f"      • {cat:<30} : {row['bonus_ancien']:.3f} → {row['bonus_attractivite']:.3f} ({row['bonus_change']:.3f})")
    
    # Nouveau bonus moyen
    bonus_mean_new = df['bonus_attractivite'].mean()
    bonus_mean_old = df['bonus_ancien'].mean()
    bonus_min_new = df['bonus_attractivite'].min()
    bonus_max_new = df['bonus_attractivite'].max()
    
    print(f"\n   📈 Bonus moyen: {bonus_mean_old:.3f} → {bonus_mean_new:.3f}")
    print(f"   📈 Bonus min: {bonus_min_new:.3f}, max: {bonus_max_new:.3f}")
    
    # Nettoyer colonnes temporaires
    df = df.drop(columns=['bonus_ancien', 'bonus_change'])
    
    return df


def save_results(df):
    """
    Sauvegarde le fichier final
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n💾 SAUVEGARDE...")
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"   ✅ {OUTPUT_FILE.name} ({size_mb:.1f} MB)")
    
    # Backup de l'ancien
    import shutil
    if INPUT_FILE.exists():
        backup_file = INPUT_FILE.parent / "HUBS_unified_old.csv"
        shutil.copy2(INPUT_FILE, backup_file)
        print(f"   💾 Backup: {backup_file.name}")


def display_summary(df):
    """
    Affiche le résumé final
    
    Args:
        df (pd.DataFrame): DataFrame final
    """
    print(f"\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL - HUBS AVEC BONUS CORRIGÉS")
    print("=" * 70)
    
    if df.empty:
        print("Aucune donnée")
        return
    
    total = len(df)
    geocoded = df['latitude'].notna().sum()
    
    print(f"\n✅ HUBS FINAUX:")
    print(f"   Total: {total:,} hubs")
    print(f"   Géocodés: {geocoded:,} ({geocoded/total*100:.1f}%)")
    
    # Par source
    if 'source' in df.columns:
        print(f"\n📋 PAR SOURCE:")
        for source in df['source'].unique():
            count = len(df[df['source'] == source])
            pct = (count / total) * 100
            bonus_mean = df[df['source'] == source]['bonus_attractivite'].mean()
            print(f"   • {source:<10} : {count:>7,} ({pct:>5.1f}%) | bonus moyen: {bonus_mean:.3f}")
    
    # Bonus
    print(f"\n💰 BONUS D'ATTRACTIVITÉ:")
    print(f"   Minimum: {df['bonus_attractivite'].min():.3f}")
    print(f"   Moyen: {df['bonus_attractivite'].mean():.3f}")
    print(f"   Médiane: {df['bonus_attractivite'].median():.3f}")
    print(f"   Maximum: {df['bonus_attractivite'].max():.3f}")
    
    # Distribution bonus
    print(f"\n📊 DISTRIBUTION DES BONUS:")
    bonus_ranges = [
        (0.25, 0.31, 'Très élevé (0.25-0.30)'),
        (0.18, 0.25, 'Élevé (0.18-0.25)'),
        (0.12, 0.18, 'Moyen (0.12-0.18)'),
        (0.08, 0.12, 'Modéré (0.08-0.12)'),
        (0.03, 0.08, 'Faible (0.03-0.08)'),
        (0.00, 0.03, 'Très faible (0.00-0.03)'),
    ]
    
    for min_b, max_b, label in bonus_ranges:
        count = len(df[(df['bonus_attractivite'] >= min_b) & (df['bonus_attractivite'] < max_b)])
        pct = (count / total) * 100
        print(f"   • {label:<30} : {count:>7,} ({pct:>5.1f}%)")
    
    # Top catégories
    print(f"\n🏆 TOP 15 CATÉGORIES:")
    for idx, (cat, count) in enumerate(df['categorie'].value_counts().head(15).items(), 1):
        bonus_mean = df[df['categorie']==cat]['bonus_attractivite'].mean()
        pct = (count / total) * 100
        cat_display = str(cat)[:35]
        print(f"   {idx:>2}. {cat_display:<35} : {count:>7,} ({pct:>4.1f}%) | bonus: {bonus_mean:.3f}")
    
    # Fichier
    print(f"\n📁 FICHIER CRÉÉ:")
    print(f"   • {OUTPUT_FILE.relative_to(BASE_DIR)}")
    
    print(f"\n💡 BONUS CORRIGÉS - PRÊT POUR LE SCORING !")
    print(f"   • Focus sur hubs de santé seniors 65+ ✅")
    print(f"   • Transports/commerces = bonus faibles ✅")
    print(f"   • Structures seniors = bonus élevés ✅")
    
    print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔧 CORRECTION DES BONUS (RAPIDE)")
    print("=" * 70)
    print(f"📋 Ce script :")
    print(f"   1. Charge HUBS_unified.csv ({INPUT_FILE.relative_to(BASE_DIR)})")
    print(f"   2. Réattribue des bonus COHÉRENTS")
    print(f"      → Focus hubs de santé pour seniors 65+")
    print(f"      → Arrêts bus: 0.15 → 0.02")
    print(f"      → Marchés: 0.20 → 0.03")
    print(f"      → Supermarchés: 0.10 → 0.05")
    print(f"   3. Sauvegarde HUBS_unified_corriges.csv")
    print(f"   ⚡ SANS dédoublonnage (garde tous les {654589:,} hubs)")
    print("=" * 70)
    
    try:
        # 1. Charger
        df = load_hubs()
        
        if df.empty:
            print("\n❌ Aucune donnée disponible")
            return False
        
        # 2. Réattribuer bonus
        df = reassign_bonus(df)
        
        if df.empty:
            print("\n❌ Échec de la réattribution")
            return False
        
        # 3. Sauvegarder
        save_results(df)
        
        # 4. Résumé
        display_summary(df)
        
        print(f"\n✅ CORRECTION TERMINÉE AVEC SUCCÈS!")
        print(f"   ⏱️  Temps d'exécution: quelques secondes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
