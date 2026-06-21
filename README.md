# Corrup.ORG (CORG) - Pipeline de Dados e Compliance Político

O **Corrup.ORG** é um projeto open-source de engenharia de dados e ciência de dados voltado para a fiscalização cidadã e compliance político. Ele processa grandes volumes de dados (notas fiscais da cota parlamentar, dados abertos da Câmara dos Deputados e declarações de bens do TSE) para gerar alertas matemáticos sobre o uso indevido de verba pública e enriquecimento ilícito.

## 🎯 Objetivo do Projeto
O objetivo primário do projeto é **encontrar "agulhas no palheiro"**: criar um painel (perfil final) que calcule indicadores estatísticos (KPIs) de atenção para cada deputado federal. O sistema deve apontar de forma automática:
- Quem está concentrando grandes fortunas da cota em um único fornecedor (risco de notas frias).
- Quem está enriquecendo na calada da noite (crescimento patrimonial inexplicável entre eleições).
- Quem gasta muito mais que os colegas de partido.
- Quem está disfarçando gastos em marketing ou consultorias (rubricas com alto risco de desvios).
O resultado alimenta diretamente painéis de visualização, como o Power BI, auxiliando jornalistas e auditores.

---

## ⚙️ Passo a Passo: Como Coletamos e Processamos os Dados

O pipeline roda de ponta a ponta quando você executa o arquivo `main.py`. Ele realiza o seguinte fluxo:

1. **Ingestão de Gastos Históricos (Save Point)**: O sistema lê primeiro o arquivo `historico_limpo.parquet`, que contém milhões de notas fiscais dos deputados (anos anteriores comprimidos para ganhar velocidade).
2. **Identificação dos Deputados Atuais**: Usando a API oficial da Câmara (`dadosabertos.camara.leg.br`), o sistema coleta a lista atualizada dos 513 deputados em exercício.
3. **Enriquecimento de CPF**: Como a lista inicial não traz CPFs e o CPF é essencial para cruzar com a Receita e TSE, o sistema navega no endpoint detalhado de cada deputado na API para extrair seu CPF.
4. **Cálculo de 20 KPIs (Inteligência)**: O sistema junta os gastos históricos com os 513 deputados atuais e processa cálculos pesados. Ele higieniza categorias de gastos (logística, marketing, consultoria), extrai as datas para verificar gastos em finais de semana, soma os valores e gera métricas estatísticas como o Z-Score Partidário.
5. **Módulo de Compliance Patrimonial (TSE)**: O pipeline baixa arquivos ZIP gigantes do TSE automaticamente, extrai os CSVs de "Bens" e "Consulta de Candidatos" (anos de 2018, 2020, 2022 e 2024), identifica os bens declarados e calcula a evolução patrimonial cruzando os dados através do CPF.
6. **Relatório de Cobertura**: Ao final, o sistema imprime e salva um log verificando quantos deputados ficaram de fora da base por falta de dados na Câmara ou problemas de LGPD do TSE.
7. **Geração da Base Final**: Os dados enriquecidos com todos os indicadores são exportados em `.csv` e `.parquet` na pasta `data/outputs/`.

---

## 📂 O que cada arquivo `.py` faz?

- `main.py`: É o "cérebro" (Controlador Principal) do projeto. Ele orquestra todas as etapas do pipeline e chama as funções dos outros arquivos na ordem correta.
- `src/extractors/camara.py`: Responsável pela conexão com as APIs da Câmara dos Deputados. Ele extrai os deputados em exercício e busca meticulosamente o CPF de cada um.
- `src/extract_tse.py`: O módulo de dados eleitorais. Ele faz download de ZIPs massivos do TSE, procura os arquivos consolidados do Brasil, agrupa os bens por candidato, faz o cruzamento pelo CPF e calcula o crescimento bruto patrimonial.
- `src/transform.py`: O motor estatístico do projeto. Ele recebe os dados brutos de notas fiscais e aplica as fórmulas complexas (Pandas) para gerar os 20 KPIs de risco, perfil financeiro e anomalias de subcotas.
- `src/relatorio_cobertura.py`: Função de monitoramento que checa a qualidade da ingestão. Verifica se algum dos 513 deputados ficou sem dados de gastos ou de patrimônio e alerta o usuário no terminal.
- `src/utils.py`: Funções auxiliares (helpers), incluindo o sistema de `log_progresso` com timestamps, que mantêm a saída visual no terminal elegante e rastreável.
- `src/extract.py` e `src/database.py`: Módulos antigos e arquivos de banco de dados locais (SQLite). São mantidos no repositório para fins de retrocompatibilidade ou para migrações futuras.

