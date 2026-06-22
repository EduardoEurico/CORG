import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table

# Evitar problemas de encoding no Windows
sys.stdout.reconfigure(encoding='utf-8')

# 1. Carregar os Dados
caminho_parquet = 'data/outputs/perfil_final_politicos.parquet'
if not os.path.exists(caminho_parquet):
    raise FileNotFoundError(f"Erro: O arquivo {caminho_parquet} não foi encontrado. Execute o pipeline (python main.py) primeiro.")

df = pd.read_parquet(caminho_parquet)

# Normalizar percentuais (multiplicar por 100 para exibição legível)
df['kpi_pct_marketing'] = df['kpi_pct_marketing'] * 100
df['kpi_pct_consultoria'] = df['kpi_pct_consultoria'] * 100
df['kpi_pct_logistica'] = df['kpi_pct_logistica'] * 100
df['kpi_pct_notas_fds'] = df['kpi_pct_notas_fds'] * 100
df['kpi_concentracao_fornecedor'] = df['kpi_concentracao_fornecedor'] * 100

# 2. Inicializar o App Dash
app = Dash(__name__, title="Corrup.ORG - Compliance Dashboard")
app.config.suppress_callback_exceptions = True

# 3. Estilos Dark Theme Premium
DARK_STYLE = {
    'backgroundColor': '#0d1117',
    'color': '#c9d1d9',
    'fontFamily': 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    'minHeight': '100vh',
    'padding': '20px'
}

HEADER_STYLE = {
    'background': 'linear-gradient(90deg, #1f2937, #111827)',
    'padding': '20px 30px',
    'borderRadius': '12px',
    'marginBottom': '20px',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.3)',
    'border': '1px solid #30363d'
}

CARD_STYLE = {
    'backgroundColor': '#161b22',
    'padding': '20px',
    'borderRadius': '10px',
    'border': '1px solid #30363d',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
    'textAlign': 'center'
}

FILTER_PANEL_STYLE = {
    'backgroundColor': '#161b22',
    'padding': '20px',
    'borderRadius': '12px',
    'border': '1px solid #30363d',
    'marginBottom': '20px'
}

SECTION_STYLE = {
    'backgroundColor': '#161b22',
    'padding': '25px',
    'borderRadius': '12px',
    'border': '1px solid #30363d',
    'marginBottom': '20px',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
}

# Opções gerais de filtros
ufs = sorted(df['siglaUf'].unique())
partidos = sorted(df['siglaPartido'].unique())

# Layout do App
app.layout = html.Div(style=DARK_STYLE, children=[
    # Header
    html.Div(style=HEADER_STYLE, children=[
        html.H1("Corrup.ORG — compliance político", 
                style={'margin': '0', 'fontSize': '28px', 'color': '#58a6ff', 'fontWeight': '700'}),
        html.P("Painel analítico integrado de fiscalização orçamentária e compliance patrimonial da Câmara dos Deputados.",
               style={'margin': '5px 0 0 0', 'color': '#8b949e', 'fontSize': '14px'})
    ]),
    
    # Abas Principais
    dcc.Tabs(id="tabs-dashboard", value='tab-geral', style={'marginBottom': '20px'}, children=[
        dcc.Tab(label='1ª Aba: Visão Geral', value='tab-geral', 
                style={'backgroundColor': '#161b22', 'color': '#c9d1d9', 'border': '1px solid #30363d'},
                selected_style={'backgroundColor': '#1f2937', 'color': '#58a6ff', 'border': '1px solid #58a6ff', 'fontWeight': 'bold'}),
        
        dcc.Tab(label='2ª Aba: Por Partido', value='tab-partido',
                style={'backgroundColor': '#161b22', 'color': '#c9d1d9', 'border': '1px solid #30363d'},
                selected_style={'backgroundColor': '#1f2937', 'color': '#58a6ff', 'border': '1px solid #58a6ff', 'fontWeight': 'bold'}),
        
        dcc.Tab(label='3ª Aba: Por Político', value='tab-politico',
                style={'backgroundColor': '#161b22', 'color': '#c9d1d9', 'border': '1px solid #30363d'},
                selected_style={'backgroundColor': '#1f2937', 'color': '#58a6ff', 'border': '1px solid #58a6ff', 'fontWeight': 'bold'}),
        
        dcc.Tab(label='4ª Aba: Por UF', value='tab-uf',
                style={'backgroundColor': '#161b22', 'color': '#c9d1d9', 'border': '1px solid #30363d'},
                selected_style={'backgroundColor': '#1f2937', 'color': '#58a6ff', 'border': '1px solid #58a6ff', 'fontWeight': 'bold'}),
        
        dcc.Tab(label='5ª Aba: Análises Específicas', value='tab-especifica',
                style={'backgroundColor': '#161b22', 'color': '#c9d1d9', 'border': '1px solid #30363d'},
                selected_style={'backgroundColor': '#1f2937', 'color': '#58a6ff', 'border': '1px solid #58a6ff', 'fontWeight': 'bold'}),
    ]),
    
    # Conteúdo Dinâmico das Abas
    html.Div(id='tabs-content')
])


