import os
import sys
sys.path.insert(0, os.getcwd())

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

from src.transform import (
    processar_historico_completo, 
    gerar_join_perfil, 
    calcular_20_kpis, 
    calcular_inconsistencia_patrimonial_multi
)
from src.extract_tse import carregar_todos_bens_tse
from src.extractors import camara

def debug_with_fix():
    DIR_RAW = 'data/raw'
    ANOS_TSE = ['2018', '2020', '2022', '2024']
    SAVE_POINT_HISTORICO = 'data/historico_limpo.parquet' 
    SAVE_POINT_DEPUTADOS = 'data/deputados_cpfs_limpos.parquet'

    df_historico = pd.read_parquet(SAVE_POINT_HISTORICO)
    df_atuais = pd.read_parquet(SAVE_POINT_DEPUTADOS)
    
    # 1. Cruzamento
    df_cruzado = gerar_join_perfil(df_historico, df_atuais)

    # 2. Replicar calcular_20_kpis mas com o FIX do fillna
    print("\n--- Executando calcular_20_kpis com FIX ---")
    grupo = ['id', 'nome', 'siglaPartido', 'siglaUf']
    if 'cpf' in df_cruzado.columns:
        grupo.append('cpf')

    mask_sem_historico = df_cruzado['valorDocumento'].isna()
    df_sem_historico = df_cruzado[mask_sem_historico][grupo].drop_duplicates()
    df_com_historico = df_cruzado[~mask_sem_historico].copy()

    perfil = df_com_historico.groupby(grupo).agg(
        total_gasto_historico=('valorDocumento', 'sum'),
        qtd_total_notas      =('valorDocumento', 'count'),
        primeiro_registro    =('dataDocumento',  'min'),
        ultimo_registro      =('dataDocumento',  'max'),
    ).reset_index()

    # KPI 1 — Ticket médio
    perfil['kpi_ticket_medio'] = perfil['total_gasto_historico'] / perfil['qtd_total_notas']
    
    # KPI 2
    max_nota = df_com_historico.groupby('id')['valorDocumento'].max().rename('kpi_max_nota_unica')
    perfil = perfil.merge(max_nota, on='id', how='left')

    # KPI 3
    std_nota = df_com_historico.groupby('id')['valorDocumento'].std().rename('kpi_volatilidade_gastos')
    perfil = perfil.merge(std_nota, on='id', how='left')

    # KPI 4
    ano_recente = int(df_com_historico['dataDocumento'].dt.year.max())
    gasto_recente = (
        df_com_historico[df_com_historico['dataDocumento'].dt.year == ano_recente]
        .groupby('id')['valorDocumento'].sum()
        .rename(f'kpi_gasto_{ano_recente}')
    )
    perfil = perfil.merge(gasto_recente, on='id', how='left')

    # KPI 5
    fornecedores_unicos = df_com_historico.groupby('id')['cnpjCpfFornecedor'].nunique().rename('kpi_qtd_fornecedores')
    perfil = perfil.merge(fornecedores_unicos, on='id', how='left')

    # KPI 6
    gastos_por_cnpj = df_com_historico.groupby(['id', 'cnpjCpfFornecedor'])['valorDocumento'].sum().reset_index()
    idx_max = gastos_por_cnpj.groupby('id')['valorDocumento'].transform('max') == gastos_por_cnpj['valorDocumento']
    max_cnpj = gastos_por_cnpj[idx_max].drop_duplicates('id').rename(columns={'valorDocumento': '_max_cnpj_valor'})
    perfil = perfil.merge(max_cnpj[['id', '_max_cnpj_valor']], on='id', how='left')
    perfil['kpi_concentracao_fornecedor'] = perfil['_max_cnpj_valor'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_max_cnpj_valor'], inplace=True)

    # KPI 7
    fidelidade = df_com_historico.groupby(['id', 'cnpjCpfFornecedor']).size().groupby(level='id').max().rename('kpi_max_notas_mesmo_cnpj')
    perfil = perfil.merge(fidelidade, on='id', how='left')

    # KPI 8
    perfil['kpi_diversidade_fornecedor'] = perfil['qtd_total_notas'] / perfil['kpi_qtd_fornecedores']

    # Categoria 3
    _SUBCOTAS_MARKETING   = ['DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR']
    _SUBCOTAS_LOGISTICA   = ['COMBUSTÍVEIS E LUBRIFICANTES', 'PASSAGENS AÉREAS', 'PASSAGENS TERRESTRES, FLUVIAIS OU LACUSTRES']
    _SUBCOTAS_CONSULTORIA = ['CONSULTORIAS, PESQUISAS E TRABALHOS TÉCNICOS', 'SERVIÇO DE SEGURANÇA PRESTADO POR EMPRESA ESPECIALIZADA']
    tipo_upper = df_com_historico['tipoDespesa'].str.upper().fillna('')

    # KPI 9
    gasto_mkt = df_com_historico[tipo_upper.isin(_SUBCOTAS_MARKETING)].groupby('id')['valorDocumento'].sum().rename('_gasto_mkt')
    perfil = perfil.merge(gasto_mkt, on='id', how='left')
    perfil['kpi_pct_marketing'] = perfil['_gasto_mkt'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_mkt'], inplace=True)

    # KPI 10
    gasto_log = df_com_historico[tipo_upper.isin(_SUBCOTAS_LOGISTICA)].groupby('id')['valorDocumento'].sum().rename('_gasto_log')
    perfil = perfil.merge(gasto_log, on='id', how='left')
    perfil['kpi_pct_logistica'] = perfil['_gasto_log'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_log'], inplace=True)

    # KPI 11
    gasto_cons = df_com_historico[tipo_upper.isin(_SUBCOTAS_CONSULTORIA)].groupby('id')['valorDocumento'].sum().rename('_gasto_cons')
    perfil = perfil.merge(gasto_cons, on='id', how='left')
    perfil['kpi_pct_consultoria'] = perfil['_gasto_cons'] / perfil['total_gasto_historico']
    perfil.drop(columns=['_gasto_cons'], inplace=True)

    # KPI 12
    subcota_moda = (
        df_com_historico.groupby('id')['tipoDespesa']
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        .rename('kpi_subcota_mais_frequente')
    )
    perfil = perfil.merge(subcota_moda, on='id', how='left')

    # Outros KPIs...
    perfil['_meses_periodo'] = ((perfil['ultimo_registro'] - perfil['primeiro_registro']).dt.days / 30.44).clip(lower=1)
    perfil['kpi_notas_por_mes'] = perfil['qtd_total_notas'] / perfil['_meses_periodo']
    
    anos_ativos = df_com_historico.groupby('id')['dataDocumento'].apply(lambda x: x.dt.year.nunique()).rename('kpi_anos_ativos')
    perfil = perfil.merge(anos_ativos, on='id', how='left')

    df_tmp = df_com_historico[['id', 'dataDocumento']].copy()
    df_tmp['_fds'] = df_tmp['dataDocumento'].dt.dayofweek >= 5
    notas_fds = df_tmp.groupby('id')['_fds'].mean().rename('kpi_pct_notas_fds')
    perfil = perfil.merge(notas_fds, on='id', how='left')

    meses_com_gasto = df_com_historico.groupby('id')['dataDocumento'].apply(lambda x: x.dt.to_period('M').nunique()).rename('_meses_com_gasto')
    perfil = perfil.merge(meses_com_gasto, on='id', how='left')
    perfil['kpi_recorrencia'] = perfil['_meses_com_gasto'] / perfil['_meses_periodo']
    perfil.drop(columns=['_meses_periodo', '_meses_com_gasto'], inplace=True)

    # Scores
    media_partido = perfil.groupby('siglaPartido')['total_gasto_historico'].transform('mean')
    std_partido   = perfil.groupby('siglaPartido')['total_gasto_historico'].transform('std').replace(0, 1)
    perfil['kpi_zscore_partido'] = (perfil['total_gasto_historico'] - media_partido) / std_partido

    media_uf = perfil.groupby('siglaUf')['total_gasto_historico'].transform('mean')
    std_uf   = perfil.groupby('siglaUf')['total_gasto_historico'].transform('std').replace(0, 1)
    perfil['kpi_zscore_uf'] = (perfil['total_gasto_historico'] - media_uf) / std_uf

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
    perfil['kpi_percentil_gasto'] = perfil['total_gasto_historico'].rank(pct=True) * 100

    if not df_sem_historico.empty:
        perfil = pd.concat([perfil, df_sem_historico], ignore_index=True)

    # AQUI: APLICAR O FIX DO FILLNA
    for col in perfil.columns:
        if pd.api.types.is_string_dtype(perfil[col]) or perfil[col].dtype == 'object':
            perfil[col] = perfil[col].fillna('N/A')
        else:
            perfil[col] = perfil[col].fillna(0)

    # 3. Bens TSE
    dict_bens_tse = carregar_todos_bens_tse(ANOS_TSE)
    
    # 4. Replicar calcular_inconsistencia_patrimonial_multi com o FIX do fillna
    print("\n--- Executando calcular_inconsistencia_patrimonial_multi com FIX ---")
    anos_validos = {ano: df for ano, df in dict_bens_tse.items() if df is not None and not df.empty}
    anos_ordenados = sorted(anos_validos.keys())

    lista_patrim = []
    for ano, df_bens in anos_validos.items():
        patrim_ano = df_bens.groupby('cpf')['valor_bem'].sum().reset_index().rename(columns={'valor_bem': 'patrimonio_total'})
        patrim_ano['ano'] = ano
        lista_patrim.append(patrim_ano)
    df_patrim_longo = pd.concat(lista_patrim, ignore_index=True)

    melhor_par = df_patrim_longo.groupby('cpf').agg(ano_inicio=('ano', 'min'), ano_fim=('ano', 'max')).reset_index()
    melhor_par = melhor_par[melhor_par['ano_inicio'] != melhor_par['ano_fim']]

    df_inicio = df_patrim_longo.rename(columns={'patrimonio_total': 'patrimonio_inicio', 'ano': 'ano_inicio'})
    df_fim = df_patrim_longo.rename(columns={'patrimonio_total': 'patrimonio_fim', 'ano': 'ano_fim'})

    evolucao = melhor_par.merge(df_inicio, on=['cpf', 'ano_inicio'], how='left')
    evolucao = evolucao.merge(df_fim, on=['cpf', 'ano_fim'], how='left')
    evolucao = evolucao.fillna(0)

    evolucao['crescimento_bruto_R$'] = evolucao['patrimonio_fim'] - evolucao['patrimonio_inicio']
    evolucao['crescimento_percentual_%'] = evolucao.apply(
        lambda r: (r['crescimento_bruto_R$'] / r['patrimonio_inicio'] * 100) if r['patrimonio_inicio'] > 0 else 0,
        axis=1
    )
    evolucao['periodo_tse'] = evolucao['ano_inicio'] + '→' + evolucao['ano_fim']
    evolucao.rename(columns={'ano_inicio': 'ano_inicio_tse', 'ano_fim': 'ano_fim_tse'}, inplace=True)

    cpfs_com_evolucao = set(evolucao['cpf'].unique())
    cpfs_1_ano = df_patrim_longo[~df_patrim_longo['cpf'].isin(cpfs_com_evolucao)]
    if not cpfs_1_ano.empty:
        cpfs_1_ano_agg = cpfs_1_ano.sort_values('ano').drop_duplicates('cpf', keep='last')
        cpfs_1_ano_agg = cpfs_1_ano_agg.rename(columns={'patrimonio_total': 'patrimonio_fim', 'ano': 'ano_fim_tse'})
        cpfs_1_ano_agg['patrimonio_inicio'] = 0
        cpfs_1_ano_agg['ano_inicio_tse'] = 'N/A'
        cpfs_1_ano_agg['crescimento_bruto_R$'] = 0
        cpfs_1_ano_agg['crescimento_percentual_%'] = 0
        cpfs_1_ano_agg['periodo_tse'] = 'apenas_' + cpfs_1_ano_agg['ano_fim_tse']
        evolucao = pd.concat([evolucao, cpfs_1_ano_agg[evolucao.columns]], ignore_index=True)

    perfil['cpf'] = perfil['cpf'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)
    colunas_evolucao = ['cpf', 'patrimonio_inicio', 'patrimonio_fim', 'ano_inicio_tse', 'ano_fim_tse', 'crescimento_bruto_R$', 'crescimento_percentual_%', 'periodo_tse']
    df_enriquecido = pd.merge(perfil, evolucao[colunas_evolucao], on='cpf', how='left')
    df_enriquecido['flag_risco_patrimonial'] = df_enriquecido['crescimento_bruto_R$'] > 3_000_000

    # AQUI: APLICAR O FIX DO FILLNA
    for col in df_enriquecido.columns:
        if pd.api.types.is_string_dtype(df_enriquecido[col]) or df_enriquecido[col].dtype == 'object':
            df_enriquecido[col] = df_enriquecido[col].fillna('N/A')
        else:
            df_enriquecido[col] = df_enriquecido[col].fillna(0)

    # 5. Tentar salvar em parquet para ver se funciona!
    col = 'kpi_subcota_mais_frequente'
    print(f"\n--- Verificar tipos finais de '{col}' ---")
    print(df_enriquecido[col].apply(type).value_counts())
    
    out_path = 'data/outputs/perfil_final_politicos_teste.parquet'
    os.makedirs('data/outputs', exist_ok=True)
    try:
        df_enriquecido.to_parquet(out_path, index=False)
        print("🎉 Parquet salvo com sucesso! O erro foi resolvido!")
    except Exception as e:
        print("❌ Falha ao salvar Parquet:", e)

if __name__ == '__main__':
    debug_with_fix()
