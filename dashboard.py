import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table

# 1. Carregar os Dados
caminho_parquet = 'data/outputs/perfil_final_politicos.parquet'
if not os.path.exists(caminho_parquet):
    raise FileNotFoundError(f"Erro: O arquivo {caminho_parquet} não foi encontrado. Execute o pipeline (python main.py) primeiro.")

df = pd.read_parquet(caminho_parquet)

# Limpezas e preparações rápidas para exibição
df['kpi_pct_marketing'] = df['kpi_pct_marketing'] * 100
df['kpi_pct_consultoria'] = df['kpi_pct_consultoria'] * 100
df['kpi_pct_logistica'] = df['kpi_pct_logistica'] * 100
df['kpi_pct_notas_fds'] = df['kpi_pct_notas_fds'] * 100
df['kpi_concentracao_fornecedor'] = df['kpi_concentracao_fornecedor'] * 100

# 2. Inicializar o App Dash
app = Dash(__name__, title="Corrup.ORG - Dashboard Compliance")

# 3. Estilos Customizados (Visual Premium & Dark Mode)
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

# Opções de Filtro
ufs = sorted(df['siglaUf'].unique())
partidos = sorted(df['siglaPartido'].unique())

# Layout do App
app.layout = html.Div(style=DARK_STYLE, children=[
    # Header
    html.Div(style=HEADER_STYLE, children=[
        html.H1("📊 Corrup.ORG — Dashboard de Compliance Político", 
                style={'margin': '0', 'fontSize': '28px', 'color': '#58a6ff', 'fontWeight': '700'}),
        html.P("Exploração interativa de padrões de risco, gastos da cota parlamentar e evolução patrimonial dos deputados atuais.",
               style={'margin': '5px 0 0 0', 'color': '#8b949e', 'fontSize': '14px'})
    ]),
    
    # Grid de KPIs
    html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))', 'gap': '15px', 'marginBottom': '20px'}, children=[
        html.Div(style=CARD_STYLE, children=[
            html.H3("Deputados Analisados", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px', 'textTransform': 'uppercase'}),
            html.Div(id='kpi-deputados', style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#58a6ff', 'marginTop': '5px'})
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.H3("Score de Risco Médio", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px', 'textTransform': 'uppercase'}),
            html.Div(id='kpi-risco-medio', style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#ff7b72', 'marginTop': '5px'})
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.H3("Crescimento Patrimonial Total", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px', 'textTransform': 'uppercase'}),
            html.Div(id='kpi-cresc-total', style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#3fb950', 'marginTop': '5px'})
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.H3("Gasto Total Acumulado", style={'margin': '0', 'color': '#8b949e', 'fontSize': '14px', 'textTransform': 'uppercase'}),
            html.Div(id='kpi-gasto-total', style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#d2a8ff', 'marginTop': '5px'})
        ])
    ]),
    
    # Painel de Filtros
    html.Div(style=FILTER_PANEL_STYLE, children=[
        html.H3("🔍 Filtros de Exploração", style={'margin': '0 0 15px 0', 'fontSize': '16px', 'color': '#c9d1d9'}),
        html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}, children=[
            # Filtro UF
            html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                html.Label("Estado (UF):", style={'color': '#8b949e', 'fontWeight': '500', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Dropdown(
                    id='dropdown-uf',
                    options=[{'label': 'Todos os Estados', 'value': 'ALL'}] + [{'label': uf, 'value': uf} for uf in ufs],
                    value='ALL',
                    clearable=False,
                    style={'backgroundColor': '#0d1117', 'color': '#0d1117'}
                )
            ]),
            # Filtro Partido
            html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                html.Label("Partido:", style={'color': '#8b949e', 'fontWeight': '500', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Dropdown(
                    id='dropdown-partido',
                    options=[{'label': 'Todos os Partidos', 'value': 'ALL'}] + [{'label': partido, 'value': partido} for partido in partidos],
                    value='ALL',
                    clearable=False,
                    style={'backgroundColor': '#0d1117', 'color': '#0d1117'}
                )
            ]),
            # Filtro Faixa de Risco
            html.Div(style={'flex': '1', 'minWidth': '200px'}, children=[
                html.Label("Score de Risco Mínimo:", style={'color': '#8b949e', 'fontWeight': '500', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Slider(
                    id='slider-risco',
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    value=0.0,
                    marks={i/10: f"{int(i*10)}%" for i in range(11)},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ])
        ])
    ]),
    
    # Seção de Gráficos
    html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginBottom': '20px'}, children=[
        # Dispersão
        html.Div(style={'backgroundColor': '#161b22', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #30363d'}, children=[
            html.H3("💸 Relação: Gasto da Cota vs. Enriquecimento Patrimonial", style={'fontSize': '16px', 'color': '#c9d1d9', 'marginTop': '0'}),
            dcc.Graph(id='scatter-plot')
        ]),
        # Distribuição de Gastos ou Ranking
        html.Div(style={'backgroundColor': '#161b22', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #30363d'}, children=[
            html.H3("🚨 Distribuição de Risco vs. Gastos com Consultoria/Marketing", style={'fontSize': '16px', 'color': '#c9d1d9', 'marginTop': '0'}),
            dcc.Graph(id='bar-plot')
        ])
    ]),
    
    # Tabela de Dados Integrada
    html.Div(style={'backgroundColor': '#161b22', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #30363d'}, children=[
        html.H3("📋 Ficha e KPIs de Deputados (Dados Filtrados)", style={'fontSize': '16px', 'color': '#c9d1d9', 'marginTop': '0'}),
        html.P("Ordene, filtre ou navegue diretamente nos dados de compliance dos parlamentares.", style={'color': '#8b949e', 'fontSize': '13px', 'marginBottom': '15px'}),
        dash_table.DataTable(
            id='deputados-table',
            columns=[
                {"name": "Nome", "id": "nome", "sortable": True},
                {"name": "Partido", "id": "siglaPartido", "sortable": True},
                {"name": "UF", "id": "siglaUf", "sortable": True},
                {"name": "Score de Risco", "id": "kpi_score_risco", "sortable": True},
                {"name": "Gasto Cota (R$)", "id": "total_gasto_historico", "sortable": True},
                {"name": "Concentração (%)", "id": "kpi_concentracao_fornecedor", "sortable": True},
                {"name": "Consultoria (%)", "id": "kpi_pct_consultoria", "sortable": True},
                {"name": "Marketing (%)", "id": "kpi_pct_marketing", "sortable": True},
                {"name": "Crescimento Bens (R$)", "id": "crescimento_bruto_R$", "sortable": True},
                {"name": "Var. Patrimonial (%)", "id": "crescimento_percentual_%", "sortable": True}
            ],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': '#21262d',
                'color': '#c9d1d9',
                'fontWeight': 'bold',
                'border': '1px solid #30363d'
            },
            style_cell={
                'backgroundColor': '#161b22',
                'color': '#8b949e',
                'border': '1px solid #30363d',
                'padding': '10px',
                'fontSize': '13px',
                'textAlign': 'left'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'kpi_score_risco', 'filter_query': '{kpi_score_risco} > 0.30'},
                    'color': '#ff7b72',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'column_id': 'crescimento_bruto_R$', 'filter_query': '{crescimento_bruto_R$} > 3000000'},
                    'color': '#58a6ff',
                    'fontWeight': 'bold'
                }
            ]
        )
    ])
])

