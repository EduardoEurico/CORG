def salvar_dados_estatisticos(df, nome_tabela):
    """
    Qualquer dado de qualquer fonte (Câmara, Senado, etc) 
    passa por aqui para ser guardado no SQLite.
    """
    salvar_no_banco(df, nome_tabela) # Aquela função que já criamos