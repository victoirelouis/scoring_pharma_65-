import pandas as pd

df = pd.read_csv('intermediaire/output/pharmacies_features_complet.csv')

print('='*80)
print('VERIFICATION COMPLETE DES VARIABLES DE SEGMENTATION')
print('='*80)

print(f'\nTotal pharmacies: {len(df):,}')
print(f'Total colonnes: {len(df.columns)}')

print('\n' + '='*80)
print('1. TYPE_ZONE')
print('='*80)
print(df['type_zone'].value_counts(dropna=False))
print(f'\nTotal categories: {df["type_zone"].nunique()}')

print('\n' + '='*80)
print('2. TYPE_ZONE_TOURISTIQUE')
print('='*80)
print(df['type_zone_touristique'].value_counts(dropna=False))
print(f'\nTotal categories (avec NaN): {df["type_zone_touristique"].nunique()}')
print(f'Non-null: {df["type_zone_touristique"].notna().sum():,} ({df["type_zone_touristique"].notna().sum()/len(df)*100:.1f}%)')

print('\n' + '='*80)
print('3. FLAG_COMMUNE_MONTAGNE')
print('='*80)
print(df['flag_commune_montagne'].value_counts(dropna=False))
print(f'\nPharmacies en montagne: {(df["flag_commune_montagne"]==1).sum():,} ({(df["flag_commune_montagne"]==1).sum()/len(df)*100:.1f}%)')

print('\n' + '='*80)
print('4. FLAG_COMMUNE_LITTORAL')
print('='*80)
print(df['flag_commune_littoral'].value_counts(dropna=False))
print(f'\nPharmacies littoral: {(df["flag_commune_littoral"]==1).sum():,} ({(df["flag_commune_littoral"]==1).sum()/len(df)*100:.1f}%)')

print('\n' + '='*80)
print('5. ZONE_ISOLEE')
print('='*80)
print(df['zone_isolee'].value_counts(dropna=False))
print(f'\nTotal categories: {df["zone_isolee"].nunique()}')

print('\n' + '='*80)
print('6. POPULATION 65+ (pour densite_seniors)')
print('='*80)
print(f'pop_65_plus_drive_10min disponible: {"pop_65_plus_drive_10min" in df.columns}')
if 'pop_65_plus_drive_10min' in df.columns:
    print(f'\nStatistiques pop_65_plus_drive_10min:')
    print(f'  Min: {df["pop_65_plus_drive_10min"].min():,.0f}')
    print(f'  Mediane: {df["pop_65_plus_drive_10min"].median():,.0f}')
    print(f'  Moyenne: {df["pop_65_plus_drive_10min"].mean():,.0f}')
    print(f'  Max: {df["pop_65_plus_drive_10min"].max():,.0f}')

print('\n' + '='*80)
print('RESUME')
print('='*80)
print('\nToutes les variables de segmentation necessaires sont presentes:')
print(f'  ✓ type_zone: {df["type_zone"].nunique()} categories')
print(f'  ✓ type_zone_touristique: {df["type_zone_touristique"].nunique()} categories ({df["type_zone_touristique"].notna().sum():,} non-null)')
print(f'  ✓ flag_commune_montagne: {(df["flag_commune_montagne"]==1).sum():,} pharmacies')
print(f'  ✓ flag_commune_littoral: {(df["flag_commune_littoral"]==1).sum():,} pharmacies')
print(f'  ✓ zone_isolee: {df["zone_isolee"].nunique()} categories')
if 'pop_65_plus_drive_10min' in df.columns:
    print(f'  ✓ pop_65_plus_drive_10min: disponible')

print('\n✓ Variables population par age et genre disponibles:')
pop_vars = ['pop_totale_drive_10min', 'pop_65_74_drive_10min', 'pop_75_84_drive_10min', 
            'pop_85_plus_drive_10min', 'pop_hommes_65_74_drive_10min', 
            'pop_hommes_75_84_drive_10min', 'pop_hommes_85_plus_drive_10min',
            'pop_femmes_65_74_drive_10min', 'pop_femmes_75_84_drive_10min', 
            'pop_femmes_85_plus_drive_10min']
for v in pop_vars:
    status = '✓' if v in df.columns else '✗'
    print(f'  {status} {v}')

print('\n' + '='*80)
print('LE SCRIPT EST PRET A ETRE EXECUTE')
print('='*80)
