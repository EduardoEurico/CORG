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

                # Tentar encontrar a versão consolidada do BRASIL primeiro
                csv_brasil = [f for f in csvs_no_zip if 'brasil' in f.lower()]
                if csv_brasil:
                    csvs_no_zip = csv_brasil

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


class TSEIdentityTracker:
    def __init__(self, df_atuais):
        self.cpfs_alvo = set(df_atuais['cpf'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11))
        self.nomes_uf_alvo = {
            f"{str(nome).upper().strip()}|{str(uf).upper().strip()}": str(cpf).replace(r'\D', '').zfill(11) 
            for cpf, nome, uf in zip(df_atuais['cpf'], df_atuais['nome'], df_atuais['siglaUf']) 
            if pd.notna(nome) and pd.notna(uf)
        }
        self.titulo_to_cpf = {}

def carregar_bens_tse(caminho_csv, tracker):
    """
    Carrega o CSV de declaração de bens e cruza com a consulta de candidatos para obter o CPF.
    Usa um sistema Multi-Chave (CPF -> Título -> Nome) para contornar bloqueios da LGPD.
    """
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

    # 4. Cascata de Cruzamento (Multi-Key)
    if 'NR_CPF_CANDIDATO' in df_consulta.columns:
        df_consulta['cpf_limpo'] = df_consulta['NR_CPF_CANDIDATO'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)
    else:
        df_consulta['cpf_limpo'] = '-4'
        
    match_cpf = df_consulta['cpf_limpo'].isin(tracker.cpfs_alvo)
    
    # Aprender títulos novos dos candidatos que deram match no CPF
    if 'NR_TITULO_ELEITORAL_CANDIDATO' in df_consulta.columns:
        novos_titulos = df_consulta[match_cpf][['NR_TITULO_ELEITORAL_CANDIDATO', 'cpf_limpo']].dropna()
        for _, r in novos_titulos.iterrows():
            tit = str(r['NR_TITULO_ELEITORAL_CANDIDATO']).strip()
            if tit != '-4' and tit != 'nan' and tit != '0':
                tracker.titulo_to_cpf[tit] = r['cpf_limpo']
                
        # Preparar match por Título
        df_consulta['titulo_limpo'] = df_consulta['NR_TITULO_ELEITORAL_CANDIDATO'].astype(str).str.strip()
        match_titulo = df_consulta['titulo_limpo'].map(tracker.titulo_to_cpf)
    else:
        match_titulo = pd.Series([None] * len(df_consulta), index=df_consulta.index)

    # Preparar match por Nome (Fallback LGPD)
    if 'NM_CANDIDATO' in df_consulta.columns and 'SG_UF' in df_consulta.columns:
        df_consulta['nome_limpo'] = df_consulta['NM_CANDIDATO'].astype(str).str.upper().str.strip()
        df_consulta['uf_limpo'] = df_consulta['SG_UF'].astype(str).str.upper().str.strip()
        df_consulta['nome_uf_chave'] = df_consulta['nome_limpo'] + '|' + df_consulta['uf_limpo']
        match_nome = df_consulta['nome_uf_chave'].map(tracker.nomes_uf_alvo)
    else:
        match_nome = pd.Series([None] * len(df_consulta), index=df_consulta.index)

    # Consolidar CPF final priorizando CPF > Titulo > Nome
    df_consulta['cpf_final'] = None
    df_consulta.loc[match_cpf, 'cpf_final'] = df_consulta.loc[match_cpf, 'cpf_limpo']
    
    mask_vazio = df_consulta['cpf_final'].isnull()
    df_consulta.loc[mask_vazio, 'cpf_final'] = match_titulo[mask_vazio]
    
    mask_vazio = df_consulta['cpf_final'].isnull()
    df_consulta.loc[mask_vazio, 'cpf_final'] = match_nome[mask_vazio]
    
    # Log de quem foi recuperado via Fallback (opcional para debug)
    recuperados_titulo = match_titulo.notnull() & (~match_cpf)
    recuperados_nome = match_nome.notnull() & (~match_cpf) & match_titulo.isnull()
    
    qtd_titulo = recuperados_titulo.sum()
    qtd_nome = recuperados_nome.sum()
    if qtd_titulo > 0 or qtd_nome > 0:
        log_progresso(f"      🛟  LGPD Fallback: {qtd_titulo} via Título | {qtd_nome} via Nome.")

    # 5. Isola a ponte (Sequencial -> CPF Final)
    df_ponte = df_consulta.dropna(subset=['cpf_final'])[['SQ_CANDIDATO', 'cpf_final']].drop_duplicates()

    # 6. Cruza os bens com a ponte
    df_final = pd.merge(df_bens_agrupado, df_ponte, on='SQ_CANDIDATO', how='inner')

    # 7. Padroniza colunas
    df_final = df_final.rename(columns={
        'cpf_final': 'cpf',
        'VR_BEM_CANDIDATO': 'valor_bem'
    })
    
    return df_final[['cpf', 'valor_bem']]


def carregar_todos_bens_tse(anos, df_atuais, pasta_dados='data'):
    """
    Carrega dados de bens do TSE para múltiplos anos.
    Usa um Tracker de Identidade para manter CPFs e Títulos em memória através dos anos.
    """
    tracker = TSEIdentityTracker(df_atuais)
    dict_bens = {}
    
    # Processa na ordem cronológica para que o tracker "aprenda" os títulos antes de chegar em 2024
    anos_ordenados = sorted(anos)
    
    for ano in anos_ordenados:
        # Tentar baixar se necessário
        baixar_tse_se_necessario(ano, pasta_dados)

        caminho_csv = os.path.join(pasta_dados, f'bem_candidato_{ano}.csv')
        df = carregar_bens_tse(caminho_csv, tracker)

        if not df.empty:
            dict_bens[str(ano)] = df
            log_progresso(f"   📊 TSE {ano}: {df['cpf'].nunique():,} candidatos com bens declarados.")
        else:
            log_progresso(f"   ⚠️ TSE {ano}: Sem dados disponíveis (arquivo ausente ou vazio).")

    log_progresso(f"✅ TSE carregado: {len(dict_bens)} anos com dados ({', '.join(dict_bens.keys())}).")
    return dict_bens