# -------------------------------------------------------------------------
# CALLBACKS & LAYOUTS DINÂMICOS
# -------------------------------------------------------------------------

@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs-dashboard', 'value')
)
def render_content(tab):
    if tab == 'tab-geral':
        # Aba 1: Visão Geral
        total_deps = len(df)
        total_gasto = df['total_gasto_historico'].sum()
        total_cresc = df['crescimento_bruto_R$'].sum()
        risco_med = df['kpi_score_risco'].mean() * 100
        
        # Gráficos da Visão Geral
        # 1. Pizza - Categorias
        df_categories = pd.DataFrame({
            'Categoria': ['Logística', 'Marketing', 'Consultorias', 'Outros'],
            'Gasto Médio (%)': [42.91, 33.56, 4.31, 19.22]
        })
        fig_pie = px.pie(df_categories, values='Gasto Médio (%)', names='Categoria', 
                         color_discrete_sequence=px.colors.qualitative.Plotly)
        fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=20, b=10))

        # 2. Distribuição do Risco
        faixas = pd.cut(df['kpi_score_risco'], bins=[-0.1, 0.15, 0.30, 1.0], labels=['Baixo (0-15%)', 'Médio (15-30%)', 'Alto (>30%)'])
        df_faixas = faixas.value_counts().reset_index()
        df_faixas.columns = ['Faixa de Risco', 'Quantidade']
        fig_risk_dist = px.bar(df_faixas, x='Faixa de Risco', y='Quantidade', color='Faixa de Risco',
                               color_discrete_sequence=['#3fb950', '#d2a8ff', '#ff7b72'])
        fig_risk_dist.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=10, r=10, t=20, b=10))

        return html.Div([
            # Cards de Resumo
            html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))', 'gap': '15px', 'marginBottom': '20px'}, children=[
                html.Div(style=CARD_STYLE, children=[
                    html.H3("Deputados Encontrados", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px'}),
                    html.Div(f"{total_deps}", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#58a6ff', 'marginTop': '5px'})
                ]),
                html.Div(style=CARD_STYLE, children=[
                    html.H3("Gasto Total Acumulado", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px'}),
                    html.Div(f"R$ {total_gasto/1000000:,.1f}M", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#d2a8ff', 'marginTop': '5px'})
                ]),
                html.Div(style=CARD_STYLE, children=[
                    html.H3("Score de Risco Médio", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px'}),
                    html.Div(f"{risco_med:.2f}%", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#ff7b72', 'marginTop': '5px'})
                ]),
                html.Div(style=CARD_STYLE, children=[
                    html.H3("Crescimento Patrimonial", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px'}),
                    html.Div(f"R$ {total_cresc/1000000:,.1f}M", style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#3fb950', 'marginTop': '5px'})
                ])
            ]),
            
            # Painel com as descrições e gráficos gerais
            html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'}, children=[
                html.Div(style=SECTION_STYLE, children=[
                    html.H3("📊 Distribuição dos Gastos da Cota", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                    html.P("Como os deputados federais gastam a verba da cota parlamentar. Viagens e publicidade representam mais de 75% dos gastos totais.", style={'color': '#8b949e', 'fontSize': '13px'}),
                    dcc.Graph(figure=fig_pie)
                ]),
                html.Div(style=SECTION_STYLE, children=[
                    html.H3("🚨 Distribuição de Faixa de Risco", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                    html.P("Segmentação dos 513 deputados por score de risco composto. Mais de 50 parlamentares encontram-se na faixa de alto risco (>30%).", style={'color': '#8b949e', 'fontSize': '13px'}),
                    dcc.Graph(figure=fig_risk_dist)
                ])
            ])
        ])
        
    elif tab == 'tab-partido':
        # Aba 2: Informações por Partido
        df_partidos = df.groupby('siglaPartido').agg(
            qtd_deputados=('id', 'count'),
            gasto_total=('total_gasto_historico', 'sum'),
            risco_medio=('kpi_score_risco', 'mean'),
            concentracao_media=('kpi_concentracao_fornecedor', 'mean'),
            cresc_medio=('crescimento_bruto_R$', 'mean')
        ).reset_index().sort_values(by='risco_medio', ascending=False)
        
        # Gráficos da aba Partido
        fig_part_risk = px.bar(df_partidos.head(10), x='siglaPartido', y='risco_medio', color='risco_medio',
                               labels={'risco_medio': 'Risco Médio', 'siglaPartido': 'Partido'},
                               color_continuous_scale=px.colors.sequential.OrRd)
        fig_part_risk.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))

        # Tabela formatada de Partidos
        data_table = df_partidos.to_dict('records')
        for r in data_table:
            r['gasto_total'] = f"R$ {r['gasto_total']/1000000:,.2f}M"
            r['risco_medio'] = f"{r['risco_medio']*100:.2f}%"
            r['concentracao_media'] = f"{r['concentracao_media']:.1f}%"
            r['cresc_medio'] = f"R$ {r['cresc_medio']/1000:,.0f}K" if r['cresc_medio'] != 0 else "R$ 0"

        return html.Div([
            html.Div(style=SECTION_STYLE, children=[
                html.H3("Partidos com Maior Score de Risco Médio (Top 10)", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                html.P("Média do score de risco dos parlamentares de cada legenda. Cidadania e PRD lideram a média.", style={'color': '#8b949e', 'fontSize': '13px'}),
                dcc.Graph(figure=fig_part_risk)
            ]),
            html.Div(style=SECTION_STYLE, children=[
                html.H3("📋 Indicadores Consolidados por Partido", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                dash_table.DataTable(
                    columns=[
                        {"name": "Partido", "id": "siglaPartido"},
                        {"name": "Integrantes (Deputados)", "id": "qtd_deputados"},
                        {"name": "Risco Médio", "id": "risco_medio"},
                        {"name": "Gasto Total", "id": "gasto_total"},
                        {"name": "Concentração Fornecedor Média", "id": "concentracao_media"},
                        {"name": "Crescimento Bens Médio", "id": "cresc_medio"}
                    ],
                    data=data_table,
                    sort_action="native",
                    page_size=10,
                    style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '10px'}
                )
            ])
        ])
        
    elif tab == 'tab-politico':
        # Aba 3: Todos os Políticos (Filtros + Dispersão + Tabela)
        return html.Div([
            # Painel de Filtros Individuais
            html.Div(style=FILTER_PANEL_STYLE, children=[
                html.H3("🔍 Filtros Dinâmicos", style={'margin': '0 0 15px 0', 'fontSize': '16px', 'color': '#c9d1d9'}),
                html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}, children=[
                    html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                        html.Label("Filtrar Estado (UF):", style={'color': '#8b949e', 'fontSize': '13px'}),
                        dcc.Dropdown(
                            id='dropdown-uf-ind',
                            options=[{'label': 'Todos', 'value': 'ALL'}] + [{'label': uf, 'value': uf} for uf in ufs],
                            value='ALL',
                            clearable=False,
                            style={'color': '#000'}
                        )
                    ]),
                    html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                        html.Label("Filtrar Partido:", style={'color': '#8b949e', 'fontSize': '13px'}),
                        dcc.Dropdown(
                            id='dropdown-partido-ind',
                            options=[{'label': 'Todos', 'value': 'ALL'}] + [{'label': part, 'value': part} for part in partidos],
                            value='ALL',
                            clearable=False,
                            style={'color': '#000'}
                        )
                    ]),
                    html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                        html.Label("Risco Mínimo:", style={'color': '#8b949e', 'fontSize': '13px'}),
                        dcc.Slider(
                            id='slider-risco-ind',
                            min=0.0, max=1.0, step=0.05, value=0.0,
                            marks={i/10: f"{int(i*10)}%" for i in range(11)}
                        )
                    ])
                ])
            ]),
            
            # Gráfico de Dispersão Cota vs Patrimônio
            html.Div(style=SECTION_STYLE, children=[
                html.H3("💸 Correlação: Gasto da Cota vs. Crescimento Patrimonial", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                html.P("Explore a relação entre o quanto de verba pública cada político utilizou e a evolução dos seus bens pessoais. Passe o mouse nos pontos para obter detalhes.", style={'color': '#8b949e', 'fontSize': '13px'}),
                dcc.Graph(id='scatter-politicos')
            ]),
            
            # Tabela de Dados Geral
            html.Div(style=SECTION_STYLE, children=[
                html.H3("📋 Dados e KPIs Individuais dos Deputados", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                dash_table.DataTable(
                    id='table-politicos-ind',
                    columns=[
                        {"name": "Nome", "id": "nome"},
                        {"name": "Partido", "id": "siglaPartido"},
                        {"name": "UF", "id": "siglaUf"},
                        {"name": "Score de Risco", "id": "kpi_score_risco"},
                        {"name": "Gasto Cota (R$)", "id": "total_gasto_historico"},
                        {"name": "Concentração (%)", "id": "kpi_concentracao_fornecedor"},
                        {"name": "Consultoria (%)", "id": "kpi_pct_consultoria"},
                        {"name": "Marketing (%)", "id": "kpi_pct_marketing"},
                        {"name": "Crescimento Bens (R$)", "id": "crescimento_bruto_R$"},
                        {"name": "Var. Patrimonial (%)", "id": "crescimento_percentual_%"}
                    ],
                    sort_action="native",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '10px'},
                    style_data_conditional=[
                        {
                            'if': {'column_id': 'kpi_score_risco', 'filter_query': '{kpi_score_risco} > 0.30'},
                            'color': '#ff7b72', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'crescimento_bruto_R$', 'filter_query': '{crescimento_bruto_R$} > 3000000'},
                            'color': '#58a6ff', 'fontWeight': 'bold'
                        }
                    ]
                )
            ])
        ])
        
    elif tab == 'tab-uf':
        # Aba 4: Por UF (Estado)
        df_ufs = df.groupby('siglaUf').agg(
            qtd_deputados=('id', 'count'),
            gasto_total=('total_gasto_historico', 'sum'),
            risco_medio=('kpi_score_risco', 'mean'),
            concentracao_media=('kpi_concentracao_fornecedor', 'mean'),
            cresc_medio=('crescimento_bruto_R$', 'mean')
        ).reset_index().sort_values(by='risco_medio', ascending=False)

        # Gráfico por Estado
        fig_uf_risk = px.bar(df_ufs.head(10), x='siglaUf', y='risco_medio', color='risco_medio',
                             labels={'risco_medio': 'Risco Médio', 'siglaUf': 'Estado (UF)'},
                             color_continuous_scale=px.colors.sequential.OrRd)
        fig_uf_risk.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))

        # Tabela formatada de Estados
        data_table_uf = df_ufs.to_dict('records')
        for r in data_table_uf:
            r['gasto_total'] = f"R$ {r['gasto_total']/1000000:,.2f}M"
            r['risco_medio'] = f"{r['risco_medio']*100:.2f}%"
            r['concentracao_media'] = f"{r['concentracao_media']:.1f}%"
            r['cresc_medio'] = f"R$ {r['cresc_medio']/1000000:,.2f}M" if r['cresc_medio'] != 0 else "R$ 0"

        return html.Div([
            html.Div(style=SECTION_STYLE, children=[
                html.H3("Estados (UF) com Maior Score de Risco Médio (Top 10)", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                html.P("Média do score de risco dos deputados agrupados por seus estados de atuação. Amapá (AP) e Maranhão (MA) lideram.", style={'color': '#8b949e', 'fontSize': '13px'}),
                dcc.Graph(figure=fig_uf_risk)
            ]),
            html.Div(style=SECTION_STYLE, children=[
                html.H3("📋 Indicadores Consolidados de Compliance por UF (Todos os 27 Estados)", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                dash_table.DataTable(
                    columns=[
                        {"name": "Estado (UF)", "id": "siglaUf"},
                        {"name": "Deputados Analisados", "id": "qtd_deputados"},
                        {"name": "Risco Médio", "id": "risco_medio"},
                        {"name": "Gasto Total", "id": "gasto_total"},
                        {"name": "Concentração Fornecedor Média", "id": "concentracao_media"},
                        {"name": "Crescimento Bens Médio", "id": "cresc_medio"}
                    ],
                    data=data_table_uf,
                    sort_action="native",
                    page_size=15,
                    style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '10px'}
                )
            ])
        ])
        
    elif tab == 'tab-especifica':
        # Aba 5: Análises Específicas (Contexto de compliance, Fornecedores Suspeitos, Crescimento Mágico)
        # Top 10 Consultoria
        top_cons = df.sort_values(by='kpi_pct_consultoria', ascending=False).head(10).to_dict('records')
        for r in top_cons:
            r['kpi_pct_consultoria'] = f"{r['kpi_pct_consultoria']:.1f}%"
            r['total_gasto_historico'] = f"R$ {r['total_gasto_historico']/1000000:,.2f}M"
            r['crescimento_bruto_R$'] = f"R$ {r['crescimento_bruto_R$']/1000:,.0f}K" if r['crescimento_bruto_R$'] != 0 else "R$ 0"

        # Top 10 Marketing
        top_mkt = df.sort_values(by='kpi_pct_marketing', ascending=False).head(10).to_dict('records')
        for r in top_mkt:
            r['kpi_pct_marketing'] = f"{r['kpi_pct_marketing']:.1f}%"
            r['total_gasto_historico'] = f"R$ {r['total_gasto_historico']/1000000:,.2f}M"
            r['crescimento_bruto_R$'] = f"R$ {r['crescimento_bruto_R$']/1000:,.0f}K" if r['crescimento_bruto_R$'] != 0 else "R$ 0"

        # Crescimento Mágico (> 3M cresc patrimonial e gasto abaixo da mediana)
        mediana_gasto = df['total_gasto_historico'].median()
        magicos = df[(df['crescimento_bruto_R$'] > 3000000) & (df['total_gasto_historico'] < mediana_gasto)].sort_values(by='crescimento_bruto_R$', ascending=False).to_dict('records')
        for r in magicos:
            r['crescimento_bruto_R$'] = f"R$ {r['crescimento_bruto_R$']/1000000:,.2f}M"
            r['total_gasto_historico'] = f"R$ {r['total_gasto_historico']/1000000:,.2f}M"
            r['kpi_score_risco'] = f"{r['kpi_score_risco']*100:.1f}%"

        return html.Div([
            html.Div(style=SECTION_STYLE, children=[
                html.H2("🔍 Análises Específicas de Compliance", style={'color': '#58a6ff', 'marginTop': '0'}),
                html.P("Esta seção traz os aprofundamentos metodológicos detalhados e cruzamentos de dados avançados.", style={'color': '#8b949e'})
            ]),
            
            # Sub-seção A: Crescimento Mágico
            html.Div(style=SECTION_STYLE, children=[
                html.H3("✨ Crescimento Patrimonial Inexplicável ('Crescimento Mágico')", style={'fontSize': '18px', 'color': '#58a6ff', 'marginTop': '0'}),
                html.P("Deputados federais que declararam evolução patrimonial superior a R$ 3 milhões ao TSE, mas mantiveram gastos de cota parlamentar abaixo da mediana da Câmara. Esse fenômeno demonstra que o enriquecimento pessoal do político não possui qualquer correlação matemática com o recebimento e uso de cotas públicas, provindo de fontes externas.", style={'color': '#8b949e', 'fontSize': '13px'}),
                dash_table.DataTable(
                    columns=[
                        {"name": "Nome", "id": "nome"},
                        {"name": "Partido", "id": "siglaPartido"},
                        {"name": "UF", "id": "siglaUf"},
                        {"name": "Crescimento de Bens", "id": "crescimento_bruto_R$"},
                        {"name": "Gasto da Cota", "id": "total_gasto_historico"},
                        {"name": "Score de Risco", "id": "kpi_score_risco"}
                    ],
                    data=magicos,
                    sort_action="native",
                    page_size=5,
                    style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '10px'}
                )
            ]),
            
            # Sub-seção B: Marketing e Consultoria
            html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'}, children=[
                html.Div(style=SECTION_STYLE, children=[
                    html.H3("📈 Top 10 — % Gasto com Marketing (Divulgação)", style={'fontSize': '16px', 'color': '#58a6ff', 'marginTop': '0'}),
                    dash_table.DataTable(
                        columns=[
                            {"name": "Nome", "id": "nome"},
                            {"name": "Partido/UF", "id": "siglaPartido"},
                            {"name": "Marketing (%)", "id": "kpi_pct_marketing"},
                            {"name": "Crescimento Bens", "id": "crescimento_bruto_R$"}
                        ],
                        data=top_mkt,
                        sort_action="native",
                        page_size=5,
                        style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                        style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '8px'}
                    )
                ]),
                html.Div(style=SECTION_STYLE, children=[
                    html.H3("📈 Top 10 — % Gasto com Consultoria", style={'fontSize': '16px', 'color': '#58a6ff', 'marginTop': '0'}),
                    dash_table.DataTable(
                        columns=[
                            {"name": "Nome", "id": "nome"},
                            {"name": "Partido/UF", "id": "siglaPartido"},
                            {"name": "Consultoria (%)", "id": "kpi_pct_consultoria"},
                            {"name": "Crescimento Bens", "id": "crescimento_bruto_R$"}
                        ],
                        data=top_cons,
                        sort_action="native",
                        page_size=5,
                        style_header={'backgroundColor': '#21262d', 'color': '#c9d1d9', 'fontWeight': 'bold'},
                        style_cell={'backgroundColor': '#161b22', 'color': '#8b949e', 'border': '1px solid #30363d', 'padding': '8px'}
                    )
                ])
            ])
        ])

