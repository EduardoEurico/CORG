# Corrup.ORG (CORG) - Pipeline de Dados e Compliance Político

O **Corrup.ORG** é um projeto de engenharia de dados e ciência de dados voltado para a análise de gastos públicos e compliance patrimonial de deputados federais. Ele realiza o cruzamento e processamento de grandes volumes de dados (notas fiscais de cota parlamentar, dados abertos da Câmara dos Deputados e dados do TSE) para gerar indicadores de risco (KPIs).

## O que o projeto faz?

O projeto funciona através de um pipeline automatizado dividido em camadas:
1. **Ingestão**: Carrega e higieniza grandes volumes de dados de gastos públicos (JSONs) dos deputados.
2. **Cruzamento de Deputados Atuais**: Conecta o histórico de despesas aos deputados atualmente no mandato usando a API da Câmara.
3. **Inteligência (20 KPIs)**: Transforma milhões de notas fiscais em métricas agregadas por deputado (ex: ticket médio, volatilidade de gastos, concentração em um único fornecedor, percentual de notas em fins de semana, score de risco geral).
4. **Compliance Patrimonial (TSE)**: Cruza os dados financeiros da Câmara com a declaração de bens dos candidatos no TSE (2018 e 2022) para identificar possíveis inconsistências na evolução patrimonial.
5. **Output**: Gera arquivos consolidados (`perfil_final_politicos.parquet` e `.csv`) com todos os dados processados, prontos para consumo por dashboards ou ferramentas de BI.

## Tecnologias Necessárias

O projeto é desenvolvido em Python e requer as seguintes bibliotecas principais:
- **Pandas**: Manipulação e análise de dados tabulares.
- **Requests**: Integração com as APIs da Câmara dos Deputados.
- **PyArrow** e **FastParquet**: Leitura e escrita otimizada no formato Parquet, essencial para lidar com o grande volume de notas fiscais de forma rápida.

## Como Rodar o Projeto (Passo a Passo)

### 1. Pré-requisitos
Certifique-se de que o Python (versão 3.8 ou superior) esteja instalado.

### 2. Instalação das Dependências
Abra o terminal na pasta raiz do projeto e instale as dependências:
```bash
pip install -r requirements.txt
```

### 3. Base de Dados (TSE)
Para que a análise patrimonial funcione completamente, o projeto requer **quatro** arquivos do TSE na pasta `data/`. Você deve baixá-los do portal de dados abertos do TSE:
- `data/bem_candidato_2018.csv` (Declaração de bens)
- `data/consulta_cand_2018.csv` (Consulta de candidatos - usado como ponte para descobrir o CPF)
- `data/bem_candidato_2022.csv` (Declaração de bens)
- `data/consulta_cand_2022.csv` (Consulta de candidatos - usado como ponte para descobrir o CPF)
*(Nota: O pipeline é resiliente. Caso não encontre esses arquivos, ele rodará perfeitamente, apenas gerando os campos patrimoniais zerados e concluindo as outras análises).*

### 4. Executando o Pipeline Principal
Rode o script principal `main.py` para executar todo o fluxo. 

**No Windows (PowerShell):**
```powershell
$env:PYTHONUTF8=1; python main.py
```
*(O `PYTHONUTF8=1` previne erros de encoding ao imprimir emojis no terminal do Windows).*

**No Linux / macOS:**
```bash
PYTHONUTF8=1 python main.py
```

Você verá o progresso etapa por etapa. Ao finalizar, ele salvará os resultados na pasta `data/outputs/`.

### 5. Validando (Testando o funcionamento)
Após a criação dos outputs pelo `main.py`, utilize o script de teste para consultar de forma rápida o topo do ranking de riscos.

```powershell
$env:PYTHONUTF8=1; python teste.py
```
Isso mostrará no seu terminal o **Top 10 de Maior Evolução Patrimonial** e o **Top 10 de Score de Risco Geral**, garantindo que tudo funcionou conforme o esperado.

## Dicionário de KPIs (Indicadores de Risco e Perfil)

