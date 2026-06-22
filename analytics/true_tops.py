import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# Load data
df = pd.read_parquet('data/outputs/perfil_final_politicos.parquet')

# Convert columns to lists or use direct dictionary/row access
# 1. Top 10 - % Gasto em Consultoria
print("\n=== TOP 10 CONSULTORIA ===")
top_cons = df.sort_values(by='kpi_pct_consultoria', ascending=False).head(10)
for idx, row in enumerate(top_cons.iterrows(), 1):
    r = row[1]
    cresc = f"R$ {r['crescimento_bruto_R$']:,.0f}" if r['crescimento_bruto_R$'] != 0 else "R$ 0"
    gasto = f"R$ {r['total_gasto_historico']/1000:,.0f}K" if r['total_gasto_historico'] < 1000000 else f"R$ {r['total_gasto_historico']/1000000:,.1f}M"
    print(f"| {idx} | **{r['nome']}** | {r['siglaPartido']}/{r['siglaUf']} | 🔴 **{r['kpi_pct_consultoria']*100:.1f}%** | {gasto} | {cresc} |")

# 2. Top 10 - % Gasto em Marketing
print("\n=== TOP 10 MARKETING ===")
top_mkt = df.sort_values(by='kpi_pct_marketing', ascending=False).head(10)
for idx, row in enumerate(top_mkt.iterrows(), 1):
    r = row[1]
    cresc = f"R$ {r['crescimento_bruto_R$']:,.0f}" if r['crescimento_bruto_R$'] != 0 else "R$ 0"
    gasto = f"R$ {r['total_gasto_historico']/1000:,.0f}K" if r['total_gasto_historico'] < 1000000 else f"R$ {r['total_gasto_historico']/1000000:,.1f}M"
    # Note: the column name in parquet might be 'kpi_pct_marketing'
    print(f"| {idx} | **{r['nome']}** | {r['siglaPartido']}/{r['siglaUf']} | 🔴 **{r['kpi_pct_marketing']*100:.1f}%** | {gasto} | {cresc} |")

# 3. Top 10 - Z-Score Partidário
print("\n=== TOP 10 Z-SCORE PARTIDÁRIO ===")
top_zpart = df.sort_values(by='kpi_zscore_partido', ascending=False).head(10)
for idx, row in enumerate(top_zpart.iterrows(), 1):
    r = row[1]
    gasto = f"R$ {r['total_gasto_historico']/1000000:,.1f}M"
    print(f"| {idx} | {r['nome']} | {r['siglaPartido']} | {gasto} | **+{r['kpi_zscore_partido']:.2f}** | Gasta {r['kpi_zscore_partido']:.2f} desvios acima da média do {r['siglaPartido']} |")

# 4. Top 10 - Z-Score por UF
print("\n=== TOP 10 Z-SCORE UF ===")
top_zuf = df.sort_values(by='kpi_zscore_uf', ascending=False).head(10)
for idx, row in enumerate(top_zuf.iterrows(), 1):
    r = row[1]
    gasto = f"R$ {r['total_gasto_historico']/1000000:,.1f}M"
    print(f"| {idx} | {r['nome']} | {r['siglaUf']} | {gasto} | **+{r['kpi_zscore_uf']:.2f}** |")

# 5. Full state (UF) analysis
print("\n=== UF ANALYSIS (ALL STATES) ===")
# Let's aggregate by state
uf_agg = df.groupby('siglaUf').agg(
    score_risco_medio=('kpi_score_risco', 'mean'),
    concentracao_media=('kpi_concentracao_fornecedor', 'mean'),
    cresc_medio=('crescimento_bruto_R$', 'mean'),
    dep_com_dados=('crescimento_bruto_R$', lambda x: (x != 0).sum()),
    total_deputados=('id', 'count')
).reset_index()

# Find principal outlier case for growth per state
outliers_growth = {}
for uf in uf_agg['siglaUf']:
    uf_df = df[(df['siglaUf'] == uf) & (df['crescimento_bruto_R$'] > 0)]
    if not uf_df.empty:
        top_row = uf_df.sort_values(by='crescimento_bruto_R$', ascending=False).iloc[0]
        outliers_growth[uf] = f"{top_row['nome']} (R$ {top_row['crescimento_bruto_R$']/1000000:,.1f}M)"
    else:
        outliers_growth[uf] = "Sem crescimento registrado"

uf_agg['principal_caso'] = uf_agg['siglaUf'].map(outliers_growth)

print("\n--- UFs ordered by average risk score ---")
uf_agg_score = uf_agg.sort_values(by='score_risco_medio', ascending=False)
for idx, row in enumerate(uf_agg_score.itertuples(), 1):
    print(f"| {idx} | **{row.siglaUf}** | {row.score_risco_medio:.3f} | {row.total_deputados} |")

print("\n--- UFs ordered by average patrimonial growth ---")
uf_agg_cresc = uf_agg.sort_values(by='cresc_medio', ascending=False)
for idx, row in enumerate(uf_agg_cresc.itertuples(), 1):
    print(f"| {idx} | **{row.siglaUf}** | R$ {row.cresc_medio:,.0f} | {row.dep_com_dados} | {row.principal_caso} |")

print("\n--- UFs ordered by average concentration ---")
uf_agg_conc = uf_agg.sort_values(by='concentracao_media', ascending=False)
for idx, row in enumerate(uf_agg_conc.itertuples(), 1):
    print(f"| {idx} | **{row.siglaUf}** | {row.concentracao_media*100:.2f}% |")
