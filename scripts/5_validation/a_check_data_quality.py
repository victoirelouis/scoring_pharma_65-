#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de CONTRÔLE QUALITÉ - Pharmacies enrichies INSEE

MISSION :
Vérifier la qualité des données avant le scoring final

VÉRIFICATIONS :
1. Complétude (valeurs manquantes)
2. Cohérence (sommes, ratios H/F, tranches d'âge)
3. Outliers (valeurs aberrantes)
4. Distribution géographique
5. Vérification des fichiers nécessaires au scoring

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
OUTPUT_DIR = BASE_DIR / "data" / "output"
ISOCHRONES_DIR = BASE_DIR / "data" / "processed" / "isochrones"
REPORTS_DIR = BASE_DIR / "data" / "reports"

# Style des graphiques
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


def load_data():
    """Charge les données enrichies"""
    print(f"\n📥 CHARGEMENT DES DONNÉES...")
    
    pharma_file = OUTPUT_DIR / "pharmacies_enrichies_insee.csv"
    
    if not pharma_file.exists():
        print(f"   ❌ {pharma_file.name} non trouvé")
        print(f"   💡 Lancez d'abord enrichir_pharmacies_optimise.py")
        return None
    
    print(f"   📁 {pharma_file.name}")
    
    df = pd.read_csv(pharma_file, encoding='utf-8', low_memory=False)
    print(f"   ✓ {len(df):,} pharmacies")
    print(f"   ✓ {len(df.columns)} colonnes")
    
    return df


def check_completeness(df):
    """Vérification 1 : Complétude des données"""
    print(f"\n" + "=" * 70)
    print("1️⃣  COMPLÉTUDE DES DONNÉES")
    print("=" * 70)
    
    issues = []
    
    # Colonnes essentielles
    essential_cols = {
        'Identification': ['id_pharmacie'],
        'Localisation': ['type_zone'],
        'Population totale': ['pop_65_74', 'pop_75_84', 'pop_85_plus'],
        'Population hommes': ['pop_hommes_65_74', 'pop_hommes_75_84', 'pop_hommes_85_plus'],
        'Population femmes': ['pop_femmes_65_74', 'pop_femmes_75_84', 'pop_femmes_85_plus'],
    }
    
    for category, cols in essential_cols.items():
        print(f"\n📋 {category}:")
        
        for col in cols:
            if col not in df.columns:
                print(f"   ❌ {col:<30} : COLONNE MANQUANTE")
                issues.append(f"Colonne manquante: {col}")
            else:
                total = len(df)
                missing = df[col].isna().sum()
                pct_missing = (missing / total) * 100
                
                status = "✅" if pct_missing == 0 else "⚠️" if pct_missing < 5 else "❌"
                print(f"   {status} {col:<30} : {total-missing:>7,}/{total:<7,} ({100-pct_missing:>5.1f}%)")
                
                if pct_missing > 5:
                    issues.append(f"{col}: {pct_missing:.1f}% valeurs manquantes")
    
    # Résumé
    if not issues:
        print(f"\n   ✅ COMPLÉTUDE PARFAITE !")
    else:
        print(f"\n   ⚠️  {len(issues)} problèmes détectés:")
        for issue in issues:
            print(f"      • {issue}")
    
    return issues


def check_consistency(df):
    """Vérification 2 : Cohérence des données"""
    print(f"\n" + "=" * 70)
    print("2️⃣  COHÉRENCE DES DONNÉES")
    print("=" * 70)
    
    issues = []
    
    # Vérifier que les colonnes nécessaires existent
    required_cols = ['pop_65_74', 'pop_75_84', 'pop_85_plus', 
                     'pop_hommes_65_74', 'pop_hommes_75_84', 'pop_hommes_85_plus',
                     'pop_femmes_65_74', 'pop_femmes_75_84', 'pop_femmes_85_plus']
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"\n   ❌ Colonnes manquantes pour vérification: {missing_cols}")
        return [f"Colonnes manquantes: {missing_cols}"]
    
    # 1. Vérification Total = Hommes + Femmes
    print(f"\n🧮 COHÉRENCE H + F = TOTAL:")
    
    for age_group in ['65_74', '75_84', '85_plus']:
        total = df[f'pop_{age_group}']
        hommes = df[f'pop_hommes_{age_group}']
        femmes = df[f'pop_femmes_{age_group}']
        
        diff = total - (hommes + femmes)
        diff_pct = (diff / total.replace(0, np.nan) * 100).mean()
        
        status = "✅" if abs(diff_pct) < 1 else "⚠️" if abs(diff_pct) < 5 else "❌"
        print(f"   {status} {age_group:<10} : écart moyen = {diff_pct:>6.2f}%")
        
        if abs(diff_pct) > 5:
            issues.append(f"Écart H+F vs Total pour {age_group}: {diff_pct:.1f}%")
    
    # 2. Vérification somme tranches ≈ POP65P
    if 'population_age_P22_POP65P' in df.columns:
        print(f"\n🧮 COHÉRENCE SOMME TRANCHES vs INSEE P22_POP65P:")
        
        total_tranches = df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']
        total_insee = df['population_age_P22_POP65P']
        
        diff = total_tranches - total_insee
        diff_pct = (diff / total_insee.replace(0, np.nan) * 100).mean()
        
        status = "✅" if abs(diff_pct) < 1 else "⚠️" if abs(diff_pct) < 5 else "❌"
        print(f"   {status} Écart reconstruction : {diff_pct:>6.2f}%")
        
        if abs(diff_pct) > 5:
            issues.append(f"Somme tranches vs INSEE: écart {diff_pct:.1f}%")
    
    # 3. Ratio Hommes/Femmes
    print(f"\n👥 RATIO HOMMES/FEMMES (attendu: ~46% H / ~54% F):")
    
    total_pop = df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']
    total_hommes = df['pop_hommes_65_74'] + df['pop_hommes_75_84'] + df['pop_hommes_85_plus']
    total_femmes = df['pop_femmes_65_74'] + df['pop_femmes_75_84'] + df['pop_femmes_85_plus']
    
    ratio_hommes = (total_hommes / total_pop.replace(0, np.nan) * 100).mean()
    ratio_femmes = (total_femmes / total_pop.replace(0, np.nan) * 100).mean()
    
    print(f"   • Hommes : {ratio_hommes:>5.1f}% (attendu: ~46%)")
    print(f"   • Femmes : {ratio_femmes:>5.1f}% (attendu: ~54%)")
    
    if not (44 <= ratio_hommes <= 48):
        issues.append(f"Ratio hommes anormal: {ratio_hommes:.1f}% (attendu ~46%)")
    
    # 4. Valeurs négatives
    print(f"\n🔍 VALEURS NÉGATIVES:")
    
    pop_cols = [col for col in df.columns if col.startswith('pop_')]
    negative_found = False
    
    for col in pop_cols:
        negatives = (df[col] < 0).sum()
        if negatives > 0:
            print(f"   ❌ {col:<30} : {negatives} valeurs négatives")
            issues.append(f"{col}: {negatives} valeurs négatives")
            negative_found = True
    
    if not negative_found:
        print(f"   ✅ Aucune valeur négative détectée")
    
    # Résumé
    if not issues:
        print(f"\n   ✅ COHÉRENCE PARFAITE !")
    else:
        print(f"\n   ⚠️  {len(issues)} problèmes détectés:")
        for issue in issues:
            print(f"      • {issue}")
    
    return issues


