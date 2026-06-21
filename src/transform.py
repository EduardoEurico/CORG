import pandas as pd
from src.utils import log_progresso, limpar_documento, safe_read_json

# =============================================================================
# CAMADA 1 — INGESTÃO (JSONs planos do portal da transparência)
# Pipeline único. Eliminado o segundo pipeline (mapear_dados_camara /
# processar_um_arquivo) que gerava dois padrões de nomes de coluna
# incompatíveis com gerar_join_perfil e calcular_20_kpis.
# =============================================================================

def padronizar_colunas(df):
    """
    Mapeia os nomes de colunas do portal da Câmara (formato antigo e novo)
    para o padrão interno do projeto. Um único dicionário, sem ambiguidade.
    """
    if df.empty:
        return df

    mapeamento = {
        # ID do deputado — várias grafias ao longo dos anos
        'ideDeputado':               'idDeputado',
        'ideCadastro':               'idDeputado',
        'id':                        'idDeputado',

        # Valor bruto do documento
        'vlrDocumento':          'valorDocumento',

        # Valor líquido (após glosa) — separado para o KPI de glosa
        'vlrLiquido':            'valorLiquido',

        # Glosa
        'vlrGlosa':              'valorGlosa',

        # Data de emissão
        'datEmissao':            'dataDocumento',
        'dataEmissao':           'dataDocumento',

        # Fornecedor
        'txtFornecedor':         'nomeFornecedor',
        'fornecedor':            'nomeFornecedor',

        # CNPJ/CPF do fornecedor
        'txtCNPJCPF':            'cnpjCpfFornecedor',
        'cnpjCPF':               'cnpjCpfFornecedor',

        # Subcota / tipo de despesa
        'txtDescricao':          'tipoDespesa',
        'descricao':             'tipoDespesa',
    }

    df = df.rename(columns=mapeamento)

    # Consolida colunas duplicadas que surgem quando dois nomes mapeiam
    # para o mesmo destino (ex: 'datEmissao' e 'dataEmissao' no mesmo arquivo)
    if df.columns.duplicated().any():
        new_cols = {}
        for col in df.columns.unique():
            subset = df[col]
            if isinstance(subset, pd.DataFrame):
                new_cols[col] = subset.bfill(axis=1).iloc[:, 0]
            else:
                new_cols[col] = subset
        df = pd.DataFrame(new_cols)

    # Garante existência das colunas obrigatórias para não quebrar downstream
    colunas_obrigatorias = [
        'idDeputado', 'valorDocumento', 'valorLiquido', 'valorGlosa',
        'dataDocumento', 'nomeFornecedor', 'cnpjCpfFornecedor', 'tipoDespesa'
    ]
    for col in colunas_obrigatorias:
        if col not in df.columns:
            df[col] = None

    return df


def higienizar_historico(df):
    """Tipagem e limpeza de valores após a padronização de colunas."""
    if df.empty:
        return df

    df['idDeputado'] = (
        df['idDeputado'].astype(str)
        .str.replace(r'\.0$', '', regex=True)
        .str.strip()
    )

    for col_valor in ['valorDocumento', 'valorLiquido', 'valorGlosa']:
        df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0).astype(float)

    df['dataDocumento'] = pd.to_datetime(df['dataDocumento'], errors='coerce')

    df['cnpjCpfFornecedor'] = df['cnpjCpfFornecedor'].apply(limpar_documento)

    for col in ['nomeFornecedor', 'tipoDespesa']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .replace(['nan', 'None', '<NA>', ''], None)
                .where(pd.notnull(df[col]), None)
            )

    return df


