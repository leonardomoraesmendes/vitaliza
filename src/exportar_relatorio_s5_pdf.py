"""Exporta a leitura executiva em PDF. Dependência opcional: reportlab.

Execute após preparar_diagnostico_s5.py. Os gráficos leem os mesmos CSVs agregados.
"""
import csv
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String, PolyLine, Circle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dados/saidas/s5_john'
INK=colors.HexColor('#20313e')
TEAL=colors.HexColor('#087e8b')
ORANGE=colors.HexColor('#d8752e')
STYLES=getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='Cover',fontName='Helvetica-Bold',fontSize=25,leading=30,textColor=INK,spaceAfter=14))
STYLES.add(ParagraphStyle(name='Section',fontName='Helvetica-Bold',fontSize=17,leading=21,textColor=TEAL,spaceAfter=12))
STYLES.add(ParagraphStyle(name='BodyS5',fontName='Helvetica',fontSize=10.2,leading=14.5,textColor=INK,spaceAfter=9))
STYLES.add(ParagraphStyle(name='SmallS5',fontName='Helvetica',fontSize=8.2,leading=11,textColor=INK,spaceAfter=7))
STYLES.add(ParagraphStyle(name='CellS5',fontName='Helvetica',fontSize=8,leading=10,textColor=INK))


def rows(name):
    with (OUT/f'{name}.csv').open() as handle:
        return list(csv.DictReader(handle))


def fmt(value, digits=2):
    return f'{float(value):,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def p(text,small=False):
    return Paragraph(text,STYLES['SmallS5' if small else 'BodyS5'])


def table(headers, data, widths=None, compact=False):
    contents=[[Paragraph(escape(str(x)),STYLES['CellS5']) for x in row] for row in [headers]+data]
    t=Table(contents,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0f0f2')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f6f8')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),3 if compact else 5),
        ('TOPPADDING',(0,0),(-1,-1),3 if compact else 5),('LINEBELOW',(0,0),(-1,0),.6,TEAL)]))
    return t


def chart(labels,series,line=False,height=230):
    d=Drawing(490,height)
    left,bottom,w,h=42,48,430,height-70
    largest=max(float(v) for values in series.values() for v in values)*1.2
    for i in range(5):
        y=bottom+h*i/4
        d.add(Line(left,y,left+w,y,strokeColor=colors.HexColor('#dce3e8'),strokeWidth=.5))
        d.add(String(left-6,y-3,f'{largest*i/4:.1f}',fontName='Helvetica',fontSize=7,textAnchor='end',fillColor=INK))
    step=w/len(labels)
    for k,(name,values) in enumerate(series.items()):
        color=[TEAL,ORANGE][k%2];points=[]
        for i,value in enumerate(values):
            x=left+step*(i+.5); y=bottom+h*float(value)/largest
            if line:
                points.extend([x,y]);d.add(Circle(x,y,2,fillColor=color,strokeColor=color))
            else:
                bw=step*.72/len(series);bx=left+step*i+step*.14+k*bw
                d.add(Rect(bx,bottom,bw-2,y-bottom,fillColor=color,strokeColor=None))
                d.add(String(bx+bw/2,y+5,fmt(value,1)+'%',fontSize=8,textAnchor='middle',fillColor=INK))
        if line:d.add(PolyLine(points,strokeColor=color,strokeWidth=1.8))
        d.add(Rect(left+k*190,8,9,9,fillColor=color,strokeColor=None))
        d.add(String(left+14+k*190,9,name,fontName='Helvetica',fontSize=8,fillColor=INK))
    for i,label in enumerate(labels):
        d.add(String(left+step*(i+.5),bottom-15,str(label),fontName='Helvetica',fontSize=6.5 if len(labels)>10 else 8,textAnchor='middle',fillColor=INK))
    return d


