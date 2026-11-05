# Clusterização dos pagantes — Semana 5 (objetivo 3)

Frente de Leonardo na divisão de 27/10/2026: construir e validar os agrupamentos, selecionar as variáveis, gerar a tabela comparativa dos segmentos e explicar o método. Os nomes abaixo são provisórios; nomes finais e personas são da frente de Kiril.

## Resultado

Os 14.753 pagantes ativos em 30/09/2026 se dividem em quatro segmentos de comportamento. Nenhuma linha foi removida: 14.753 entram e 14.753 saem com segmento.

| | Distantes | Engajados em casa | Engajados ao ar livre | Recém-chegados |
|---|---:|---:|---:|---:|
| Segmento no código | 0 | 1 | 2 | 3 |
| Assinantes | 2.783 | 4.315 | 4.793 | 2.862 |
| % da base | 18,9% | 29,2% | 32,5% | 19,4% |
| Dias ativos ÷ dias de conta na janela de 90 dias (mediana) | 0,02 | 0,27 | 0,30 | 0,32 |
| Dias ativos em 90 dias (mediana) | 2 | 24 | 26 | 14 |
| Dias desde o último treino (mediana) | 36,8 | 2,2 | 1,7 | 1,8 |
| Sem nenhum treino em 90 dias | 27,3% | 0% | 0% | 0% |
| Treinos em vídeo (mediana da proporção) | 17% | 86% | 19% | 27% |
| Minutos por treino (mediana) | 46,0 | 41,5 | 47,9 | 43,3 |
| Posts por 90 dias de conta (média) | 0,7 | 1,8 | 2,0 | 2,1 |
| Seguidores (média) | 1,9 | 2,0 | 2,1 | 0,2 |
| Tempo de assinatura (mediana, dias) | 338 | 334 | 361 | 38 |
| *Descritivas, fora do agrupamento:* | | | | |
| Plano anual | 91,8% | 51,7% | 53,5% | 39,4% |
| Cobrança pelas lojas | 69,0% | 70,4% | 71,2% | 69,5% |
| Renovação automática desligada (retrato de 01/10) | **57,5%** | 7,6% | 4,8% | 3,3% |
| Com ticket nos últimos 90 dias | 3,3% | 3,5% | 3,3% | 6,2% |
| Receita líquida mensal equivalente (total) | R$ 63,3 mil | R$ 122,3 mil | R$ 134,5 mil | R$ 85,4 mil |
| Receita líquida mensal equivalente (média por pessoa) | R$ 22,76 | R$ 28,34 | R$ 28,05 | R$ 29,85 |

A receita somada dos quatro segmentos (R$ 405,5 mil) bate com o valor após taxas da frente financeira de John.

**Leitura em uma linha por segmento** (fatos medidos; interpretação e personas ficam com Kiril):

- **Distantes:** quase não treinam (mediana de 2 dias ativos em 90 dias; 27% sem nenhum treino), são majoritariamente anuais, e 57,5% já desligaram a renovação automática.
- **Engajados em casa:** frequência alta, treinos majoritariamente em vídeo (força, funcional, HIIT, ioga), sessões um pouco mais curtas.
- **Engajados ao ar livre:** frequência alta, treinos majoritariamente ao ar livre (corrida, caminhada, pedal), sessões mais longas e o maior tempo de casa.
- **Recém-chegados:** mediana de 38 dias de assinatura, a maior frequência relativa da base, ainda sem rede social no app (0,2 seguidores em média), e o dobro de tickets dos demais.

**Validação externa.** A renovação desligada não entrou no agrupamento, que usou só comportamento de uso. Mesmo assim, ela se concentra num segmento: 57,5% nos Distantes, contra 3% a 8% nos demais. É a evidência mais forte de que os grupos capturam algo real, e o dado mais relevante para a priorização: R$ 63,3 mil mensais equivalentes, com mais da metade já sinalizando saída.

## Método

### 1. Base

`dados/processados/s5_john/base_clusterizacao.csv`, gerada do bruto por `src/preparar_diagnostico_s5.py`. Essa preparação já trata fusos (lojas e garmin em UTC), contas de teste, durações zero, distâncias impossíveis e treinos duplicados entre app e relógio. A regeneração reproduziu as referências conhecidas (14.753 pagantes, 9.383 cópias removidas, 3.649 durações zero) e foi idêntica, linha a linha, à base que John compartilhou com o grupo.

### 2. Variáveis: uma por dimensão de comportamento

As 17 candidatas eram muito redundantes: as seis de volume (treinos, minutos e dias ativos, em 30 e 90 dias) têm correlação de Spearman entre 0,80 e 0,99. Usar todas daria a "quanto treina" um peso seis vezes maior e transformaria os segmentos em faixas de volume. O agrupamento usa oito variáveis, uma por dimensão; a maior correlação entre elas, já transformadas, é 0,62.

| Dimensão | Variável |
|---|---|
| Frequência | dias ativos ÷ min(90, dias de conta + 1) |
| Intensidade | minutos por treino em 90 dias |
| Recência | dias desde o último treino válido |
| Tendência | treinos nos últimos 30 dias − treinos nos 30 anteriores |
| Modalidade | proporção de treinos em vídeo em 90 dias |
| Social (produção) | posts por 90 dias de conta |
| Social (rede) | seguidores no corte |
| Tempo de casa | dias de assinatura |

Ficaram fora do agrupamento e só descrevem os segmentos:

