import pandas as pd

df = pd.read_csv('intermediaire/output/pharmacies_features_engineered.csv')
ratio_cols = [col for col in df.columns if 'ratio' in col.lower()]

print(f'Total colonnes ratio: {len(ratio_cols)}')
print('\n--- Analyse des ratios hors limites [0,1] ---\n')

out_of_bounds = {}
for col in ratio_cols:
    below_0 = (df[col] < 0).sum()
    above_1 = (df[col] > 1).sum()
    
    if below_0 > 0 or above_1 > 0:
        out_of_bounds[col] = {
            '<0': below_0, 
            '>1': above_1, 
            'min': df[col].min(), 
            'max': df[col].max()
        }
        print(f'{col}:')
        print(f'  < 0: {below_0} pharmacies ({below_0/len(df)*100:.2f}%)')
        print(f'  > 1: {above_1} pharmacies ({above_1/len(df)*100:.2f}%)')
        print(f'  Min: {df[col].min():.4f}, Max: {df[col].max():.4f}\n')

print(f'\nRESUME: {len(out_of_bounds)}/{len(ratio_cols)} colonnes ratio ont des valeurs hors [0,1]')