def check_outliers(df):
    """Vérification 3 : Détection des outliers"""
    print(f"\n" + "=" * 70)
    print("3️⃣  DÉTECTION DES OUTLIERS")
    print("=" * 70)
    
    issues = []
    
    # Colonnes à vérifier
    pop_cols = ['pop_65_74', 'pop_75_84', 'pop_85_plus']
    
    print(f"\n📊 STATISTIQUES DESCRIPTIVES:")
    print(f"{'Colonne':<20} {'Min':>8} {'Q1':>8} {'Médiane':>8} {'Q3':>8} {'Max':>8} {'Outliers':>10}")
    print("-" * 85)
    
    for col in pop_cols:
        if col not in df.columns:
            continue
        
        data = df[col].dropna()
        
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 3 * iqr
        upper_bound = q3 + 3 * iqr
        
        outliers = ((data < lower_bound) | (data > upper_bound)).sum()
        outliers_pct = (outliers / len(data)) * 100
        
        print(f"{col:<20} {data.min():>8.0f} {q1:>8.0f} {data.median():>8.0f} "
              f"{q3:>8.0f} {data.max():>8.0f} {outliers:>8} ({outliers_pct:>4.1f}%)")
        
        if outliers_pct > 5:
            issues.append(f"{col}: {outliers_pct:.1f}% outliers (>5%)")
    
    # Pharmacies avec populations extrêmes
    print(f"\n🔍 TOP 5 PHARMACIES - POPULATIONS ÉLEVÉES:")
    total_pop = df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']
    df_temp = df.copy()
    df_temp['total_pop_65plus'] = total_pop
    
    top5 = df_temp.nlargest(5, 'total_pop_65plus')
    for idx, (_, row) in enumerate(top5.iterrows(), 1):
        nom = row.get('nom', f"ID {row['id_pharmacie']}")
        pop = row['total_pop_65plus']
        zone = row.get('type_zone', 'N/A')
        print(f"   {idx}. {nom:<40} : {pop:>8,.0f} ({zone})")
    
    print(f"\n🔍 TOP 5 PHARMACIES - POPULATIONS FAIBLES:")
    bottom5 = df_temp.nsmallest(5, 'total_pop_65plus')
    for idx, (_, row) in enumerate(bottom5.iterrows(), 1):
        nom = row.get('nom', f"ID {row['id_pharmacie']}")
        pop = row['total_pop_65plus']
        zone = row.get('type_zone', 'N/A')
        print(f"   {idx}. {nom:<40} : {pop:>8,.0f} ({zone})")
    
    # Résumé
    if not issues:
        print(f"\n   ✅ PAS D'OUTLIERS MAJEURS")
    else:
        print(f"\n   ⚠️  {len(issues)} alertes:")
        for issue in issues:
            print(f"      • {issue}")
    
    return issues


