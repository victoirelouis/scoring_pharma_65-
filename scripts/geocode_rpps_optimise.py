#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script RPPS OPTIMISÉ : Géocodage parallèle + Attribution des poids

OPTIMISATIONS :
- Multiprocessing avec 50 workers par défaut
- Traitement par batch de 1000 adresses
- Cache intelligent
- Progression en temps réel

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
import warnings
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import traceback

# Supprimer les warnings
warnings.filterwarnings('ignore')

# Configuration des chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"
# Ajouter le dossier Téléchargements comme alternative
DOWNLOADS_DIR = Path.home() / "Downloads"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
CACHE_DIR = BASE_DIR / "data" / "cache"

# API BAN
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/"

# Nombre de workers parallèles (réduit pour éviter surcharge API)
MAX_WORKERS = 10  # 10 workers pour ne pas bloquer l'API BAN

# Configuration RPPS - Spécialités pour seniors (BONUS > 0 uniquement)
RPPS_SPECIALITES = {
    # ESSENTIELLES (0.18)
    'Médecine Générale': {'categorie': 'Médecin généraliste', 'bonus': 0.18},
    'Gériatrie Gérontologie': {'categorie': 'Gériatre', 'bonus': 0.18},
    
    # TRÈS FRÉQUENTES (0.14-0.16)
    'Cardiologie': {'categorie': 'Cardiologue', 'bonus': 0.16},
    'Rhumatologie': {'categorie': 'Rhumatologue', 'bonus': 0.16},
    'Ophtalmologie': {'categorie': 'Ophtalmologue', 'bonus': 0.15},
    'Néphrologie': {'categorie': 'Néphrologue', 'bonus': 0.15},
    'Endocrinologie Diabétologie': {'categorie': 'Endocrinologue', 'bonus': 0.15},
    'Neurologie': {'categorie': 'Neurologue', 'bonus': 0.14},
    'Gastro Entérologie': {'categorie': 'Gastro-entérologue', 'bonus': 0.14},
    
    # FRÉQUENTES (0.11-0.13)
    'Dermatologie': {'categorie': 'Dermatologue', 'bonus': 0.13},
    'Pneumologie': {'categorie': 'Pneumologue', 'bonus': 0.13},
    'Urologie': {'categorie': 'Urologue', 'bonus': 0.13},
    'Oncologie Cancérologie': {'categorie': 'Oncologue', 'bonus': 0.13},
    'Phlébologie Angeiologie': {'categorie': 'Angiologue', 'bonus': 0.12},
    'Hématologie': {'categorie': 'Hématologue', 'bonus': 0.12},
    'Médecine Interne': {'categorie': 'Interniste', 'bonus': 0.12},
    'Rééducation Fonctionnelle': {'categorie': 'Médecin rééducateur', 'bonus': 0.11},
    'Allergologie': {'categorie': 'Allergologue', 'bonus': 0.11},
    
    # MODÉRÉES (0.08-0.10)
    'Psychiatrie': {'categorie': 'Psychiatre', 'bonus': 0.10},
    'Oto Rhino Laryngologie': {'categorie': 'ORL', 'bonus': 0.10},
    'Chirurgie Orthopédique': {'categorie': 'Chirurgien orthopédiste', 'bonus': 0.10},
    'Radiothérapie': {'categorie': 'Radiothérapeute', 'bonus': 0.10},
    'Anesthésiologie Réanimation': {'categorie': 'Anesthésiste', 'bonus': 0.08},
    'Chirurgie Générale': {'categorie': 'Chirurgien', 'bonus': 0.08},
    'Stomatologie': {'categorie': 'Stomatologue', 'bonus': 0.08},
    
    # PEU PERTINENTES (0.03-0.05)
    'Gynécologie': {'categorie': 'Gynécologue', 'bonus': 0.05},
    'Médecine Esthétique': {'categorie': 'Médecin esthétique', 'bonus': 0.03},
    'Chirurgie Dentaire': {'categorie': 'Dentiste', 'bonus': 0.05},
    
    # EXCLUS (bonus = 0) - commentés pour ne pas les traiter
    # 'Pédiatrie': {'categorie': 'Pédiatre', 'bonus': 0.00},
    # 'Sage Femme': {'categorie': 'Sage-femme', 'bonus': 0.00},
}


