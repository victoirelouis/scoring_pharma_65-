"""
Script de vérification de l'environnement et des fichiers

Exécutez ce script AVANT de lancer le pipeline ML pour vérifier que :
- Tous les fichiers sources existent
- Les colonnes nécessaires sont présentes
- Les dépendances Python sont installées
- La structure des dossiers est correcte

Usage:
    python verifier_environnement.py

Auteur: Pipeline ML Pharmacies
Date: 2025-01-10
"""

import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("VÉRIFICATION DE L'ENVIRONNEMENT - PIPELINE ML PHARMACIES")
print("=" * 80)
print()

# ============================================================================
# 1. VÉRIFICATION DES DÉPENDANCES PYTHON
# ============================================================================

print("1. Vérification des dépendances Python...")
print("-" * 80)

required_packages = {
    'pandas': '2.0.0',
    'numpy': '1.24.0',
    'geopandas': '0.14.0',
    'shapely': '2.0.0',
    'sklearn': '1.3.0',
    'lightgbm': '4.0.0',
    'shap': '0.42.0',
    'matplotlib': '3.7.0',
    'tqdm': '4.65.0',
    'optuna': '3.2.0',
    'statsmodels': '0.14.0',
}

missing_packages = []
outdated_packages = []

for package, min_version in required_packages.items():
    try:
        if package == 'sklearn':
            import sklearn
            pkg = sklearn
            pkg_name = 'scikit-learn'
        else:
            pkg = __import__(package)
            pkg_name = package
        
        installed_version = getattr(pkg, '__version__', 'unknown')
        print(f"  ✓ {pkg_name:20s} {installed_version:15s} (min: {min_version})")
    
    except ImportError:
        print(f"  ✗ {pkg_name:20s} NON INSTALLÉ")
        missing_packages.append(pkg_name)

if missing_packages:
    print()
    print("⚠️  PACKAGES MANQUANTS :")
    print(f"   Installez avec : pip install {' '.join(missing_packages)}")
    print()
else:
    print()
    print("✓ Toutes les dépendances sont installées !")
    print()

# ============================================================================
# 2. VÉRIFICATION DE LA CONFIGURATION
# ============================================================================

print("2. Vérification de la configuration...")
print("-" * 80)

try:
    from config_ml import (
        INPUT_FILES,
        DATA_INTERMEDIATE_DIR,
        DATA_OUTPUT_DIR,
        HUBS_DEDUPLICATION_CONFIG,
        ISOCHRONES_CONFIG
    )
    print("  ✓ Fichier config_ml.py chargé avec succès")
except ImportError as e:
    print(f"  ✗ Erreur lors du chargement de config_ml.py : {e}")
    sys.exit(1)

print()

# ============================================================================
# 3. VÉRIFICATION DES FICHIERS SOURCES
# ============================================================================

print("3. Vérification des fichiers sources...")
print("-" * 80)

files_ok = True

# Pharmacies
pharma_path = INPUT_FILES['pharmacies']
if pharma_path.exists():
    print(f"  ✓ Pharmacies : {pharma_path}")
    
    # Charger et vérifier les colonnes
    try:
        import pandas as pd
        df_pharma = pd.read_csv(pharma_path, nrows=5, sep=';')
        
        col_id = ISOCHRONES_CONFIG['colonne_id_pharmacie']
        if col_id in df_pharma.columns:
            print(f"    → Colonne '{col_id}' présente ✓")
        else:
            print(f"    → ERREUR : Colonne '{col_id}' manquante !")
            print(f"    → Colonnes disponibles : {list(df_pharma.columns)}")
            files_ok = False
        
        # Compter lignes
        df_pharma_full = pd.read_csv(pharma_path, sep=';')
        print(f"    → {len(df_pharma_full):,} pharmacies trouvées")
    
    except Exception as e:
        print(f"    → Erreur lecture : {e}")
        files_ok = False
else:
    print(f"  ✗ Pharmacies : FICHIER INTROUVABLE")
    print(f"    Chemin attendu : {pharma_path}")
    files_ok = False

print()