def check_geographic_distribution(df):
    """Vérification 4 : Distribution géographique"""
    print(f"\n" + "=" * 70)
    print("4️⃣  DISTRIBUTION GÉOGRAPHIQUE")
    print("=" * 70)
    
    issues = []
    
    if 'type_zone' not in df.columns:
        print(f"\n   ⚠️  Colonne 'type_zone' absente")
        return [f"Colonne type_zone absente"]
    
    # Distribution par type de zone
    print(f"\n🗺️  PHARMACIES PAR TYPE DE ZONE:")
    
    zone_counts = df['type_zone'].value_counts()
    total = len(df)
    
    for zone, count in zone_counts.items():
        pct = (count / total) * 100
        print(f"   • {zone:<15} : {count:>6,} ({pct:>5.1f}%)")
    
    # Population moyenne par type de zone
    print(f"\n👥 POPULATION MOYENNE 65+ PAR TYPE DE ZONE:")
    
    total_pop = df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']
    df_temp = df.copy()
    df_temp['total_pop_65plus'] = total_pop
    
    for zone in df_temp['type_zone'].unique():
        df_zone = df_temp[df_temp['type_zone'] == zone]
        avg_pop = df_zone['total_pop_65plus'].mean()
        print(f"   • {zone:<15} : {avg_pop:>8,.0f} personnes/pharmacie")
    
    # Vérifier cohérence (urbain > rural)
    if 'urbain' in zone_counts.index and 'rural' in zone_counts.index:
        df_urbain = df_temp[df_temp['type_zone'] == 'urbain']
        df_rural = df_temp[df_temp['type_zone'] == 'rural']
        
        avg_urbain = df_urbain['total_pop_65plus'].mean()
        avg_rural = df_rural['total_pop_65plus'].mean()
        
        if avg_rural > avg_urbain:
            issues.append(f"Incohérence: pop rurale ({avg_rural:.0f}) > urbaine ({avg_urbain:.0f})")
    
    # Résumé
    if not issues:
        print(f"\n   ✅ DISTRIBUTION COHÉRENTE")
    else:
        print(f"\n   ⚠️  {len(issues)} alertes:")
        for issue in issues:
            print(f"      • {issue}")
    
    return issues


