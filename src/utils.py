import re
import pandas as pd
import unicodedata
import sqlite3
import os
from datetime import datetime


def log_progresso(mensagem):
    """Auxiliar para exibir logs formatados no console do backend com timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] - {mensagem}")

def limpar_documento(doc):
    """Remove caracteres de CPF/CNPJ e garante string de 11 ou 14 dígitos."""
    if pd.isna(doc): return None
    doc = re.sub(r'\D', '', str(doc))
    return doc.zfill(11) if len(doc) <= 11 else doc.zfill(14)

def normalizar_nome(nome):
    """Remove acentos e padroniza nomes para facilitar o cruzamento."""
    if not isinstance(nome, str): return ""
    nome = nome.upper().strip()
    return "".join(ch for ch in unicodedata.normalize('NFD', nome) 
                   if unicodedata.category(ch) != 'Mn')

def safe_read_json(caminho):
    """Lê JSON com tratamento de erro e encoding."""
    try:
        return pd.read_json(caminho, encoding='utf-8')
    except Exception as e:
        log_progresso(f"⚠️ Erro ao ler {caminho}: {e}")
        return pd.DataFrame()


def salvar_no_banco(df, tabela, db_name="data/transparencia.db"):
    """
    Salva o DataFrame em uma tabela SQL. 
    Se a tabela já existir, ele adiciona os novos dados (append).
    """
    try:
        # Garante que a pasta data existe
        os.makedirs(os.path.dirname(db_name), exist_ok=True)
        
        conn = sqlite3.connect(db_name)
        # index=False evita que o pandas crie uma coluna extra para o ID do dataframe
        df.to_sql(tabela, conn, if_exists='append', index=False)
        conn.close()
        log_progresso(f"✅ {len(df)} linhas inseridas na tabela '{tabela}' com sucesso.")
    except Exception as e:
        log_progresso(f"❌ Erro ao salvar no banco: {e}")

def ler_do_banco(query, db_name="data/transparencia.db"):
    """
    Executa uma consulta SQL e retorna um DataFrame.
    Útil para buscar os dados para calcular os KPIs.
    """
    try:
        conn = sqlite3.connect(db_name)
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        log_progresso(f"❌ Erro ao ler do banco: {e}")
        return pd.DataFrame()