def find_file(patterns):
    """Recherche un fichier selon des patterns"""
    # Chercher d'abord dans Téléchargements
    for pattern in patterns:
        files = list(DOWNLOADS_DIR.glob(pattern))
        if files:
            return files[0]
    
    # Puis dans INPUT_DIR
    for pattern in patterns:
        files = list(INPUT_DIR.glob(pattern))
        if files:
            return files[0]
    return None


def nettoyer_adresse(rue, code_postal, ville):
    """
    Nettoie et formate une adresse pour améliorer le géocodage
    
    Args:
        rue (str): Nom de rue
        code_postal (str): Code postal
        ville (str): Nom de ville
        
    Returns:
        tuple: (rue_clean, cp_clean, ville_clean)
    """
    import re
    
    if pd.isna(rue) or pd.isna(code_postal) or pd.isna(ville):
        return None, None, None
    
    rue = str(rue).strip()
    code_postal = str(code_postal).strip()
    ville = str(ville).strip()
    
    # Retirer CEDEX des codes postaux et villes
    code_postal = re.sub(r'\s*CEDEX.*$', '', code_postal, flags=re.IGNORECASE)
    ville = re.sub(r'\s*CEDEX.*$', '', ville, flags=re.IGNORECASE)
    
    # Garder seulement les 5 premiers chiffres du code postal
    cp_match = re.search(r'\d{5}', code_postal)
    if cp_match:
        code_postal = cp_match.group()
    else:
        return None, None, None  # Code postal invalide
    
    # Nettoyer la ville (enlever numéros d'arrondissement)
    ville = re.sub(r'\s+\d{1,2}[EeRr]*$', '', ville).strip()
    
    # Nettoyer la rue
    rue = rue.strip()
    
    return rue, code_postal, ville


