# Conferência das personas de Kiril — revisão técnica

**Trabalho original de personas e das duas conferências: Kiril + Claude — Grupo 01.**
Nova reprodução e revisão: John Neto (apoio de Codex), em 07/11/2026.
Este relatório reúne as duas conferências em uma versão pública sem dados individuais;
não substitui a aprovação de Kiril e do grupo.

## Resultado e alcance

O novo recálculo, independente das funções de preparação, apresentou concordância nas 17 métricas
dos 108 registros distintos identificados nos PDFs de Kiril, dentro das tolerâncias declaradas.
O pipeline de Leonardo também foi reproduzido, gerando os quatro grupos com os mesmos tamanhos.
O resultado fornece evidência de consistência nos casos examinados; não certifica toda a base
ou a interpretação das personas. Os conferidores de Kiril estão publicados em `src/conferir_12_registros_s5.py`
e `src/conferir_96_registros_s5.py`, com o recálculo em `src/conferencia_comum_s5.py`.

| Conferência | Pessoas por segmento | Pessoas | Comparações | Concordantes |
|---|---:|---:|---:|---:|
| PDF de 12 registros, 06/11 | 3 | 12 | 204 | 204 |
| PDF de 96 registros, 07/11 | 24 | 96 | 1.632 | 1.632 |
| Total, sem sobreposição | 27 | 108 | 1.836 | 1.836 |

As listas foram extraídas dos próprios PDFs e confrontadas com a população reproduzida.
Foram verificados unicidade, ausência de sobreposição e quantidade por segmento.
As seeds 42 e 96 e os papéis de seleção A/B/C são descritos por Kiril. Os conferidores publicados em `src/`
reproduzem os sorteios: reexecutados sobre `segmentos.csv`, selecionaram exatamente os mesmos 12 e 96 registros
(mesmos `user_id` e mesmos papéis) e deram 96/96 registros com 17/17 métricas. O sorteio é por quotas e depende da
ordem das linhas de `segmentos.csv`, da ordem das chamadas ao gerador aleatório e da versão do pandas.

## Correção da conclusão estatística