# -------------------------------------------------------------------------
# CALLBACK DE ATUALIZAÇÃO DA ABA 3 (POR POLÍTICO)
# -------------------------------------------------------------------------
@app.callback(
    [Output('scatter-politicos', 'figure'),
     Output('table-politicos-ind', 'data')],
    [Input('dropdown-uf-ind', 'value'),
     Input('dropdown-partido-ind', 'value'),
     Input('slider-risco-ind', 'value')]
)
def filter_individual_politicians(uf_sel, partido_sel, risco_min):
    dff = df.copy()
    
    # Aplicar filtros
    if uf_sel != 'ALL':
        dff = dff[dff['siglaUf'] == uf_sel]
    if partido_sel != 'ALL':
        dff = dff[dff['siglaPartido'] == partido_sel]
        
    dff = dff[dff['kpi_score_risco'] >= risco_min]
    
    # 1. Gráfico de dispersão
    if not dff.empty:
        fig_scatter = px.scatter(
            dff,
            x='total_gasto_historico',
            y='crescimento_bruto_R$',
            color='kpi_score_risco',
            size='kpi_ticket_medio',
            hover_name='nome',
            hover_data={
                'siglaPartido': True,
                'siglaUf': True,
                'kpi_score_risco': ':.3f',
                'crescimento_percentual_%': ':.1f%',
                'total_gasto_historico': ':$,.2f',
                'crescimento_bruto_R$': ':$,.2f'
            },
            color_continuous_scale=px.colors.sequential.OrRd,
            labels={
                'total_gasto_historico': 'Gasto Total da Cota (R$)',
                'crescimento_bruto_R$': 'Crescimento Patrimonial (R$)',
                'kpi_score_risco': 'Score de Risco'
            }
        )
        fig_scatter.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            coloraxis_colorbar=dict(title="Risco"),
            margin=dict(l=10, r=10, t=10, b=10)
        )
    else:
        fig_scatter = go.Figure()
        fig_scatter.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')
        
    # 2. Formatar tabela
    tabela_dados = dff.to_dict('records')
    for row in tabela_dados:
        row['kpi_score_risco'] = f"{row['kpi_score_risco']:.3f}"
        row['total_gasto_historico'] = f"R$ {row['total_gasto_historico']:,.2f}"
        row['kpi_concentracao_fornecedor'] = f"{row['kpi_concentracao_fornecedor']:.1f}%"
        row['kpi_pct_consultoria'] = f"{row['kpi_pct_consultoria']:.1f}%"
        row['kpi_pct_marketing'] = f"{row['kpi_pct_marketing']:.1f}%"
        row['crescimento_bruto_R$'] = f"R$ {row['crescimento_bruto_R$']:,.2f}"
        row['crescimento_percentual_%'] = f"{row['crescimento_percentual_%']:.1f}%" if pd.notnull(row['crescimento_percentual_%']) else "N/A"
        
    return fig_scatter, tabela_dados


# Execução do Servidor local
if __name__ == '__main__':
    print("Inicializando o servidor do dashboard local...")
    print("Acesse o link: http://127.0.0.1:8050")
    app.run(debug=True, port=8050)
