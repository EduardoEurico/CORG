import os
import pandas as pd
import numpy as np

def clean_text(text):
    if not isinstance(text, str):
        return text
    
    # Substituir os caracteres corrompidos Unicode '' ou '\ufffd' de forma segura
    for bad_char in ['\ufffd', '']:
        # Maiúsculos
        text = text.replace(f'DIVULGA{bad_char}O', 'DIVULGAÇÃO')
        text = text.replace(f'SERVI{bad_char}O', 'SERVIÇO')
        text = text.replace(f'SERVI{bad_char}OS', 'SERVIÇOS')
        text = text.replace(f'MANUTEN{bad_char}O', 'MANUTENÇÃO')
        text = text.replace(f'LOCA{bad_char}O', 'LOCAÇÃO')
        text = text.replace(f'ALIMENTA{bad_char}O', 'ALIMENTAÇÃO')
        text = text.replace(f'EMBARCA{bad_char}ES', 'EMBARCAÇÕES')
        text = text.replace(f'TC{bad_char}NICOS', 'TÉCNICOS')
        text = text.replace(f'COMUNICA{bad_char}O', 'COMUNICAÇÃO')
        text = text.replace(f'IM{bad_char}VEIS', 'IMÓVEIS')
        text = text.replace(f'IM{bad_char}VEL', 'IMÓVEL')
        text = text.replace(f'NEG{bad_char}CIOS', 'NEGÓCIOS')
        text = text.replace(f'NEG{bad_char}CIO', 'NEGÓCIO')
        text = text.replace(f'CANGU{bad_char}U', 'CANGUÇU')
        text = text.replace(f'EUN{bad_char}CIO', 'EUNÍCIO')
        text = text.replace(f'HERC{bad_char}LIO', 'HERCÍLIO')
        text = text.replace(f'A{bad_char}REA', 'AÉREA')
        text = text.replace(f'A{bad_char}REO', 'AÉREO')
        text = text.replace(f'GR{bad_char}FICA', 'GRÁFICA')
        text = text.replace(f'ROG{bad_char}RIO', 'ROGÉRIO')
        text = text.replace(f'COMBUST{bad_char}VEIS', 'COMBUSTÍVEIS')
        
        # Minúsculos / CamelCase
        text = text.replace(f'divulga{bad_char}o', 'divulgação')
        text = text.replace(f'servi{bad_char}o', 'serviço')
        text = text.replace(f'servi{bad_char}os', 'serviços')
        text = text.replace(f'manuten{bad_char}o', 'manutenção')
        text = text.replace(f'loca{bad_char}o', 'locação')
        text = text.replace(f'alimenta{bad_char}o', 'alimentação')
        text = text.replace(f'embarca{bad_char}es', 'embarcações')
        text = text.replace(f't{bad_char}cnicos', 'técnicos')
        text = text.replace(f'comunica{bad_char}o', 'comunicação')
        text = text.replace(f'im{bad_char}veis', 'imóveis')
        text = text.replace(f'im{bad_char}vel', 'imóvel')
        text = text.replace(f'neg{bad_char}cios', 'negócios')
        text = text.replace(f'neg{bad_char}cio', 'negócio')
        text = text.replace(f'cangu{bad_char}u', 'canguçu')
        text = text.replace(f'eun{bad_char}cio', 'eunício')
        text = text.replace(f'herc{bad_char}lio', 'hercílio')
        text = text.replace(f'a{bad_char}rea', 'aérea')
        text = text.replace(f'a{bad_char}reo', 'aéreo')
        text = text.replace(f'gr{bad_char}fica', 'gráfica')
        text = text.replace(f'rog{bad_char}rio', 'rogério')
        text = text.replace(f'combust{bad_char}veis', 'combustíveis')
        
        text = text.replace(f'Gest{bad_char}o', 'Gestão')
        text = text.replace(f'GEST{bad_char}O', 'GESTÃO')
        text = text.replace(f'gest{bad_char}o', 'gestão')
        
        # Eliminação genérica caso reste
        text = text.replace(bad_char, '')
        
    return text

