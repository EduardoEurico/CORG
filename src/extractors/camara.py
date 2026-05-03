import pandas as pd
import requests
import os
import time
import glob
from src.utils import log_progresso, salvar_no_banco
from src.transform import processar_historico_completo

def get_deputados_atuais():
    """Busca a lista de todos os deputados na legislatura atual."""
    log_progresso("Buscando lista de deputados atuais na API da Câmara...")
    
    # O PULO DO GATO: ?itens=1000 garante que não vamos cair na paginação!
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados?itens=1000"
    
    response = requests.get(url)
    if response.status_code == 200:
        dados = response.json().get('dados', [])
        df = pd.DataFrame(dados)
        log_progresso(f"✅ Encontrados {len(df)} deputados ativos.")
        return df
    else:
        log_progresso(f"❌ Erro ao acessar API da Câmara: {response.status_code}")
        return pd.DataFrame()

def enriquecer_cpfs(df_atuais):
    """
    Entra no perfil detalhado de cada deputado para extrair o CPF oficial.
    """
    log_progresso(f"Buscando CPF de {len(df_atuais)} deputados... (Isso leva uns 2 minutos ☕)")
    cpfs_extraidos = []
    
    for index, row in df_atuais.iterrows():
        id_deputado = row['id']
        url_detalhe = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}"
        
        try:
            res = requests.get(url_detalhe, timeout=10)
            if res.status_code == 200:
                dados_detalhe = res.json().get('dados', {})
                # Pega o CPF se existir
                cpf = dados_detalhe.get('cpf', None)
                cpfs_extraidos.append({'id': id_deputado, 'cpf': cpf})
            else:
                cpfs_extraidos.append({'id': id_deputado, 'cpf': None})
        except Exception as e:
            cpfs_extraidos.append({'id': id_deputado, 'cpf': None})
            
        # Delay de segurança (0.2s) para evitar bloqueio por DDoS (Rate Limit) da API do Governo
        time.sleep(0.2)
        
        # Feedback visual a cada 50 deputados
        if (index + 1) % 50 == 0:
            log_progresso(f"⏳ Baixando CPFs: {index + 1}/{len(df_atuais)} concluídos...")

    # Transforma a lista de CPFs num DataFrame
    df_cpfs = pd.DataFrame(cpfs_extraidos)
    
    # Junta os CPFs com a base principal pelo ID
    df_final = pd.merge(df_atuais, df_cpfs, on='id', how='left')
    log_progresso("✅ Enriquecimento de CPFs concluído com sucesso!")
    
    return df_final

def migrar_jsons_historicos(diretorio_data='data'):
    """Processa e salva os dados no SQLite."""
    padrao = os.path.join(diretorio_data, "*.json")
    arquivos = sorted(glob.glob(padrao))
    
    if not arquivos:
        log_progresso(f"⚠️ Nenhum arquivo JSON encontrado em: {diretorio_data}")
        return

    for caminho in arquivos:
        log_progresso(f"⏳ Processando: {os.path.basename(caminho)}")
        df_limpo = processar_historico_completo([caminho])
        
        if not df_limpo.empty:
            salvar_no_banco(df_limpo, "gastos_camara")
    
    log_progresso("✅ Migração finalizada.")