def check_scoring_readiness(df):
    """Vérification 5 : Prêt pour le scoring"""
    print(f"\n" + "=" * 70)
    print("5️⃣  VÉRIFICATION PRÊT POUR SCORING")
    print("=" * 70)
    
    issues = []
    
    # 1. Fichier hubs
    print(f"\n📁 FICHIER HUBS:")
    
    # Le bon fichier est HUBS_unified_final.csv
    hubs_file = OUTPUT_DIR / "HUBS_unified_final.csv"
    
    if hubs_file.exists():
        df_hubs = pd.read_csv(hubs_file, encoding='utf-8', low_memory=False, nrows=5)
        print(f"   ✅ {hubs_file.name} trouvé")
        
        if 'bonus_attractivite' not in df_hubs.columns:
            print(f"   ❌ Colonne 'bonus_attractivite' manquante")
            issues.append("Colonne bonus_attractivite manquante dans hubs")
        else:
            print(f"   ✅ Colonne 'bonus_attractivite' présente")
    else:
        print(f"   ❌ Fichier hubs non trouvé")
        issues.append("Fichier hubs non trouvé")
    
    # 2. Isochrones
    print(f"\n📁 ISOCHRONES:")
    
    if not ISOCHRONES_DIR.exists():
        print(f"   ❌ Dossier isochrones non trouvé: {ISOCHRONES_DIR}")
        issues.append("Dossier isochrones non trouvé")
    else:
        # Chercher dans les sous-dossiers drive_XX et walk_XX
        isochrone_files = []
        subdirs = []
        for subdir in ISOCHRONES_DIR.iterdir():
            if subdir.is_dir() and (subdir.name.startswith('drive_') or subdir.name.startswith('walk_')):
                subdirs.append(subdir.name)
                isochrone_files.extend(list(subdir.glob("*.geojson")))
        
        nb_isochrones = len(isochrone_files)
        nb_pharmacies = len(df)
        coverage_pct = (nb_isochrones / nb_pharmacies) * 100 if nb_pharmacies > 0 else 0
        
        print(f"   ✓ Dossier: {ISOCHRONES_DIR}")
        print(f"   ✓ Sous-dossiers: {', '.join(subdirs) if subdirs else 'Aucun'}")
        print(f"   ✓ {nb_isochrones:,} fichiers .geojson")
        print(f"   ✓ Couverture: {coverage_pct:.1f}% des pharmacies")
        
        if coverage_pct < 90:
            print(f"   ⚠️  Couverture < 90%")
            issues.append(f"Couverture isochrones: {coverage_pct:.1f}% < 90%")
        else:
            print(f"   ✅ Couverture suffisante")
    
    # 3. Colonnes nécessaires au scoring
    print(f"\n📋 COLONNES NÉCESSAIRES AU SCORING:")
    
    required_for_scoring = [
        'id_pharmacie',
        'type_zone',
        'pop_65_74', 'pop_75_84', 'pop_85_plus',
    ]
    
    missing = [col for col in required_for_scoring if col not in df.columns]
    
    if missing:
        print(f"   ❌ Colonnes manquantes:")
        for col in missing:
            print(f"      • {col}")
            issues.append(f"Colonne manquante: {col}")
    else:
        print(f"   ✅ Toutes les colonnes présentes")
    
    # Résumé
    print(f"\n" + "=" * 70)
    if not issues:
        print(f"✅ PRÊT POUR LE SCORING !")
        print(f"   Vous pouvez lancer scoring_final_optimise.py")
    else:
        print(f"⚠️  {len(issues)} PROBLÈMES À RÉSOUDRE:")
        for issue in issues:
            print(f"   • {issue}")
    print("=" * 70)
    
    return issues