Foram removidas as afirmações de limite populacional de erro de 25% e 3%, com 95% de confiança.
Não encontrar divergências finais nos casos examinados não autoriza aplicar automaticamente
a regra de três à população. O desenho mistura quotas por segmento e condições de elegibilidade;
não foram demonstradas probabilidades de inclusão nem um estimador adequado a esse desenho.
Estratificar uma amostra não é, em si, um erro: a inferência exige incorporar seu plano de seleção.
Referência: [Statistics Canada — amostragem probabilística](https://www150.statcan.gc.ca/n1/edu/power-pouvoir/ch13/prob/5214899-eng.htm).

Não se calculou limite populacional nesta revisão. A cobertura foi de aproximadamente 0,73%
dos pagantes, com foco em conferir regras e casos selecionados. As 17 métricas da mesma pessoa
não são tratadas como 17 observações independentes para inferência estatística.

## Base, ponte e qualidade

Preparação regenerada a partir dos brutos, sem alterar os originais. Onze arquivos usados na
preparação tiveram hashes conferidos antes/depois; a nova revisão também preservou os hashes
dos 12 arquivos tabulares disponíveis. Saídas detalhadas ficam exclusivamente em `dados/`.

| Fonte/etapa | Linhas restantes |
|---|---:|
| Usuários brutos | 64.948 |
| Usuários sem contas de teste, e-mail normalizado | 64.888 |
| Assinaturas brutas | 32.643 |
| Assinaturas sem contas de teste | 32.583 |
| Ativas no retrato, antes de excluir testes | 14.813 |
| Pagantes no corte, reconstruídos por eventos e conciliados ao retrato | 14.753 |
| Após transformação para clusterização | 14.753 |
| Com um único segmento | 14.753 |
| Atividades brutas | 1.254.475 |
| Atividades após retirar 9.383 cópias do app | 1.245.092 |
| Atividades com duração válida | 1.241.461 |
| Pagamentos aprovados, sem testes, antes do limite | 161.930 |
| Pagamentos após deduplicação de conta + instante + valor | 159.989 |
| Posts anteriores ao limite e sem testes | 119.187 |
| Relações de seguir anteriores ao limite e sem testes | 113.207 |

| Dimensão | Achado reproduzido | Tratamento/limite |
|---|---|---|
| Completude | 177 pagantes sem recência; 759 sem treino em 90 dias | Ausência estrutural; manter no arquivo descritivo |
| Validade | 3.649 durações inválidas antes de deduplicar; sexo em 6 grafias e sistema em 5 | Volume só com duração positiva; normalização explícita das categorias descritivas |
| Consistência | 5 divergências entre estado conhecido de renovação por eventos e retrato; 1.112 sem estado inicial conhecido nos eventos | Preservar fontes separadas; tabela de personas identifica o retrato de 01/10 |
| Unicidade | 9.383 cópias de treino; 1.941 cobranças aprovadas duplicadas | Conferência aplica as regras do grupo; 14.753 chaves únicas na saída |
| Temporalidade | 207.954 treinos Garmin com ajuste de fuso; 1.938 contas com janela de tendência incompleta | Garmin −3h; corte exclusivo em 01/10; neutralização da tendência apenas na matriz |

As auditorias de cinco dimensões e suas contagens completas foram regeneradas pelo código de
preparação em `dados/processados/s5_john/` e `dados/saidas/s5_john/`. Não se alterou regra do bruto.

## Arquivo descritivo e matriz do agrupamento

Confirmado em `src/clusterizacao_s5.py`, função `preparar`, no commit de Leonardo indicado abaixo:

| Variável | Valor guardado no arquivo descritivo | Valor na matriz, antes de log/corte/padronização | Pessoas |
|---|---|---|---:|
| Tendência com exposição inferior a 60 dias | Diferença original dos dois períodos de 30 dias | Zero, como neutralização da janela incompleta | 1.938 |
| Recência sem treino válido em 2026 | Ausente | 273 dias, limite inferior convencional | 177 |
| Minutos por treino sem treino em 90 dias | Ausente | Mediana da variável | 759 |
| Proporção de vídeo sem treino em 90 dias | Ausente | Mediana da variável | 759 |

O relatório original de 12 registros descreve três divergências iniciais de tendência;
o de 96 descreve quatro de recência. Esses episódios são relatos de Kiril, não logs recuperados
por esta revisão. As diferenças entre representações foram confirmadas no código e nas bases.
Não se afirma que todo o pipeline está livre de erros.

## As 17 métricas e tolerâncias

| Métrica | Tolerância absoluta |
|---|---:|
| Dias ativos em 90 dias | Exata |
| Média de minutos por treino em 90 dias | 0,000001 |
| Proporção de vídeo em 90 dias | 0,000001 |
| Recência em dias | 0,01 dia; ausência deve coincidir |
| Variação de treinos, últimos 30 dias menos os 30 anteriores | Exata |
| Indicador de tendência incompleta | Exata |
| Exposição em dias, máximo 90 | Exata |
| Dias ativos / exposição | 0,000001 |
| Posts em 90 dias | Exata |
| Seguidores antes do limite | Exata |
| Tickets abertos em 90 dias | Exata |
| Tempo de assinatura | 1 dia |
| Plano | Texto exato |
| Canal de cobrança | Texto exato |
| Renovação desligada no retrato | Exata |
| Proxy líquida mensal equivalente | R$ 0,001 |
| Nível no onboarding | Texto exato ou ausência coincidente |

Nas 17 linhas acima, cada métrica teve 12/12 e 96/96 concordâncias nas respectivas amostras.
Tempo de assinatura: na amostra de 96, 86 casos diferiram em um dia e 10 não diferiram;
na de 12, 11 diferiram em um dia e um não diferiu. O recálculo usa a data de início do retrato;
o pipeline usa o instante reconstruído. A concordância inclui essa tolerância e não significa
igualdade literal em todas as células. As demais tolerâncias são as documentadas por Kiril.

Regras: janela de 90 dias [03/07, 01/10); duas janelas de 30 dias [01/09, 01/10) e [02/08, 01/09);
UTC com sufixo Z convertido para Brasília; Garmin sem sufixo ajustado em −3h; treino válido
com duração positiva; cópia do app com tipo original e duração iguais e início a até 5 minutos
do relógio. Vídeo = força/strength, funcional, HIIT e yoga. Valores ausentes são comparados
como ausência, sem aplicar a imputação do K-means ao arquivo descritivo.

## Reexecução da clusterização

Mesmo código e versões, oito variáveis, k=4, seed 42, `n_init=50` no ajuste final.
Varredura k=2 a 8, com 20 subamostras de 80% por k, mantendo a sequência do gerador aleatório.
Padronização, log1p e cortes nos percentis 1/99 foram os do código de Leonardo.

| Indicador de k=4 | Reprodução |
|---|---:|
| Silhueta em amostra de 5.000 | 0,168918 |
| ARI médio de reamostragem | 0,990136 |
| Menor ARI nas 20 reamostragens | 0,983873 |
| ARI entre K-means e Ward em amostra de 6.000 | 0,629524 |

Há evidência de estabilidade no procedimento de reamostragem reproduzido. A baixa silhueta
limita a separação dos grupos; nenhuma dessas medidas demonstra estabilidade temporal,
causalidade ou validade das interpretações autorais. A clusterização continua dependente
da revisão do PR #5; esta entrega não incorpora nem aprova esse PR automaticamente.

## Correções adicionais e validações parciais

- Proxy líquida total reproduzida: R$ 405.539,32. Não é receita contábil nem previsão de perda.
- Desligados por segmento: 1.599, 329, 228 e 94, total 2.250.
- Adormecidos desligados: R$ 34.837,16 mensais equivalentes; 1.577 dos 1.599 no anual.
- Cenário de aniversários 01/10 a 29/11: 439 pessoas, R$ 9.539,30. O rascunho trazia R$ 9,8 mil.
- O log termina no corte: zero eventos posteriores a 30/09. Entre 6.365 eventos históricos
  de renovação anual, 3.314 têm mês/dia recebido igual ao mês/dia do início no retrato.
  É uma checagem de calendário, sujeita a horário de recebimento e histórico, não uma previsão.
  Não confirma a próxima renovação de 439 pessoas; falta uma regra validada de próximo vencimento.
- Cadastro e cliques foram recalculados; a tabela pública usa contagens agregadas e denominadores.
  No rascunho, a idade mediana de Rua e ritmo era 47,0 porque ele excluía idades fora de 14 a 90 anos (133 pessoas);
  sem esse filtro, como nesta revisão e em `src/levantar_personas_s5.py`, é 47,1.
- Motivações e metas por palavras-chave: classificador e regras publicados em `src/personas_regras_s5.py`
  (um tema principal por resposta, denominador = respostas com conteúdo, meta com data como sinalizador à parte).
  Os percentuais reexecutados coincidem com o rascunho. É o código do próprio rascunho, não uma verificação independente.
- Amostra maior cobre mais casos, mas não elimina erro compartilhado de regra: o recálculo
  independente continua usando as definições documentadas pelo mesmo grupo.

## Conferência humana e próximos passos

O `AGENTS.md` lido pede três registros do resultado conferidos à mão; não especifica três por persona.
Kiril propôs três por persona e depois sugeriu uma revisão humana de um por persona.
Esta revisão executou verificações por código e não registra uma validação humana como concluída.
O mínimo local de três e a cobertura adicional proposta devem ter revisor e evidência local registrados.
Os arquivos detalhados podem apoiar essa revisão, sem enviá-los ao GitHub.

Antes de aprovação: revisão autoral de Kiril, revisão dos tratamentos pelo grupo, decisão sobre
nomes e integração à priorização. Não há recomendação de contato individual nesta entrega.

## Reprodução e rastreabilidade

Referências fixadas:

- Preparação: main em `8d408862735fb1faec3cd43c8fbbf338544be484`.
- Clusterização: `eafaf08a246ed5470d31dce7c63fd2c196788fc3`, branch `leo/clusterizacao-s5`, [PR #5](https://github.com/leonardomoraesmendes/vitaliza/pull/5).
- Ambiente executado: Python 3.14; pandas 3.1.0; numpy 2.5.4; scikit-learn 1.9.1; pypdf 7.0.0.
- Entrada autoral: `sumario_executivo_conferencia.pdf`, `sumario_executivo_amostra_96_registros.pdf`
  e `Personas Vitaliza – rascunho.pdf`, recebidos por John. Originais preservados.
- SHA-256 PDF de 12: `5918af47e0bcbb6c463a1fa68653786a47c792c0234f3668c9bd8ff5b3622403`.
- SHA-256 PDF de 96: `10e187f1a189632cb209943d9418bcf701cee7e91b88c6326354bac72a50c94d`.

Versão vigente dos sumários (v2). Os PDFs acima são a versão 1: o texto deles ainda traz os limites
de erro de 25% e 3%, retirados na seção anterior. Os de 12 e de 96 registros passaram a ter a
versão 2, que remove essa frase e não muda nenhuma métrica, contagem ou pessoa conferida. Os
arquivos ficam com Kiril, fora do repositório público; os hashes permitem confirmar qual versão
cada pessoa recebeu.

- SHA-256 PDF de 12, v2 (`sumario_executivo_conferencia_v2.pdf`): `eb4a711457b63642a2bd1239a2892632bdfa10f9788005ae2dd72d1b23ab64b5`.
- SHA-256 PDF de 96, v2 (`sumario_executivo_amostra_96_registros_v2.pdf`): `e8b53b8946a4014f56888b73bc786228deac41bd033ce3cdcc56e7049062ec69`.
- `Personas Vitaliza – rascunho.pdf` também está superado: traz R$ 9,8 mil no cenário de aniversários; o valor correto é R$ 9.539,30 (`personas_s5.md`).

Em um ambiente isolado, com as bases originais montadas conforme o README:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-revisao-kiril.txt
git fetch https://github.com/leonardomoraesmendes/vitaliza.git leo/clusterizacao-s5
.venv/bin/python src/preparar_diagnostico_s5.py
.venv/bin/python src/revisar_personas_kiril_s5.py \
  --pdf-12 /caminho/local/sumario_executivo_conferencia.pdf \
  --pdf-96 /caminho/local/sumario_executivo_amostra_96_registros.pdf
.venv/bin/python -m unittest discover -s tests -v
```

O script recupera o código de Leonardo pelo SHA, sem copiá-lo para o PR e sem rodar seu `main`.
Se a preparação mudar, a referência deve ser revisada antes da execução. Este script ainda lê os `user_id` dos PDFs;
os conferidores de `src/` sorteiam as mesmas amostras por seed e não dependem dos PDFs, que não estão no repositório público.

Levantamento descritivo, cenário de aniversários e conferências por seed (só pandas e pyarrow; gravam em `dados/saidas/s5_kiril/`):

```sh
.venv/bin/python src/levantar_personas_s5.py
.venv/bin/python src/calcular_risco_janela_s5.py
.venv/bin/python src/conferir_12_registros_s5.py
.venv/bin/python src/conferir_96_registros_s5.py
```

Todos os resultados detalhados, inclusive comparações individuais, ficam em
`dados/saidas/s5_kiril_revisao/`, ignorado no Git. O manifesto local contém hashes das fontes,
versões e resultados. Nenhum envio de base ou PDF original faz parte da reprodução.