def geocode_with_ban(address, postcode=None):
    """
    Géocode une adresse avec l'API BAN (optimisé)
    
    Args:
        address (str): Adresse complète
        postcode (str): Code postal
        
    Returns:
        tuple: (latitude, longitude, score)
    """
    try:
        params = {'q': address, 'limit': 1}
        if postcode:
            params['postcode'] = postcode
        
        # Timeout augmenté pour laisser le temps à l'API
        response = requests.get(BAN_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                coords = feature['geometry']['coordinates']
                score = feature['properties'].get('score', 0)
                return coords[1], coords[0], score  # lat, lon, score
        
        return None, None, 0
    except:
        return None, None, 0


def geocode_row(row_data):
    """
    Géocode une ligne (fonction pour worker)
    
    Args:
        row_data (dict): Données de la ligne
        
    Returns:
        dict: Ligne avec coordonnées
    """
    try:
        # Construire adresse
        full_address = f"{row_data['adresse']} {row_data['code_postal']} {row_data['commune']}".strip()
        
        # Géocoder
        if len(full_address) < 5:
            lat, lon, score = None, None, 0
        else:
            lat, lon, score = geocode_with_ban(full_address, row_data['code_postal'])
        
        # Ajouter coordonnées
        row_data['latitude'] = lat
        row_data['longitude'] = lon
        row_data['geo_score'] = score
        
        return row_data
    except Exception as e:
        # En cas d'erreur, retourner sans coordonnées
        row_data['latitude'] = None
        row_data['longitude'] = None
        row_data['geo_score'] = 0
        return row_data


def geocode_batch_parallel(rows_data, max_workers=MAX_WORKERS):
    """
    Géocode un batch de lignes en parallèle
    
    Args:
        rows_data (list): Liste de dictionnaires à géocoder
        max_workers (int): Nombre de workers
        
    Returns:
        list: Lignes géocodées
    """
    import time
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre tous les jobs
        futures = {executor.submit(geocode_row, row): row for row in rows_data}
        
        # Récupérer les résultats au fur et à mesure
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                # Petit délai pour ne pas surcharger l'API
                time.sleep(0.01)
            except Exception as e:
                # En cas d'erreur, ajouter la ligne sans coordonnées
                original_row = futures[future]
                original_row['latitude'] = None
                original_row['longitude'] = None
                original_row['geo_score'] = 0
                results.append(original_row)
    
    return results


def load_and_geocode_rpps_parallel(max_to_geocode=None):
    """
    Charge RPPS et géocode en parallèle (OPTIMISÉ)
    
    Args:
        max_to_geocode (int): Limite (None = tous)
        
    Returns:
        pd.DataFrame: DataFrame géocodé
    """
    print(f"\n👨‍⚕️ TRAITEMENT RPPS OPTIMISÉ...")
    
    # Chercher fichier
    patterns = ["*RPPS*.csv", "*rpps*.csv", "*rpps*.txt", "*PS_LibreAcces*.txt", "*medecin*.txt"]
    rpps_file = find_file(patterns)
    
    if not rpps_file:
        print("   ⚠️  Fichier RPPS non trouvé")
        return pd.DataFrame()
    
    print(f"   📁 Fichier: {rpps_file.name}")
    
    # Cache
    cache_file = CACHE_DIR / "rpps_geocoded_avec_poids.csv"
    if cache_file.exists():
        print(f"   💾 Chargement depuis cache...")
        df_cached = pd.read_csv(cache_file, encoding='utf-8')
        geocoded = df_cached['latitude'].notna().sum()
        print(f"   ✅ {len(df_cached):,} médecins ({geocoded:,} géocodés - {geocoded/len(df_cached)*100:.1f}%)")
        return df_cached
    
    try:
        # Lire RPPS
        print(f"   📖 Lecture du fichier...")
        df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            for sep in ['|', ';', '\t', ',']:
                try:
                    df = pd.read_csv(rpps_file, sep=sep, encoding=encoding, low_memory=False)
                    if len(df.columns) > 5:
                        print(f"      ✓ Encodage: {encoding}, Séparateur: '{sep}'")
                        break
                except:
                    continue
            if df is not None:
                break
        
        if df is None:
            print("   ❌ Impossible de lire le fichier")
            return pd.DataFrame()
        
        print(f"   ✓ {len(df):,} lignes chargées")
        
        # Colonne spécialité
        specialite_col = 'NomSpecialiteGers'
        if specialite_col not in df.columns:
            print(f"   ❌ Colonne '{specialite_col}' non trouvée")
            return pd.DataFrame()
        
        print(f"   ✓ Colonne spécialité: {specialite_col}")
        
        # Filtrer spécialités avec bonus > 0
        print(f"\n   🔍 Filtrage des spécialités (bonus > 0)...")
        specialites_valides = {k: v for k, v in RPPS_SPECIALITES.items() if v['bonus'] > 0}
        
        df_filtered = df[df[specialite_col].isin(specialites_valides.keys())].copy()
        print(f"   ✓ {len(specialites_valides)} spécialités avec bonus > 0")
        print(f"   ✓ {len(df_filtered):,} médecins à géocoder")
        print(f"   ❌ Exclus : Pédiatrie, Sage Femme (bonus = 0)")
        
        if len(df_filtered) == 0:
            print("   ⚠️  Aucun médecin trouvé")
            return pd.DataFrame()
        
        # Limiter si test
        if max_to_geocode and len(df_filtered) > max_to_geocode:
            print(f"   ⚠️  Limitation à {max_to_geocode:,} pour test")
            df_filtered = df_filtered.head(max_to_geocode)
        
        # Identifier colonnes
        print(f"\n   🔍 Identification des colonnes...")
        
        adresse_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['voie', 'adresse', 'rue']):
                adresse_col = col
                break
        
        cp_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['postal', 'cp']):
                cp_col = col
                break
        
        commune_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['commune', 'ville']):
                commune_col = col
                break
        
        id_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['identification', 'id', 'rpps']):
                id_col = col
                break
        
        print(f"      ✓ Adresse: {adresse_col}")
        print(f"      ✓ Code postal: {cp_col}")
        print(f"      ✓ Commune: {commune_col}")
        print(f"      ✓ ID: {id_col}")
        
        # Préparer données pour géocodage parallèle
        print(f"\n   📦 Préparation des données avec nettoyage...")
        rows_to_geocode = []
        
        for idx, row in df_filtered.iterrows():
            specialite = row[specialite_col]
            config = specialites_valides.get(specialite, {})
            
            # Nettoyer l'adresse
            rue_orig = row[adresse_col] if adresse_col and pd.notna(row.get(adresse_col)) else ''
            cp_orig = row[cp_col] if cp_col and pd.notna(row.get(cp_col)) else ''
            ville_orig = row[commune_col] if commune_col and pd.notna(row.get(commune_col)) else ''
            
            rue_clean, cp_clean, ville_clean = nettoyer_adresse(rue_orig, cp_orig, ville_orig)
            
            # Ignorer les adresses invalides après nettoyage
            if not rue_clean or not cp_clean or not ville_clean:
                continue
            
            row_data = {
                'id_hub': f"RPPS_{row[id_col] if id_col and pd.notna(row.get(id_col)) else idx}",
                'nom': f"Cabinet {config.get('categorie', 'Médecin')}",
                'adresse': rue_clean,
                'code_postal': cp_clean,
                'commune': ville_clean,
                'type_hub': 'cabinet_medical',
                'categorie': config.get('categorie', 'Médecin'),
                'bonus_attractivite': config.get('bonus', 0.10),
                'source': 'RPPS',
            }
            rows_to_geocode.append(row_data)
        
        total = len(rows_to_geocode)
        print(f"   ✓ {total:,} adresses valides prêtes (après nettoyage)")
        
        # Géocodage parallèle par batch
        print(f"\n   🚀 GÉOCODAGE PARALLÈLE ({MAX_WORKERS} workers)...")
        print(f"   ⚡ Ceci devrait être TRÈS RAPIDE !")
        
        batch_size = 10000  # Traiter par batch de 10000
        all_results = []
        
        start_time = time.time()
        
        for i in range(0, total, batch_size):
            batch = rows_to_geocode[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"      Batch {batch_num}/{total_batches} ({len(batch)} adresses)...", end=' ')
            
            batch_start = time.time()
            results = geocode_batch_parallel(batch, max_workers=MAX_WORKERS)
            batch_time = time.time() - batch_start
            
            all_results.extend(results)
            
            # Stats du batch
            geocoded_batch = sum(1 for r in results if r.get('latitude') is not None)
            success_rate = (geocoded_batch / len(batch)) * 100
            speed = len(batch) / batch_time
            
            print(f"✓ {batch_time:.1f}s ({speed:.0f} addr/s, succès: {success_rate:.0f}%)")
            
            # Sauvegarde intermédiaire tous les batches (tous les 10000 adresses)
            temp_cache = CACHE_DIR / "rpps_geocoding_temp.csv"
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df_temp = pd.DataFrame(all_results)
            df_temp.to_csv(temp_cache, index=False, encoding='utf-8')
            if batch_num % 5 == 0:  # Afficher message tous les 5 batches
                print(f"      💾 Sauvegarde: {len(all_results):,} adresses")
        
        total_time = time.time() - start_time
        
        # Créer DataFrame final
        df_result = pd.DataFrame(all_results)
        
        # Sauvegarder cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df_result.to_csv(cache_file, index=False, encoding='utf-8')
        
        # Stats finales
        total_geocoded = df_result['latitude'].notna().sum()
        success_rate_total = (total_geocoded / len(df_result)) * 100
        avg_speed = len(df_result) / total_time
        
        print(f"\n   ✅ GÉOCODAGE TERMINÉ !")
        print(f"      • Total: {len(df_result):,} médecins")
        print(f"      • Géocodés: {total_geocoded:,} ({success_rate_total:.1f}%)")
        print(f"      • Temps: {total_time:.1f}s")
        print(f"      • Vitesse moyenne: {avg_speed:.0f} adresses/seconde 🚀")
        
        # Top spécialités
        print(f"\n   📊 Top 10 spécialités :")
        for idx, (spec, count) in enumerate(df_result['categorie'].value_counts().head(10).items(), 1):
            bonus = df_result[df_result['categorie']==spec]['bonus_attractivite'].iloc[0]
            geocoded_spec = df_result[df_result['categorie']==spec]['latitude'].notna().sum()
            print(f"      {idx:>2}. {spec:<25} : {count:>6,}  (bonus: {bonus:.2f}, géo: {geocoded_spec:>5,})")
        
        return df_result
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def save_results(df):
    """Sauvegarde les résultats"""
    print(f"\n💾 SAUVEGARDE...")
    
    if df.empty:
        print("   ❌ Aucune donnée")
        return
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / "rpps_geocoded_avec_poids.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    size_mb = output_file.stat().st_size / (1024 * 1024)
    
    print(f"   ✅ {output_file.name} ({size_mb:.1f} MB)")
    print(f"   ✓ {len(df):,} médecins")
    print(f"   ✓ {df['latitude'].notna().sum():,} géocodés")