---

## 🛠️ Tecnologias Necessárias
- **Pandas**: Manipulação e análise de dados tabulares.
- **Requests** e **Urllib**: Integração com APIs e download de ZIPs da Câmara e TSE.
- **PyArrow** / **FastParquet**: Leitura e escrita otimizada no formato Parquet.

### Como Rodar o Projeto
1. Certifique-se de que o Python (versão 3.8 ou superior) esteja instalado.
2. Abra o terminal na pasta raiz e instale as dependências: `pip install -r requirements.txt`
3. Rode o script principal:
**No Windows (PowerShell):**
```powershell
$env:PYTHONUTF8=1; python main.py
```
**No Linux / macOS:**
```bash
PYTHONUTF8=1 python main.py
```

---

## 📖 Dicionário de KPIs (Indicadores de Risco)
*Abaixo estão os indicadores consolidados gerados no `perfil_final_politicos.csv`:*

### Categoria 1: Financeiros
- **`kpi_ticket_medio`**: Ticket médio por nota fiscal (Total gasto / quantidade de notas).
- **`kpi_max_nota_unica`**: O valor da maior nota fiscal única emitida pelo deputado.
- **`kpi_volatilidade_gastos`**: Desvio padrão dos valores das notas (indica picos muito anormais).

### Categoria 2: Concentração e Fornecedores (Risco de Laranjas)
- **`kpi_qtd_fornecedores`**: Total de CNPJs contratados.
- **`kpi_concentracao_fornecedor`**: Porcentagem do gasto total enviada a um ÚNICO fornecedor (0 a 1).
- **`kpi_max_notas_mesmo_cnpj`**: Número máximo de notas para um mesmo fornecedor.
- **`kpi_diversidade_fornecedor`**: Razão entre total de notas e a quantidade de CNPJs únicos.

### Categoria 3: Temáticos / Subcotas
- **`kpi_pct_marketing`**: Gastos com "Divulgação da Atividade Parlamentar".
- **`kpi_pct_logistica`**: Gastos em viagens (Combustíveis, Passagens, Aluguéis de veículos).
- **`kpi_pct_consultoria`**: Consultorias técnicas e segurança privada.
- **`kpi_subcota_mais_frequente`**: A subcota mais usada repetidas vezes.

### Categoria 4: Temporal e Frequência
- **`kpi_notas_por_mes`**: Média de emissão de notas.
- **`kpi_pct_notas_fds`**: Porcentagem de notas fiscais geradas em fins de semana.

### Categoria 5: Scores e Benchmarks
- **`kpi_zscore_partido`**: Z-Score apontando se ele gasta de forma obscena comparado aos pares de seu próprio partido.
- **`kpi_zscore_uf`**: Z-Score do gasto em relação aos conterrâneos de estado.
- **`kpi_score_risco`**: **Score Geral de Atenção (0 a 1)**.

### Categoria 6: Evolução Patrimonial (TSE)
- **`crescimento_bruto_R$`** e **`crescimento_percentual_%`**: O valor exato do crescimento dos bens (em Reais e em Porcentagem).
- **`flag_risco_patrimonial`**: Alerta crítico se o enriquecimento foi maior que R$ 3 milhões no mandato.
- **`patrimonio_2018`** e **`patrimonio_2022`**: Campos de retrocompatibilidade para dashboards legados.