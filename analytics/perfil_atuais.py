import pandas as pd
from src.utils import ler_do_banco, log_progresso

def executar_analise_perfil(df_atuais):
    """Lê do banco, faz o Join e calcula os KPIs de perfil."""
    log_progresso("🔍 Analytics: Lendo dados da Câmara no banco...")
    df_historico = ler_do_banco("SELECT * FROM gastos_camara")

    if df_historico.empty:
        log_progresso("⚠️ Histórico vazio no banco. Verifique a migração.")
        return pd.DataFrame()

    # 1. Join com Deputados Atuais
    # Usamos o 'id' da API e o 'id_politico' que salvamos no banco
    df_base = pd.merge(
        df_historico,
        df_atuais[['id', 'nome', 'siglaPartido', 'siglaUf']],
        left_on='id_politico',
        right_on='id',
        how='inner'
    )

    if df_base.empty:
        log_progresso("⚠️ Nenhum cruzamento encontrado entre histórico e deputados atuais.")
        return pd.DataFrame()

    # 2. Cálculo de KPIs
    log_progresso("📊 Calculando indicadores de desempenho...")
    
    # Agrupamento base
    perfil = df_base.groupby(['id', 'nome', 'siglaPartido', 'siglaUf']).agg(
        total_gasto=('valor', 'sum'),
        qtd_notas=('valor', 'count')
    ).reset_index()

    # --- KPI DE CONCENTRAÇÃO (CORREÇÃO DO ERRO) ---
    # Verificamos se a coluna de documento existe antes de agrupar
    col_doc = 'documento_fornecedor'
    if col_doc in df_base.columns:
        gastos_fornecedor = df_base.groupby(['id', col_doc])['valor'].sum().reset_index()
        # Pega o maior gasto individual por fornecedor para cada deputado
        max_fornecedor = gastos_fornecedor.sort_values('valor', ascending=False).drop_duplicates('id')
        
        perfil = perfil.merge(max_fornecedor[['id', 'valor']], on='id', how='left', suffixes=('', '_max_fornecedor'))
        perfil['kpi_concentracao'] = (perfil['valor_max_fornecedor'] / perfil['total_gasto']).fillna(0)
    else:
        log_progresso("⚠️ Coluna 'documento_fornecedor' ausente. KPI de concentração zerado.")
        perfil['kpi_concentracao'] = 0

    # Ranking Percentil
    perfil['kpi_percentil_gasto'] = perfil['total_gasto'].rank(pct=True) * 100

    return perfil.fillna(0)