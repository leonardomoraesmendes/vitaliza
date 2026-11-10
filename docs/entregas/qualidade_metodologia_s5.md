# Qualidade dos dados e metodologia da S5

Frente de Claudinne. Base de trabalho: a preparação de John incorporada pelo PR #4 (`dados/processados/s5_john/`). Código: [`src/checagens_qualidade_s5.py`](../../src/checagens_qualidade_s5.py). Decisões: [`decisoes.md`](../../decisoes.md#qualidade-e-metodologia-de-claudinne--s5-04112026).

## Resumo

A base de clusterização dos 14.753 pagantes está consistente e pode ser usada: 14 regras de consistência e 9 recálculos de fórmula, feitos em todas as linhas, deram zero divergência. Os riscos para as conclusões estão em quatro escolhas de método:

1. **Inativos pagantes.** 759 assinantes (5,1%) não treinaram em 90 dias e têm `proporcao_video_90d` vazia. Se entrarem no algoritmo, formam um cluster artificial. Proposta: segmento definido por regra, fora do agrupamento.
2. **Variáveis redundantes.** Treinos, minutos e dias ativos têm correlação de Spearman de 0,95 a 0,99. Se as três entrarem, o volume de uso pesa três vezes na distância.
3. **Escala e assimetria.** Minutos, tempo de assinatura e dias desde o último treino têm cauda longa. Sem log e padronização, poucos extremos definem os grupos.
4. **Risco sem desfecho.** A base é um retrato do corte, sem quem saiu depois. O risco de cada segmento é hipótese apoiada no diagnóstico histórico, não previsão.

Achados novos, fora do `decisoes.md` até aqui: `sistema` com grafias diferentes (3.665 linhas, 24,8%) e 189 anuais por influenciador ainda em R$ 239,90 depois do primeiro ano.

## Conferência pelos critérios de avaliação

| Critério | Evidência | Situação | O que falta |
|---|---|---|---|
| Completude | Matriz provisória plano × canal × engajamento (16 combinações), totais e elegibilidade das ofertas | Parcial | Trocar o engajamento pelos clusters e acrescentar a ação |
| Consistência | População, percentuais e bases monetárias reconciliados com o enunciado; receita após taxas separada da contribuição; números de John recalculados de forma independente | Atende, com ressalva | Decidir o preço de renovação dos 189 anuais em R$ 239,90 |
| Validade | Sinais de risco tratados como associação; a única fonte causal é a campanha sorteada de 10/08 | Parcial | Comparar as variáveis de uso entre os quatro grupos da campanha |
| Reprodutibilidade | Script versionado, sementes fixas, ponte de filtros, 16 testes de John | Atende na base tratada | Conferir 3 registros contra `atividades.parquet` |
| Viabilidade | Limites mensais de orçamento, WhatsApp, CS e ofertas contra o tamanho dos grupos | Parcial | Custo real de IA, ainda não cotado |
| Governança | `.gitignore` exclui `/dados/` e `.env`; nenhum `.csv` ou `.parquet` versionado na `main`; brutos só leitura | Atende | Bases por assinante fora do Git e dos grupos de mensagem |

### Completude: matriz provisória e elegibilidade

Até os clusters ficarem prontos, o engajamento (com ou sem treino em 90 dias) é o segmento provisório. A junção por `user_id` é um para um.

| Plano | Canal | Com treino em 90 dias | Sem treino em 90 dias | Total |
|---|---|---|---|---|
| Anual | App Store | 2.798 | 249 | 3.047 |
| Anual | Google Play | 2.651 | 277 | 2.928 |
| Anual | Cartão | 1.629 | 174 | 1.803 |
| Anual | Pix | 644 | 56 | 700 |
| Mensal | App Store | 2.348 | 0 | 2.348 |
| Mensal | Google Play | 2.035 | 1 | 2.036 |
| Mensal | Cartão | 1.189 | 2 | 1.191 |
| Mensal | Pix | 700 | 0 | 700 |
| **Total** | | **13.994** | **759** | **14.753** |

756 dos 759 inativos (99,6%) são anuais: já pagaram o ano, e o risco se concentra na renovação. O mesmo vale para a renovação desligada: 2.084 dos 2.255 casos são anuais.

