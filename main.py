def run_pipeline():
    # 1. Coleta a lista "quente" da API
    df_atuais = get_deputados_atuais()
    
    # 2. Carrega o "Cold Data" (CSV que você baixou)
    # Supondo que o arquivo se chame 'Ano-2025.csv'
    df_despesas_bruto = carregar_dados_despesas("data/Ano-2025.csv")

    if not df_atuais.empty and not df_despesas_bruto.empty:
        log_progresso("Cruzando dados: Filtrando apenas deputados atuais...")
        
        # O CSV da Câmara costuma usar 'ideDeputado' ou 'nuCarteiraParlamentar'
        # Verifique o cabeçalho do seu CSV baixado e ajuste o 'left_on'
        df_final = pd.merge(
            df_atuais, 
            df_despesas_bruto, 
            left_on='id', 
            right_on='idDeputado', # Ajuste conforme o cabeçalho do CSV
            how='inner'
        )
        
        log_progresso(f"Base pronta com {len(df_final)} registros filtrados.")
        df_final.to_parquet("data/base_trabalho.parquet")