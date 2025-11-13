import pandas as pd

df = pd.read_csv('intermediaire/output/pharmacies_features_selected.csv')

print('='*80)
print('VERIFICATION DES DONNEES POUR CALIBRATION')
print('='*80)

print(f'\nTotal pharmacies: {len(df):,}')

print('\n1. TYPE_ZONE - Repartition complete:')
print(df['type_zone'].value_counts(dropna=False).sort_index())
print(f'\nTotal categories type_zone: {df["type_zone"].nunique()}')

print('\n2. CA disponibles:')
print(f'  ca_total: {df["ca_total"].notna().sum():,} ({df["ca_total"].notna().sum()/len(df)*100:.1f}%)')
print(f'  ca_ethique: {df["ca_ethique"].notna().sum():,} ({df["ca_ethique"].notna().sum()/len(df)*100:.1f}%)')
print(f'  ca_conseil: {df["ca_conseil"].notna().sum():,} ({df["ca_conseil"].notna().sum()/len(df)*100:.1f}%)')

print('\n3. Variables population par age (drive_10min):')
vars_pop_age = [c for c in df.columns if 'pop_' in c and 'drive_10min' in c and any(age in c for age in ['65_74', '75_84', '85_plus', 'totale'])]
print(f'  Nombre de variables age: {len(vars_pop_age)}')
for v in sorted(vars_pop_age):
    print(f'    - {v}')

print('\n4. Variables population par genre et age (drive_10min):')
vars_pop_genre = [c for c in df.columns if 'pop_' in c and 'drive_10min' in c and ('hommes' in c or 'femmes' in c)]
print(f'  Nombre de variables genre: {len(vars_pop_genre)}')
for v in sorted(vars_pop_genre):
    print(f'    - {v}')

print('\n5. Colonnes avec "zone" dans le nom:')
zone_cols = [c for c in df.columns if 'zone' in c.lower() or 'flag' in c.lower()]
for v in sorted(zone_cols):
    if v in df.columns:
        nunique = df[v].nunique() if df[v].dtype == 'object' else 'numeric'
        print(f'    - {v:40s} : {nunique}')

print('\n' + '='*80)
print('RESUME:')
print('='*80)
print(f'\nType_zone dispose de {df["type_zone"].nunique()} categories:')
for cat in sorted(df['type_zone'].dropna().unique()):
    count = (df['type_zone'] == cat).sum()
    print(f'  - {cat:20s}: {count:6,} pharmacies ({count/len(df)*100:5.1f}%)')
    
print(f'\nPharmacies avec CA complet: {df[df["ca_total"].notna() & df["ca_ethique"].notna() & df["ca_conseil"].notna()].shape[0]:,}')
print(f'Variables population disponibles: {len([c for c in df.columns if "pop_" in c and "drive_10min" in c])}')
