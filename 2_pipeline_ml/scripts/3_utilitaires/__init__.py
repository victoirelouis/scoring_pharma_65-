"""
Package utilitaire pour le pipeline ML Phase 2

Ce package contient :
- config_ml.py : Configuration centralisée du pipeline ML

Scripts déplacés vers 1_data_prep/ :
- associate_pharmacies_to_iris.py → 1_data_prep/scripts/3_isochrones/d_*
- associate_uncovered_iris.py → 1_data_prep/scripts/3_isochrones/e_*
- data_quality_check.py → 1_data_prep/scripts/5_validation/b_*
- nettoyer_matrice_iris.py → obsolète (fonctionnalité intégrée dans c_calculate_w_iris.py)
"""

__version__ = "2.0.0"