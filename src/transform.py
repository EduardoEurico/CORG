import pandas as pd
import numpy as np

def processar_perfis(caminho_csv):
    df = pd.read_csv(caminho_csv)
    
    # 1. KPI: Gasto Total e Médio por Deputado
    perfil = df.groupby(['id_deputado', 'nome_deputado', 'partido', 'uf']).agg(
        total_gasto=('valorDocumento', 'sum'),
        qtd_notas=('valorDocumento', 'count'),
        maior_gasto=('valorDocumento', 'max')
    ).reset_index()

    # 2. KPI: Índice de Concentração de Fornecedor (IC)
    # Pegamos o maior gasto de cada deputado com um único CNPJ e dividimos pelo total
    gastos_por_cnpj = df.groupby(['id_deputado', 'cnpjCpfFornecedor'])['valorDocumento'].sum().reset_index()
    max_por_cnpj = gastos_por_cnpj.groupby('id_deputado')['valorDocumento'].max()
    
    perfil = perfil.merge(max_por_cnpj.rename('max_unico_fornecedor'), on='id_deputado')
    perfil['indice_concentracao'] = perfil['max_unico_fornecedor'] / perfil['total_gasto']

    # 3. KPI: Categoria Dominante (Feature Engineering)
    idx_max_cat = df.groupby(['id_deputado', 'tipoDespesa'])['valorDocumento'].sum().idxmax()
    # (Essa parte requer um map mais detalhado, mas a lógica é identificar o "estilo" de gasto)

    return perfil

# Exemplo de uso
# df_final_perfis = processar_perfis("dados_completos_deputados_2025.csv")

def gerar_score_final(df_perfil):
    # Normalizando os valores entre 0 e 1 para o cálculo do Score
    # Quanto mais próximo de 1, mais "intenso" é aquele perfil no indicador
    
    for col in ['total_gasto', 'indice_concentracao', 'qtd_notas']:
        max_val = df_perfil[col].max()
        min_val = df_perfil[col].min()
        df_perfil[f'n_{col}'] = (df_perfil[col] - min_val) / (max_val - min_val)

    # Cálculo do Score Ponderado (Pesos que você define como regra de negócio)
    df_perfil['score_perfil'] = (
        df_perfil['n_total_gasto'] * 0.4 + 
        df_perfil['n_indice_concentracao'] * 0.4 + 
        df_perfil['n_qtd_notas'] * 0.2
    )
    
    return df_perfil