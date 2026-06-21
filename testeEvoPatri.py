import pandas as pd

# Ajusta a formatação para não mostrar notação científica e facilitar a leitura
pd.options.display.float_format = '{:,.2f}'.format

# Carrega o produto final do seu pipeline
df = pd.read_parquet('data/outputs/perfil_final_politicos.parquet')

# Filtra as colunas que importam para essa visão
colunas = [
    'nome', 'siglaPartido', 'siglaUf', 
    'patrimonio_2018', 'patrimonio_2022', 
    'crescimento_bruto_R$', 'kpi_score_risco'
]

print("--- 💰 TOP 10: MAIOR EVOLUÇÃO PATRIMONIAL (R$) ---")
top_grana = df.sort_values('crescimento_bruto_R$', ascending=False)[colunas].head(10)
print(top_grana.to_string(index=False))

print("\n--- ⚠️ TOP 10: MAIOR SCORE DE RISCO GERAL ---")
top_risco = df.sort_values('kpi_score_risco', ascending=False)[colunas].head(10)
print(top_risco.to_string(index=False))