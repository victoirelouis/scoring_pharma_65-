import pandas as pd

# IDs des pharmacies sans coordonnées dans le fichier output
ids_missing = [2060274, 2007362, 2241941, 2093839, 2014326, 2093650, 
               2001107, 2001894, 2113404, 2002542, 2002584]

# Vérifier dans le fichier SOURCE
print("=" * 80)
print("VÉRIFICATION FICHIER SOURCE: pharmacies_final.csv")
print("=" * 80)
df_source = pd.read_csv('data/input/data_cleaning/pharmacies_final.csv', sep=';')
print(f"Pharmacies totales dans le source: {len(df_source)}")

missing_source = df_source[df_source['id_pharmacie'].isin(ids_missing)]
print(f"\nPharmacies trouvées dans le source: {len(missing_source)}/11")

if len(missing_source) > 0:
    print("\nDétail des pharmacies dans le FICHIER SOURCE:")
    print(missing_source[['id_pharmacie', 'nom_pharmacie', 'latitude', 
                          'longitude', 'commune']].to_string(index=False))
    
    # Compter combien ont des NaN
    nan_in_source = missing_source[missing_source['latitude'].isna() | 
                                   missing_source['longitude'].isna()]
    print(f"\n🔍 Pharmacies DÉJÀ sans coordonnées dans le source: {len(nan_in_source)}/11")

# Vérifier dans le fichier OUTPUT
print("\n" + "=" * 80)
print("VÉRIFICATION FICHIER OUTPUT: pharmacies_avec_hubs.csv")
print("=" * 80)
df_output = pd.read_csv('intermediaire/output/pharmacies_avec_hubs.csv', sep=',')
missing_output = df_output[df_output['id_pharmacie'].isin(ids_missing)]
print(f"Pharmacies trouvées dans l'output: {len(missing_output)}/11")

if len(missing_output) > 0:
    print("\nDétail des pharmacies dans le FICHIER OUTPUT:")
    print(missing_output[['id_pharmacie', 'nom_pharmacie', 'latitude', 
                         'longitude', 'commune']].to_string(index=False))

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("✅ Problème identifié si NaN dans source = NaN dans output")
print("❌ Bug de traitement si coordonnées OK dans source mais NaN dans output")
