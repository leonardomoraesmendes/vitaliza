"""Validação final dos arquivos, privacidade do pacote e entropia editorial.

Entropia é avaliada aqui como dispersão, repetição e ambiguidade da informação;
não se atribui uma nota estatística de qualidade a uma contagem de palavras.
"""
from collections import Counter
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dados/saidas/s5_john'


def main():
    completed=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True,check=True)
    test_count=int(re.search(r'Ran (\d+) tests?',completed.stderr).group(1))
    manifest=json.loads((ROOT/'dados/processados/s5_john/manifesto_validacao.json').read_text())
    assert manifest['assinantes_corte']==14753
    assert len(manifest['sha256_brutos'])==11
    docs=['sintese_para_relatorio.md','diagnostico.md','dicionario_base_analitica.md','LEIA-ME.md']
    paragraph_counts=Counter()
    for name in docs:
        text=(OUT/name).read_text()
        assert not re.search(r'\b(TODO|TBD|FIXME)\b',text)
        for block in text.split('\n\n'):
            if len(block)>100 and not block.startswith(('#','|','```')):
                paragraph_counts[re.sub(r'\s+',' ',block.strip())]+=1
    duplicates=[k for k,v in paragraph_counts.items() if v>1]
    assert not duplicates,'Parágrafos repetidos: revisar redundância'
    for path in OUT.iterdir():
        if path.suffix in {'.md','.csv','.svg'}:
            assert not re.search(r'\bu_[0-9a-f]{8}\b',path.read_text()),f'Identificador individual em {path}'
    figures=sorted(OUT.glob('*.svg'))
    assert len(figures)==4
    for path in figures:
        root=ET.parse(path).getroot()
        assert root.attrib.get('aria-label')
    for path in (ROOT/'notebooks').glob('*.ipynb'):
        for cell in json.loads(path.read_text())['cells']:
            if cell['cell_type']=='code':
                assert not cell.get('outputs'),f'Notebook com saídas: {path}'
    pdf=OUT/'John_Preparacao_Diagnostico_S5.pdf'
    assert pdf.exists() and pdf.stat().st_size>10000
    contents=(OUT/'diagnostico.md').read_text()
    for necessary in ['Hipóteses','Fontes']:
        assert necessary.lower() in (OUT/'sintese_para_relatorio.md').read_text().lower()
    assert 'mês anterior' in contents and 'exposições' in contents
    review=f'''# Revisão de qualidade e análise de entropia — entrega de John

## Cobertura e rastreabilidade

- Base final: {manifest['assinantes_corte']} pagantes; painel: {manifest['exposicoes_painel']} exposições usuário-mês.
- Onze fontes brutas com hashes preservados antes e depois da preparação.
- {test_count} testes de regras temporais, moeda, ausência, denominadores e deduplicação executados com sucesso.
- Três assinantes ativos e três expirações confrontados com a fonte independente do retrato; âncoras oficiais e somas por plano/canal conferidas.
- Quatro gráficos com rótulos de acesso, tabelas com denominadores e dicionário completo das variáveis.
- Pacote textual sem identificadores individuais; notebooks sem saídas. Bases individuais e conferências permanecem na pasta ignorada de dados.

## Análise de entropia editorial

Critério adotado: verificar se a informação necessária está concentrada, compreensível e acompanhada de evidência, com repetições e ambiguidades controladas. A avaliação é editorial; não se converte a frequência de palavras em uma suposta nota de qualidade.

| Aspecto | Verificação | Resultado |
|---|---|---|
| Dispersão | Um texto curto para integração, um método completo, tabelas separadas e roteiro de estudo | Cada arquivo tem função identificada no LEIA-ME |
| Redundância | Parágrafos idênticos acima de 100 caracteres nos quatro documentos principais | {len(duplicates)} repetições exatas; reiterar limites essenciais junto aos resultados é intencional |
| Ambiguidade de população | Ativos no início do mês, pagantes no corte e respostas à pesquisa identificados separadamente | Denominadores nomeados; exposições não são pessoas distintas |
| Ambiguidade temporal | Corte, janelas de 30/90 dias e mês anterior especificados | Sem informação posterior ao corte nos indicadores temporais utilizados |
| Causalidade | Evidências e hipóteses separadas; próximos testes identificados | Associações não apresentadas como efeito causal |
| Incerteza preservada | BI/detalhe e renovação mantidos como fontes distintas | Pendências explícitas, sem ajuste para forçar concordância |
| Dependências | Clusters, personas, priorização e consolidação coletiva ainda dependem das demais frentes | Contribuição de John identificada; relatório do grupo não declarado concluído |

## Limitações residuais

Continuam abertas a conciliação de fontes de uso, as divergências de renovação e a explicação causal da piora. O agrupamento e sua validação pertencem a Leonardo. A prova de resultado desta entrega é descritiva e de preparação, dentro do corte do case.

O PDF deve receber conferência visual após cada nova exportação. As verificações automáticas acima não substituem essa leitura.
'''
    (OUT/'revisao_qualidade_entropia.md').write_text(review)
    print('Arquivos, identificadores, gráficos, notebooks e entropia editorial: verificados.')


if __name__=='__main__':main()
