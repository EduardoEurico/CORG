"""
Módulo de Relatório de Cobertura
Identifica lacunas de dados no perfil final e gera CSV + log detalhado.
"""
import pandas as pd
import os
from src.utils import log_progresso


def gerar_relatorio_cobertura(df_perfil_final, caminho_saida='data/outputs/relatorio_cobertura.csv'):
    """
    Analisa o perfil final e gera um relatório identificando:
    - Deputados sem histórico de gastos (KPIs = 0)
    - Deputados sem dados patrimoniais do TSE
    - Deputados com cobertura completa

    Salva o relatório como CSV e imprime resumo no console.
    """
    log_progresso("📋 Gerando relatório de cobertura de dados...")

    df = df_perfil_final.copy()

    # --- Classificar cobertura de gastos ---
    df['tem_historico_gastos'] = df['total_gasto_historico'].gt(0)

    # --- Classificar cobertura patrimonial ---
    if 'patrimonio_fim' in df.columns:
        df['tem_patrimonio_tse'] = df['patrimonio_fim'].gt(0) | df['patrimonio_inicio'].gt(0)
    elif 'patrimonio_2022' in df.columns:
        # Retrocompatibilidade com formato antigo
        df['tem_patrimonio_tse'] = df['patrimonio_2022'].gt(0) | df['patrimonio_2018'].gt(0)
    else:
        df['tem_patrimonio_tse'] = False

    # --- Classificar motivo da lacuna ---
    def classificar_lacuna(row):
        motivos = []
        if not row['tem_historico_gastos']:
            motivos.append('Sem histórico de gastos (deputado novo/suplente)')
        if not row['tem_patrimonio_tse']:
            if 'cpf' in row.index and (str(row.get('cpf', '')) == '0' or str(row.get('cpf', '')) == '00000000000'):
                motivos.append('CPF ausente/inválido')
            else:
                motivos.append('CPF não encontrado no TSE (não concorreu em eleições disponíveis)')
        return ' | '.join(motivos) if motivos else 'Cobertura completa'

    df['motivo_lacuna'] = df.apply(classificar_lacuna, axis=1)

    # --- Status de cobertura ---
    def classificar_status(row):
        if row['tem_historico_gastos'] and row['tem_patrimonio_tse']:
            return '✅ Completo'
        elif row['tem_historico_gastos'] and not row['tem_patrimonio_tse']:
            return '⚠️ Sem patrimônio TSE'
        elif not row['tem_historico_gastos'] and row['tem_patrimonio_tse']:
            return '⚠️ Sem gastos'
        else:
            return '❌ Sem dados'

    df['status_cobertura'] = df.apply(classificar_status, axis=1)

    # --- Selecionar colunas para o relatório ---
    colunas_relatorio = ['nome', 'siglaPartido', 'siglaUf']
    if 'cpf' in df.columns:
        colunas_relatorio.append('cpf')
    colunas_relatorio.extend([
        'tem_historico_gastos', 'total_gasto_historico',
        'tem_patrimonio_tse', 'status_cobertura', 'motivo_lacuna'
    ])

    # Adicionar período TSE se disponível
    if 'periodo_tse' in df.columns:
        colunas_relatorio.append('periodo_tse')

    df_relatorio = df[[c for c in colunas_relatorio if c in df.columns]].copy()
    df_relatorio = df_relatorio.sort_values(
        ['tem_historico_gastos', 'tem_patrimonio_tse', 'nome'],
        ascending=[True, True, True]
    )

    # --- Salvar CSV ---
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    df_relatorio.to_csv(caminho_saida, index=False, encoding='utf-8-sig')

    # --- Imprimir resumo ---
    total = len(df)
    completos = (df['status_cobertura'] == '✅ Completo').sum()
    sem_patrimonio = (df['status_cobertura'] == '⚠️ Sem patrimônio TSE').sum()
    sem_gastos = (df['status_cobertura'] == '⚠️ Sem gastos').sum()
    sem_dados = (df['status_cobertura'] == '❌ Sem dados').sum()

    pct_cobertura = completos / total * 100 if total > 0 else 0

    print()
    log_progresso("=" * 60)
    log_progresso("📊 RELATÓRIO DE COBERTURA DE DADOS")
    log_progresso("=" * 60)
    log_progresso(f"  Total de deputados:          {total}")
    log_progresso(f"  ✅ Cobertura completa:        {completos} ({completos/total*100:.1f}%)")
    log_progresso(f"  ⚠️  Sem patrimônio TSE:       {sem_patrimonio}")
    log_progresso(f"  ⚠️  Sem histórico de gastos:  {sem_gastos}")
    log_progresso(f"  ❌ Sem nenhum dado:           {sem_dados}")
    log_progresso(f"  📈 Taxa de cobertura total:   {pct_cobertura:.1f}%")
    log_progresso("=" * 60)

    # Listar quem está com lacuna
    lacunosos = df[df['status_cobertura'] != '✅ Completo']
    if not lacunosos.empty:
        log_progresso(f"\n  Deputados com lacunas ({len(lacunosos)}):")
        for _, row in lacunosos.iterrows():
            nome = row.get('nome', 'N/A')
            partido = row.get('siglaPartido', '')
            uf = row.get('siglaUf', '')
            status = row['status_cobertura']
            motivo = row['motivo_lacuna']
            log_progresso(f"   {status} {nome} ({partido}/{uf}) — {motivo}")

    log_progresso(f"\n  📄 Relatório salvo em: {caminho_saida}")
    print()

    return df_relatorio
