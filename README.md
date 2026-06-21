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