| Oferta | Quem pode receber | Pagantes elegíveis | Custo por oferta |
|---|---|---|---|
| 30% de desconto por 3 meses | Mensal | 6.275 | R$ 35,91 (R$ 11,97/mês) |
| 1 mês grátis no fim do ciclo | Anual | 8.478 | R$ 25,00 |
| Pausa de até 60 dias | Qualquer plano | 14.753 | Receita adiada |
| Plano de treino personalizado | Qualquer plano | 14.753 | Sem custo direto |

### Consistência: população e bases monetárias

14.753 pagantes; 57,5% anual e 42,5% mensal; App Store 36,6%, Google Play 33,6%, cartão 20,3%, Pix 9,5%. Os líquidos por assinante batem com a tabela de taxas (ex.: R$ 33,92 no mensal pela loja; R$ 254,92 ÷ 12 = R$ 21,24 no anual pela loja).

| Etapa (equivalente mensal da carteira) | Valor |
|---|---|
| Receita bruta aproximada | R$ 457.281,85 |
| (−) Taxas de loja, cartão e Pix | −R$ 51.742,53 |
| **Receita após taxas** | **R$ 405.539,32** |
| (−) Custo de servir: R$ 4,20 × 14.753 | −R$ 61.962,60 |
| **Contribuição aproximada** | **R$ 343.576,72** |

"Receita após taxas" e "contribuição" não são sinônimos: a diferença é de R$ 61.962,60 por mês.

Conferência independente da frente de valor de John:

| Número de John | Recalculado | Situação |
|---|---|---|
| Bruto R$ 457,3 mil; após taxas R$ 405,5 mil; contribuição R$ 343,6 mil | R$ 457.281,85; R$ 405.539,32; R$ 343.576,72 | Bate |
| Contribuição do mensal: lojas R$ 29,72, cartão R$ 34,30, Pix R$ 35,30 | Líquido do enunciado − R$ 4,20 | Bate |
| 1.702 sem treino em setembro, R$ 30,1 mil de contribuição | 1.702; R$ 30.144,90 | Bate |
| CRM no teto: R$ 6.147,53 | R$ 600 + R$ 5.400 + R$ 147,53 | Bate |
| Ofertas para toda a base: R$ 437,3 mil | 6.275 × R$ 35,91 + 8.478 × R$ 25,00 = R$ 437.285,25 | Bate |
| Equilíbrio de 3 meses, mensal pela loja: WhatsApp 0,45 p.p., CS 20,19 p.p. | R$ 0,40 ÷ R$ 89,16 e R$ 18 ÷ R$ 89,16 | Bate |

**Duas definições de inatividade.** John usa "sem treino em setembro" (1.702); esta frente usa "sem treino em 90 dias" (759). Os 759 estão todos dentro dos 1.702 e valem R$ 13,3 mil de contribuição mensal. Proposta para o relatório: "inativos há 90 dias" (759) e "inativos recentes" (943).

**Ressalva.** Pelo enunciado, R$ 239,90 vale só no primeiro ano do anual por influenciador. 189 assinantes com mais de 365 dias de assinatura ainda têm R$ 239,90 como última cobrança, todos vindos de influenciador. Manter a tarifa observada é defensável para descrever a carteira; para projetar a renovação, o enunciado indica R$ 299,90 (cerca de R$ 945/mês a mais na receita bruta equivalente).

### Reprodutibilidade: ponte de filtros

| Passo | Linhas | Fonte da regra |
|---|---|---|
| Assinaturas ativas no retrato de 01/10 | 14.813 | `assinaturas.csv` |
| (−) Contas de teste (`@vitaliza.com.br`) | −60 | `decisoes.md` |
| **Pagantes no corte** | **14.753** | Bate com o enunciado |
| (−) Sem treino em 90 dias (segmento por regra) | −759 | Esta frente |
| **Base para o algoritmo de clusterização** | **13.994** | Proposta a Leonardo |

### Validade: sinal de risco não é efeito de ação

Uso baixo, renovação desligada e tempo sem treinar indicam quem tende a sair, não quem ficaria se fosse contatado. O efeito de uma ação só vem da campanha de 10/08 (14.120 pagantes sorteados em quatro grupos). A campanha caiu dentro da janela de 90 dias (03/07 a 30/09): se mudou o comportamento, as variáveis de uso já carregam parte do efeito. Antes de fechar os clusters, comparar as variáveis de uso entre os quatro grupos.