def processar_historico_completo(lista_caminhos_json):
    """
    Lê todos os JSONs planos do portal da transparência, padroniza e concatena.
    Retorna um DataFrame único pronto para o join com os deputados atuais.
    """
    colunas_finais = [
        'idDeputado', 'valorDocumento', 'valorLiquido', 'valorGlosa',
        'dataDocumento', 'nomeFornecedor', 'cnpjCpfFornecedor', 'tipoDespesa'
    ]

    lista_dfs = []
    for caminho in lista_caminhos_json:
        df_ano = safe_read_json(caminho)
        if df_ano.empty:
            continue

        # JSONs planos não têm chave 'dados', mas protegemos caso apareça
        if 'dados' in df_ano.columns:
            df_ano = pd.json_normalize(df_ano['dados'])

        df_ano = padronizar_colunas(df_ano)
        df_ano = higienizar_historico(df_ano)
        lista_dfs.append(df_ano[colunas_finais])

    if not lista_dfs:
        log_progresso("⚠️ Nenhum arquivo JSON processado com sucesso.")
        return pd.DataFrame()

    df_total = pd.concat(lista_dfs, ignore_index=True)
    log_progresso(f"✅ Histórico consolidado: {len(df_total):,} registros de {len(lista_dfs)} arquivos.")
    return df_total


# =============================================================================
# CAMADA 2 — CRUZAMENTO COM DEPUTADOS ATUAIS
# =============================================================================

def gerar_join_perfil(df_historico, df_deputados_atuais):
    """
    Cruza o histórico completo com a lista de quem está no mandato hoje.
    Usa RIGHT JOIN para manter TODOS os deputados, mesmo os que não têm
    histórico de gastos nos JSONs (ex: suplentes recém-empossados).
    Requer que df_deputados_atuais já tenha a coluna 'cpf'
    (populada por camara.enriquecer_cpfs).
    """
    if df_historico.empty or df_deputados_atuais.empty:
        log_progresso("⚠️ gerar_join_perfil: um dos DataFrames está vazio.")
        return pd.DataFrame()

    df_dep = df_deputados_atuais.copy()
    df_dep['id'] = df_dep['id'].astype(str).str.strip()

    colunas_dep = ['id', 'nome', 'siglaPartido', 'siglaUf']
    if 'cpf' in df_dep.columns:
        colunas_dep.append('cpf')
    else:
        log_progresso("⚠️ Coluna 'cpf' ausente em df_deputados_atuais — join TSE não funcionará.")

    df_cruzado = pd.merge(
        df_historico,
        df_dep[colunas_dep],
        left_on='idDeputado',
        right_on='id',
        how='right'   # mantém TODOS os deputados, mesmo sem histórico
    )

    total_deputados = df_cruzado['id'].nunique()
    com_historico = df_cruzado.dropna(subset=['valorDocumento'])['id'].nunique()
    sem_historico = total_deputados - com_historico

    if sem_historico > 0:
        ids_sem = set(df_cruzado['id'].unique()) - set(
            df_cruzado.dropna(subset=['valorDocumento'])['id'].unique()
        )
        nomes_sem = df_cruzado[df_cruzado['id'].isin(ids_sem)][['nome', 'siglaPartido', 'siglaUf']].drop_duplicates()
        log_progresso(
            f"⚠️ {sem_historico} deputados SEM histórico de gastos:"
        )
        for _, r in nomes_sem.iterrows():
            log_progresso(f"   → {r['nome']} ({r['siglaPartido']}/{r['siglaUf']})")

    log_progresso(
        f"✅ Join realizado: {len(df_cruzado):,} registros "
        f"para {total_deputados} deputados "
        f"({com_historico} com histórico + {sem_historico} sem)."
    )
    return df_cruzado


# =============================================================================
# CAMADA 3 — KPIs (20 indicadores de perfil)
# =============================================================================

# Subcotas por categoria — usadas nos KPIs temáticos (Categoria 3)
_SUBCOTAS_MARKETING   = ['DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR']
_SUBCOTAS_LOGISTICA   = [
    'COMBUSTÍVEIS E LUBRIFICANTES',
    'PASSAGENS AÉREAS',
    'PASSAGENS TERRESTRES, FLUVIAIS OU LACUSTRES',
]
_SUBCOTAS_CONSULTORIA = [
    'CONSULTORIAS, PESQUISAS E TRABALHOS TÉCNICOS',
    'SERVIÇO DE SEGURANÇA PRESTADO POR EMPRESA ESPECIALIZADA',
]


