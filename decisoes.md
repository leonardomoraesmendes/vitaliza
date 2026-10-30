# Registro de decisões

Todo problema de qualidade ou regra de cálculo entra na tabela: uma linha por decisão. A coluna **Dimensão** usa as cinco dimensões do `AGENTS.md` (Completude, Validade, Consistência, Unicidade, Temporalidade) ou **Regra** para regras de negócio. Quando a decisão precisar de explicação, detalhe na seção abaixo da tabela.

| Data | Arquivo | Dimensão | Problema | Decisão | Critério | Linhas afetadas | Quem |
|---|---|---|---|---|---|---|---|
| 2026-10-22 | `pagamentos.csv` | Validade | `valor` em dois formatos: `34.90` e `"R$ 34,90"` | Converter para número | Remover `R$ `, trocar vírgula por ponto | 19.750 | Leo + Claude |
| 2026-10-22 | `pagamentos.csv` | Temporalidade | `data_hora` mistura UTC (lojas) e horário de Brasília (site) | Converter tudo para Brasília antes de agrupar por mês | Sufixo `Z` = UTC → −3h; sem sufixo = já em Brasília | 112.126 em UTC; 53.422 em Brasília | Leo + Claude |
| 2026-10-22 | `pagamentos.csv` | Unicidade | Cobranças aprovadas duplicadas | Manter uma | Mesmo `user_id` + `data_hora` exata + `valor`, ambas `aprovado` | 1.941 na base (93 em set/26) | Leo + Claude |
| 2026-10-22 | `pagamentos.csv` | Regra | Faturamento somava todos os status | Faturamento usa só `aprovado`; líquido desconta taxas de canal | Ver [Faturamento mensal](#faturamento-mensal) | — | Leo + Claude |
| 2026-10-22 | `pagamentos.csv` | Consistência | Estorno `p_0160370` de R$ 299,90 sobre cobrança de R$ 239,90 | Marcar; não corrigir | Estorno maior que a cobrança original | 1 | Leo + Claude |
| 2026-10-22 | `assinaturas.csv` × `pagamentos.csv` | Consistência | 292 chargebacks em assinaturas × 296 em pagamentos | **Pendente:** investigar | — | 4 | — |
| 2026-10-22 | `usuarios.csv` | Validade | E-mails com maiúsculas ou espaços | Normalizar com `strip().lower()` antes de comparar | E-mail ≠ e-mail normalizado | 959 | Leo + Claude |
| 2026-10-22 | `usuarios.csv` × `assinaturas.csv` | Validade | Contas de teste; `plano_atual = cortesia` e `canal_cobranca = interno` não existem no dicionário | Excluir de toda contagem de assinantes | E-mail `@vitaliza.com.br` | 60 | Leo + Claude |
| 2026-10-22 | `assinaturas.csv` × `usuarios.csv` | Consistência | Assinatura com `inicio` anterior a `data_cadastro` | Marcar; **pendente:** entender a origem | `inicio < data(data_cadastro)` | 42 | Leo + Claude |
| 2026-10-22 | `onboarding.csv` | Completude | `objetivo_texto` e `como_conheceu` vazios | Manter nulo: o dicionário marca como opcionais | Nulo | 5.467 (8,6%) e 4.586 (7,2%) | Leo + Claude |
| 2026-10-22 | `onboarding.csv` | Completude | Respostas preenchidas sem conteúdo (`nada`, `😂`, `.`, `x`, `sla`, `kkkk`, `asdf`, `ok`, `-`, `nao sei`) | Marcar como **sem conteúdo**, separado de nulo; não apagar | Texto normalizado na lista | 13.768 em `objetivo_texto`; 11.515 em `como_conheceu` | Leo + Claude |
| 2026-10-22 | `onboarding.csv` | Completude | `nivel` e `dias_por_semana` vazios, sem o dicionário dizer que são opcionais | Marcar como "não informado"; não imputar | Nulo | 4.513 (7,1%) e 6.368 (10,0%) | Leo + Claude |
| 2026-10-22 | `onboarding.csv` | Validade | `dias_por_semana` em texto livre: `3`, `3x`, `3 vezes` | **Pendente:** extrair o número | Valor não numérico | 24.034 | — |
| 2026-10-22 | `atividades.parquet` | Validade | Distância incompatível com o próprio treino (até 10.012 km num pedal de 160 min) | Marcar como distância inválida; quando precisar, usar a distância implícita `duracao_min / ritmo_min_km` | \|distância ÷ (duração ÷ ritmo) − 1\| > 10%. Substitui o corte fixo de 200 km | 999 (948 acima de 200 km + 51 abaixo) | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Validade | Duração zero | Marcar como duração inválida; não usar em médias de duração | `duracao_min == 0` (nenhuma negativa) | 3.649 (1.991 com distância preenchida) | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Consistência | `tipo` em dois idiomas: 11 valores para 7 tipos. Todo o inglês vem do `app`, a partir de 15/04/2026 | Padronizar em português antes de contar por tipo (mapa proposto, ainda não aplicado) | `run`→`corrida`, `walk`→`caminhada`, `strength`→`forca`, `ride`→`pedal` | 376.930 (30%): 162.108 + 88.509 + 85.548 + 40.765 | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Completude | Treinos sem distância | Não é erro: manter nulo | Vídeo (sem percurso) ou ar livre com `gps_ok = False` | 574.835 (567.511 vídeo + 7.324 GPS falho) | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Consistência | `gps_ok = True` em todos os treinos em vídeo; ar livre com GPS falho tem distância mas não ritmo | Não interpretar `gps_ok` como "tinha GPS" | Cruzamento `tipo` × `gps_ok` | 567.511 vídeo; 7.455 sem ritmo | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Unicidade | O mesmo treino chega duas vezes: pelo relógio e como cópia no `app` | Proposta (não aplicada): manter o registro do relógio, descartar a cópia do app | Mesma conta, tipo e duração; início a até 5 min, com o `inicio` do garmin corrigido de UTC (−3h) | 9.383 pares: 5.199 garmin + 4.184 apple_health | Leo + Claude |
| 2026-10-22 | `atividades.parquet` | Temporalidade | `inicio` sem sufixo de fuso; garmin grava em UTC, app e apple_health em Brasília | Fuso por `origem`: garmin −3h | Testado nos dados: pares com o garmin a exatamente +3h; apple_health a 0h | 207.954 treinos do garmin | Leo + Claude |
| 2026-10-22 | `uso_mensal.csv` | Temporalidade | Mês sem treino muda de forma na virada: linha ausente em 2025, linha com zero em 2026. Média do arquivo cai de 265 para 118 min sem mudança de comportamento | Comparar médias entre anos só com `minutos > 0`; ao montar variáveis por usuário e mês, linha ausente em 2025 vale zero | `minutos == 0`; ausência de `user_id` × `mes` em 2025 | 303.735 linhas zeradas (todas em 2026) | Leo + Claude |
| 2026-10-22 | `uso_mensal.csv` | Temporalidade | Linhas zeradas com `sessoes_app > 0` (abriu o app sem treinar) só existem a partir de 2026 | Usar como variável só em janelas de 2026; não reconstruível para 2025 | `minutos == 0` e `sessoes_app > 0` | 262.242 (86% das zeradas) | Leo + Claude |
| 2026-10-22 | `heatmaps_90d/` | — | Imagens entregues em zip | Extrair em `2026-07-31/` e `2026-09-30/`; remover zips e `__MACOSX` | Contagem igual ao dicionário | 12.426 + 13.047 imagens | Leo + Claude |

---

## Detalhes

### Preparação e diagnóstico de John — S5 (27/10/2026)

As decisões abaixo implementam a contribuição aprovada de preparação, integração e diagnóstico. Não substituem decisões de clusterização, personas ou priorização final das outras frentes. Execução: `src/preparar_diagnostico_s5.py`; resultados e critérios em `dados/saidas/s5_john/`.

| Data | Arquivo | Dimensão | Problema | Decisão | Critério | Linhas afetadas | Quem |
|---|---|---|---|---|---|---|---|
| 2026-10-27 | assinaturas × eventos | Regra | Retrato não representa estado histórico | Semear apenas inícios anteriores a 01/07/2024; demais inícios e fins vêm dos eventos; validar alternância e estabilidade de plano/canal | Intervalo início inclusivo e fim exclusivo; desligamento de renovação não encerra assinatura | 260.328 exposições usuário-mês de jan/25 a set/26; 14.753 pagantes no corte | John + Codex |
| 2026-10-27 | uso_mensal | Temporalidade | Uso do mês da saída pode refletir a própria saída | Usar o mês anterior e exigir assinatura vigente desde o início desse mês nas comparações por faixa de uso | Cobertura desde jan/25; jan/25 não recebe uso de dez/24; ausência de treino em cobertura conhecida vira zero; sessões ausentes de 2025 ficam nulas | Contagens por grupo nos CSVs de churn por uso | John + Codex |
| 2026-10-27 | atividades | Temporalidade | Garmin registra em UTC sem sufixo | Aplicar correção −3h antes do corte e dos pares | Regra por origem documentada na exploração anterior | 207.954 registros | John + Codex |
| 2026-10-27 | atividades | Unicidade | Cópias do relógio no app distorcem volume | Reconhecer pares pelo tipo original e manter o relógio | Mesma conta, tipo original e duração, diferença até 5 min; cada registro em no máximo um par | 9.383 cópias removidas | John + Codex |
| 2026-10-27 | atividades | Consistência | Tipos em dois idiomas fragmentam agregações | Padronizar tipo depois de reconhecer os pares | Mapa já proposto na exploração anterior | 376.930 tipos padronizados | John + Codex |
| 2026-10-27 | atividades | Validade | Duração inválida e distância incompatível | Manter marcação; treinos com duração inválida não entram no volume válido; distância inválida fica nula e fora dos clusters | Duração ≤ 0; distância divergente do ritmo em mais de 10%; fallback >200 km quando ritmo/duração não avaliáveis | 3.649 durações antes da deduplicação; 999 distâncias incompatíveis + 3 altas não avaliáveis | John + Codex |
| 2026-10-27 | onboarding | Validade | Dias pretendidos em texto | Extrair apenas valores inequívocos de 1 a 7; todos = 7; preservar ausência | N, Nx ou N vezes; não imputar campo vazio | Dicionário gerado registra ausências da base final | John + Codex |
| 2026-10-27 | feed_posts × amizades × suporte | Temporalidade | Conteúdo/data de resolução posterior ao corte | Excluir posts e relações futuras; reconstruir pendência do ticket por abertura e resolução; não usar status atual como passado | Limite exclusivo 01/10/2026 em Brasília | 122 posts e 273 relações futuras; 41 resoluções após o corte | John + Codex |
| 2026-10-27 | usuarios | Temporalidade | Cadastro posterior ao corte | Sinalizar; tempo de cadastro negativo ficaria ausente | Data de cadastro ≥ limite exclusivo | 119 cadastros; nenhum entre os 14.753 ativos do corte | John + Codex |
| 2026-10-27 | usuarios × assinaturas | Consistência | Assinatura anterior ao cadastro | Sinalizar, sem alterar os totais de assinatura conciliados | Início anterior ao dia de cadastro | 42 assinaturas | John + Codex |
| 2026-10-27 | uso_mensal × atividades | Consistência | Contagem do BI difere do detalhe tratado | Manter fontes identificadas; tendência candidata aos clusters usa duas janelas iguais de 30 dias da atividade tratada | Não atribuir toda divergência a cópias; não fundir BI e detalhe como medidas equivalentes | 6.716 linhas de setembro divergem, incluindo 5.542 pagantes do corte | John + Codex |
| 2026-10-27 | eventos × retrato | Consistência | Renovação desligada reconstruída difere do retrato | Preservar fontes separadas; marcar divergência e estado inicial não informado; fora da clusterização candidata | Eventos ordenados pelo horário recebido; não reordenar para forçar concordância | 5 divergências conhecidas; 1.112 ativos sem estado inicial nos eventos relevantes | John + Codex |
| 2026-10-27 | pagamentos | Regra | Última cobrança não é receita mensal reconhecida | Criar apenas aproximação descritiva: última cobrança mensal ou anual / 12; taxas separadas | Apenas aprovados antes do corte, sem duplicatas; não desconta estornos/chargebacks nem calcula LTV/ROI | Todos os 14.753 pagantes têm ao menos uma cobrança aprovada | John + Codex |
| 2026-10-27 | base para clusterização | Regra | Vazamento e peso excessivo de variáveis correlacionadas | Entregar somente indicadores observados como candidatos; excluir desfecho futuro, intenção de cancelamento, identificadores como variável e valores financeiros | Leonardo seleciona variáveis e escalas; 17 candidatas, mais user_id como chave | 14.753 linhas | John + Codex |

### Faturamento mensal

O faturamento do mês segue quatro etapas, nesta ordem:

| Etapa | Regra | Set/2026 |
|---|---|---|
| 0. Soma ingênua | Todos os status | R$ 509.588 |
| 1. Só aprovados | Excluir `recusado`, `estornado`, `chargeback` | R$ 499.503 |
| 2. Fuso | Converter UTC → Brasília (UTC−3) antes de atribuir o mês | R$ 499.402 |
| 3. Duplicatas | Remover 2ª ocorrência de mesmo `user_id` + `data_hora` + `valor` aprovados (93 pares) | **R$ 492.572 (bruto)** |
| 4. Taxas de canal | App Store/Google Play 15%, cartão 3,5%, Pix 0,99% (enunciado, seção 03) | **R$ 436.442 (líquido)** |

O faturamento é apurado no fuso da empresa; duplicatas com horário idêntico são falha de cobrança, não receita; líquido reflete o que efetivamente entra no caixa.

**Pendência:** estornos e chargebacks lançados no mês (set/26: −R$ 3.058,20) são excluídos, mas não descontados. Definir se a visão é caixa ou competência.

### Base pagante ativa

Base pagante ativa = `status_atual == 'ativa'` em `assinaturas.csv`, excluindo contas de teste → **14.753** (14.813 − 60). Código: `notebooks/01_pagantes_ativos.ipynb`.

Bate exatamente com o enunciado (14.753; 57% anual / 43% mensal; App Store 36,6%, Google Play 33,6%, cartão 20,3%, Pix 9,5%). A primeira versão filtrava `plano_atual == 'cortesia'`; dá o mesmo resultado porque as 60 contas de teste são as 60 cortesias, mas o critério de negócio é a conta de teste.

Conferência manual: 3 contas sorteadas (seed 42) têm cobrança aprovada recente em `pagamentos.csv`; a conta de teste conferida não tem nenhuma.

**Limite:** `assinaturas.csv` é retrato de 01/10/2026. Para ativos em datas anteriores (ex.: início de cada mês, para churn), reconstruir a partir de `eventos_assinatura.csv`.

### Completude do onboarding

Código: `notebooks/02_qualidade_onboarding.ipynb`. Somando nulos e respostas sem conteúdo, `objetivo_texto` fica vazio na prática em cerca de 30% das contas, não 8,6%. Para a extração com IA (objetivo 5 do case), essas respostas não devem ir ao modelo: custam e não informam. A lista de respostas sem conteúdo foi montada a partir das respostas curtas mais repetidas e pode crescer.

### Validade das atividades

Código: `notebooks/03_qualidade_atividades.ipynb`. O roteiro usa o corte de 200 km; adotamos a regra do ritmo porque usa o próprio treino como referência. Nos treinos válidos, distância ÷ (duração ÷ ritmo) fica em 1,000 ± 0,3%; nos acima de 200 km, de 40 a 130 vezes — sem fator único, então não é erro de unidade a converter, é valor corrompido. O ritmo informado segue plausível (1,8 a 13 min/km), por isso a distância implícita é a substituta. Três treinos acima de 200 km não são avaliáveis pelo ritmo (duração zero ou sem ritmo) e continuam marcados pelo corte de 200 km.

### Tipos em dois idiomas

Código: `notebooks/04_consistencia_atividades.ipynb`. Primeiro registrado como Validade; reclassificado como **Consistência**: cada valor é válido sozinho, o problema é a mesma categoria escrita de dois jeitos.

A troca é abrupta: nenhum treino em inglês até 14/04/2026; a partir de 15/04, ~99% dos treinos pareados do `app` saem em inglês. Garmin e Apple Health nunca mudaram. Hipótese: versão nova do app. O resíduo em português no app depois de 15/04 (4.032 treinos, ~1%) são **cópias de treinos do relógio**, que mantêm o nome original — verificado no notebook 06. A hipótese inicial ("quem não atualizou o app") estava errada.

**Hipótese para o objetivo 2:** abril de 2026 foi o pior mês de churn (8,1%). Uma versão nova do app na mesma quinzena é suspeita, não causa; testar com `versao_app` e `tickets_suporte.csv` do período.

### Treinos em dobro

Código: `notebooks/06_unicidade_atividades.ipynb`. O fuso de cada origem foi testado antes de corrigido: nos candidatos a par, o garmin fica exatamente +3h e o apple_health 0h. Sem a correção, só os 4.184 pares do apple_health aparecem. Cada treino aparece em no máximo um par, e a distância é igual em todos.

A cópia do app herda tipo (em português) e `fc_media` do relógio; os demais treinos do app têm `fc_media` vazio em 88% dos casos. Por isso o registro a manter é o do relógio. Sem deduplicar, quem tem relógio conectado parece treinar mais.

### Uso mensal na virada do ano

Código: `notebooks/05_temporalidade_uso_mensal.ipynb`. O dicionário não avisa a mudança de regra de registro. As linhas com treino seguem contínuas (14.048 em out/25, 13.624 em dez/25, 15.433 em jan/26); o salto de 13.624 para 41.130 linhas vem só das linhas zeradas.

**Risco para o modelo (objetivo 4):** com separação no tempo, variáveis de inatividade calculadas sobre o arquivo como está fariam o modelo aprender a mudança de registro entre os anos, não o comportamento.

**Pendente:** definir o universo de cada mês (quem deveria ter linha) com `assinaturas.csv`/`eventos_assinatura.csv` para completar 2025 com zeros; conferir `minutos` contra `duracao_min` de `atividades.parquet` em 2026.
