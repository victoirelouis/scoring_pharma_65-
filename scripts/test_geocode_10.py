#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rapide de géocodage sur 10 adresses
"""

import pandas as pd
import requests
import time
from pathlib import Path

# Chemins
BASE_DIR = Path(r"N:\Commun_GERS\Victoire LOUIS\PyScore\PROFILS DE PATIENTELE\Git\scoring_pharma_65-")
INPUT_DIR = BASE_DIR / "data" / "input"

# API BAN
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/"

def geocode_ban(address, postcode):
    """Géocode une adresse avec l'API BAN"""
    try:
        params = {'q': address, 'limit': 1}
        if postcode:
            params['postcode'] = postcode
        
        print(f"  Requête: {address[:50]}... | CP: {postcode}")
        
        response = requests.get(BAN_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                coords = feature['geometry']['coordinates']
                score = feature['properties'].get('score', 0)
                print(f"  ✓ SUCCÈS - Lat: {coords[1]:.6f}, Lon: {coords[0]:.6f}, Score: {score:.2f}")
                return coords[1], coords[0], score
        
        print(f"  ✗ ÉCHEC - Pas de résultat")
        return None, None, 0
        
    except Exception as e:
        print(f"  ✗ ERREUR - {type(e).__name__}: {str(e)[:50]}")
        return None, None, 0

def main():
    print("="*80)
    print("TEST GÉOCODAGE - 10 ADRESSES")
    print("="*80)
    
    # Charger RPPS
    rpps_file = INPUT_DIR / "RPPS.csv"
    print(f"\n📖 Lecture de {rpps_file.name}...")
    df = pd.read_csv(rpps_file, nrows=10000)
    
    # Filtrer spécialités
    SPECIALITES = {'Médecine Générale', 'Cardiologie', 'Dermatologie'}
    df_filtered = df[df['NomSpecialiteGers'].isin(SPECIALITES)].head(10)
    
    print(f"✓ {len(df_filtered)} adresses à tester\n")
    
    # Tester géocodage
    results = []
    success_count = 0
    
    for idx, row in df_filtered.iterrows():
        print(f"\n{idx+1}/10:")
        address = f"{row['Rue']} {row['CodePostal']} {row['Ville']}"
        lat, lon, score = geocode_ban(address, str(row['CodePostal'])[:5])
        
        if lat is not None:
            success_count += 1
        
        results.append({
            'adresse': address[:60],
            'latitude': lat,
            'longitude': lon,
            'score': score
        })
        
        # Délai entre requêtes
        time.sleep(0.5)
    
    # Résumé
    print("\n" + "="*80)
    print(f"RÉSULTATS: {success_count}/10 géocodées avec succès ({success_count*10}%)")
    print("="*80)
    
    # Afficher résultats
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

if __name__ == "__main__":
    main()
