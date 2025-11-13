#!/bin/bash

################################################################################
# Script d'automatisation - Pipeline Scoring Pharmacies 65+
################################################################################
#
# Ce script exécute et valide automatiquement tous les scripts du pipeline.
# Il s'arrête immédiatement si un script échoue ou si la validation détecte
# des erreurs critiques.
#
# Utilisation :
#   chmod +x run_pipeline_auto.sh
#   ./run_pipeline_auto.sh
#
# Options :
#   ./run_pipeline_auto.sh --steps 1-3    # Exécute uniquement les scripts 1 à 3
#   ./run_pipeline_auto.sh --step 1       # Exécute uniquement le script 1
#
################################################################################

set -e  # Arrête le script en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}🔄 $1${NC}"
}

# Configuration
VALIDATION_SCRIPT="validation_data_quality_complete.py"

# Liste des scripts dans l'ordre
declare -A SCRIPTS
SCRIPTS[1]="ml_01_prepare_hubs_par_isochrone.py"
SCRIPTS[2]="ml_02_prepare_concurrence.py"
SCRIPTS[3]="ml_03_prepare_population_isochrones.py"
SCRIPTS[4]="ml_04_integration_complete.py"
SCRIPTS[5]="ml_05_feature_engineering.py"
SCRIPTS[6]="ml_06_selection_features.py"
SCRIPTS[7]="ml_07_split_train_test.py"
SCRIPTS[8]="ml_08_baseline_models.py"
SCRIPTS[9]="ml_09_lightgbm_optimized.py"
SCRIPTS[10]="ml_10_evaluation_finale.py"
SCRIPTS[11]="ml_11_interpretabilite_shap.py"
SCRIPTS[12]="ml_12_predictions_finales.py"
SCRIPTS[13]="ml_13_analyse_segmentee.py"
SCRIPTS[14]="ml_14_rapport_final.py"

# Parse les arguments
START_STEP=1
END_STEP=14

if [ "$1" = "--step" ] && [ -n "$2" ]; then
    START_STEP=$2
    END_STEP=$2
elif [ "$1" = "--steps" ] && [ -n "$2" ]; then
    IFS='-' read -r START_STEP END_STEP <<< "$2"
fi

# Affichage du début
print_header "PIPELINE SCORING PHARMACIES 65+ - EXÉCUTION AUTOMATIQUE"
echo ""
echo "Scripts à exécuter : $START_STEP à $END_STEP"
echo "Date : $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Compteurs
TOTAL_SCRIPTS=$((END_STEP - START_STEP + 1))
COMPLETED=0

# Boucle sur chaque script
for STEP in $(seq $START_STEP $END_STEP); do
    SCRIPT="${SCRIPTS[$STEP]}"
    
    if [ -z "$SCRIPT" ]; then
        print_error "Script $STEP non défini"
        exit 1
    fi
    
    echo ""
    print_header "ÉTAPE $STEP/$END_STEP : $SCRIPT"
    
    # Vérifie que le fichier existe
    if [ ! -f "$SCRIPT" ]; then
        print_error "Fichier non trouvé : $SCRIPT"
        exit 1
    fi
    
    # Exécute le script
    print_info "Exécution du script..."
    if python "$SCRIPT"; then
        print_success "Script exécuté avec succès"
    else
        print_error "Erreur lors de l'exécution du script $SCRIPT"
        exit 1
    fi
    
    echo ""
    
    # Valide le script
    print_info "Validation des données (Script $STEP)..."
    if python "$VALIDATION_SCRIPT" --step $STEP; then
        print_success "Validation réussie pour Script $STEP"
        COMPLETED=$((COMPLETED + 1))
    else
        print_error "Validation échouée pour Script $STEP"
        echo ""
        echo "Consulte le rapport de validation pour plus de détails."
        exit 1
    fi
    
    echo ""
    print_success "Étape $STEP/$END_STEP terminée"
    
    # Affiche la progression
    PROGRESS=$((COMPLETED * 100 / TOTAL_SCRIPTS))
    echo "Progression globale : $COMPLETED/$TOTAL_SCRIPTS scripts complétés (${PROGRESS}%)"
done

# Résumé final
echo ""
print_header "PIPELINE TERMINÉ AVEC SUCCÈS ! 🎉"
echo ""
echo "📊 Résumé de l'exécution :"
echo "  - Scripts exécutés : $COMPLETED/$TOTAL_SCRIPTS"
echo "  - Scripts validés : $COMPLETED/$TOTAL_SCRIPTS"
echo "  - Date de fin : $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
print_success "Tous les scripts ont été exécutés et validés avec succès !"
echo ""
echo "💡 Prochaines étapes :"
if [ $END_STEP -lt 8 ]; then
    echo "  - Exécuter les scripts ML (8-14)"
    echo "  - Commande : ./run_pipeline_auto.sh --steps 8-14"
elif [ $END_STEP -lt 14 ]; then
    echo "  - Terminer les scripts ML restants"
    echo "  - Commande : ./run_pipeline_auto.sh --steps $((END_STEP+1))-14"
else
    echo "  - Consulter le rapport final : ml_14_rapport_final.py"
    echo "  - Analyser les prédictions : predictions_finales.csv"
    echo "  - Examiner l'interprétabilité : SHAP values"
fi
echo ""