def generate_report(all_issues, df):
    """Génère un rapport récapitulatif"""
    print(f"\n" + "=" * 70)
    print("📊 RAPPORT DE CONTRÔLE QUALITÉ")
    print("=" * 70)
    
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    report_file = REPORTS_DIR / "data_quality_report.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("RAPPORT DE CONTRÔLE QUALITÉ - PHARMACIES ENRICHIES\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fichier: pharmacies_enrichies_insee.csv\n")
        f.write(f"Nombre de pharmacies: {len(df):,}\n")
        f.write(f"Nombre de colonnes: {len(df.columns)}\n\n")
        
        # Résumé par catégorie
        categories = [
            "1. Complétude",
            "2. Cohérence",
            "3. Outliers",
            "4. Distribution géographique",
            "5. Prêt pour scoring"
        ]
        
        f.write("RÉSUMÉ PAR CATÉGORIE:\n")
        f.write("-" * 70 + "\n")
        
        total_issues = sum(len(issues) for issues in all_issues.values())
        
        for cat_name, issues in zip(categories, all_issues.values()):
            status = "✅ OK" if len(issues) == 0 else f"⚠️  {len(issues)} problème(s)"
            f.write(f"{cat_name:<30} : {status}\n")
            if issues:
                for issue in issues:
                    f.write(f"   • {issue}\n")
            f.write("\n")
        
        f.write("=" * 70 + "\n")
        if total_issues == 0:
            f.write("✅ QUALITÉ PARFAITE - PRÊT POUR LE SCORING\n")
        else:
            f.write(f"⚠️  {total_issues} PROBLÈMES DÉTECTÉS - À CORRIGER AVANT SCORING\n")
        f.write("=" * 70 + "\n")
    
    print(f"\n   ✅ Rapport sauvegardé:")
    print(f"      {report_file}")
    
    # Statistiques de base
    print(f"\n📊 STATISTIQUES GLOBALES:")
    print(f"   • Pharmacies: {len(df):,}")
    print(f"   • Population 65+ totale: {(df['pop_65_74'].sum() + df['pop_75_84'].sum() + df['pop_85_plus'].sum()):,.0f}")
    print(f"   • Population moyenne/pharmacie: {((df['pop_65_74'] + df['pop_75_84'] + df['pop_85_plus']).mean()):,.0f}")


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔍 CONTRÔLE QUALITÉ - PHARMACIES ENRICHIES INSEE")
    print("=" * 70)
    
    try:
        # Charger données
        df = load_data()
        if df is None:
            return False
        
        # Exécuter toutes les vérifications
        all_issues = {}
        
        all_issues['completeness'] = check_completeness(df)
        all_issues['consistency'] = check_consistency(df)
        all_issues['outliers'] = check_outliers(df)
        all_issues['geographic'] = check_geographic_distribution(df)
        all_issues['scoring_ready'] = check_scoring_readiness(df)
        
        # Générer rapport
        generate_report(all_issues, df)
        
        # Verdict final
        total_issues = sum(len(issues) for issues in all_issues.values())
        
        if total_issues == 0:
            print(f"\n✅ CONTRÔLE QUALITÉ RÉUSSI !")
            print(f"   → Vous pouvez lancer scoring_final_optimise.py")
            return True
        else:
            print(f"\n⚠️  CONTRÔLE QUALITÉ : {total_issues} PROBLÈMES DÉTECTÉS")
            print(f"   → Consultez le rapport: data/reports/data_quality_report.txt")
            print(f"   → Corrigez les problèmes avant de lancer le scoring")
            return False
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