### Viabilidade: limites mensais contra o tamanho dos grupos

| Recurso | Limite mensal (enunciado) | Grupo que disputaria o recurso | Cabe? |
|---|---|---|---|
| Orçamento de CRM, com descontos e IA | R$ 40.000 | Com reserva integral, no máximo 1.113 descontos do mensal ou 1.600 meses grátis do anual (alternativas, sem IA) | Exige escolher subgrupo |
| WhatsApp | 1.500 mensagens (R$ 600) | Renovação desligada: 2.255 | Não; cobre 67% |
| CS | 300 atendimentos (R$ 5.400) | Inativos há 90 dias: 759 | Não; cobre 40% |
| Push | 1 por assinante por semana | Toda a base | Sim |
| E-mail | Sem limite (R$ 0,01) | Toda a base: R$ 147,53 por envio | Sim |
| IA generativa | Mesmo orçamento | — | Pendente: custo não cotado |

## As cinco dimensões na base de clusterização

| Dimensão | O que foi medido | Resultado |
|---|---|---|
| Completude | Vazios por coluna, contra o dicionário | 4 colunas com vazios, todas previstas: `proporcao_video_90d` 759 (5,1%), `dias_desde_ultimo_treino_2026` 177 (1,2%), `nivel` 1.029 (7,0%), `dias_planejados_semana` 1.491 (10,1%) |
| Validade | Domínio de categorias e faixas plausíveis | `nivel` só com as 3 categorias do dicionário; dias planejados de 1 a 7; proporção de vídeo de 0 a 1; negativos só na variação, onde são esperados (5.355 quedas); 58 extremos plausíveis |
| Consistência | Regras entre colunas e entre as duas bases | 14 regras com 0 divergências; 17 colunas idênticas nas duas bases; `sistema` com 3.665 grafias diferentes |
| Unicidade | `user_id` e linhas repetidas | 0 `user_id` duplicados; 2 linhas iguais fora o `user_id`, ambas inativas: pessoas diferentes com o mesmo perfil |
| Temporalidade | Janelas, corte e cobertura | Janelas fecham no corte exclusivo de 01/10/2026; recência só cobre 2026; campanha de 10/08 dentro da janela de 90 dias |

## Problemas e características por dimensão

**Novo** = encontrado nesta frente. Os demais já estavam no `decisoes.md` e foram tratados na preparação. Tipo segue o `AGENTS.md`: problema ou característica do dado.

| Dimensão | Tipo | Problema ou característica | Linhas | Tratamento | Efeito na segmentação |
|---|---|---|---|---|---|
| Unicidade | Problema | Treino do relógio copiado no app | 9.383 cópias | Removidas; mantém o relógio | Quem tem relógio não parece treinar mais |
| Temporalidade | Problema | Garmin em UTC sem sufixo | 207.954 treinos | −3h antes do corte | Treino na janela certa |
| Temporalidade | Problema | Posts, relações e resoluções de ticket após o corte | 122 / 273 / 41 | Excluídos ou reconstruídos até o corte | Sem vazamento |
| Temporalidade | Característica | `assinaturas.csv` é retrato de 01/10 | 14.753 | Situação reconstruída pelos eventos | Pagantes confiáveis no corte |
| Temporalidade | Característica | **Novo:** recência limitada a 2026 | 177 (1,2%) | Marcar como censurado | "Sem treino desde pelo menos 01/01/2026" |
| Validade | Problema | Treinos com duração zero | 3.649 | Fora do volume válido | Volume não inflado |
| Validade | Problema | Distância incompatível com o treino | 999 | Distância anulada; fora dos clusters | Nenhuma variável de distância |
| Validade | Problema | Contas de teste | 60 | Excluídas | Total bate com o enunciado |
| Validade | Problema | `dias_por_semana` em texto livre | 24.034 | Número de 1 a 7; resto vazio | Variável usável, com ausências |
| Validade | Característica | **Novo:** sessões médias acima de 300 min | 12 | Manter e marcar | Limite no p99 |
| Validade | Característica | **Novo:** 40 ou mais treinos em 30 dias (máx. 62) | 46 | Manter e marcar | Limite no p99 |
| Validade | Característica | **Novo:** mais treinos que dias de assinatura | 395 | Manter: treinos do teste de 7 dias | Ler recém-chegados com cautela |
| Consistência | Problema | Tipo de treino em dois idiomas | 376.930 | Padronizado em português | Proporção de vídeo sobre categorias únicas |
| Consistência | Problema | BI mensal diverge do detalhe | 5.542 pagantes | BI fora dos clusters | Ver Limitações |
| Consistência | Problema | Renovação: eventos × retrato | 5 + 1.112 | Fontes separadas; fora dos clusters | Só descritivo |
| Consistência | Problema | **Novo:** `sistema` com grafias diferentes | 3.665 (24,8%) | Padronizar em minúsculas (android 7.475, ios 7.278) | Cortes por sistema sem grupos partidos |
| Consistência | Problema | **Novo:** anual por influenciador em R$ 239,90 após o 1º ano | 189 | Pendente com John | Projeção de valor, não clusters |
| Completude | Problema | `nivel` vazio, sem ser opcional | 1.029 (7,0%) | "Não informado" | Fora do algoritmo |
| Completude | Problema | `dias_planejados_semana` vazio | 1.491 (10,1%) | "Não informado" | Fora do algoritmo |
| Completude | Problema | Objetivo pseudo-vazio | 4.441 (30,1%) | `objetivo_sem_conteudo` | Objetivo declarado serve pouco às personas |
| Completude | Característica | **Novo:** sem treino em 90 dias | 759 (5,1%) | Segmento à parte | Ver Tratamentos |

