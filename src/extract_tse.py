import pandas as pd
import os
from src.utils import log_progresso

def carregar_bens_tse(caminho_csv):
    """
    Carrega o CSV de declaração de bens e cruza com a consulta de candidatos para obter o CPF.
    """
    # Descobre automaticamente o nome do arquivo de consulta baseado no ano do arquivo de bens
    caminho_consulta = caminho_csv.replace('bem_candidato', 'consulta_cand')

    if not os.path.exists(caminho_csv) or not os.path.exists(caminho_consulta):
        log_progresso(f"⚠️ Arquivos TSE ausentes (bens ou consulta): {caminho_csv}")
        return pd.DataFrame()

    log_progresso(f"Lendo dados do TSE: {caminho_csv} e cruzando com ponte de CPFs...")
    
    # 1. Lê os Bens
    df_bens = pd.read_csv(
        caminho_csv, sep=';', encoding='latin1', on_bad_lines='skip', decimal=','
    )
    
    # 2. Lê a Consulta (A Ponte)
    df_consulta = pd.read_csv(
        caminho_consulta, sep=';', encoding='latin1', on_bad_lines='skip'
    )

    # 3. Soma os bens agrupando pelo Sequencial do Candidato
    if 'SQ_CANDIDATO' not in df_bens.columns or 'VR_BEM_CANDIDATO' not in df_bens.columns:
        return pd.DataFrame()
        
    df_bens_agrupado = df_bens.groupby('SQ_CANDIDATO', as_index=False)['VR_BEM_CANDIDATO'].sum()

    # 4. Isola a ponte (Sequencial -> CPF)
    df_ponte = df_consulta[['SQ_CANDIDATO', 'NR_CPF_CANDIDATO']].drop_duplicates()

    # 5. Cruza os bens com a ponte para descobrir o CPF
    df_final = pd.merge(df_bens_agrupado, df_ponte, on='SQ_CANDIDATO', how='inner')

    # 6. Padroniza colunas para o transform.py
    df_final = df_final.rename(columns={
        'NR_CPF_CANDIDATO': 'cpf',
        'VR_BEM_CANDIDATO': 'valor_bem'
    })
    
    # 7. Limpeza blindada do CPF
    df_final['cpf'] = df_final['cpf'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)
    
    return df_final[['cpf', 'valor_bem']]