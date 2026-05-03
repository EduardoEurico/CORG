import os
import glob
from src.utils import log_progresso

def listar_arquivos_historicos(diretorio_data):
    """Retorna uma lista com o caminho de todos os arquivos JSON na pasta."""
    # Procura por qualquer arquivo .json dentro da pasta informada
    arquivos = glob.glob(os.path.join(diretorio_data, "*.json"))
    log_progresso(f"📂 {len(arquivos)} arquivos históricos encontrados para processamento.")
    return sorted(arquivos) # Ordena para processar do mais antigo ao mais novo