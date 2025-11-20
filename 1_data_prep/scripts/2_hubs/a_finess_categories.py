#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration des catégories FINESS
Catégorisation simplifiée des établissements médicaux et médico-sociaux

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

# Mapping : libellé FINESS → catégorie simplifiée + type
FINESS_CATEGORIES = {
    # EHPAD et structures pour seniors
    "Etablissement d'Hébergement pour Personnes Agées Dépendantes": {
        'categorie': 'EHPAD',
        'type': 'ehpad'
    },
    "Unité de Soins de Longue Durée": {
        'categorie': 'EHPAD',
        'type': 'ehpad'
    },
    "Maison de retraite": {
        'categorie': 'EHPAD',
        'type': 'ehpad'
    },

    # Dialyse
    "Centre de dialyse": {
        'categorie': 'Dialyse',
        'type': 'dialyse'
    },
    "Unité de dialyse médicalisée": {
        'categorie': 'Dialyse',
        'type': 'dialyse'
    },
    "Centre d'autodialyse": {
        'categorie': 'Dialyse',
        'type': 'dialyse'
    },

    # Hôpitaux
    "Centre Hospitalier (C.H.)": {
        'categorie': 'Hôpital',
        'type': 'hopital'
    },
    "Centre Hospitalier Régional (C.H.R.)": {
        'categorie': 'CHR',
        'type': 'hopital'
    },
    "Hôpital local": {
        'categorie': 'Hôpital local',
        'type': 'hopital'
    },
    "Centre Hospitalier Universitaire": {
        'categorie': 'CHU',
        'type': 'hopital'
    },

    # Cliniques
    "Clinique": {
        'categorie': 'Clinique',
        'type': 'clinique'
    },
    "Clinique chirurgicale": {
        'categorie': 'Clinique chirurgicale',
        'type': 'clinique'
    },
    "Clinique médicale": {
        'categorie': 'Clinique médicale',
        'type': 'clinique'
    },

    # Laboratoires
    "Laboratoire d'analyses de biologie médicale": {
        'categorie': 'Laboratoire',
        'type': 'laboratoire'
    },

    # SSR (Soins de Suite et Réadaptation)
    "Centre de Soins de Suite et de Réadaptation": {
        'categorie': 'SSR',
        'type': 'ssr'
    },

    # Centres de santé
    "Centre de santé": {
        'categorie': 'Centre de santé',
        'type': 'centre_sante'
    },
    "Maison de santé": {
        'categorie': 'Maison de santé',
        'type': 'centre_sante'
    },

    # Pharmacies
    "Pharmacie d'officine": {
        'categorie': 'Pharmacie',
        'type': 'pharmacie'
    },

    # Autres établissements médicaux
    "Cabinet médical": {
        'categorie': 'Cabinet médical',
        'type': 'cabinet'
    },
    "Cabinet dentaire": {
        'categorie': 'Cabinet dentaire',
        'type': 'cabinet'
    },
    "Cabinet infirmier": {
        'categorie': 'Cabinet infirmier',
        'type': 'cabinet'
    },
}


def get_category(libelle):
    """
    Récupère la catégorie simplifiée pour un libellé FINESS

    Args:
        libelle: Libellé FINESS complet

    Returns:
        str: Catégorie simplifiée ou 'Non configuré'
    """
    config = FINESS_CATEGORIES.get(libelle)
    return config['categorie'] if config else 'Non configuré'


def get_type(libelle):
    """
    Récupère le type pour un libellé FINESS

    Args:
        libelle: Libellé FINESS complet

    Returns:
        str: Type ou 'non_configure'
    """
    config = FINESS_CATEGORIES.get(libelle)
    return config['type'] if config else 'non_configure'