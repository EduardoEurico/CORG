import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
from src.extractors import camara
from src.extract_tse import carregar_todos_bens_tse
from src.transform import (
    processar_historico_completo, 
    gerar_join_perfil, 
    calcular_20_kpis, 
    calcular_inconsistencia_patrimonial_multi
)
from src.relatorio_cobertura import gerar_relatorio_cobertura
from src.utils import log_progresso

def run_pipeline():
    # 1. Configurações de Caminhos e Nomes
    DIR_RAW = 'data/raw'
    ARQUIVO_FINAL_PARQUET = 'data/outputs/perfil_final_politicos.parquet'
    ARQUIVO_FINAL_CSV = 'data/outputs/perfil_final_politicos.csv'
    
    # Save Points
    SAVE_POINT_HISTORICO = 'data/historico_limpo.parquet' 

    # Anos do TSE para buscar dados patrimoniais
    ANOS_TSE = ['2018', '2020', '2022', '2024']

    log_progresso("🚀 Iniciando Pipeline de Ciência de Dados (Corrup.ORG)...")

    # --- CAMADA 1: INGESTÃO (HISTÓRICO COM SAVE POINT) ---
    if os.path.exists(SAVE_POINT_HISTORICO):
        log_progresso("📦 Save Point detectado! Carregando histórico já processado (Modo Turbo ⚡)...")
        df_historico = pd.read_parquet(SAVE_POINT_HISTORICO)
        
    else:
        log_progresso("⏳ Save point não encontrado. Processando JSONs crus do zero (Isso vai demorar um pouco)...")
        if not os.path.exists(DIR_RAW):
            log_progresso(f"❌ Pasta {DIR_RAW} não encontrada. Baixe os JSONs primeiro.")
            return

        caminhos_jsons = [os.path.join(DIR_RAW, f) for f in os.listdir(DIR_RAW) if f.endswith('.json')]
        df_historico = processar_historico_completo(caminhos_jsons)
        
        # Cria o Save Point para a próxima vez!
        if not df_historico.empty:
            log_progresso("💾 Salvando o processamento em um Save Point (Parquet) para as próximas execuções...")
            df_historico.to_parquet(SAVE_POINT_HISTORICO, index=False)

    if df_historico.empty:
        log_progresso("❌ Erro: O histórico de despesas está vazio.")
        return
   # --- CAMADA 2: DEPUTADOS ATUAIS E ENRIQUECIMENTO ---
    SAVE_POINT_DEPUTADOS = 'data/deputados_cpfs_limpos.parquet'
    
    if os.path.exists(SAVE_POINT_DEPUTADOS):
        log_progresso("📦 Save Point detectado! Carregando deputados e CPFs do cache...")
        df_atuais = pd.read_parquet(SAVE_POINT_DEPUTADOS)
    else:
        log_progresso("⏳ Consultando API para lista de deputados atuais (Sem cache)...")
        df_atuais = camara.get_deputados_atuais()

        if not df_atuais.empty:
            df_atuais = camara.enriquecer_cpfs(df_atuais)
            # Salva para a próxima vez!
            df_atuais.to_parquet(SAVE_POINT_DEPUTADOS, index=False)

    if df_atuais.empty:
        log_progresso("❌ Erro: Não foi possível obter os deputados.")
        return

    # Cruzamento de histórico e deputados atuais (RIGHT JOIN: mantém todos os 513)
    df_cruzado = gerar_join_perfil(df_historico, df_atuais)
    if df_cruzado.empty:
        log_progresso("❌ Erro: O cruzamento (Join) resultou em uma base vazia.")
        return

    # --- CAMADA 3: INTELIGÊNCIA (20 KPIs) ---
    # Transforma milhões de notas fiscais em uma linha de inteligência por deputado
    df_perfil_kpis = calcular_20_kpis(df_cruzado)

    if df_perfil_kpis.empty:
        log_progresso("⚠️ Aviso: O dataframe de perfis gerou vazio no cálculo de KPIs.")
        return

    # --- CAMADA 4: COMPLIANCE PATRIMONIAL (TSE MULTI-ANO) ---
    log_progresso(f"🔎 Iniciando módulo de Compliance: Cruzamento TSE multi-ano ({', '.join(ANOS_TSE)})...")
    dict_bens_tse = carregar_todos_bens_tse(ANOS_TSE)
    
    # Executa a função multi-ano de patrimônio
    df_perfil_final = calcular_inconsistencia_patrimonial_multi(
        dict_bens_tse, df_perfil_kpis
    )

    # --- CAMADA 5: RELATÓRIO DE COBERTURA ---
    gerar_relatorio_cobertura(df_perfil_final)

    # --- CAMADA 6: OUTPUT (SAÍDA PARA O POWER BI) ---
    os.makedirs('data/outputs', exist_ok=True)
    df_perfil_final.to_parquet(ARQUIVO_FINAL_PARQUET, index=False)
    df_perfil_final.to_csv(ARQUIVO_FINAL_CSV, index=False, encoding='utf-8-sig')
    
    log_progresso(f"✅ Pipeline finalizado com sucesso! {len(df_perfil_final)} deputados salvos em 'data/outputs/'")

if __name__ == "__main__":
    run_pipeline()