def display_summary(df):
    """Affiche le résumé"""
    print(f"\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 70)
    
    if df.empty:
        print("Aucune donnée")
        return
    
    total = len(df)
    geocoded = df['latitude'].notna().sum()
    
    print(f"\n✅ SUCCÈS !")
    print(f"   Total: {total:,} médecins")
    print(f"   Géocodés: {geocoded:,} ({geocoded/total*100:.1f}%)")
    
    # Distribution bonus
    print(f"\n💰 BONUS (Top 5) :")
    bonus_dist = df['bonus_attractivite'].value_counts().sort_index(ascending=False).head(5)
    for bonus, count in bonus_dist.items():
        pct = (count / total) * 100
        print(f"   • {bonus:.2f} : {count:>6,} ({pct:>5.1f}%)")
    
    # Score moyen
    scores = df[df['geo_score'] > 0]['geo_score']
    if len(scores) > 0:
        print(f"\n🎯 Score confiance moyen: {scores.mean():.3f}")
    
    print(f"\n📁 Fichier créé:")
    print(f"   • data/processed/rpps_geocoded_avec_poids.csv")
    
    print(f"\n💡 Prochaine étape:")
    print(f"   Fusionner avec votre finess_complet.csv !")
    
    print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🚀 GÉOCODAGE RPPS ULTRA-OPTIMISÉ")
    print("=" * 70)
    print(f"⚡ Configuration:")
    print(f"   • Workers parallèles: {MAX_WORKERS}")
    print(f"   • Batch size: 1000 adresses")
    print(f"   • Spécialités: 28 (bonus > 0)")
    print(f"   • Exclusions: Pédiatrie, Sage-femme")
    print(f"\n💾 Cache: relancer = instantané")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Créer répertoires
        for directory in [OUTPUT_DIR, CACHE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Option test
        # max_to_geocode = 5000  # Décommenter pour tester sur 5000
        max_to_geocode = None  # None = tous
        
        # Géocoder RPPS
        df_rpps = load_and_geocode_rpps_parallel(max_to_geocode=max_to_geocode)
        
        if df_rpps.empty:
            print("\n❌ Aucune donnée")
            return False
        
        # Sauvegarder
        save_results(df_rpps)
        
        # Résumé
        display_summary(df_rpps)
        
        # Temps total
        elapsed = time.time() - start_time
        print(f"\n⏱️  Temps TOTAL: {elapsed/60:.1f} minutes")
        
        if elapsed < 300:  # Moins de 5 minutes
            print(f"🚀 ULTRA-RAPIDE ! {len(df_rpps)/elapsed:.0f} adresses/seconde")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
