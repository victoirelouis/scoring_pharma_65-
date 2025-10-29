"""
Script de validation basique de la structure du projet
N'importe pas les modules qui nécessitent des dépendances externes
"""

import sys
from pathlib import Path

def validate_structure():
    """Valide la structure du projet"""
    print("Validation de la structure du projet Scoring Pharma 65+")
    print("=" * 60)
    
    required_files = [
        'README.md',
        'requirements.txt',
        '.gitignore',
        'config.yaml',
        'main.py',
        'src/scoring_pharma/__init__.py',
        'src/scoring_pharma/data_loader.py',
        'src/scoring_pharma/scoring_engine.py',
        'src/scoring_pharma/visualizer.py',
        'src/scoring_pharma/utils.py',
        'docs/METHODOLOGIE.md',
        'docs/USAGE.md',
        'data/README.md',
        'data/example_pharmacies.csv',
        'data/example_demographics.csv',
        'data/example_economic.csv',
        'tests/__init__.py',
        'tests/test_data_loader.py',
        'tests/test_scoring_engine.py',
        'tests/test_utils.py',
    ]
    
    required_dirs = [
        'src/scoring_pharma',
        'data',
        'docs',
        'tests',
        'notebooks',
        'output',
    ]
    
    base_path = Path(__file__).parent
    
    # Vérification des répertoires
    print("\n✓ Vérification des répertoires...")
    all_dirs_exist = True
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MANQUANT")
            all_dirs_exist = False
    
    # Vérification des fichiers
    print("\n✓ Vérification des fichiers...")
    all_files_exist = True
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MANQUANT")
            all_files_exist = False
    
    # Vérification de la syntaxe Python (sans imports des dépendances)
    print("\n✓ Vérification de la syntaxe Python...")
    python_files = [
        'main.py',
        'src/scoring_pharma/__init__.py',
        'src/scoring_pharma/data_loader.py',
        'src/scoring_pharma/scoring_engine.py',
        'src/scoring_pharma/visualizer.py',
        'src/scoring_pharma/utils.py',
    ]
    
    syntax_ok = True
    for file_path in python_files:
        full_path = base_path / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
            print(f"  ✓ {file_path}")
        except SyntaxError as e:
            print(f"  ✗ {file_path} - ERREUR DE SYNTAXE: {e}")
            syntax_ok = False
    
    # Résumé
    print("\n" + "=" * 60)
    if all_dirs_exist and all_files_exist and syntax_ok:
        print("✓ Validation réussie ! Le projet est correctement structuré.")
        return 0
    else:
        print("✗ La validation a échoué. Veuillez corriger les erreurs.")
        return 1

if __name__ == '__main__':
    sys.exit(validate_structure())
