import pandas as pd
import os
import zipfile
import urllib.request
from src.utils import log_progresso


# URLs do CDN do TSE seguem o padrão:
# https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_YYYY.zip
# https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_YYYY.zip
_TSE_CDN_BASE = 'https://cdn.tse.jus.br/estatistica/sead/odsele'


def baixar_tse_se_necessario(ano, pasta_destino='data'):
    """
    Verifica se os CSVs do TSE para o ano já existem.
    Se não, baixa os ZIPs do CDN do TSE e extrai os CSVs relevantes.
    Retorna True se os arquivos estão disponíveis, False se falhou.
    """
    csv_bens = os.path.join(pasta_destino, f'bem_candidato_{ano}.csv')
    csv_consulta = os.path.join(pasta_destino, f'consulta_cand_{ano}.csv')

    # Se ambos já existem, não precisa baixar
    if os.path.exists(csv_bens) and os.path.exists(csv_consulta):
        return True

    log_progresso(f"📥 Baixando dados TSE {ano} do CDN...")

    os.makedirs(pasta_destino, exist_ok=True)

    sucesso = True
    for tipo in ['bem_candidato', 'consulta_cand']:
        csv_path = os.path.join(pasta_destino, f'{tipo}_{ano}.csv')
        if os.path.exists(csv_path):
            continue

        url = f'{_TSE_CDN_BASE}/{tipo}/{tipo}_{ano}.zip'
        zip_path = os.path.join(pasta_destino, f'{tipo}_{ano}.zip')

        try:
            log_progresso(f"   ↓ {url}")
            urllib.request.urlretrieve(url, zip_path)

            # Extrair o CSV relevante do ZIP
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Procurar pelo CSV principal (ignora LEIAMEs e outros)
                csvs_no_zip = [f for f in zf.namelist()
                               if f.lower().endswith('.csv')
                               and tipo.lower() in f.lower()]

                if not csvs_no_zip:
                    # Fallback: pegar qualquer CSV grande
                    csvs_no_zip = [f for f in zf.namelist()
                                   if f.lower().endswith('.csv')]

                if csvs_no_zip:
                    # Extrair o CSV e renomear para o padrão esperado
                    arquivo_extraido = csvs_no_zip[0]
                    zf.extract(arquivo_extraido, pasta_destino)

                    caminho_extraido = os.path.join(pasta_destino, arquivo_extraido)
                    if caminho_extraido != csv_path:
                        # Renomear para o padrão esperado
                        if os.path.exists(csv_path):
                            os.remove(csv_path)
                        os.rename(caminho_extraido, csv_path)

                    log_progresso(f"   ✅ Extraído: {tipo}_{ano}.csv")
                else:
                    log_progresso(f"   ❌ Nenhum CSV encontrado no ZIP para {tipo}_{ano}")
                    sucesso = False

            # Limpar o ZIP
            if os.path.exists(zip_path):
                os.remove(zip_path)

        except Exception as e:
            log_progresso(f"   ❌ Falha ao baixar {tipo}_{ano}: {e}")
            # Limpar ZIP parcial
            if os.path.exists(zip_path):
                os.remove(zip_path)
            sucesso = False

    return sucesso


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


def carregar_todos_bens_tse(anos, pasta_dados='data'):
    """
    Carrega dados de bens do TSE para múltiplos anos.
    Para cada ano, tenta baixar os dados se não existirem.
    Retorna um dicionário {ano_str: DataFrame}.
    """
    dict_bens = {}
    for ano in anos:
        # Tentar baixar se necessário
        baixar_tse_se_necessario(ano, pasta_dados)

        caminho_csv = os.path.join(pasta_dados, f'bem_candidato_{ano}.csv')
        df = carregar_bens_tse(caminho_csv)

        if not df.empty:
            dict_bens[str(ano)] = df
            log_progresso(f"   📊 TSE {ano}: {df['cpf'].nunique():,} candidatos com bens declarados.")
        else:
            log_progresso(f"   ⚠️ TSE {ano}: Sem dados disponíveis (arquivo ausente ou vazio).")

    log_progresso(f"✅ TSE carregado: {len(dict_bens)} anos com dados ({', '.join(dict_bens.keys())}).")
    return dict_bens