# Hubs
hubs_path = INPUT_FILES['hubs']
if hubs_path.exists():
    print(f"  ✓ Hubs : {hubs_path}")
    
    # Charger et vérifier les colonnes
    try:
        import pandas as pd
        df_hubs = pd.read_csv(hubs_path, nrows=5)
        
        col_type = HUBS_DEDUPLICATION_CONFIG['colonne_type']
        col_lat = HUBS_DEDUPLICATION_CONFIG['colonne_latitude']
        col_lon = HUBS_DEDUPLICATION_CONFIG['colonne_longitude']
        
        required_cols = [col_type, col_lat, col_lon]
        missing_cols = [col for col in required_cols if col not in df_hubs.columns]
        
        if not missing_cols:
            print(f"    → Colonnes '{col_type}', '{col_lat}', '{col_lon}' présentes ✓")
        else:
            print(f"    → ERREUR : Colonnes manquantes : {missing_cols}")
            print(f"    → Colonnes disponibles : {list(df_hubs.columns)}")
            files_ok = False
        
        # Compter lignes
        df_hubs_full = pd.read_csv(hubs_path)
        print(f"    → {len(df_hubs_full):,} hubs trouvés")
        
        # Compter par catégorie
        if col_type in df_hubs_full.columns:
            categories_count = df_hubs_full[col_type].value_counts()
            print(f"    → {len(categories_count)} catégories différentes")
            print(f"    → Top 5 catégories :")
            for cat, count in categories_count.head(5).items():
                print(f"      - {cat}: {count:,}")
    
    except Exception as e:
        print(f"    → Erreur lecture : {e}")
        files_ok = False
else:
    print(f"  ✗ Hubs : FICHIER INTROUVABLE")
    print(f"    Chemin attendu : {hubs_path}")
    files_ok = False

print()

# Isochrones
for iso_type in ISOCHRONES_CONFIG['types_isochrones']:
    iso_dir = INPUT_FILES[f'isochrones_{iso_type}']
    
    if iso_dir.exists() and iso_dir.is_dir():
        # Compter fichiers
        iso_files = list(iso_dir.glob('*.geojson'))
        print(f"  ✓ Isochrones {iso_type} : {len(iso_files):,} fichiers")
        print(f"    Répertoire : {iso_dir}")
        
        if len(iso_files) == 0:
            print(f"    ⚠️  ATTENTION : Aucun fichier .geojson trouvé !")
            files_ok = False
    else:
        print(f"  ✗ Isochrones {iso_type} : RÉPERTOIRE INTROUVABLE")
        print(f"    Chemin attendu : {iso_dir}")
        files_ok = False

print()

# ============================================================================
# 4. VÉRIFICATION DES RÉPERTOIRES DE SORTIE
# ============================================================================

print("4. Vérification des répertoires de sortie...")
print("-" * 80)

dirs_to_check = [
    ('Intermédiaire', DATA_INTERMEDIATE_DIR),
    ('Sortie finale', DATA_OUTPUT_DIR),
]

for dir_name, dir_path in dirs_to_check:
    if dir_path.exists():
        print(f"  ✓ {dir_name:20s} : {dir_path}")
    else:
        print(f"  ✗ {dir_name:20s} : N'EXISTE PAS")
        print(f"    Création du répertoire...")
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"    ✓ Créé : {dir_path}")

print()

# ============================================================================
# 5. RÉSUMÉ
# ============================================================================

print("=" * 80)
print("RÉSUMÉ")
print("=" * 80)

if missing_packages:
    print("❌ DÉPENDANCES : Packages manquants")
    print(f"   → Installez avec : pip install {' '.join(missing_packages)}")
else:
    print("✅ DÉPENDANCES : OK")

if files_ok:
    print("✅ FICHIERS SOURCES : OK")
else:
    print("❌ FICHIERS SOURCES : Problèmes détectés (voir ci-dessus)")

print("✅ RÉPERTOIRES : OK")
print()

if missing_packages or not files_ok:
    print("⚠️  ATTENTION : Des problèmes ont été détectés.")
    print("   Corrigez-les avant de lancer le pipeline ML.")
    print()
    sys.exit(1)
else:
    print("🎉 Tout est prêt ! Vous pouvez lancer le pipeline ML.")
    print()
    print("Prochaine étape :")
    print("  python ml_01_prepare_hubs_par_isochrone.py")
    print()
    sys.exit(0)