def calcular_20_kpis(df_base):
    """
    Recebe o DataFrame no nível de nota fiscal (saída de gerar_join_perfil)
    e retorna um DataFrame com um deputado por linha e 20 KPIs calculados.
    Deputados sem histórico de gastos são mantidos com KPIs = 0.
    """
    log_progresso("📊 Calculando os 20 KPIs de perfil...")

    if df_base.empty:
        return pd.DataFrame()

    # Colunas de agrupamento — cpf é opcional (pode vir vazio)
    grupo = ['id', 'nome', 'siglaPartido', 'siglaUf']
    if 'cpf' in df_base.columns:
        grupo.append('cpf')

    # -------------------------------------------------------------------------
    # SEPARAR deputados sem histórico (vindos do right join)
    # Eles têm valorDocumento = NaN porque não casaram com nenhuma nota
    # -------------------------------------------------------------------------
    mask_sem_historico = df_base['valorDocumento'].isna()
    df_sem_historico = df_base[mask_sem_historico][grupo].drop_duplicates()
    df_com_historico = df_base[~mask_sem_historico].copy()

    if df_com_historico.empty:
        log_progresso("⚠️ Nenhum deputado com histórico de gastos.")
        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # BASE — agrupamento principal (apenas deputados COM dados)
    # -------------------------------------------------------------------------
    perfil = df_com_historico.groupby(grupo).agg(
        total_gasto_historico=('valorDocumento', 'sum'),
        qtd_total_notas      =('valorDocumento', 'count'),
        primeiro_registro    =('dataDocumento',  'min'),
        ultimo_registro      =('dataDocumento',  'max'),
    ).reset_index()

    # -------------------------------------------------------------------------
    # CATEGORIA 1 — FINANCEIROS
    # -------------------------------------------------------------------------

    # KPI 1 — Ticket médio por nota
    perfil['kpi_ticket_medio'] = (
        perfil['total_gasto_historico'] / perfil['qtd_total_notas']
    )

    # KPI 2 — Maior nota única emitida
    max_nota = (
        df_com_historico.groupby('id')['valorDocumento'].max()
        .rename('kpi_max_nota_unica')
    )
    perfil = perfil.merge(max_nota, on='id', how='left')

    # KPI 3 — Volatilidade (desvio padrão dos valores por nota)
    std_nota = (
        df_com_historico.groupby('id')['valorDocumento'].std()
        .rename('kpi_volatilidade_gastos')
    )
    perfil = perfil.merge(std_nota, on='id', how='left')

    # KPI 4 — Gasto no ano mais recente disponível nos dados
    ano_recente = int(df_com_historico['dataDocumento'].dt.year.max())
    gasto_recente = (
        df_com_historico[df_com_historico['dataDocumento'].dt.year == ano_recente]
        .groupby('id')['valorDocumento'].sum()
        .rename(f'kpi_gasto_{ano_recente}')
    )
    perfil = perfil.merge(gasto_recente, on='id', how='left')

    # -------------------------------------------------------------------------
    # CATEGORIA 2 — CONCENTRAÇÃO E FORNECEDORES
    # -------------------------------------------------------------------------

    gastos_por_cnpj = (
        df_com_historico.groupby(['id', 'cnpjCpfFornecedor'])['valorDocumento']
        .sum().reset_index()
    )

    # KPI 5 — Quantidade de fornecedores únicos (CNPJs distintos)
    fornecedores_unicos = (
        df_com_historico.groupby('id')['cnpjCpfFornecedor'].nunique()
        .rename('kpi_qtd_fornecedores')
    )
    perfil = perfil.merge(fornecedores_unicos, on='id', how='left')

    # KPI 6 — Concentração no fornecedor principal (% do gasto total)
    idx_max = (
        gastos_por_cnpj.groupby('id')['valorDocumento']
        .transform('max') == gastos_por_cnpj['valorDocumento']
    )
    max_cnpj = (
        gastos_por_cnpj[idx_max]
        .drop_duplicates('id')
        .rename(columns={'valorDocumento': '_max_cnpj_valor'})
    )
    perfil = perfil.merge(max_cnpj[['id', '_max_cnpj_valor']], on='id', how='left')
    perfil['kpi_concentracao_fornecedor'] = (
        perfil['_max_cnpj_valor'] / perfil['total_gasto_historico']
    )
    perfil.drop(columns=['_max_cnpj_valor'], inplace=True)

    # KPI 7 — Máximo de notas emitidas pelo mesmo CNPJ (fidelidade ao fornecedor)
    fidelidade = (
        df_com_historico.groupby(['id', 'cnpjCpfFornecedor']).size()
        .groupby(level='id').max()
        .rename('kpi_max_notas_mesmo_cnpj')
    )
    perfil = perfil.merge(fidelidade, on='id', how='left')

    # KPI 8 — Diversidade de fornecedores (notas / fornecedores únicos)
    # Quanto menor, mais concentrado em poucos fornecedores
    perfil['kpi_diversidade_fornecedor'] = (
        perfil['qtd_total_notas'] / perfil['kpi_qtd_fornecedores']
    )

    # -------------------------------------------------------------------------
    # CATEGORIA 3 — TEMÁTICOS / SUBCOTA
    # -------------------------------------------------------------------------

    tipo_upper = df_com_historico['tipoDespesa'].str.upper().fillna('')

    # KPI 9 — % gasto com marketing / divulgação parlamentar
    gasto_mkt = (
        df_com_historico[tipo_upper.isin(_SUBCOTAS_MARKETING)]
        .groupby('id')['valorDocumento'].sum()
        .rename('_gasto_mkt')
    )
    perfil = perfil.merge(gasto_mkt, on='id', how='left')
    perfil['kpi_pct_marketing'] = perfil['_gasto_mkt'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_mkt'], inplace=True)

    # KPI 10 — % gasto com logística (combustível + passagens)
    gasto_log = (
        df_com_historico[tipo_upper.isin(_SUBCOTAS_LOGISTICA)]
        .groupby('id')['valorDocumento'].sum()
        .rename('_gasto_log')
    )
    perfil = perfil.merge(gasto_log, on='id', how='left')
    perfil['kpi_pct_logistica'] = perfil['_gasto_log'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_log'], inplace=True)

    # KPI 11 — % gasto com consultoria e serviços técnicos
    gasto_cons = (
        df_com_historico[tipo_upper.isin(_SUBCOTAS_CONSULTORIA)]
        .groupby('id')['valorDocumento'].sum()
        .rename('_gasto_cons')
    )
    perfil = perfil.merge(gasto_cons, on='id', how='left')
    perfil['kpi_pct_consultoria'] = perfil['_gasto_cons'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_cons'], inplace=True)

    # KPI 12 — Subcota mais frequente (moda da tipoDespesa)
    subcota_moda = (
        df_com_historico.groupby('id')['tipoDespesa']
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        .rename('kpi_subcota_mais_frequente')
    )
    perfil = perfil.merge(subcota_moda, on='id', how='left')

    # -------------------------------------------------------------------------
    # CATEGORIA 4 — TEMPORAL E FREQUÊNCIA
    # -------------------------------------------------------------------------

    perfil['_meses_periodo'] = (
        (perfil['ultimo_registro'] - perfil['primeiro_registro'])
        .dt.days / 30.44
    ).clip(lower=1)

    # KPI 13 — Média de notas por mês ativo
    perfil['kpi_notas_por_mes'] = perfil['qtd_total_notas'] / perfil['_meses_periodo']

    # KPI 14 — Anos distintos com pelo menos um registro de gasto
    anos_ativos = (
        df_com_historico.groupby('id')['dataDocumento']
        .apply(lambda x: x.dt.year.nunique())
        .rename('kpi_anos_ativos')
    )
    perfil = perfil.merge(anos_ativos, on='id', how='left')

    # KPI 15 — % de notas emitidas em fins de semana (sábado=5, domingo=6)
    df_tmp = df_com_historico[['id', 'dataDocumento']].copy()
    df_tmp['_fds'] = df_tmp['dataDocumento'].dt.dayofweek >= 5
    notas_fds = (
        df_tmp.groupby('id')['_fds'].mean()
        .rename('kpi_pct_notas_fds')
    )
    perfil = perfil.merge(notas_fds, on='id', how='left')

    # KPI 16 — Recorrência (meses com gasto / total de meses no período)
    meses_com_gasto = (
        df_com_historico.groupby('id')['dataDocumento']
        .apply(lambda x: x.dt.to_period('M').nunique())
        .rename('_meses_com_gasto')
    )
    perfil = perfil.merge(meses_com_gasto, on='id', how='left')
    perfil['kpi_recorrencia'] = perfil['_meses_com_gasto'] / perfil['_meses_periodo']
    perfil.drop(columns=['_meses_periodo', '_meses_com_gasto'], inplace=True)

    # -------------------------------------------------------------------------
    # CATEGORIA 5 — SCORES E BENCHMARKS
    # -------------------------------------------------------------------------

    # KPI 17 — Desvio do gasto em relação à média do partido (Z-score)
    media_partido = perfil.groupby('siglaPartido')['total_gasto_historico'].transform('mean')
    std_partido   = perfil.groupby('siglaPartido')['total_gasto_historico'].transform('std').replace(0, 1)
    perfil['kpi_zscore_partido'] = (perfil['total_gasto_historico'] - media_partido) / std_partido

    # KPI 18 — Desvio do gasto em relação à média da UF (Z-score)
    media_uf = perfil.groupby('siglaUf')['total_gasto_historico'].transform('mean')
    std_uf   = perfil.groupby('siglaUf')['total_gasto_historico'].transform('std').replace(0, 1)
    perfil['kpi_zscore_uf'] = (perfil['total_gasto_historico'] - media_uf) / std_uf

    # KPI 19 — Score de risco ponderado (0 a 1)
    # Cada componente normalizado 0-1 antes de somar para evitar escalas díspares
    def norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn) if mx > mn else pd.Series(0.0, index=s.index)

    perfil['kpi_score_risco'] = (
        norm(perfil['kpi_concentracao_fornecedor']) * 0.25 +
        norm(perfil['kpi_volatilidade_gastos'])     * 0.20 +
        norm(perfil['kpi_pct_notas_fds'])           * 0.15 +
        norm(perfil['kpi_zscore_partido'].abs())     * 0.20 +
        norm(perfil['kpi_pct_consultoria'])          * 0.20
    )

    # KPI 20 — Percentil de gasto geral (0 = menor gasto, 100 = maior)
    perfil['kpi_percentil_gasto'] = perfil['total_gasto_historico'].rank(pct=True) * 100

    # -------------------------------------------------------------------------
    # REINSERIR deputados sem histórico (KPIs = 0)
    # -------------------------------------------------------------------------
    if not df_sem_historico.empty:
        log_progresso(f"📋 Reinserindo {len(df_sem_historico)} deputados sem histórico (KPIs = 0).")
        perfil = pd.concat([perfil, df_sem_historico], ignore_index=True)

    # -------------------------------------------------------------------------
    # FINALIZAÇÃO
    # -------------------------------------------------------------------------
    # fillna inteligente: strings recebem 'N/A', numéricos recebem 0
    for col in perfil.columns:
        if pd.api.types.is_string_dtype(perfil[col]) or perfil[col].dtype == 'object':
            perfil[col] = perfil[col].fillna('N/A')
        else:
            perfil[col] = perfil[col].fillna(0)
    log_progresso(f"✅ KPIs calculados para {len(perfil)} deputados.")
    return perfil


# =============================================================================
# CAMADA 4 — ENRIQUECIMENTO PATRIMONIAL (TSE) — MULTI-ANO
# =============================================================================

def calcular_inconsistencia_patrimonial_multi(dict_bens_por_ano, df_perfil_kpis):
    """
    Versão multi-ano da análise patrimonial.
    Recebe um dicionário {ano_str: DataFrame_bens} com todos os anos disponíveis
    e escolhe o melhor par (mais antigo → mais recente) para cada deputado.

    Colunas de saída:
      - patrimonio_inicio, patrimonio_fim, ano_inicio_tse, ano_fim_tse
      - crescimento_bruto_R$, crescimento_percentual_%
      - periodo_tse (ex: "2018→2024")
      - flag_risco_patrimonial
    """
    # Filtrar apenas anos com dados válidos
    anos_validos = {ano: df for ano, df in dict_bens_por_ano.items()
                    if df is not None and not df.empty}

    if len(anos_validos) < 2:
        log_progresso("⚠️ Menos de 2 anos TSE disponíveis — pulando análise patrimonial.")
        for col in ['patrimonio_inicio', 'patrimonio_fim', 'ano_inicio_tse',
                    'ano_fim_tse', 'crescimento_bruto_R$', 'crescimento_bruto',
                    'crescimento_percentual_%', 'crescimento_percentual',
                    'periodo_tse', 'flag_risco_patrimonial', 'patrimonio_2018', 'patrimonio_2022']:
            df_perfil_kpis[col] = 0
        return df_perfil_kpis

    if 'cpf' not in df_perfil_kpis.columns or (df_perfil_kpis['cpf'] == 0).all():
        log_progresso("⚠️ Coluna 'cpf' ausente ou vazia — pulando análise patrimonial.")
        for col in ['patrimonio_inicio', 'patrimonio_fim', 'ano_inicio_tse',
                    'ano_fim_tse', 'crescimento_bruto_R$', 'crescimento_bruto',
                    'crescimento_percentual_%', 'crescimento_percentual',
                    'periodo_tse', 'flag_risco_patrimonial', 'patrimonio_2018', 'patrimonio_2022']:
            df_perfil_kpis[col] = 0
        return df_perfil_kpis

    anos_ordenados = sorted(anos_validos.keys())
    log_progresso(f"🔎 Calculando evolução patrimonial multi-ano: {', '.join(anos_ordenados)}...")

    # Montar tabela longa: cpf | ano | patrimonio_total
    lista_patrim = []
    for ano, df_bens in anos_validos.items():
        patrim_ano = (
            df_bens.groupby('cpf')['valor_bem'].sum().reset_index()
            .rename(columns={'valor_bem': 'patrimonio_total'})
        )
        patrim_ano['ano'] = ano
        lista_patrim.append(patrim_ano)

    df_patrim_longo = pd.concat(lista_patrim, ignore_index=True)

    # Para cada CPF, encontrar o ano mais antigo e o mais recente com dados
    melhor_par = df_patrim_longo.groupby('cpf').agg(
        ano_inicio=('ano', 'min'),
        ano_fim=('ano', 'max'),
    ).reset_index()

    # Só considerar CPFs com pelo menos 2 anos distintos para evolução
    melhor_par = melhor_par[melhor_par['ano_inicio'] != melhor_par['ano_fim']]

    # Buscar o valor do patrimônio no ano início e ano fim
    df_inicio = df_patrim_longo.rename(columns={'patrimonio_total': 'patrimonio_inicio', 'ano': 'ano_inicio'})
    df_fim = df_patrim_longo.rename(columns={'patrimonio_total': 'patrimonio_fim', 'ano': 'ano_fim'})

    evolucao = melhor_par.merge(df_inicio, on=['cpf', 'ano_inicio'], how='left')
    evolucao = evolucao.merge(df_fim, on=['cpf', 'ano_fim'], how='left')
    evolucao = evolucao.fillna(0)

    evolucao['crescimento_bruto_R$'] = evolucao['patrimonio_fim'] - evolucao['patrimonio_inicio']
    evolucao['crescimento_bruto'] = evolucao['crescimento_bruto_R$']
    evolucao['crescimento_percentual_%'] = evolucao.apply(
        lambda r: (r['crescimento_bruto_R$'] / r['patrimonio_inicio'] * 100)
                  if r['patrimonio_inicio'] > 0 else 0,
        axis=1
    )
    evolucao['crescimento_percentual'] = evolucao['crescimento_percentual_%']
    evolucao['periodo_tse'] = evolucao['ano_inicio'] + '→' + evolucao['ano_fim']
    evolucao.rename(columns={'ano_inicio': 'ano_inicio_tse', 'ano_fim': 'ano_fim_tse'}, inplace=True)

    # Adicionar CPFs que aparecem em apenas 1 ano (sem evolução, mas com patrimônio)
    cpfs_com_evolucao = set(evolucao['cpf'].unique())
    cpfs_1_ano = df_patrim_longo[~df_patrim_longo['cpf'].isin(cpfs_com_evolucao)]
    if not cpfs_1_ano.empty:
        # Pegar o registro mais recente para cada CPF de 1 ano
        cpfs_1_ano_agg = cpfs_1_ano.sort_values('ano').drop_duplicates('cpf', keep='last')
        cpfs_1_ano_agg = cpfs_1_ano_agg.rename(columns={'patrimonio_total': 'patrimonio_fim', 'ano': 'ano_fim_tse'})
        cpfs_1_ano_agg['patrimonio_inicio'] = 0
        cpfs_1_ano_agg['ano_inicio_tse'] = 'N/A'
        cpfs_1_ano_agg['crescimento_bruto_R$'] = 0
        cpfs_1_ano_agg['crescimento_bruto'] = 0
        cpfs_1_ano_agg['crescimento_percentual_%'] = 0
        cpfs_1_ano_agg['crescimento_percentual'] = 0
        cpfs_1_ano_agg['periodo_tse'] = 'apenas_' + cpfs_1_ano_agg['ano_fim_tse']
        evolucao = pd.concat([evolucao, cpfs_1_ano_agg[evolucao.columns]], ignore_index=True)

    # Merge com perfil
    df_perfil_kpis = df_perfil_kpis.copy()
    df_perfil_kpis['cpf'] = (
        df_perfil_kpis['cpf'].astype(str)
        .str.replace(r'\D', '', regex=True)
        .str.zfill(11)
    )

    colunas_evolucao = ['cpf', 'patrimonio_inicio', 'patrimonio_fim',
                        'ano_inicio_tse', 'ano_fim_tse',
                        'crescimento_bruto_R$', 'crescimento_bruto',
                        'crescimento_percentual_%', 'crescimento_percentual',
                        'periodo_tse']
    df_enriquecido = pd.merge(df_perfil_kpis, evolucao[colunas_evolucao], on='cpf', how='left')
    df_enriquecido['flag_risco_patrimonial'] = (
        df_enriquecido['crescimento_bruto_R$'] > 3_000_000
    )

    # Retrocompatibilidade: adicionar colunas de patrimônio de 2018 e 2022 para o Power BI
    for ano in ['2018', '2022']:
        df_enriquecido[f'patrimonio_{ano}'] = 0
        if ano in anos_validos:
            mapa = anos_validos[ano].groupby('cpf')['valor_bem'].sum()
            mapa.index = mapa.index.astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)
            df_enriquecido[f'patrimonio_{ano}'] = df_enriquecido['cpf'].map(mapa).fillna(0)

    casamentos = df_enriquecido['patrimonio_fim'].gt(0).sum()
    total = len(df_enriquecido)
    log_progresso(
        f"✅ Patrimônio cruzado: {casamentos}/{total} deputados com dados TSE encontrados "
        f"(anos: {', '.join(anos_ordenados)})."
    )
    # fillna inteligente: strings recebem 'N/A', numéricos recebem 0
    for col in df_enriquecido.columns:
        if pd.api.types.is_string_dtype(df_enriquecido[col]) or df_enriquecido[col].dtype == 'object':
            df_enriquecido[col] = df_enriquecido[col].fillna('N/A')
        else:
            df_enriquecido[col] = df_enriquecido[col].fillna(0)
    return df_enriquecido