As ausências do onboarding parecem aleatórias: quem não informou (2.409, 16,3%) tem medianas iguais às de quem informou (262 × 263 dias de assinatura; 8 × 8 treinos em 30 dias; 20 × 20 dias ativos em 90 dias), e a taxa de vazio fica entre 14,5% e 17,5% em todas as faixas de tempo de assinatura.

Os extremos são poucos e plausíveis: mediana de 43 min por treino, p99 de 114; os 5 maiores (403 a 515 min) são de quem treinou uma única vez em 90 dias; os 62 treinos em 30 dias vêm de 29 dias ativos.

## Conferência por amostras e recálculos

Regras e fórmulas foram testadas em todas as linhas (a lista completa está em `src/checagens_qualidade_s5.py`). Todas deram 0, exceto `tickets_pendentes_corte > tickets_90d` (730), esperado: tickets abertos há mais de 90 dias e ainda pendentes.

**Atividade antes do início da assinatura.** 395 recentes têm mais dias de treino que dias de assinatura (ex.: `u_0a980c4d`, 0 dias e 10 treinos). Em 100% dos casos o cadastro foi 7 dias antes do início pago e nenhum treino é anterior ao cadastro: são treinos do teste grátis.

**Três registros contra fonte independente** (BI de `uso_mensal.csv`, semente 7):

| user_id | Plano e canal | Treinos set (tratado × BI) | Minutos set (tratado × BI) | Treinos ago (tratado × BI) | Leitura |
|---|---|---|---|---|---|
| u_12a65a8e | Mensal, Google Play | 7 × 7 | 245,0 × 192 | 3 × 3 | Contagens batem; BI com 22% menos minutos |
| u_6fbffe39 | Anual, App Store | 9 × 9 | 418,7 × 352 | 8 × 9 | Quase iguais; BI com 16% menos minutos |
| u_c5a24d55 | Mensal, Google Play | 6 × 1 | 267,6 × 41 | 9 × 1 | BI capta 1 de 6; padrão das 5.542 divergências |

Nos três, o cadastro confirma o teste de 7 dias (129 − 122, 577 − 570, 610 − 603) e a receita líquida bate com a tabela de taxas. A fonte independente confirma a contagem na maioria dos casos e mostra que o BI subconta minutos de forma sistemática. A causa não está no dicionário: pergunta em aberto.

## Tratamentos recomendados para a clusterização

Propostas a Leonardo, que decide a seleção final. Nenhuma remove linhas: os 14.753 continuam no relatório.

1. Separar os 759 inativos há 90 dias como segmento por regra e rodar o algoritmo nos 13.994.
2. Uma variável por conceito (maior correlação entre elas: 0,48):