def main():
    print("Carregando bases...")
    df_historico = pd.read_parquet('data/historico_limpo.parquet')
    df_atuais = pd.read_parquet('data/deputados_cpfs_limpos.parquet')
    
    # Padronizar idDeputado
    df_atuais['id'] = df_atuais['id'].astype(str).str.strip()
    df_historico['idDeputado'] = df_historico['idDeputado'].astype(str).str.strip()
    
    # Filtrar apenas gastos de deputados atuais
    df_cruzado = pd.merge(df_historico, df_atuais[['id', 'nome', 'siglaPartido', 'siglaUf']], left_on='idDeputado', right_on='id', how='inner')
    
    # Limpar textos nas colunas críticas
    df_cruzado['nomeFornecedor'] = df_cruzado['nomeFornecedor'].apply(clean_text)
    df_cruzado['tipoDespesa'] = df_cruzado['tipoDespesa'].apply(clean_text)
    df_cruzado['nome'] = df_cruzado['nome'].apply(clean_text)
    
    # 1. Concentração Extrema por Deputado (excluindo aéreas, correios, telefonia, e pedágios/postos genéricos)
    excluir_termos = [
        's.a.', 'sa ', 's/a', 'telef', 'claro', 'vivo', 'tim ', 'oi ', 'postal', 'correio', 
        'gol ', 'tam ', 'azul ', 'latam', 'passagem', 'concessionaria', 'ramal', 'celular func', 
        'imovel func', 'imóvel func', 'aerea', 'aérea', 'voe', 'avianca'
    ]
    
    df_filtrado_privado = df_cruzado.copy()
    # Filtrar por tamanho de CNPJ (comprimento > 10 após retirar zeros à esquerda)
    df_filtrado_privado = df_filtrado_privado[df_filtrado_privado['cnpjCpfFornecedor'].str.strip().str.replace(r'^0+', '', regex=True).str.len() > 10]
    # Filtrar termos excluídos
    df_filtrado_privado = df_filtrado_privado[~df_filtrado_privado['nomeFornecedor'].str.contains('|'.join(excluir_termos), case=False, na=False)]
    
    # Calcular total de gastos históricos de cada deputado
    total_gasto_dep = df_cruzado.groupby('idDeputado')['valorLiquido'].sum().to_dict()
    
    # Achar o principal fornecedor privado de cada deputado
    fornec_dep = df_filtrado_privado.groupby(['idDeputado', 'nome', 'siglaPartido', 'siglaUf', 'cnpjCpfFornecedor', 'nomeFornecedor', 'tipoDespesa']).agg(
        gasto_fornec=('valorLiquido', 'sum')
    ).reset_index()
    
    fornec_dep = fornec_dep.sort_values(by=['idDeputado', 'gasto_fornec'], ascending=[True, False])
    principal_fornec = fornec_dep.groupby('idDeputado').first().reset_index()
    
    principal_fornec['gasto_total_dep'] = principal_fornec['idDeputado'].map(total_gasto_dep)
    principal_fornec['pct_concentracao'] = (principal_fornec['gasto_fornec'] / principal_fornec['gasto_total_dep']) * 100
    
    # Ordenar por percentual e pegar os top
    top_concentracao_extrema = principal_fornec.sort_values(by='pct_concentracao', ascending=False).head(15)
    
    # 2. Fornecedores Compartilhados de Alta Frequência (Excluindo concessionárias, telefonia, aéreas grandes)
    df_comp_agg = df_cruzado.groupby(['cnpjCpfFornecedor', 'nomeFornecedor']).agg(
        qtd_deputados=('idDeputado', 'nunique'),
        gasto_total=('valorLiquido', 'sum')
    ).reset_index()
    
    df_shared_filtered = df_comp_agg[
        (df_comp_agg['cnpjCpfFornecedor'].str.strip().str.replace(r'^0+', '', regex=True).str.len() > 10) & 
        (~df_comp_agg['nomeFornecedor'].str.contains('S.A.|S/A|TAM|GOL|AZUL|TELEF|POSTAL|CORREIO|CLARO|VIVO|TIM|AVIANCA|CELULAR|RAMAL', case=False, na=False))
    ]
    
    top_shared = df_shared_filtered.sort_values(by='qtd_deputados', ascending=False).head(10)
    
    # 3. Top Fornecedores de Marketing (Divulgação)
    df_mkt = df_cruzado[df_cruzado['tipoDespesa'].str.contains('DIVULG', case=False, na=False)]
    df_mkt_filtrado = df_mkt[~df_mkt['nomeFornecedor'].str.contains('FACEBOOK|META SERV', case=False, na=False)]
    
    top_mkt_suppliers = df_mkt_filtrado.groupby(['cnpjCpfFornecedor', 'nomeFornecedor']).agg(
        gasto_total=('valorLiquido', 'sum'),
        qtd_notas=('valorLiquido', 'count'),
        qtd_deputados=('idDeputado', 'nunique')
    ).reset_index().sort_values(by='gasto_total', ascending=False).head(10)
    
    # 4. Top Fornecedores de Consultoria (Consultorias e Serviços Técnicos)
    df_cons = df_cruzado[df_cruzado['tipoDespesa'].str.contains('CONSULT|SEGURAN', case=False, na=False)]
    
    top_cons_suppliers = df_cons.groupby(['cnpjCpfFornecedor', 'nomeFornecedor']).agg(
        gasto_total=('valorLiquido', 'sum'),
        qtd_notas=('valorLiquido', 'count'),
        qtd_deputados=('idDeputado', 'nunique')
    ).reset_index().sort_values(by='gasto_total', ascending=False).head(10)
    
    # Salvar em arquivos JSON
    os.makedirs('data/outputs', exist_ok=True)
    
    top_concentracao_extrema.to_json('data/outputs/fornecedores_concentracao_extrema.json', orient='records', force_ascii=False, indent=2)
    top_shared.to_json('data/outputs/fornecedores_compartilhados.json', orient='records', force_ascii=False, indent=2)
    top_mkt_suppliers.to_json('data/outputs/fornecedores_marketing.json', orient='records', force_ascii=False, indent=2)
    top_cons_suppliers.to_json('data/outputs/fornecedores_consultoria.json', orient='records', force_ascii=False, indent=2)
    
    print("Sucesso! Arquivos JSON de fornecedores criados e limpos em data/outputs/")

if __name__ == '__main__':
    main()
