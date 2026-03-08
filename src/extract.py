import os
import requests
import pandas as pd
import time
from tqdm import tqdm 

def get_todos_deputados():
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    params = {'ordem': 'ASC', 'ordenarPor': 'nome'}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return pd.DataFrame(response.json()['dados'])
    except Exception as e:
        print(f"❌ Erro ao buscar lista de deputados: {e}")
        return pd.DataFrame()

def get_gastos_completos(id_deputado, ano=2025):
    """
    Coleta todas as páginas de gastos de um deputado específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"
    all_expenses = []
    pagina = 1
    
    while True:
        params = {'ano': ano, 'itens': 100, 'pagina': pagina}
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                break
            
            dados = response.json()['dados']
            if not dados: # Se a página vier vazia, terminou a coleta
                break
                
            all_expenses.extend(dados)
            pagina += 1
            time.sleep(0.05) # Pequeno delay para não sobrecarregar a API
        except:
            break
            
    return pd.DataFrame(all_expenses)

# --- EXECUÇÃO PRINCIPAL ---

print("Step 1: Coletando lista de deputados...")
df_lista_deputados = get_todos_deputados()

if not df_lista_deputados.empty:
    lista_final_gastos = []
    
    # Usando tqdm para acompanhar o progresso (essencial para 513 requests)
    print(f"Step 2: Coletando gastos de {len(df_lista_deputados)} deputados. Isso pode levar alguns minutos...")
    
    for _, deputado in tqdm(df_lista_deputados.iterrows(), total=len(df_lista_deputados)):
        df_temp = get_gastos_completos(deputado['id'], ano=2025)
        
        if not df_temp.empty:
            # Injetamos informações do deputado para facilitar o cruzamento posterior
            df_temp['id_deputado'] = deputado['id']
            df_temp['nome_deputado'] = deputado['nome']
            df_temp['partido'] = deputado['siglaPartido']
            df_temp['uf'] = deputado['siglaUf']
            
            lista_final_gastos.append(df_temp)

    # Concatena todos os DataFrames da lista em um só
    if lista_final_gastos:
        df_final = pd.concat(lista_final_gastos, ignore_index=True)
        
        # --- LIMPEZA E PRÉ-PROCESSAMENTO (Conceito 2 do Projeto) ---
        # 1. Converter valores para float (essencial para cálculos)
        df_final['valorDocumento'] = pd.to_numeric(df_final['valorDocumento'], errors='coerce')
        # 2. Converter data para datetime
        df_final['dataDocumento'] = pd.to_datetime(df_final['dataDocumento'], errors='coerce')
        
        # Salva o resultado final em CSV para usar no Power BI ou próximas etapas
        os.makedirs("data", exist_ok=True)
        df_final.to_csv("data/dados_completos_deputados_2025.csv", index=False, encoding='utf-8-sig')
        print(f"\n✅ Concluído! Arquivo gerado com {len(df_final)} registros de gastos.")
    else:
        print("⚠️ Nenhuma despesa foi encontrada no período.")