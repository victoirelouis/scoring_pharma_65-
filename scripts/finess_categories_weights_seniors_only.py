#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration des catégories FINESS pertinentes pour les SENIORS 65+

UNIQUEMENT les catégories utiles pour le modèle pharmacie seniors.
Les catégories non pertinentes (enfance, formation, etc.) sont EXCLUES.

Poids d'attractivité pour les pharmacies 65+ :
- 0.25-0.30 : Très forte attractivité (EHPAD, structures seniors)
- 0.20-0.24 : Forte attractivité (hôpitaux, soins spécialisés seniors)
- 0.15-0.19 : Attractivité moyenne (centres santé, laboratoires)
- 0.10-0.14 : Attractivité modérée (services complémentaires)

Auteur: Système de scoring pharmacie 65+
Date: Novembre 2025
"""

# Mapping : libellé FINESS -> configuration
# UNIQUEMENT les catégories PERTINENTES pour les seniors 65+
FINESS_CATEGORIES_WEIGHTS = {
    # ============================================================
    # STRUCTURES SENIORS - PRIORITÉ MAXIMALE (0.25-0.30)
    # ============================================================
    "Etablissement d'hébergement pour personnes âgées dépendantes": {
        'type': 'ehpad',
        'categorie': 'EHPAD',
        'bonus': 0.30,
        'description': 'Hébergement médicalisé seniors'
    },
    'Résidences autonomie': {
        'type': 'ehpad',
        'categorie': 'Résidence autonomie',
        'bonus': 0.28,
        'description': 'Logement adapté seniors autonomes'
    },
    "EHPA percevant des crédits d'assurance maladie": {
        'type': 'ehpad',
        'categorie': 'EHPA médicalisé',
        'bonus': 0.28,
        'description': 'Hébergement seniors avec soins'
    },
    "EHPA ne percevant pas des crédits d'assurance maladie": {
        'type': 'ehpad',
        'categorie': 'EHPA non médicalisé',
        'bonus': 0.25,
        'description': 'Hébergement seniors'
    },
    'Centre de Jour pour Personnes Agées': {
        'type': 'service_senior',
        'categorie': 'Centre de jour seniors',
        'bonus': 0.25,
        'description': 'Accueil de jour seniors'
    },
    "Service d'Aide aux Personnes Agées": {
        'type': 'service_senior',
        'categorie': 'Service aide seniors',
        'bonus': 0.20,
        'description': 'Aide et accompagnement seniors'
    },
    'Centres Locaux Information Coordination P.A .(C.L.I.C.)': {
        'type': 'service_senior',
        'categorie': 'CLIC',
        'bonus': 0.15,
        'description': 'Information coordination seniors'
    },
    
    # ============================================================
    # HÔPITAUX ET CLINIQUES (0.12-0.18)
    # Poids réduits car concurrence pharmacie interne
    # Mais indicateur d'infrastructure santé pour consultations externes
    # ============================================================
    'Centre Hospitalier (C.H.)': {
        'type': 'hopital',
        'categorie': 'Centre Hospitalier',
        'bonus': 0.15,
        'description': 'Hôpital général'
    },
    'Centre Hospitalier Régional (C.H.R.)': {
        'type': 'hopital',
        'categorie': 'CHR',
        'bonus': 0.15,
        'description': 'Centre hospitalier régional'
    },
    'Centre hospitalier, ex Hôpital local': {
        'type': 'hopital',
        'categorie': 'Hôpital local',
        'bonus': 0.18,
        'description': 'Hôpital de proximité - plus de consultations externes'
    },
    'Etablissement de Soins Chirurgicaux': {
        'type': 'hopital',
        'categorie': 'Clinique chirurgicale',
        'bonus': 0.12,
        'description': 'Chirurgie - patients hospitalisés'
    },
    'Etablissement de Soins Médicaux': {
        'type': 'hopital',
        'categorie': 'Clinique médicale',
        'bonus': 0.12,
        'description': 'Médecine générale'
    },
    'Etablissement de santé privé autorisé en SSR': {
        'type': 'hopital',
        'categorie': 'Clinique SSR',
        'bonus': 0.14,
        'description': 'Soins de suite - flux sortants'
    },
    'Etablissement de Soins Pluridisciplinaire': {
        'type': 'hopital',
        'categorie': 'Établissement pluridisciplinaire',
        'bonus': 0.12,
        'description': 'Soins multiples'
    },
    'Hôpital des armées': {
        'type': 'hopital',
        'categorie': 'Hôpital militaire',
        'bonus': 0.12,
        'description': 'Service santé armées'
    },
    'Autre Etablissement Loi Hospitalière': {
        'type': 'hopital',
        'categorie': 'Autre établissement',
        'bonus': 0.12,
        'description': 'Établissement sanitaire'
    },
    
    # ============================================================
    # SOINS SPÉCIALISÉS SENIORS (0.18-0.26)
    # Poids ÉLEVÉS car consultations externes / soins domicile
    # = vrais clients des pharmacies de ville
    # ============================================================
    'Etablissement de Soins Longue Durée': {
        'type': 'soin_specialise',
        'categorie': 'Soins longue durée',
        'bonus': 0.26,
        'description': 'Séjour long seniors - forte consommation pharma'
    },
    'Centre de dialyse': {
        'type': 'soin_specialise',
        'categorie': 'Centre dialyse',
        'bonus': 0.26,
        'description': 'Dialyse externe - patients ambulatoires'
    },
    "Structure d'Alternative à la dialyse en centre": {
        'type': 'soin_specialise',
        'categorie': 'Dialyse alternative',
        'bonus': 0.24,
        'description': 'Dialyse hors centre'
    },
    'Hospitalisation à Domicile': {
        'type': 'soin_specialise',
        'categorie': 'HAD',
        'bonus': 0.24,
        'description': 'Soins domicile - prescriptions pharmacie ville'
    },
    'Service de Soins Infirmiers A Domicile (S.S.I.A.D)': {
        'type': 'soin_specialise',
        'categorie': 'SSIAD',
        'bonus': 0.24,
        'description': 'Infirmiers domicile - pharmacie ville'
    },
    'Centre de Lutte Contre Cancer': {
        'type': 'soin_specialise',
        'categorie': 'Centre cancer',
        'bonus': 0.22,
        'description': 'Oncologie - beaucoup de traitement oral'
    },
    'Centre de Consultations Cancer': {
        'type': 'soin_specialise',
        'categorie': 'Consultation cancer',
        'bonus': 0.18,
        'description': 'Consultation oncologie externe'
    },
    'Equipes de Soins Spécialisées': {
        'type': 'soin_specialise',
        'categorie': 'Équipe soins spécialisés',
        'bonus': 0.18,
        'description': 'Soins spécialisés'
    },
    'Traitements Spécialisés à Domicile': {
        'type': 'soin_specialise',
        'categorie': 'Traitement domicile',
        'bonus': 0.20,
        'description': 'Soins domicile - pharmacie ville'
    },
    
    # ============================================================
    # CENTRES DE SANTÉ (0.15-0.20)
    # ============================================================
    'Centre de Santé': {
        'type': 'centre_sante',
        'categorie': 'Centre de santé',
        'bonus': 0.18,
        'description': 'Centre santé pluridisciplinaire'
    },
    'Maison de santé (L.6223-3)': {
        'type': 'centre_sante',
        'categorie': 'Maison de santé',
        'bonus': 0.18,
        'description': 'Maison santé pluri-professionnelle'
    },
    'Centre de soins et de prévention': {
        'type': 'centre_sante',
        'categorie': 'Centre soins prévention',
        'bonus': 0.16,
        'description': 'Soins et prévention'
    },
    'Maison médicale de garde (MMG)': {
        'type': 'centre_sante',
        'categorie': 'Maison médicale garde',
        'bonus': 0.15,
        'description': 'Permanence soins'
    },
    
    # ============================================================
    # LABORATOIRES (0.10-0.15)
    # ============================================================
    "Laboratoire d'Analyses": {
        'type': 'laboratoire',
        'categorie': 'Laboratoire analyse',
        'bonus': 0.15,
        'description': 'Analyses médicales'
    },
    'Laboratoire de Biologie Médicale': {
        'type': 'laboratoire',
        'categorie': 'Laboratoire biologie',
        'bonus': 0.15,
        'description': 'Biologie médicale'
    },
    'Autre Laboratoire de Biologie Médicale sans FSE': {
        'type': 'laboratoire',
        'categorie': 'Laboratoire sans FSE',
        'bonus': 0.12,
        'description': 'Laboratoire privé'
    },
    'Etablissement de Transfusion Sanguine': {
        'type': 'laboratoire',
        'categorie': 'Transfusion sanguine',
        'bonus': 0.10,
        'description': 'Don du sang'
    },
    
    # ============================================================
    # SANTÉ MENTALE (0.10-0.18)
    # ============================================================
    'Centre Hospitalier Spécialisé lutte Maladies Mentales': {
        'type': 'sante_mentale',
        'categorie': 'CHS psychiatrie',
        'bonus': 0.18,
        'description': 'Hôpital psychiatrique'
    },
    'Maison de Santé pour Maladies Mentales': {
        'type': 'sante_mentale',
        'categorie': 'Maison santé mentale',
        'bonus': 0.15,
        'description': 'Santé mentale'
    },
    'Centre Médico-Psychologique (C.M.P.)': {
        'type': 'sante_mentale',
        'categorie': 'CMP',
        'bonus': 0.12,
        'description': 'Consultation psy ambulatoire'
    },
    "Centre d'Accueil Thérapeutique à temps partiel (C.A.T.T.P.)": {
        'type': 'sante_mentale',
        'categorie': 'CATTP',
        'bonus': 0.10,
        'description': 'Accueil thérapeutique partiel'
    },
    'Appartement de Coordination Thérapeutique (A.C.T.)': {
        'type': 'sante_mentale',
        'categorie': 'ACT',
        'bonus': 0.12,
        'description': 'Coordination thérapeutique'
    },
    
    # ============================================================
    # ADDICTOLOGIE (0.10-0.12)
    # ============================================================
    'Centre soins accompagnement prévention addictologie (CSAPA)': {
        'type': 'addictologie',
        'categorie': 'CSAPA',
        'bonus': 0.12,
        'description': 'Addictions'
    },
    'Ctre.Accueil/ Accomp.Réduc.Risq.Usag. Drogues (C.A.A.R.U.D.)': {
        'type': 'addictologie',
        'categorie': 'CAARUD',
        'bonus': 0.10,
        'description': 'Réduction risques drogues'
    },
    
    # ============================================================
    # PRÉVENTION SANTÉ SENIORS (0.08-0.12)
    # ============================================================
    'Centre de vaccination': {
        'type': 'prevention',
        'categorie': 'Centre vaccination',
        'bonus': 0.12,
        'description': 'Vaccination'
    },
    "Centre gratuit d'information de dépistage et de diagnostic": {
        'type': 'prevention',
        'categorie': 'CeGIDD',
        'bonus': 0.10,
        'description': 'Dépistage'
    },
    "Centre d'Examens de Santé": {
        'type': 'prevention',
        'categorie': 'Examen santé',
        'bonus': 0.10,
        'description': 'Bilan santé'
    },
    'Centre de Lutte Antituberculeuse (CLAT)': {
        'type': 'prevention',
        'categorie': 'CLAT',
        'bonus': 0.08,
        'description': 'Tuberculose'
    },
    
    # ============================================================
    # HANDICAP ADULTES (0.12-0.18) - Pertinent car beaucoup de seniors
    # ============================================================
    "Maison d'Accueil Spécialisée (M.A.S.)": {
        'type': 'handicap_adulte',
        'categorie': 'MAS',
        'bonus': 0.18,
        'description': 'Accueil handicap lourd'
    },
    "Foyer d'Accueil Médicalisé pour Adultes Handicapés (F.A.M.)": {
        'type': 'handicap_adulte',
        'categorie': 'FAM',
        'bonus': 0.18,
        'description': 'Accueil médicalisé handicap'
    },
    'Etab.Acc.Médicalisé en tout ou partie personnes handicapées': {
        'type': 'handicap_adulte',
        'categorie': 'Accueil médicalisé handicap',
        'bonus': 0.16,
        'description': 'Hébergement médicalisé'
    },
    'Foyer de Vie pour Adultes Handicapés': {
        'type': 'handicap_adulte',
        'categorie': 'Foyer vie handicap',
        'bonus': 0.14,
        'description': 'Foyer vie'
    },
    'Foyer Hébergement Adultes Handicapés': {
        'type': 'handicap_adulte',
        'categorie': 'Foyer hébergement handicap',
        'bonus': 0.12,
        'description': 'Hébergement handicap'
    },
    'Maisons Départementales des Personnes Handicapées': {
        'type': 'handicap_adulte',
        'categorie': 'MDPH',
        'bonus': 0.12,
        'description': 'Maison handicap'
    },
    
    # ============================================================
    # SOCIAL ET PRÉCARITÉ SANTÉ (0.08-0.15)
    # ============================================================
    'Lits Halte Soins Santé (L.H.S.S.)': {
        'type': 'social',
        'categorie': 'LHSS',
        'bonus': 0.15,
        'description': 'Soins précarité'
    },
    "Lits d'Accueil Médicalisés (L.A.M.)": {
        'type': 'social',
        'categorie': 'LAM',
        'bonus': 0.15,
        'description': 'Accueil médicalisé précarité'
    },
    'Centre Hébergement & Réinsertion Sociale (C.H.R.S.)': {
        'type': 'social',
        'categorie': 'CHRS',
        'bonus': 0.10,
        'description': 'Hébergement insertion'
    },
    'Equipe Mobile Médico-Sociale Précarité': {
        'type': 'social',
        'categorie': 'Équipe mobile précarité',
        'bonus': 0.10,
        'description': 'Maraude sociale'
    },
    "Structure qui contribue au Service d'Accès aux Soins": {
        'type': 'social',
        'categorie': 'Accès soins',
        'bonus': 0.10,
        'description': 'Permanence accès soins'
    },
    'Maisons Relais - Pensions de Famille': {
        'type': 'social',
        'categorie': 'Maison relais',
        'bonus': 0.08,
        'description': 'Logement accompagné'
    },
    
    # ============================================================
    # SERVICES AIDE DOMICILE SENIORS (0.12-0.18)
    # ============================================================
    'Service autonomie aide et soins (SAAS)': {
        'type': 'service_domicile',
        'categorie': 'SAAS',
        'bonus': 0.18,
        'description': 'Aide et soins autonomie'
    },
    'Service autonomie aide (SAA)': {
        'type': 'service_domicile',
        'categorie': 'SAA',
        'bonus': 0.15,
        'description': 'Aide autonomie'
    },
    "Service d'Aide Ménagère à Domicile": {
        'type': 'service_domicile',
        'categorie': 'Aide ménagère domicile',
        'bonus': 0.14,
        'description': 'Aide ménagère'
    },
    "Structure Dispensatrice à domicile d'Oxygène à usage médical": {
        'type': 'service_domicile',
        'categorie': 'Oxygène domicile',
        'bonus': 0.14,
        'description': 'Oxygénothérapie domicile'
    },
    'Service de Repas à Domicile': {
        'type': 'service_domicile',
        'categorie': 'Portage repas',
        'bonus': 0.12,
        'description': 'Portage repas'
    },
    
    # ============================================================
    # TUTELLE ET PROTECTION MAJEURS (0.12)
    # ============================================================
    'Service mandataire judiciaire à la protection des majeurs': {
        'type': 'tutelle',
        'categorie': 'Mandataire judiciaire',
        'bonus': 0.12,
        'description': 'Protection majeurs'
    },
    
    # ============================================================
    # COORDINATION ET TÉLÉSANTÉ (0.08-0.12)
    # ============================================================
    'Communautés professionnelles territoriales de santé (CPTS)': {
        'type': 'coordination',
        'categorie': 'CPTS',
        'bonus': 0.12,
        'description': 'Coordination santé'
    },
    "Dispositif d'appui à la coordination": {
        'type': 'coordination',
        'categorie': 'DAC',
        'bonus': 0.10,
        'description': 'Appui coordination'
    },
    'Sociétés de téléconsultation (STLC)': {
        'type': 'coordination',
        'categorie': 'Téléconsultation',
        'bonus': 0.10,
        'description': 'Téléconsultation'
    },
    
    # ============================================================
    # THERMALISME (0.10) - Pertinent pour seniors
    # ============================================================
    'Etablissement Thermal': {
        'type': 'thermalisme',
        'categorie': 'Thermalisme',
        'bonus': 0.10,
        'description': 'Cure thermale'
    },
}


def get_finess_config(libelle):
    """
    Récupère la configuration pour un libellé FINESS
    
    Args:
        libelle (str): Libellé de la catégorie FINESS
        
    Returns:
        dict: Configuration ou None
    """
    return FINESS_CATEGORIES_WEIGHTS.get(libelle)


def get_all_categories():
    """
    Retourne toutes les catégories avec leurs poids
    
    Returns:
        dict: Toutes les catégories
    """
    return FINESS_CATEGORIES_WEIGHTS


# Pour usage direct
if __name__ == "__main__":
    print("Configuration FINESS - Poids d'attractivité SENIORS 65+")
    print("=" * 70)
    print("⚠️  SEULEMENT les catégories pertinentes pour les seniors")
    print("=" * 70)
    
    # Compter par type
    types_count = {}
    for config in FINESS_CATEGORIES_WEIGHTS.values():
        type_hub = config['type']
        types_count[type_hub] = types_count.get(type_hub, 0) + 1
    
    print(f"\nTotal catégories configurées : {len(FINESS_CATEGORIES_WEIGHTS)}")
    print(f"\nRépartition par type :")
    for type_hub, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {type_hub:<30} : {count:>3} catégories")
    
    # Top bonus
    print(f"\n📊 Top 15 bonus d'attractivité :")
    sorted_by_bonus = sorted(
        FINESS_CATEGORIES_WEIGHTS.items(),
        key=lambda x: x[1]['bonus'],
        reverse=True
    )
    for libelle, config in sorted_by_bonus[:15]:
        print(f"  {config['bonus']:.2f} - {config['categorie']}")
    
    print(f"\n✅ Catégories EXCLUES :")
    print(f"  • Protection enfance (non pertinent)")
    print(f"  • Handicap enfant (non pertinent)")
    print(f"  • Formation (non pertinent)")
    print(f"  • Pharmacies (déjà dans votre dataset)")
