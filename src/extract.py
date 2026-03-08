import pandas as pd
import requests
import os
from src.utils import log_progresso

def get_deputados_atuais():
    """Busca a lista oficial e atualizada de deputados via API."""
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    params = {'ordem': 'ASC', 'ordenarPor': 'nome'}
    try:
        log_progresso("Consultando API para lista de deputados atuais...")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        df = pd.DataFrame(response.json()['dados'])
        return df
    except Exception as e:
        log_progresso(f"❌ Erro ao buscar deputados: {e}")
        return pd.DataFrame()

def carregar_dados_despesas(caminho_csv):
    """Carrega o CSV pesado que você baixou do portal."""
    if not os.path.exists(caminho_csv):
        log_progresso(f"⚠️ Arquivo {caminho_csv} não encontrado!")
        return pd.DataFrame()
    
    log_progresso(f"Lendo CSV de despesas: {caminho_csv}...")
    # Usamos low_memory=False pois arquivos da Câmara costumam ter tipos mistos
    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8') 
    return df