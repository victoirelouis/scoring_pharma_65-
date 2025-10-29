# Données du Projet

## Structure des Données

Ce répertoire contient les données nécessaires pour le calcul du scoring des pharmacies.

### Fichiers Attendus

1. **pharmacies.csv** : Liste des pharmacies à analyser
   - id_pharmacie
   - nom
   - adresse
   - latitude
   - longitude
   - code_postal
   - ville

2. **demographics.csv** : Données démographiques par zone
   - code_zone
   - population_65_plus
   - population_65_74
   - population_75_84
   - population_85_plus
   - croissance_5ans

3. **economic.csv** : Données économiques par zone
   - code_zone
   - revenu_median
   - nb_residences_seniors
   - nb_ehpad
   - indice_commercial

4. **competitors.csv** : Pharmacies concurrentes
   - id_concurrent
   - latitude
   - longitude
   - distance_km

### Format des Données

Tous les fichiers CSV doivent utiliser :
- Encodage UTF-8
- Séparateur : virgule (,)
- Décimales : point (.)

### Confidentialité

⚠️ Les fichiers de données réels ne sont pas versionnés dans le dépôt Git pour des raisons de confidentialité. Seuls les exemples et la structure sont partagés.