Abaixo está a lista detalhada de todas as métricas (KPIs) geradas pelo sistema para cada deputado no arquivo final (`perfil_final_politicos.csv`), dividida por categorias.

### Categoria 1: Financeiros
- **`kpi_ticket_medio`**: Ticket médio por nota fiscal (Total gasto dividido pela quantidade de notas emitidas).
- **`kpi_max_nota_unica`**: O valor da maior nota fiscal única emitida pelo deputado.
- **`kpi_volatilidade_gastos`**: Desvio padrão dos valores das notas, indicando se os gastos são constantes ou possuem picos muito anormais.
- **`kpi_gasto_{ano}`**: O total de gastos do deputado no ano mais recente disponível (ex: `kpi_gasto_2026`).

### Categoria 2: Concentração e Fornecedores
- **`kpi_qtd_fornecedores`**: Quantidade total de fornecedores únicos (CNPJs distintos) contratados.
- **`kpi_concentracao_fornecedor`**: Qual a porcentagem do gasto total do deputado que foi destinado a um único fornecedor principal (varia de 0 a 1).
- **`kpi_max_notas_mesmo_cnpj`**: O número máximo de notas emitidas para um mesmo fornecedor (indicando fidelidade ou possível dependência).
- **`kpi_diversidade_fornecedor`**: Razão entre o total de notas e a quantidade de fornecedores únicos. Quanto menor, mais concentrado em poucos fornecedores.

### Categoria 3: Temáticos / Subcotas
- **`kpi_pct_marketing`**: Porcentagem do gasto total destinada à "Divulgação da Atividade Parlamentar".
- **`kpi_pct_logistica`**: Porcentagem do gasto total destinada à logística (Combustíveis, Lubrificantes, Passagens).
- **`kpi_pct_consultoria`**: Porcentagem do gasto total com serviços de consultoria, pesquisa, trabalhos técnicos e segurança privada.
- **`kpi_subcota_mais_frequente`**: A categoria de despesa (subcota) com maior frequência de uso (moda).

### Categoria 4: Temporal e Frequência
- **`kpi_notas_por_mes`**: Média de notas fiscais emitidas por cada mês ativo do mandato.
- **`kpi_anos_ativos`**: Quantidade de anos distintos em que houve pelo menos um registro de gasto.
- **`kpi_pct_notas_fds`**: Porcentagem de notas fiscais emitidas em fins de semana (sábados e domingos).
- **`kpi_recorrencia`**: Proporção de meses em que houve emissão de notas (Meses com gasto / Total de meses do período avaliado).

### Categoria 5: Scores e Benchmarks
- **`kpi_zscore_partido`**: Desvio do gasto total do deputado em relação à média dos gastos de seu próprio partido.
- **`kpi_zscore_uf`**: Desvio do gasto total do deputado em relação à média dos gastos dos deputados de seu próprio estado (UF).
- **`kpi_score_risco`**: Score ponderado geral de risco (0 a 1), baseado na concentração de fornecedores, volatilidade de gastos, uso de notas no final de semana, desvio de gasto do partido e alto uso de consultorias.
- **`kpi_percentil_gasto`**: Onde o deputado se encontra na distribuição geral de gastos (ex: 99 significa que ele gasta mais do que 99% dos outros deputados).

### Categoria 6: Evolução Patrimonial (TSE)
- **`patrimonio_inicio`** e **`patrimonio_fim`**: Valor total declarado em bens no início (ano mais antigo detectado) e no fim (ano mais recente).
- **`ano_inicio_tse`** e **`ano_fim_tse`**: Os anos que demarcam o período da análise patrimonial (ex: 2018 e 2022).
- **`crescimento_bruto_R$`** e **`crescimento_percentual_%`**: O valor exato do crescimento dos bens (em Reais e em Porcentagem).
- **`flag_risco_patrimonial`**: Alerta (Verdadeiro ou Falso) se o enriquecimento bruto for maior que R$ 3.000.000,00 no período.
- **`patrimonio_2018`** e **`patrimonio_2022`**: Campos de retrocompatibilidade garantindo os valores exatos de patrimônio nestes anos para sistemas legados como o Power BI antigo.