- `tickets_90d`: 96% das pessoas têm zero chamados, e quem abriu um ficaria a cerca de 5 desvios-padrão da média. O K-means criaria um grupo por efeito de escala.
- `nivel` e `dias_planejados_semana`: são declarações do cadastro, não comportamento, e têm de 7% a 10% de ausência.
- Plano, canal, receita e renovação: o enunciado pede segmentos que não usem a informação de quem saiu, e o valor financeiro é usado depois, na priorização.

### 3. Exposição

Quem tem conta há menos de 90 dias não teve como acumular a janela inteira e pareceria pouco ativo por construção. O denominador é o tempo de **cadastro**, não o de assinatura, porque registrar treino é grátis e o Premium começa com 7 dias de teste. 206 pessoas têm mais dias ativos do que dias de assinatura; nenhuma tem mais do que dias de conta + 1. A correção afeta 2.784 contas.

A tendência compara os últimos 30 dias com os 30 anteriores. Com menos de 60 dias de conta, a janela anterior está incompleta e a variação sai positiva por construção. Nessas 1.938 contas, a tendência fica neutra (0).

Antes da correção, os recém-chegados apareciam como "pouco ativos, acelerando" (+7,1 treinos na tendência). Depois dela, são o segmento de maior frequência relativa, com tendência de −0,3 na parte comparável.

### 4. Ausências e escala

| Variável | Ausência | Regra | Linhas |
|---|---|---|---:|
| Recência | sem treino em 2026 | 273 dias: limite inferior, já que não há treino desde 01/01 | 177 |
| Minutos por treino | zero treino em 90 dias | mediana (valor neutro) | 759 |
| Proporção de vídeo | zero treino em 90 dias | mediana (valor neutro) | 759 |

As ausências são estruturais. Os 177 sem recência são exatamente os 177 sem treino em 2026, e os 759 são exatamente os sem treino em 90 dias. Por isso não há o que corrigir; o que se decide é como representar a ausência sem inventar comportamento.

Variáveis com cauda longa (intensidade, recência, posts, seguidores, tempo de casa) recebem `log1p`. Todas são cortadas nos percentis 1 e 99 e padronizadas (média 0, desvio 1), para que nenhuma domine a distância por causa da unidade.

### 5. Escolha de k

K-means com k de 2 a 8, avaliado por inércia, silhueta, Calinski-Harabasz e estabilidade. A estabilidade é medida pelo ARI entre o ajuste completo e 20 ajustes em amostras de 80% da base.

| k | Silhueta | ARI médio | ARI mínimo | Menor grupo |
|---:|---:|---:|---:|---:|
| 2 | 0,162 | 0,982 | 0,916 | 32,7% |
| 3 | 0,162 | 0,978 | 0,945 | 23,5% |
| **4** | **0,169** | **0,990** | **0,984** | **18,9%** |
| 5 | 0,167 | 0,968 | 0,633 | 15,3% |
| 6 | 0,170 | 0,983 | 0,972 | 7,7% |
| 7 | 0,175 | 0,980 | 0,959 | 7,3% |
| 8 | 0,167 | 0,908 | 0,585 | 6,5% |

Escolhemos k = 4 por quatro motivos:

- é o mais estável;
- o menor grupo tem 19% da base;
- está dentro do intervalo de 3 a 4 grupos da entrega;
- separa os engajados entre vídeo e ar livre, o que muda a mensagem no objetivo 6.

Num agrupamento hierárquico de Ward, sobre uma amostra de 6.000 pessoas, a concordância com o K-means é ARI 0,63.

**Limitação.** A silhueta fica perto de 0,17 em todos os k. Os assinantes não formam grupos naturalmente isolados; o comportamento varia de forma contínua. Os segmentos são cortes estáveis e interpretáveis desse contínuo, úteis para escolher mensagens, e não tipos naturais. Pessoas perto da fronteira entre dois segmentos se parecem com ambos.

### 6. Conferências

- A ponte de linhas fecha: 14.753 → 14.753 → 14.753.
- Quatro assinantes foram recalculados direto de `dados/brutos/`, com lógica independente do pipeline. São três de segmentos diferentes com relógio conectado (incluindo a correção de fuso do garmin e a remoção de cópias) e um de conta recente, para exercitar a exposição. As 20 métricas bateram (notebook, seção 6).
- A receita total dos segmentos bate com a frente financeira (R$ 405,5 mil).

## Limitações e próximos passos

- Os segmentos descrevem o retrato de 30/09/2026. Uma pessoa muda de segmento com o tempo, e um Recém-chegado vira Engajado ou Distante. Para o modelo de churn (objetivo 4), o segmento pode entrar como variável desde que seja recalculado em cada data de corte, para não vazar informação.
- A renovação desligada ajuda a validar, mas não diz quem vai sair; o risco individual é do objetivo 4.
- Dentro dos Distantes, 27% não treinam há mais de 90 dias e o restante treina pouco. Se a priorização precisar separar os dois casos, um subagrupamento só nesse segmento é o próximo passo natural.

## Reprodução

```sh
.venv/bin/python src/preparar_diagnostico_s5.py   # base de John, a partir do bruto
.venv/bin/python src/clusterizacao_s5.py           # varredura de k
.venv/bin/python src/clusterizacao_s5.py --k 4     # segmentos, perfil e conferências
```

Roteiro de estudo: `notebooks/08_clusterizacao.ipynb`.

Saídas fora do Git:

- `dados/processados/s5_leo/segmentos.csv`: `user_id` → segmento, para integração com as frentes de Kiril e John;
- `dados/saidas/s5_leo/`: perfil, varredura, tratamentos, ponte de linhas e resumo.