| Conceito | Variável | Transformação |
|---|---|---|
| Frequência | `dias_ativos_90d` | Padronizar |
| Intensidade | `minutos_90d` ÷ `treinos_90d` | Limitar no p99 (114 min), log, padronizar |
| Tendência | `variacao_treinos_tratados_30d` | Padronizar |
| Recência | `dias_desde_ultimo_treino_2026` | Log, padronizar |
| Formato | `proporcao_video_90d` | Já de 0 a 1 |
| Tempo de casa | `tempo_assinatura_dias` | Log, padronizar |
| Comunidade | `posts_90d`, `seguidores_corte` | Padronizar; `seguindo_corte` sai (0,80 com seguidores) |

3. Limitar extremos no p99 em vez de excluir.
4. Onboarding fora do algoritmo; "não informado" visível nas personas.
5. Tickets como sim/não (3,9% abriram; máximo 2), para descrever.
6. Padronizar `sistema` antes das tabelas de valor e das personas.
7. Plano, canal, receita, renovação desligada e nível só para descrever os grupos depois.

## Limitações que afetam as conclusões

| Limitação | O que não podemos afirmar | Como escrever |
|---|---|---|
| Retrato do corte, sem desfecho posterior | Que um segmento "vai cancelar" | Risco como hipótese apoiada no histórico |
| Só pagantes ativos em 30/09 (sobrevivência) | Como eram os que já saíram | Segmentos descrevem a carteira atual |
| Associação não é causa | Que treinar menos causa a saída | "Está associado a"; efeito só com sorteio |
| Recência só em 2026 (máx. 271 dias) | Há quanto tempo param os 177 | "Desde pelo menos 01/01/2026" |
| Uso dos recém-chegados inclui o teste (395) | Que reflete o uso já pagando | Cautela na leitura |
| BI × detalhe divergem em 5.542 (correlação 0,76) | Que são a mesma medida | Citar a fonte; clusters só com o tratado |
| Receita aproximada | Receita contábil, LTV, retorno | "Receita mensal equivalente aproximada" |
| Onboarding autodeclarado (16,3% vazio; objetivo 30,1% pseudo-vazio) | Que o nível declarado é o real | Separar declarado de observado |
| Sociais com pouca amplitude (0 a 13) | Diferenças finas | Faixas nas personas |
| Contato pode piorar a saída de quem pouco usa | Que os inativos são prioridade automática | "Monitorar" até haver evidência do efeito |

## Pendências

- [ ] Até 08/11: conferir 3 registros contra `atividades.parquet` (pedido abaixo).
- [ ] Leonardo: confirmar os 759 fora do algoritmo e o conjunto de variáveis.
- [ ] John: padronizar `sistema` e decidir o preço de renovação dos 189 anuais em R$ 239,90.
- [ ] Comparar as variáveis de uso entre os quatro grupos da campanha de 10/08.
- [ ] Revisar os 451 casos `revisar = 1` de `dados/processados/s5_claudinne/qualidade_flags.csv`.
- [ ] Cotar o custo de IA e incluí-lo no orçamento de R$ 40.000/mês.

```
Pergunta:      os indicadores de atividade da base de clusterização batem com o bruto, no corte de 30/09/2026?
Arquivos:      dados/brutos/atividades.parquet e dados/processados/s5_john/base_clusterizacao.csv (dicionário em docs/).
Regras:        sorteie 3 user_id (semente 42); aplique as regras do decisoes.md (Garmin −3h, sem cópias
               do app, duração > 0, corte exclusivo 01/10/2026 em Brasília); mostre as linhas depois de
               cada filtro; não altere nada em dados/brutos/.
Saída:         tabela lado a lado (base × recalculado) de treinos_30d, minutos_90d, dias_ativos_90d e
               dias_desde_ultimo_treino_2026, com a tabela de filtros e o código em notebooks/.
Pronto quando: os 3 registros batem, ou cada diferença tem explicação registrada no decisoes.md.
```

## Reprodução

```sh
.venv/bin/python src/preparar_diagnostico_s5.py   # gera as bases de John
.venv/bin/python src/checagens_qualidade_s5.py    # reproduz todos os números desta frente
```