def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(TEAL);canvas.setLineWidth(.7);canvas.line(18*mm,18*mm,192*mm,18*mm)
    canvas.setFont('Helvetica',7.5);canvas.setFillColor(INK)
    canvas.drawString(18*mm,13*mm,'Vitaliza | S5 | Contribuição preparada para John | Corte: 30/09/2026')
    canvas.drawRightString(192*mm,13*mm,str(doc.page));canvas.restoreState()


def main():
    monthly=rows('churn_mensal');plan=rows('churn_plano_jan_set');channel=rows('churn_canal_ano')
    use=rows('churn_uso_anterior');useplan=rows('churn_uso_anterior_por_plano');price=rows('churn_periodo_reajuste')
    story=[]
    def title(t):story.append(Paragraph(t,STYLES['Section']))
    def para(t,small=False):story.append(p(t,small))
    def nextpage():story.append(PageBreak())

    story.append(p('MBA INTELI • MÓDULO 2 • SEMANA 5',True))
    story.append(Spacer(1,9*mm))
    story.append(Paragraph('Preparação dos dados<br/>e diagnóstico de churn',STYLES['Cover']))
    para('Contribuição de John para o relatório de segmentação da Vitaliza. Versão preparada para revisão e integração pelo grupo.')
    story.append(Spacer(1,4*mm))
    title('O que os dados sustentam')
    story.append(table(['Achado','Evidência','Leitura'],[
        ['Alta do churn','5,61% → 6,61% em jan–set','Piora de aproximadamente 1 ponto percentual em períodos equivalentes.'],
        ['Piora dentro dos planos','Mensal: 9,14% → 10,86%\nAnual: 2,45% → 3,32%','A mudança de composição para o anual atenua a alta agregada.'],
        ['Uso anterior associado à saída','2026: 11,18% sem treinos\n4,04% com oito ou mais','Sinal para diagnóstico; sem efeito causal demonstrado.'],
        ['Hipótese técnica a investigar','383 tickets técnicos em maio e 310 em junho/2026','Picos posteriores não explicam, sozinhos, o pico de churn de abril.'],
    ],[95,165,230]))
    story.append(Spacer(1,5*mm))
    para('<b>Base entregue:</b> 14.753 pagantes no corte, uma linha por usuário. O arquivo para Leonardo contém 17 variáveis candidatas de agrupamento e a chave de integração. Seleção das variáveis, tratamento de ausências, escalas e validação dos clusters pertencem à frente de clusterização.')
    para('<b>Escopo:</b> integração, indicadores, diagnóstico e hipóteses. O trabalho ainda não atribui clusters, prevê saída futura, estima uplift ou calcula retorno de contato.')
    para('<b>Leitura das taxas:</b> salvo indicação de média mensal simples, o churn de um período é calculado por perdas divididas por exposições usuário-mês. Exposições não são pessoas distintas.',True)
    nextpage()

    title('1. Evolução do churn')
    para('Em cada mês, o denominador é a população pagante ativa no início; o numerador contém as pessoas dessa população cuja assinatura expirou no mês. Inícios e fins dentro do próprio mês ficam fora dessa taxa.')
    story.append(chart([x['mes'][5:7]+'/'+x['mes'][2:4] for x in monthly],{'Churn observado': [float(x['churn_pct']) for x in monthly]},True,205))
    story.append(table(['Mês','Ativos no início','Perdas','Churn'],[
        [x['mes'],fmt(x['expostos'],0),fmt(x['perdas'],0),fmt(x['churn_pct'])+'%'] for x in monthly],[110,135,110,135],compact=True))
    story.append(Spacer(1,3*mm))
    para('Média mensal simples: <b>5,62% em 2025</b> e <b>6,62% em jan–set/2026</b>. O pico de abril/2026 foi de 1.154 perdas sobre 14.237 ativos (8,11%). Na comparação jan–set dos dois anos, a taxa ponderada passa de 5,61% para 6,61%.',True)
    nextpage()

    title('2. Plano, canal e composição')
    para('A piora aparece nos dois planos em meses equivalentes. O anual tem calendário de renovação diferente: sua taxa menor não é uma medida direta de maior satisfação.')
    labels=['mensal','anual']
    story.append(chart(labels,{year:[float(next(x['churn_pct'] for x in plan if x['ano']==year and x['plano']==label)) for label in labels] for year in ['2025','2026']},height=185))
    para('Gráfico acima: janeiro a setembro nos dois anos. Taxas por exposição usuário-mês.',True)
    para('<b>Decomposição da alta de aproximadamente 1,00 p.p.:</b> +1,25 p.p. vêm aritmeticamente da piora das taxas dentro dos planos; −0,25 p.p. vêm da mudança de composição. A participação do anual nas exposições cresce de 52,83% para 56,37%. A decomposição fecha a conta e não identifica causas.')
    labels=['app_store','google_play','web_cartao','web_pix']
    story.append(chart(labels,{year:[float(next(x['churn_pct'] for x in channel if x['ano']==year and x['canal_cobranca']==label)) for label in labels] for year in ['2025','2026']},height=185))
    para('Gráfico de canais: 2025 completo e janeiro–setembro/2026. Em 2026, as taxas vão de 5,96% na App Store a 7,33% no Pix. Canal pode marcar diferenças de plano, público, tempo de casa ou cobrança; a comparação bruta não isola seu efeito.',True)
    nextpage()

    title('3. Uso anterior e saída posterior')
    para('A comparação usa os treinos do mês anterior, entre pessoas que já eram pagantes no início daquele mês. Isso evita medir como antecedente uma queda de uso produzida pelo próprio cancelamento.')
    labels=['0 treinos','1–3 treinos','4–7 treinos','8+ treinos']
    story.append(chart(labels,{year:[float(next(x['churn_pct'] for x in use if x['ano']==year and x['faixa_uso_anterior']==label)) for label in labels] for year in ['2025','2026']},height=220))
    para('2025: fevereiro–dezembro; janeiro não tem uso de dezembro/2024 disponível. 2026: janeiro–setembro. A tabela abaixo separa os planos em 2026.',True)
    story.append(table(['Plano','Treinos no mês anterior','Exposições','Perdas','Churn'],[
        [x['plano'],x['faixa_uso_anterior'],fmt(x['expostos'],0),fmt(x['perdas'],0),fmt(x['churn_pct'])+'%'] for x in useplan if x['ano']=='2026'],[70,150,95,80,95]))
    story.append(Spacer(1,4*mm))
    para('O gradiente permanece dentro dos dois planos. Ainda é necessário controlar tempo de assinatura, calendário de renovação e perfil. As taxas são históricas de grupos; não são probabilidades individuais nem demonstram que aumentar treinos causa retenção.')
    para('No corte atual, 1.702 pagantes não registraram treino válido em setembro e 1.148 tinham menos de 30 dias de assinatura. São populações distintas; as janelas de uso precisam ser interpretadas junto ao tempo de exposição.',True)
    nextpage()

    title('4. Hipóteses e limites do diagnóstico')
    story.append(table(['Hipótese','Evidência','Próxima verificação'],[
        ['Baixo engajamento antecede saída','Gradiente por uso anterior persiste dentro dos planos.','Comparar coortes, tempo de casa e elegibilidade de renovação.'],
        ['Reajuste contribuiu para churn mensal','10,07% em jan–fev; 12,82% em mar–abr; 10,34% em mai–set/2026.','Separar sazonalidade, mudanças de perfil e ciclos; comparação entre períodos não basta.'],
        ['Problema técnico afetou retenção','Tickets técnicos aumentam de 19 em abril para 383 em maio e 310 em junho.','Ligar abertura anterior à saída e tema do ticket. Não presumir versão histórica do app.'],
        ['Canal indica fricções ou públicos diferentes','Taxas de canal distintas em 2026.','Separar plano, perfil e saída por falha de pagamento.'],
    ],[100,180,210]))
    story.append(Spacer(1,5*mm))
    para('<b>Fontes de uso não conciliadas:</b> 6.716 linhas de setembro diferem entre BI e atividade tratada, incluindo 5.542 pagantes atuais. A diferença não foi atribuída apenas a duplicatas. O histórico identifica a fonte BI; as variáveis recomendadas para clusterização usam a atividade tratada e duas janelas iguais de 30 dias para medir tendência.')
    para('<b>Renovação automática:</b> cinco divergências conhecidas entre eventos e retrato; em 1.112 ativos os eventos relevantes não informam o estado inicial. Os campos ficam separados, com ausências e sinalização, e fora dos candidatos ao agrupamento.')
    para('<b>Viés da pesquisa:</b> cancelamento no site e resposta opcional limitam a representatividade. Renovação desligada não equivale a perda de assinatura. Associação de uso, preço ou suporte com churn não identifica, isoladamente, causa.')
    para('<b>Valor:</b> a última cobrança aprovada, dividida por 12 no anual, é uma aproximação mensal descritiva. Não é receita contábil, LTV nem retorno de retenção. Estornos, chargebacks, ofertas e custo de servir precisam de tratamento próprio.')
    nextpage()

    title('5. Método, validação e encaminhamento')
    para('<b>Reconstrução temporal.</b> Eventos fornecem início e expiração. Assinaturas anteriores a 01/07/2024 usam o início do retrato como semente. A base atual contém uma assinatura por conta, sem troca de plano/canal nos eventos; essas condições são verificadas. Contas de teste são excluídas pelo e-mail normalizado.')
    para('<b>Tratamento.</b> Horários são convertidos para Brasília e limitados a 30/09/2026. Foram removidas 9.383 cópias de treinos do relógio no app. Duração inválida fica marcada e fora dos agregados válidos; 999 distâncias incompatíveis e três altas sem avaliação por ritmo ficam nulas. A regra não altera os arquivos originais.')
    para('<b>Cobertura.</b> Em 2025, ausência de linha no BI é tratada como zero treino somente dentro da cobertura e população definidas. Sessões do app ausentes nos meses sem treino de 2025 continuam ausentes. Janeiro/2025 não recebe uso anterior inventado.')
    para('<b>Validação.</b> Fechamento nas âncoras oficiais, soma por plano/canal, três assinantes e três expirações confrontados com o retrato, testes das regras temporais e hashes dos 11 arquivos brutos utilizados antes e depois. Dados individuais e amostras ficam fora do Git.')
    story.append(table(['Frente','Material de apoio'],[
        ['Leonardo','Base por pagante, 17 variáveis candidatas e dicionário; selecionar, tratar ausências e validar os grupos.'],
        ['Claudinne','Filtros, auditoria por coluna, alertas e decisões de tratamento.'],
        ['Kiril','Diagnóstico e hipóteses; personas dependem dos clusters e de evidências observadas.'],
        ['Marcela','Plano, canal, indicadores e aproximações financeiras identificadas; completar custos e valor.'],
        ['John','Síntese editável, método, tabelas, gráficos e roteiro de estudo para integrar o relatório.'],
    ],[85,405]))
    story.append(Spacer(1,5*mm))
    para('<b>Rastreabilidade:</b> docs/enunciado.md; docs/dicionario_dados.md; decisoes.md; src/preparar_diagnostico_s5.py. Tabelas e textos completos em dados/saidas/s5_john/. Bases individuais e manifesto em dados/processados/s5_john/.',True)
    para('<b>Pendente do grupo:</b> clusters, personas e priorização final. Para medir churn por cluster, aplicar a segmentação a observações históricas compatíveis; grupos feitos só com sobreviventes no corte não identificam diretamente os perfis de quem já saiu.',True)

    dest=OUT/'John_Preparacao_Diagnostico_S5.pdf'
    doc=SimpleDocTemplate(str(dest),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=23*mm,
        title='Vitaliza — Preparação dos dados e diagnóstico — John',author='Contribuição preparada para John Neto')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(dest)


if __name__=='__main__':
    main()
