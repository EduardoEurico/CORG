import re
import unicodedata

def formatar_nome(nome):
    """
    Normaliza nomes para facilitar o cruzamento (remove acentos e espaços extras).
    Ex: 'José da Silva ' -> 'JOSE DA SILVA'
    """
    if not isinstance(nome, str):
        return ""
    nome = nome.upper().strip()
    # Remove acentos usando Normal Form Decomposition (NFD)
    nome = "".join(ch for ch in unicodedata.normalize('NFD', nome) 
                   if unicodedata.category(ch) != 'Mn')
    return nome

def limpar_cnpj_cpf(documento):
    """
    Remove caracteres não numéricos de CNPJ ou CPF.
    Ex: '12.345.678/0001-99' -> '12345678000199'
    """
    if pd.isna(documento):
        return ""
    return re.sub(r'\D', '', str(documento))

def categorizar_valor(valor, media_grupo):
    """
    Classifica um valor com base na média de um grupo (ex: partido).
    Conceito de Ciência de Dados: Rotulação (Labeling).
    """
    if valor > media_group * 1.5:
        return "Muito Acima da Média"
    elif valor < media_group * 0.5:
        return "Muito Abaixo da Média"
    else:
        return "Dentro da Média"

def log_progresso(mensagem):
    """Auxiliar para exibir logs formatados no console do backend."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] - {mensagem}")