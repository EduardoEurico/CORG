import pandas as pd
import numpy as np

# Load data
print("Carregando bases...")
df_historico = pd.read_parquet('data/historico_limpo.parquet')
df_atuais = pd.read_parquet('data/deputados_cpfs_limpos.parquet')

# Convert id columns to string and merge to get current deputies' expenses
df_atuais['id'] = df_atuais['id'].astype(str).str.strip()
df_historico['idDeputado'] = df_historico['idDeputado'].astype(str).str.strip()

df_cruzado = pd.merge(df_historico, df_atuais[['id', 'nome', 'siglaPartido', 'siglaUf']], left_on='idDeputado', right_on='id', how='inner')

# Filter for marketing and consultoria by matching the exact categories from value_counts
df_mkt = df_cruzado[df_cruzado['tipoDespesa'].str.contains('DIVULG', case=False, na=False)]
df_cons = df_cruzado[df_cruzado['tipoDespesa'].str.contains('CONSULT', case=False, na=False)]

print("\nTop Marketing Suppliers:")
top_mkt = df_mkt.groupby(['cnpjCpfFornecedor', 'nomeFornecedor']).agg(
    gasto_total=('valorLiquido', 'sum'),
    qtd_notas=('valorLiquido', 'count'),
    qtd_deputados=('idDeputado', 'nunique')
).reset_index().sort_values(by='gasto_total', ascending=False)
print(top_mkt.head(15).to_string(index=False))

print("\nTop Consultoria Suppliers:")
top_cons = df_cons.groupby(['cnpjCpfFornecedor', 'nomeFornecedor']).agg(
    gasto_total=('valorLiquido', 'sum'),
    qtd_notas=('valorLiquido', 'count'),
    qtd_deputados=('idDeputado', 'nunique')
).reset_index().sort_values(by='gasto_total', ascending=False)
print(top_cons.head(15).to_string(index=False))