# 4. Callbacks de Atualização Dinâmica
@app.callback(
    [Output('kpi-deputados', 'children'),
     Output('kpi-risco-medio', 'children'),
     Output('kpi-cresc-total', 'children'),
     Output('kpi-gasto-total', 'children'),
     Output('scatter-plot', 'figure'),
     Output('bar-plot', 'figure'),
     Output('deputados-table', 'data')],
    [Input('dropdown-uf', 'value'),
     Input('dropdown-partido', 'value'),
     Input('slider-risco', 'value')]
)
def atualizar_dashboard(uf_sel, partido_sel, risco_min):
    # Filtrar dados com base nos inputs
    dff = df.copy()
    
    if uf_sel != 'ALL':
        dff = dff[dff['siglaUf'] == uf_sel]
    if partido_sel != 'ALL':
        dff = dff[dff['siglaPartido'] == partido_sel]
    
    dff = dff[dff['kpi_score_risco'] >= risco_min]
    
    # Calcular KPIs do topo
    total_deps = len(dff)
    risco_med = f"{dff['kpi_score_risco'].mean() * 100:.1f}%" if total_deps > 0 else "0.0%"
    cresc_tot = f"R$ {dff['crescimento_bruto_R$'].sum()/1000000:,.1f}M" if total_deps > 0 else "R$ 0M"
    gasto_tot = f"R$ {dff['total_gasto_historico'].sum()/1000000:,.1f}M" if total_deps > 0 else "R$ 0M"
    
    # 1. Criar Gráfico de Dispersão (Plotly)
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

    # 2. Criar Gráfico de Barras Dinâmico (KPIs)
    if not dff.empty:
        # Top 10 mais arriscados da seleção atual
        dff_top = dff.sort_values(by='kpi_score_risco', ascending=False).head(10)
        fig_bar = px.bar(
            dff_top,
            x='nome',
            y='kpi_score_risco',
            color='kpi_pct_consultoria',
            hover_data=['siglaPartido', 'siglaUf', 'kpi_pct_marketing'],
            labels={
                'kpi_score_risco': 'Score de Risco (0 a 1)',
                'nome': 'Deputado',
                'kpi_pct_consultoria': '% Consultoria'
            },
            color_continuous_scale=px.colors.sequential.Viridis,
        )
        fig_bar.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis={'categoryorder': 'total descending', 'title': ''},
            margin=dict(l=10, r=10, t=10, b=10)
        )
    else:
        fig_bar = go.Figure()
        fig_bar.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')

    # 3. Formatar dados da tabela
    tabela_dados = dff.to_dict('records')
    # Arredondamentos finos para legibilidade na tabela
    for row in tabela_dados:
        row['kpi_score_risco'] = f"{row['kpi_score_risco']:.3f}"
        row['total_gasto_historico'] = f"R$ {row['total_gasto_historico']:,.2f}"
        row['kpi_concentracao_fornecedor'] = f"{row['kpi_concentracao_fornecedor']:.1f}%"
        row['kpi_pct_consultoria'] = f"{row['kpi_pct_consultoria']:.1f}%"
        row['kpi_pct_marketing'] = f"{row['kpi_pct_marketing']:.1f}%"
        row['crescimento_bruto_R$'] = f"R$ {row['crescimento_bruto_R$']:,.2f}"
        row['crescimento_percentual_%'] = f"{row['crescimento_percentual_%']:.1f}%" if pd.notnull(row['crescimento_percentual_%']) else "N/A"

    return total_deps, risco_med, cresc_tot, gasto_tot, fig_scatter, fig_bar, tabela_dados

# Execução do Servidor local
if __name__ == '__main__':
    print("🛸 Inicializando o servidor do dashboard local...")
    print("👉 Acesse o link: http://127.0.0.1:8050")
    app.run_server(debug=True, port=8050)
