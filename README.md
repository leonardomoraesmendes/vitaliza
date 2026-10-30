# Vitaliza — Grupo 01

Business case do Módulo 2 do MBA em IA e Dados para Negócios (Inteli).

A Vitaliza é um app brasileiro de treino (fictício) com modelo freemium: 64.948 contas cadastradas e 14.753 assinantes pagantes ativos em 30/09/2026, a data de corte. O churn mensal subiu de 5,6% em 2025 para 6,6% em 2026, e a empresa não sabe por quê.

O case pede um sistema que responda **quem vai sair, em quem vale a pena agir, com qual mensagem e quanto isso rende**.

## Objetivos

| # | Pergunta de negócio | Técnica |
|---|---|---|
| 1 | Quantos assinantes ativos? Quanto perde por mês, por plano e canal? | Análise descritiva, qualidade de dados, reconstrução de estado por eventos |
| 2 | Por que o churn subiu em 2026? | Análise exploratória e diagnóstica |
| 3 | Quem são os assinantes? | Clusterização |
| 4 | Quem vai sair nos 60 dias após o corte (até 29/11/2026)? | Classificação supervisionada (logística → árvores → bagging/boosting) com validação temporal |
| 5 | Texto e imagem melhoram a previsão o bastante para pagar o custo? | Extração com IA generativa + contagem de pixels |
| 6 | Quem contatar, com qual mensagem, e quem deixar quieto? | Uplift a partir do experimento de 10/08/2026 |
| 7 | Quanto a ação rende em R$? | Avaliação por lucro, com as premissas da seção 03 do enunciado |
| 8 | O que dizer a cada pessoa? | Geração de mensagens com IA generativa |

Detalhes em [`docs/Vitaliza - Enunciado do case.pdf`](docs/).

## Estrutura

```
vitaliza-grupo-01/
├── AGENTS.md           regras do projeto para pessoas e agentes de IA
├── CLAUDE.md           aponta para AGENTS.md
├── decisoes.md         registro de decisões de tratamento e premissas
├── docs/               enunciado e dicionário de dados (PDF oficial + .md para agentes)
├── dados/              fora do repositório (ver abaixo)
│   ├── brutos/         só leitura: 12 arquivos + heatmaps_90d/
│   └── processados/    tabelas intermediárias geradas por código
├── notebooks/          exploração e análises
├── src/                código reutilizável
└── saidas/             gráficos, tabelas e apresentações
```

**Regra central: o bruto nunca é editado.** `dados/brutos/` é somente leitura no sistema de arquivos. Toda limpeza gera um arquivo novo em `dados/processados/`, por código versionado, e toda decisão vai para `decisoes.md`.

## Ambiente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Entregas

| Notebook | Pergunta | Resultado |
|---|---|---|
| [`01_pagantes_ativos`](notebooks/01_pagantes_ativos.ipynb) | Pagantes ativos no corte | 14.753 (bate com o enunciado) |
| [`02_qualidade_onboarding`](notebooks/02_qualidade_onboarding.ipynb) | Completude do `onboarding.csv` | ~30% sem objetivo na prática (8,6% nulo + 21,5% sem conteúdo) |
| [`03_qualidade_atividades`](notebooks/03_qualidade_atividades.ipynb) | Validade de distância e duração em `atividades.parquet` | 999 distâncias impossíveis pelo ritmo; 3.649 durações zero |
| [`04_consistencia_atividades`](notebooks/04_consistencia_atividades.ipynb) | `tipo` em português e inglês | 11 valores → 7 tipos; inglês só no app, desde 15/04/2026 |
| [`05_temporalidade_uso_mensal`](notebooks/05_temporalidade_uso_mensal.ipynb) | Mês sem treino em 2025 × 2026 | Ausente em 2025, zero em 2026: média cai de 265 para 118 min só pela mudança de registro |
| [`06_unicidade_atividades`](notebooks/06_unicidade_atividades.ipynb) | Treinos que chegam pelo app e pelo relógio | 9.383 pares (5.199 garmin + 4.184 apple_health), só visíveis com o fuso do garmin corrigido |

## Contribuição de John — Semana 5

Após gerar as saídas localmente, a preparação e o diagnóstico estarão em `dados/saidas/s5_john/sintese_para_relatorio.md`, com método completo em `dados/saidas/s5_john/diagnostico.md`. Esses arquivos não são versionados.
O ponto de entrada para estudo é [`notebooks/07_preparacao_diagnostico_john.ipynb`](notebooks/07_preparacao_diagnostico_john.ipynb).

Para reproduzir, na raiz: `.venv/bin/python src/preparar_diagnostico_s5.py`.
Verificação das regras: `.venv/bin/python -m unittest discover -s tests -v`.

- `dados/processados/s5_john/base_clusterizacao.csv`: 14.753 pagantes, chave `user_id` e variáveis candidatas; tratar ausências e selecionar/padronizar variáveis antes do agrupamento.
- `dados/processados/s5_john/base_assinantes_corte.csv`: contexto complementar, valores descritivos e alertas de conciliação.
- `dados/processados/s5_john/painel_churn_mensal.parquet`: exposições históricas, uso anterior e desfecho dentro da cobertura; não concatenar como se cada linha fosse uma pessoa distinta.
- `dados/saidas/s5_john/`: tabelas agregadas, quatro gráficos e dicionário das variáveis. Assim como os arquivos individuais, essas saídas são ignoradas no Git.

Os resultados não incluem clusters, previsão futura, uplift ou ROI. O PDF de leitura, quando exportado, acompanha a síntese e não substitui as tabelas e o método.

## Como montar os dados

`dados/` não é versionado. Depois de clonar:

1. Baixe o data room do case (12 arquivos e os dois zips de heatmaps).
2. Coloque os arquivos em `dados/brutos/`.
3. Extraia os zips em `dados/brutos/heatmaps_90d/`, que deve conter `2026-07-31/` (12.426 PNGs) e `2026-09-30/` (13.047 PNGs).
4. Trave a pasta: `chmod -R a-w dados/brutos`.

| Arquivo | Forma | Uma linha por | Linhas |
|---|---|---|---|
| `usuarios.csv` | Tabela | conta | 64.948 |
| `assinaturas.csv` | Tabela | assinatura (retrato de 01/10/2026) | 32.643 |
| `amizades.csv` | Tabela | relação de seguir | 113.480 |
| `campanha_ago26.csv` | Tabela | assinante sorteado | 14.120 |
| `eventos_assinatura.csv` | Log | evento | 275.565 |
| `pagamentos.csv` | Log | cobrança | 165.548 |
| `uso_mensal.csv` | Log | usuário e mês | 591.662 |
| `atividades.parquet` | Log | treino | 1.254.475 |
| `onboarding.csv` | Texto | conta | 63.929 |
| `pesquisa_saida.csv` | Texto | resposta | 643 |
| `feed_posts.csv` | Texto | post | 119.309 |
| `tickets_suporte.csv` | Texto | chamado | 4.422 |
| `heatmaps_90d/` | Imagem | assinante e data | 12.426 + 13.047 |
