"""Gera o PDF unico da entrega a partir do banco, das figuras e de config/entrega.json.

Uso: python scripts/03_pdf.py
"""
import inspect

import pandas as pd
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from zeladoria import assistente, config, db, etl, indicadores  # noqa: E402

E = json.loads((RAIZ / "config" / "entrega.json").read_text(encoding="utf-8"))
R = json.loads((config.DIR_PROC / "resumo.json").read_text(encoding="utf-8"))
AZUL = colors.HexColor("#111111")
OURO = colors.HexColor("#B08D5E")

ss = getSampleStyleSheet()
N = ParagraphStyle("n", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica", fontSize=17, textColor=AZUL, spaceBefore=10, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica", fontSize=12, textColor=OURO) if False else ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, textColor=AZUL, spaceBefore=8, spaceAfter=4)
LEG = ParagraphStyle("leg", parent=N, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
COD = ParagraphStyle("cod", fontName="Courier", fontSize=6.8, leading=8.4, backColor=colors.HexColor("#F5F4F0"),
                     borderPadding=5, spaceAfter=8, spaceBefore=2)
CAPA = ParagraphStyle("capa", parent=ss["Title"], fontName="Helvetica", fontSize=34, textColor=AZUL, spaceAfter=16, leading=32)
CEN = ParagraphStyle("cen", parent=N, alignment=TA_CENTER, fontSize=11, leading=16)


def p(t):
    return Paragraph(t, N)


def pct(v, casas=0):
    return f"{100 * v:.{casas}f}%".replace(".", ",")


def num(v, casas=2):
    return f"{v:.{casas}f}".replace(".", ",")


def mil(v):
    return f"{int(v):,}".replace(",", ".")


def tabela(dados, larguras=None, fonte=7.8):
    cel = ParagraphStyle("cel", parent=N, fontSize=fonte, leading=fonte + 2, spaceAfter=0)
    cab = ParagraphStyle("cab", parent=cel, textColor=colors.white, fontName="Helvetica-Bold")
    linhas = [[Paragraph(str(c), cab) for c in dados[0]]] + \
             [[Paragraph(str(c), cel) for c in l] for l in dados[1:]]
    t = Table(linhas, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F4F0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return t


def figura(nome, largura_cm, legenda):
    from PIL import Image as PI
    cam = config.DIR_ASSETS / nome
    w, h = PI.open(cam).size
    larg = largura_cm * cm
    teto = 22.3 * cm                      # altura util da pagina, com folga para titulo e legenda
    if larg * h / w > teto:
        larg = teto * w / h
    return [Image(str(cam), width=larg, height=larg * h / w), Paragraph(legenda, LEG)]


def codigo(obj, max_linhas=60):
    fonte = inspect.getsource(obj).rstrip().split("\n")[:max_linhas]
    return Preformatted("\n".join(l[:118] for l in fonte), COD)


def montar():
    dist = db.ler("SELECT * FROM res_distrito ORDER BY indice")
    amp = db.ler("SELECT * FROM res_servico_amplitude ORDER BY demandas DESC")
    met = db.ler("SELECT * FROM res_modelos")
    funil = db.ler("SELECT etapa, linhas FROM auditoria_funil ORDER BY ordem")
    arqs = db.ler("SELECT * FROM auditoria_arquivo ORDER BY abertura_min")
    reco = db.ler("SELECT * FROM res_recomendador")
    kk = db.ler("SELECT * FROM res_kmeans_k")
    g, J = R["geral"], config.JANELA_DIAS
    arv = amp[amp["servico"].str.startswith("Árvore - Solicitar avaliação")].iloc[0]
    gui = amp[amp["servico"].str.startswith("Guias, sarjetas")].iloc[0]
    ent = amp[amp["servico"].str.startswith("Entulho")].iloc[0]
    tb = amp[amp["servico"] == "Tapa-buraco"].iloc[0]
    gb = met.set_index("modelo")
    s = []

    # ---------------------------------------------------------------- capa
    s += [Spacer(1, 3.2 * cm), Paragraph("FIAP · Global Solution 2026.2 · CitizenTech", CEN),
          Paragraph("Graduação em Inteligência Artificial · Fase 7", CEN), Spacer(1, 1.2 * cm),
          Paragraph(E.get("categoria", "").upper(), ParagraphStyle("eye", parent=CEN, fontSize=9, textColor=OURO)),
          Paragraph(E["titulo"], CAPA), Paragraph(f"<b>{E.get('assinatura', '')}</b>", CEN),
          Paragraph(E["subtitulo"], CEN), Spacer(1, .5 * cm),
          Paragraph(" · ".join(x.upper() for x in E.get("pilares", [])),
                    ParagraphStyle("pil", parent=CEN, fontSize=8.5, textColor=colors.grey)),
          Spacer(1, 1.2 * cm),
          Paragraph("<b>Integrantes</b>", CEN)]
    for i in E["integrantes"]:
        s.append(Paragraph(f"{i['nome']} · {i['rm']}", CEN))
    s += [Spacer(1, .4 * cm), Paragraph(f"<b>Turma:</b> {E['turma']} · <b>{E['grupo']}</b>", CEN)]
    if E.get("quero_concorrer"):
        s += [Spacer(1, 1.2 * cm), Paragraph("<b>QUERO CONCORRER</b>", CEN)]
    s += [Spacer(1, 2.2 * cm), Paragraph("Novembro de 2026", CEN), PageBreak()]

    # ---------------------------------------------------------------- resumo visual
    s += [Paragraph("Resumo visual", H1)]
    s += figura("tela0_inicio.png", 15.6,
                "Aba Visão geral da aplicação, em execução sobre o banco real: resumo executivo dos achados.")
    s += [PageBreak()]

    # ---------------------------------------------------------------- 1
    s += [Paragraph("1. Introdução", H1), p(
        "A zeladoria urbana afeta diretamente a segurança, a mobilidade e a qualidade de vida de quem vive "
        "em São Paulo. Um buraco na rua, uma árvore que precisa de poda ou um bueiro entupido pode parecer "
        "um problema pontual, mas, quando o atendimento demora ou varia muito entre distritos, o impacto "
        "recai sobre milhares de pessoas, e pode se tornar um sinal de desigualdade no acesso aos serviços "
        "públicos."),
        p("Hoje, o morador pode registrar uma solicitação pelo SP156, mas tem pouca informação para entender "
          "qual serviço escolher, qual prazo esperar ou como o atendimento se compara ao de outros lugares "
          "da cidade. A gestão, por sua vez, dispõe de dados, mas precisa interpretá-los sem deixar que "
          "diferenças entre os tipos de serviço ou pedidos ainda em aberto distorçam a análise."),
        p(f"A dimensão do problema aparece nos dados: entre <b>{mil(g['demandas'])} demandas de zeladoria</b> "
          f"analisadas, abertas de janeiro a setembro de 2026, a proporção finalizada em até {J} dias variou "
          f"de {pct(R['taxa_bruta']['min'])} a {pct(R['taxa_bruta']['max'])} entre distritos. Para pedidos de "
          f"avaliação de poda de árvore, a diferença foi ainda maior: de {pct(arv['p10'])} no distrito do "
          f"percentil 10 a {pct(arv['p90'])} no do percentil 90. Esses números mostram que conhecer o volume "
          "de solicitações não basta. É necessário identificar onde o atendimento demora mais para serviços "
          "equivalentes e oferecer informação compreensível a quem precisa agir ou cobrar soluções."),
        p(f"É para responder a essa necessidade que propomos o <b>{E['titulo']}</b>: uma plataforma que "
          "transforma dados públicos em informação útil para moradores e gestores. A solução compara prazos "
          "de forma mais justa, destaca combinações de serviço e distrito que merecem atenção e ajuda o "
          "cidadão a encontrar o serviço adequado e consultar um prazo provável. Assim, a tecnologia "
          "contribui para que a zeladoria seja acompanhada com mais transparência, prioridade e "
          "responsabilidade pública."),
        Paragraph("1.1 Público beneficiado e atores", H2), p(
        "<b>Morador de São Paulo</b> que precisa abrir um pedido de zeladoria e não conhece o nome "
        "administrativo do serviço nem o prazo provável. <b>Lideranças comunitárias, conselhos "
        "participativos e imprensa local</b>, que precisam de evidência comparável entre territórios para "
        "cobrar o poder público. <b>Gestores de subprefeituras e da zeladoria municipal</b>, que podem "
        "identificar em quais serviços e distritos o atendimento destoa da cidade. A Prefeitura é a "
        "fornecedora dos dados (SMIT, Portal de Dados Abertos) e a executora dos serviços."),
        Paragraph("1.2 Objetivo", H2), p(
        "Construir uma prova de conceito que (a) meça a desigualdade territorial no prazo de atendimento "
        "de zeladoria com método que resista a crítica técnica, (b) aponte à prefeitura onde agir primeiro: "
        "quais combinações de serviço e distrito concentram o atraso, quais pedidos já passaram do prazo "
        "típico e onde vários moradores pedem a mesma coisa, (c) entregue ao morador o serviço correto e o "
        "prazo provável no distrito dele a partir de uma descrição em linguagem comum e (d) faça isso com "
        "dados públicos reais, código reproduzível e limites declarados."),
        Paragraph("1.3 Objetivos de Desenvolvimento Sustentável", H2), p(
        "<b>ODS 11, Cidades e comunidades sustentáveis.</b> Zeladoria é a manutenção do espaço urbano "
        "compartilhado. A solução apoia gestão urbana baseada em evidência e participação informada do "
        "morador. <b>ODS 10, Redução das desigualdades.</b> O indicador central mede se o serviço público "
        "chega no mesmo ritmo a territórios diferentes. <b>ODS 16, Paz, justiça e instituições eficazes.</b> "
        "A solução transforma dado aberto em transparência utilizável sobre o desempenho de um serviço "
        "público.")]

    # ---------------------------------------------------------------- 2
    s += [Paragraph("2. Desenvolvimento", H1), Paragraph("2.1 Visão geral do funcionamento", H2), p(
        "A solução tem quatro camadas. <b>Dados:</b> três arquivos trimestrais do SP156 são lidos, "
        "validados e carregados em um banco relacional SQLite com modelo dimensional. <b>Análise:</b> "
        "indicadores de prazo com tratamento de censura, índice de equidade padronizado e agrupamento de "
        "distritos. <b>Modelos:</b> classificadores que estimam a chance de finalização em 30 dias e um "
        "recomendador de serviço por similaridade de texto. <b>Aplicação:</b> painel Streamlit com mapa, "
        "comparação entre distritos e um fluxo para o morador, com assistente de orientação restrito aos "
        "fatos calculados."),
        *figura("fig0_arquitetura.png", 16.5, "Diagrama de arquitetura: do dado aberto ao uso pelo morador e pelo gestor."),
        tabela([["Disciplina ou conteúdo", "Onde foi aplicado", "Por quê"],
                ["Python e engenharia de software", "Pacote modular src/zeladoria, exceções próprias, logging, scripts de execução",
                 "Reprodutibilidade: o resultado inteiro é regenerado com três comandos"],
                ["Tratamento e análise exploratória de dados", "ETL com detecção de formato, funil de qualidade, pandas",
                 "Os arquivos do portal têm formatos incompatíveis entre si"],
                ["Banco de dados relacional e SQL", "Modelo dimensional com 3 dimensões e 1 fato, restrições CHECK e chaves estrangeiras, visão e 5 consultas analíticas",
                 "Integridade garantida pelo banco, não só pelo código"],
                ["Estatística", "Kaplan-Meier, padronização indireta, intervalo de confiança, Spearman",
                 "Média simples de prazo é enviesada quando há demandas em aberto"],
                ["Machine Learning não supervisionado", "K-Means com escolha de k por silhueta", "Segmentar distritos por perfil de demanda e atendimento"],
                ["Machine Learning supervisionado", "Regressão logística e gradient boosting com validação temporal",
                 "Estimar chance de finalização e medir o quanto o distrito acrescenta"],
                ["Redes neurais", "MLP (32,16) comparada aos demais modelos", "Verificar se um modelo não linear justifica a complexidade"],
                ["Análise de sobrevivência preditiva", "Alerta antecipado: chance de um pedido em aberto passar de 30 dias, dada a idade dele, com simulação em seis datas passadas",
                 "Transformar o diagnóstico em previsão acionável e validada"],
                ["Sistemas de recomendação e PLN", "TF-IDF de palavras e caracteres com similaridade de cosseno e léxico curado",
                 "Ligar a linguagem do morador ao catálogo administrativo"],
                ["IA generativa", "Redação da orientação a partir de uma ficha de fatos, com verificador de números",
                 "Linguagem acessível sem risco de prazo inventado"],
                ["Cibersegurança e LGPD", "Minimização de dados, mascaramento de CPF, telefone e e-mail, SQL parametrizado, conexão somente leitura, log sem conteúdo",
                 "O morador digita texto livre em um serviço público"],
                ["Visualização interativa", "Streamlit e Plotly: mapa, barras, curvas de permanência", "Tornar o resultado explorável por não técnicos"]],
               [4.0 * cm, 7.4 * cm, 5.6 * cm]),
        Paragraph("Tabela 1. Integração entre disciplinas.", LEG),
        Paragraph("2.2 Origem dos dados", H2), p(
        "Fonte: Portal de Dados Abertos da Prefeitura de São Paulo, conjunto <i>Dados do SP156 - "
        "Solicitações</i>, mantido pela Secretaria Municipal de Inovação e Tecnologia, disponível em "
        "dados.prefeitura.sp.gov.br/dataset/dados-do-sp156. Foram usados os arquivos CSV do 1º, 2º e 3º "
        "trimestres de 2026, baixados em 18/11/2026. Cada linha é uma solicitação, com 15 colunas: datas de "
        "abertura e de finalização, canal, tema, assunto, serviço, status, órgão, endereço, coordenadas, "
        "subprefeitura e distrito. Não há dado pessoal do solicitante nem identificador de protocolo."),
        tabela([["Arquivo", "Codificação", "Separador", "Formato de data", "Linhas", "Abertura", "Data de corte"]] +
               [[a.arquivo, a.codificacao, a.separador, a.formato_data.replace("%", ""), mil(a.linhas),
                 f"{a.abertura_min} a {a.abertura_max}", a.data_corte] for a in arqs.itertuples()],
               [4.1 * cm, 1.8 * cm, 1.6 * cm, 2.2 * cm, 1.6 * cm, 3.9 * cm, 1.9 * cm], 7.2),
        Paragraph("Tabela 2. Perfil detectado de cada arquivo. O terceiro trimestre é publicado em formato diferente.", LEG),
        Paragraph("2.3 Qualidade e limitações dos dados encontradas", H2), p(
        "<b>Formatos incompatíveis.</b> Os dois primeiros arquivos usam ponto e vírgula, codificação "
        "Windows-1252 e datas no padrão dia/mês/ano. O terceiro usa vírgula, UTF-8 e mês/dia/ano. Ler o "
        "terceiro com o padrão brasileiro não gera erro em parte das linhas: gera datas trocadas. O "
        "tratamento detecta e valida o formato de cada arquivo e interrompe a carga se houver ambiguidade."),
        p("<b>Serviços duplicados por grafia.</b> O travessão dos nomes de serviço vira caractere de controle "
          "se o arquivo for lido como Latin-1, e o mesmo serviço aparece duas vezes. A leitura em "
          "Windows-1252 e a normalização de texto reduziram o catálogo do recorte de 67 para 64 serviços."),
        p("<b>Demandas em aberto (censura).</b> "
          f"{pct(g['pct_aberta'])} das demandas ainda estavam em aberto na data de corte do arquivo. Além "
          "disso, os arquivos têm tempos de observação diferentes: os dois primeiros trimestres foram "
          "observados até agosto e o terceiro até outubro. Calcular a média de prazo só das finalizadas "
          "subestimaria o prazo e favoreceria o período mais recente."),
        p("<b>Data de extração ausente.</b> O portal não informa quando cada arquivo foi extraído. Adotamos "
          "a maior data de finalização de cada arquivo como data de corte, que é o limite inferior da data "
          "real."),
        p(f"<b>Registros repetidos.</b> Há linhas idênticas nas 15 colunas, em alguns casos mais de cem no "
          f"mesmo endereço e dia. Sem protocolo, não é possível distinguir vários moradores de uma carga em "
          f"lote. Tratamos linhas idênticas como uma demanda e preservamos a contagem. O ranking de "
          f"distritos praticamente não muda sem essa regra (Spearman "
          f"{num(R['sensibilidade_repetidos_spearman'])} entre as duas versões do índice)."),
        p("<b>Distrito ausente ou codificado.</b> Em temas não territoriais o distrito é vazio, e em parte "
          "dos registros de Ouvidoria SUS ele aparece como código numérico. Esses códigos não seguem a "
          "ordem alfabética dos distritos, o que verificamos cruzando CEP. No recorte de zeladoria o "
          "distrito está preenchido em mais de 99% das linhas."),
        Paragraph("2.4 Tratamento", H2), p(
        "O recorte de zeladoria reúne 15 assuntos com execução física no território: entulho, reparo de "
        "asfalto, árvore, capinação e roçada, drenagem, varrição, guias e calçadas, coleta, lixeiras, "
        "praças, córregos, vielas e escadarias. Ficaram fora fiscalização (poluição sonora, ambulantes), "
        "certidões e ouvidorias. Cada exclusão é registrada em uma tabela de auditoria no próprio banco."),
        tabela([["Etapa", "Linhas"]] + [[e.replace("_", " "), mil(l)] for e, l in funil.itertuples(index=False)],
               [8 * cm, 3 * cm]),
        Paragraph("Tabela 3. Funil de tratamento, gravado na tabela auditoria_funil.", LEG),
        Paragraph("2.5 Modelagem do banco", H2), p(
        "Banco SQLite com modelo dimensional: <b>dim_distrito</b> (96 linhas, com centróide e distância ao "
        "centro), <b>dim_servico</b> (64), <b>dim_canal</b> e <b>fato_demanda</b>. O banco rejeita por "
        "restrição CHECK uma demanda finalizada sem data, prazo negativo ou demanda marcada como resolvida "
        "sem estar finalizada. Logradouro, número e CEP não são persistidos e a coordenada é arredondada a "
        "três casas decimais, cerca de 100 metros. A visão vw_demanda desnormaliza para análise. SQLite foi "
        "escolhido por ser um arquivo único, o que permite ao avaliador rodar o projeto sem instalar "
        "servidor. O esquema usa SQL padrão e migra para Oracle ou PostgreSQL com ajuste de tipos."),
        Paragraph("2.6 Método de medição do prazo", H2), p(
        f"<b>Taxa de finalização em {J} dias.</b> Só entram demandas observadas por pelo menos {J} dias, "
        "para que toda demanda tenha tido a mesma oportunidade de ser finalizada. <b>Mediana e percentil "
        "80.</b> Calculados pelo estimador de Kaplan-Meier, que usa a informação das demandas em aberto em "
        "vez de descartá-las. Quando mais da metade segue em aberto, a mediana é reportada como não "
        "atingida, e não como um número."),
        p("<b>Índice de equidade.</b> Distritos pedem serviços diferentes, e cada serviço tem um prazo "
          f"típico: remoção de entulho é finalizada em {J} dias em {pct(ent['mediana'])} dos casos no "
          f"distrito mediano, manutenção de guias e sarjetas em {pct(gui['mediana'])}. Comparar taxas brutas "
          "entre distritos mistura desempenho com composição da demanda. O índice divide o número de "
          "demandas finalizadas na janela pelo número esperado se cada serviço pedido no distrito tivesse a "
          "taxa média da cidade (padronização indireta). Índice 1,00 significa desempenho igual ao da "
          "cidade para o mesmo conjunto de serviços."),
        Paragraph("2.7 Códigos principais", H2), p(
        "<b>Detecção do formato de data</b> (src/zeladoria/etl.py). Testa os dois formatos e só aceita se "
        "exatamente um deles produzir todas as datas válidas, período de abertura dentro de um trimestre "
        "e nenhuma finalização anterior à abertura. Se os dois ou nenhum passarem, levanta ErroDeDados."),
        codigo(etl.detectar_formato_data),
        p("<b>Kaplan-Meier</b> (src/zeladoria/indicadores.py). Para cada dia com evento, multiplica a "
          "fração que continua em aberto entre as demandas ainda em risco naquele dia."),
        codigo(indicadores.kaplan_meier), codigo(indicadores.percentil_km),
        p("<b>Índice padronizado</b>. A coluna esperado soma, para cada demanda do distrito, a taxa da "
          "cidade para aquele serviço."),
        codigo(indicadores.indice_por_distrito),
        p("<b>Alerta antecipado</b>. Para cada pedido em aberto, busca a curva de sobrevivência do par "
          "serviço e distrito, recua para a do serviço quando falta volume, e devolve S(30) dividido por S(k)."),
        codigo(indicadores.prob_passar_da_janela),
        p("<b>Trava da IA generativa</b> (src/zeladoria/assistente.py). O modelo de linguagem recebe uma "
          "ficha de fatos em JSON e a instrução de usar somente esses fatos. A resposta é comparada com a "
          "ficha: se contiver qualquer número ausente dela, é descartada e o sistema usa a redação "
          "determinística. O relato do morador é higienizado antes e nunca entra na instrução de sistema."),
        codigo(assistente.numeros_fora_da_ficha), codigo(assistente.responder),
        Paragraph("2.8 Segurança e privacidade", H2), p(
        "O texto do morador nunca é concatenado em SQL: todas as consultas com entrada externa são "
        "parametrizadas e a aplicação lê o banco por conexão somente leitura. O texto é limitado a 300 "
        "caracteres, tem caracteres de controle removidos e CPF, telefone e e-mail mascarados antes de "
        "qualquer uso, com aviso ao usuário. O log de uso guarda serviço, distrito e tamanho do texto, "
        "nunca o conteúdo. A chave da API de IA generativa é lida de variável de ambiente e não é "
        "versionada. O banco não guarda endereço.")]

    # ---------------------------------------------------------------- 3
    s += [PageBreak(), Paragraph("3. Resultados obtidos", H1),
          Paragraph("3.1 A desigualdade existe e é estável", H2), p(
        f"O índice de equidade varia de <b>{num(R['indice']['min'])}</b> a <b>{num(R['indice']['max'])}</b> "
        f"entre os 96 distritos, com 80% deles entre {num(R['indice']['p10'])} e {num(R['indice']['p90'])}. "
        "Não é ruído de um período: calculado separadamente por trimestre, o ordenamento dos distritos se "
        f"mantém (Spearman {num(R['estabilidade_spearman']['t1_t2'])} entre o 1º e o 2º trimestres e "
        f"{num(R['estabilidade_spearman']['t2_t3'])} entre o 2º e o 3º). Com janela de 60 dias em vez de 30 "
        f"o ordenamento também se mantém (Spearman {num(R['sensibilidade_janela60_spearman'])})."),
        tabela([["Menores índices", "Índice", f"% em {J}d", "Mediana (dias)", "Maiores índices", "Índice",
                 f"% em {J}d", "Mediana (dias)"]] +
               [[a.distrito.title(), num(a.indice), pct(a.taxa_bruta), int(a.p50_dias),
                 b.distrito.title(), num(b.indice), pct(b.taxa_bruta), int(b.p50_dias)]
                for a, b in zip(dist.head(8).itertuples(), dist.tail(8).iloc[::-1].itertuples())],
               [3.4 * cm, 1.4 * cm, 1.5 * cm, 2.1 * cm, 3.6 * cm, 1.4 * cm, 1.5 * cm, 2.1 * cm]),
        Paragraph("Tabela 4. Distritos nos extremos do índice de equidade, janeiro a setembro de 2026.", LEG)]
    s += figura("fig4_estabilidade.png", 7.2, "Figura 1. Índice por distrito no 2º e no 3º trimestres.")
    _d = db.demandas()
    _e = _d[_d["elegivel_janela"] == 1]
    _c = _e.groupby("servico").agg(v=("resolvida_janela", "size"), a=("resolvida_janela", lambda x: (1 - x).sum()))
    _c = _c.sort_values("a", ascending=False)
    _v3, _a3 = _c["v"].head(3).sum() / _c["v"].sum(), _c["a"].head(3).sum() / _c["a"].sum()
    _med = {k: indicadores.percentil_km(q["dias"], q["finalizada"], 0.5) for k, q in _d.groupby("servico")}
    _vol = _d["servico"].value_counts()
    _rap = sum(_vol[k] for k, m in _med.items() if m is not None and m <= 3) / _vol.sum()
    _len = sum(_vol[k] for k, m in _med.items() if m is None or m > 30) / _vol.sum()
    _p80 = indicadores.percentil_km(_d["dias"], _d["finalizada"], 0.8)
    s += [Paragraph("3.2 Ela se concentra em poucos serviços", H2), p(
        f"<b>Três serviços respondem por {pct(_a3)} do atraso.</b> Tapa-buraco, avaliação de poda de árvore e "
        f"manutenção de guias e sarjetas somam {pct(_v3)} dos pedidos e {pct(_a3)} dos pedidos não finalizados "
        f"em {J} dias. A zeladoria opera em duas velocidades: {pct(_rap)} do volume está em serviços com "
        f"mediana de até 3 dias, e {pct(_len)} em serviços cuja mediana passa de {J} dias. Por isso a mediana "
        f"geral, de {int(g['p50_dias'])} dias, esconde a cauda: um em cada cinco pedidos fica em aberto por "
        f"mais de {int(_p80)} dias."), p(
        f"Serviços executados por contratos de escala são quase uniformes na cidade: remoção de entulho "
        f"tem {num(100 * ent['amplitude_p90_p10'], 0)} pontos percentuais entre o distrito no percentil 10 e "
        f"o no percentil 90. Em avaliação de poda de árvore a diferença é de "
        f"<b>{num(100 * arv['amplitude_p90_p10'], 0)} pontos</b> ({pct(arv['p10'])} contra {pct(arv['p90'])}), "
        f"em manutenção de guias e sarjetas de <b>{num(100 * gui['amplitude_p90_p10'], 0)} pontos</b> "
        f"({pct(gui['p10'])} contra {pct(gui['p90'])}) e em tapa-buraco de "
        f"{num(100 * tb['amplitude_p90_p10'], 0)} pontos. A implicação prática é que uma política de "
        "equalização não precisa atuar sobre toda a zeladoria: precisa atuar sobre poucos serviços.")]
    s += figura("fig2_servico_distritos.png", 14.5,
                "Figura 2. Distribuição, entre distritos, da taxa de finalização em 30 dias para os oito serviços de maior volume.")
    s += figura("fig5_km_tapa_buraco.png", 10.5,
                "Figura 3. Tapa-buraco nos distritos com menor e maior taxa de finalização, com a curva da cidade.")
    ce = R["centralidade"]
    s += [Paragraph("3.3 Ela não segue a lógica centro e periferia", H2), p(
        "A hipótese inicial do projeto era que distritos periféricos seriam atendidos mais lentamente. "
        f"<b>Os dados não sustentam essa hipótese.</b> A correlação entre o índice e a distância à Praça da "
        f"Sé é fraca e de sinal contrário ao esperado (Spearman {num(ce['spearman_indice_x_distancia'])}, "
        f"p = {num(ce['p_valor'], 3)}). Entre os menores índices há distritos centrais e de alta renda, "
        "como Perdizes, Moema e Vila Leopoldina, ao lado de distritos da zona leste, como Parque do Carmo "
        "e Cidade Líder."),
        p("Essa leitura tem limites que impedem concluir que a periferia é mais bem atendida. A base só "
          "registra o que foi pedido: onde o morador registra menos, ou desiste de registrar, o problema "
          "não aparece. Finalizada significa encerramento administrativo, não execução confirmada. E "
          "distância ao centro é uma aproximação grosseira de condição socioeconômica. O resultado "
          "sustentado é mais restrito: a desigualdade de prazo existe, é persistente e não se explica por "
          "centralidade.")]
    s += figura("fig3_centralidade.png", 9.5, "Figura 4. Índice de equidade e distância ao centro. Cada ponto é um distrito.")
    P = R["prioridade"]
    pares = db.ler("SELECT * FROM res_prioridade ORDER BY posicao LIMIT 10")
    s += [Paragraph("3.4 Onde agir primeiro", H2), p(
        "Informar o prazo ao morador não reduz o prazo. A parte do sistema voltada à gestão transforma "
        "o diagnóstico em ordem de ação, com três leituras."),
        p(f"<b>Atraso evitável.</b> Para cada combinação de serviço e distrito abaixo do distrito mediano "
          f"da cidade naquele serviço, calculamos quantos pedidos a mais seriam finalizados em {J} dias se "
          f"ela alcançasse essa referência, que metade dos distritos já atinge. O total é de "
          f"<b>{mil(round(P['ganho_total']))} pedidos</b>, e ele é concentrado: das {mil(P['pares_avaliados'])} "
          f"combinações com volume suficiente, <b>20 respondem por {pct(P['acum_20'])}</b>, 50 por "
          f"{pct(P['acum_50'])} e <b>100 por {pct(P['acum_100'])}</b>. É uma conta de ordem de grandeza "
          "para priorizar, não uma previsão: ela não sabe por que a combinação está abaixo da referência."),
        tabela([["#", "Serviço", "Distrito", "Pedidos", f"% em {J}d", "Referência", "Pedidos a mais"]] +
               [[a.posicao, a.servico[:46], a.distrito.title(), mil(a.elegiveis), pct(a.taxa),
                 pct(a.referencia), mil(round(a.ganho))] for a in pares.itertuples()],
               [0.9 * cm, 6.4 * cm, 2.9 * cm, 1.5 * cm, 1.5 * cm, 1.9 * cm, 1.9 * cm], 7.2),
        Paragraph("Tabela de prioridade: as dez combinações com maior atraso evitável.", LEG)]
    s += figura("fig8_pareto.png", 10.5, "Concentração do atraso evitável nas combinações de serviço e distrito.")
    s += [p(f"<b>Fila de atrasados.</b> No retrato de 08/10/2026 havia {mil(P['abertas_retrato'])} pedidos em "
            f"aberto entre os abertos de julho a setembro. Desses, <b>{mil(P['atrasadas'])}</b> estavam em "
            "aberto há mais dias do que 8 em cada 10 pedidos do mesmo serviço levaram na cidade. O critério é "
            "relativo ao serviço: remoção de entulho atrasa em poucos dias, reforma de galeria só depois de "
            "meses. Usamos apenas o último arquivo para que o retrato tenha uma única data."),
          p(f"<b>Pontos de reincidência.</b> Agrupando pedidos em aberto do mesmo serviço em células de cerca "
            f"de 100 metros, há <b>{mil(P['pontos_3'])} pontos com três ou mais pedidos</b> e "
            f"{mil(P['pontos_5'])} com cinco ou mais. É o sinal mais direto, nos dados, de necessidade "
            "compartilhada por vários moradores, e uma ida da equipe resolve vários pedidos."),
          p("<b>Efeito de segunda ordem considerado.</b> Priorizar por volume de reclamações favorece quem "
            "reclama mais e pode ampliar a desigualdade com distritos que registram pouco. Por isso o plano "
            "de ação não ordena por volume bruto: compara cada combinação com a referência do próprio "
            "serviço. O viés de registro não desaparece, e está declarado nas limitações. A base também não "
            "traz gravidade: um fio solto e uma lixeira quebrada pesam igual. Um peso por risco precisa ser "
            "definido pela prefeitura.")]
    AL = R["alerta"]
    btab = db.ler("SELECT * FROM res_backtest ORDER BY data")
    s += [p(f"<b>Alerta antecipado.</b> As três leituras anteriores descrevem o que já aconteceu. O alerta prevê: "
            f"para cada pedido em aberto há menos de {J} dias, estima a chance de ele passar de {J} dias. O "
            "modelo é uma curva de sobrevivência por serviço e distrito, usada de forma condicional: a chance "
            f"de não finalizar até o dia {J}, dado que o pedido já espera há k dias, é S({J}) dividido por S(k). "
            "A idade do pedido é informação que a taxa histórica simples ignora: um pedido que já passou do "
            "prazo em que a maioria é resolvida tem chance muito maior de se arrastar."),
          p(f"No retrato de 08/10/2026 havia {mil(AL['abertos_recentes'])} pedidos em aberto há menos de {J} "
            f"dias, e o modelo estima que <b>{mil(round(AL['devem_passar']))}</b> deles passarão do prazo "
            f"({pct(AL['devem_passar'] / AL['abertos_recentes'])}). <b>Validação:</b> o alerta foi simulado em "
            f"{AL['simulacoes']} datas passadas. Em cada uma, o modelo foi ajustado apenas com o que era "
            "conhecido naquele dia e a previsão foi comparada com o desfecho real. O total previsto ficou a no "
            f"máximo <b>{num(100 * AL['erro_total_max'], 1)}% do total real</b>, com AUC entre "
            f"{num(AL['auc_min'], 2)} e {num(AL['auc_max'], 2)}. A referência, que aplica a taxa histórica do "
            f"serviço sem considerar a idade, subestimou o total em {num(abs(100 * AL['erro_total_referencia_medio']), 0)}% "
            f"em média, com AUC médio de {num(AL['auc_referencia_medio'], 2)}."),
          tabela([["Data", "Pedidos em aberto", "Previsto", "Real", "Erro do total", "AUC", "AUC referência"]] +
                 [[pd.Timestamp(b.data).strftime("%d/%m/%Y"), mil(b.pedidos), mil(round(b.previsto)), mil(b.real),
                   f"{num(100 * b.erro_total, 1)}%", num(b.auc, 3), num(b.auc_referencia, 3)] for b in btab.itertuples()],
                 [2.3 * cm, 3 * cm, 2 * cm, 2 * cm, 2.4 * cm, 1.6 * cm, 2.6 * cm]),
          Paragraph("Simulações do alerta antecipado em datas passadas.", LEG)]
    s += figura("fig9_alerta.png", 12, "Total de pedidos que passaram de 30 dias: previsto pelo alerta, previsto pela referência e real.")
    s += figura("tela4_agir.png", 12.2, "Aba Onde agir: plano de ação, alerta antecipado, fila de atrasados e pontos de reincidência.")
    s += [Paragraph("3.5 Grupos de distritos", H2), p(
        f"O K-Means sobre variáveis padronizadas de atendimento, canal, volume e mix de assuntos indicou "
        f"k = {int(kk.loc[kk['silhueta'].idxmax(), 'k'])} pela maior silhueta média "
        f"({num(kk['silhueta'].max())}). O valor é baixo, e isso é informado como resultado: os distritos "
        "formam um contínuo, não tipos bem separados. Os grupos servem como segmentação de leitura. O grupo "
        "de menor índice médio reúne 30 distritos, com maior peso de árvore e asfalto na demanda e mediana "
        "de prazo próxima de 8 dias, contra cerca de 3 dias nos demais.")]
    s += figura("fig7_kmeans_k.png", 6.5, "Figura 5. Silhueta média por número de grupos.")
    s += [Paragraph("3.6 Modelos preditivos", H2), p(
        f"Alvo: demanda finalizada em até {J} dias. Treino com demandas abertas de janeiro a junho "
        f"({mil(met['treino'].max())}), teste com as abertas de julho a setembro ({mil(met['teste'].max())}). "
        "A divisão é temporal porque demandas do mesmo lote de execução são correlacionadas e uma divisão "
        "aleatória inflaria as métricas."),
        tabela([["Modelo", "AUC", "Brier", "Log loss"]] +
               [[m.modelo, num(m.auc, 4), num(m.brier, 4), num(m.log_loss, 4)] for m in met.itertuples()],
               [7 * cm, 2 * cm, 2 * cm, 2 * cm]),
        Paragraph("Tabela 5. Desempenho no conjunto de teste (3º trimestre).", LEG), p(
        f"Três leituras. Primeira: saber apenas o serviço já leva a AUC "
        f"{num(gb.loc['Baseline (taxa do servico)', 'auc'], 3)}, ou seja, o tipo de serviço é o principal "
        f"determinante do prazo. Segunda: o gradient boosting sem a variável distrito não supera essa "
        f"referência ({num(gb.loc['Gradient boosting sem distrito', 'auc'], 3)}), e com o distrito chega a "
        f"{num(gb.loc['Gradient boosting', 'auc'], 3)}. O ganho é modesto e vem todo do território, o que é "
        "coerente com a seção 3.2. Terceira: a rede neural empata com o gradient boosting em AUC e perde "
        "em calibração, então não justifica a complexidade adicional neste problema."),
        p("A calibração mostra que o modelo subestima a chance de finalização nas faixas intermediárias "
          "do teste, porque o 3º trimestre teve taxa geral maior que o período de treino, e superestima na "
          "faixa mais alta. Por isso o painel mostra a chance do modelo ao lado da frequência histórica "
          "observada, e não no lugar dela.")]
    s += figura("fig6_modelos.png", 14, "Figura 6. Comparação de modelos e curva de calibração do gradient boosting.")
    rr = R["recomendador"]
    erros = reco[reco["top3"] == 0]
    s += [Paragraph("3.7 Recomendador de serviço", H2), p(
        "A base aberta não contém o texto digitado pelo morador, o que impede treinar um classificador "
        "supervisionado de descrições. A alternativa foi recuperação por similaridade sobre o catálogo, "
        "com um léxico que liga termos comuns (cratera, galho, sofá, meio-fio) aos termos administrativos. "
        f"A avaliação usou <b>{rr['consultas']} consultas simuladas, escritas pela equipe</b>, e não relatos "
        f"reais de moradores: acerto na primeira sugestão em {pct(rr['top1'])} e entre as três primeiras em "
        f"{pct(rr['top3'], 1)}. O painel apresenta as três para o morador escolher. Consultas em que o "
        "serviço esperado não apareceu entre as três: " +
        "; ".join(f"“{t}”" for t in erros["texto"]) + "."),
        Paragraph("3.8 Protótipo", H2), p(
        "As telas abaixo são capturas da aplicação em execução sobre o banco real.")]
    s += figura("tela1_panorama.png", 15.5, "Figura 7. Aba Distritos: índice de equidade por distrito e relação com a distância ao centro.")
    s += figura("tela2_servico.png", 15.5, "Figura 8. Aba de comparação do mesmo serviço entre distritos.")
    s += figura("tela5_metodo.png", 13.5, "Aba Método: comparação de modelos, calibração, simulações do alerta e técnicas usadas.")
    s += figura("tela3_pedido.png", 15.5,
                "Figura 9. Fluxo do morador: descrição livre, serviços sugeridos, prazo no distrito e orientação.")
    log = (RAIZ / "docs" / "evidencias_pytest.txt").read_text(encoding="utf-8")
    s += [Paragraph("3.9 Evidências de teste", H2), p(
        f"A suíte automatizada tem {log.count(chr(32)+chr(80)+chr(65)+chr(83)+chr(83)+chr(69)+chr(68))} testes: leitura dos dois formatos de arquivo e recusa de formato "
        "ambíguo, regras de limpeza e censura, Kaplan-Meier conferido com cálculo manual, neutralidade do "
        "índice ao mix de serviços, cálculo de atraso evitável, fila e pontos de reincidência, alerta antecipado "
        "e reconstrução do retrato em data passada, restrições do banco, injeção de SQL tratada como texto, conexão "
        "somente leitura, mascaramento de dados pessoais, descarte de resposta de IA com número inventado, "
        "tolerância a falha da API e abertura do painel de ponta a ponta. Saída da execução:"),
        Preformatted(log, COD),
        p("<b>O que foi e o que não foi testado.</b> Todo o fluxo com redação determinística foi executado e "
          "testado. As travas da IA generativa foram testadas com um cliente simulado, que reproduz "
          "resposta fiel, resposta com número inventado e falha de rede. " + E.get("nota_teste_llm",
          "A chamada a um provedor real de IA generativa não foi executada pela equipe até a data desta "
          "entrega, portanto esse caminho é apresentado como implementado e não como validado.")),
        Paragraph("3.10 Limitações do protótipo", H2), p(
        "<b>Finalizada não é resolvida:</b> não há dado de execução nem de satisfação por demanda. "
        "<b>Viés de registro:</b> só existe o que foi pedido. <b>Associação, não causa:</b> o índice mostra "
        "onde o prazo difere, não por quê; contratos, equipes, clima e tipo de via não estão na base. "
        "<b>Intervalos de confiança otimistas:</b> supõem demandas independentes. <b>Nove meses de um "
        "ano:</b> não separa sazonalidade de tendência. <b>Sem validação com usuários:</b> a etapa de "
        "conversar com moradores e gestores não foi realizada, e o recomendador foi avaliado com consultas "
        "simuladas. <b>Sem variável socioeconômica:</b> renda e população por distrito não foram "
        "integradas, então não há taxa por habitante. <b>Mapa por centróide:</b> sem malha de distritos. "
        "<b>Sem implantação em nuvem:</b> a aplicação roda localmente. <b>Alerta não testado em "
        "operação:</b> foi validado por simulação em datas passadas e prevê encerramento no sistema, não "
        "execução do serviço."),
        Paragraph("3.11 Como medir o impacto", H2), tabela([
            ["Indicador", "Linha de base (jan-set 2026)", "Como acompanhar"],
            ["Diferença entre percentis 90 e 10 da taxa em 30 dias, poda de árvore", f"{num(100 * arv['amplitude_p90_p10'], 0)} p.p.", "Recalcular a cada trimestre publicado"],
            ["Idem, guias e sarjetas", f"{num(100 * gui['amplitude_p90_p10'], 0)} p.p.", "Idem"],
            ["Menor índice de equidade entre distritos", num(R["indice"]["min"]), "Idem"],
            ["Atraso evitável total", f"{mil(round(R['prioridade']['ganho_total']))} pedidos", "Idem; a meta é reduzir nas combinações priorizadas"],
            ["Pedidos em aberto além do prazo típico do serviço", mil(R["prioridade"]["atrasadas"]), "Idem"],
            ["Demandas em aberto na data de corte", pct(g["pct_aberta"]), "Idem"],
            ["Acerto do recomendador entre as 3 primeiras sugestões", f"{pct(rr['top3'], 1)} (simulado)", "Substituir por escolhas reais registradas no log de uso"],
            ["Pedidos abertos no serviço correto", "Sem linha de base", "Exige parceria com a Prefeitura para medir reclassificação de pedidos"]],
            [7.2 * cm, 4.2 * cm, 5.6 * cm]),
        Paragraph("Tabela 6. Indicadores de impacto propostos.", LEG)]

    # ---------------------------------------------------------------- 4
    s += [Paragraph("4. Conclusões", H1), p(
        "A pergunta da Global Solution é como os conhecimentos de IA e das disciplinas cursadas podem "
        "resolver um problema real. A resposta deste trabalho tem duas partes. Para o morador, a POC "
        "entrega algo que hoje ele não tem: o nome correto do serviço a partir da descrição dele e o prazo "
        "que pedidos iguais levaram no distrito dele, com a honestidade de dizer quando a mediana não foi "
        "atingida. Para quem gere o serviço, entrega uma medida de desigualdade territorial que não "
        "confunde composição da demanda com desempenho, e uma ordem de ação: quais combinações de serviço "
        "e distrito atacar primeiro, quais pedidos já passaram do prazo típico e onde uma única ida da "
        "equipe atende vários moradores."),
        p("O resultado mais relevante contrariou a hipótese de partida. A desigualdade existe e persiste "
          "entre trimestres, mas não acompanha a distância ao centro e está concentrada em poucos serviços. "
          "Isso muda a recomendação: em vez de um diagnóstico genérico de periferia desassistida, os dados "
          "apontam para a gestão de serviços específicos, como poda, guias e sarjetas e roçada, em "
          "distritos específicos."),
        p("Boa parte do valor veio de decisões de método anteriores a qualquer modelo: validar o formato de "
          "cada arquivo, tratar censura, padronizar pelo mix e comparar o modelo com uma referência simples. "
          "Sem a primeira, um trimestre inteiro teria datas trocadas sem erro aparente. Sem a última, o "
          "ganho do aprendizado de máquina pareceria maior do que é."),
        p("<b>Próximos passos.</b> Integrar população e renda por distrito para taxas por habitante e para "
          "testar a relação com condição socioeconômica. Incluir a malha oficial de distritos no mapa. "
          "Validar o recomendador e a linguagem da orientação com moradores. Propor à Prefeitura a "
          "publicação da data de extração, de um identificador de protocolo e de um campo de execução "
          "confirmada, que removeriam as três principais limitações deste trabalho. Implantar em nuvem com "
          "atualização trimestral automática."),
        Paragraph("5. Links da entrega", H1),
        p(f"<b>Vídeo demonstrativo (YouTube, não listado):</b> {E['link_video']}"),
        p(f"<b>Repositório GitHub (privado, compartilhado com fiap-tutoria):</b> {E['link_repositorio']}")]
    return s


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    if doc.page > 1:
        canvas.drawString(2 * cm, 1.1 * cm, f"{E['titulo']} · Global Solution 2026.2 · {E['grupo']}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, str(doc.page))
    canvas.restoreState()


if __name__ == "__main__":
    destino = RAIZ / "docs" / "GS2_ZelaSP.pdf"
    doc = SimpleDocTemplate(str(destino), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=E["titulo"],
                            author=", ".join(i["nome"] for i in E["integrantes"]))
    doc.build(montar(), onFirstPage=rodape, onLaterPages=rodape)
    pend = [k for k in ("turma", "link_video", "link_repositorio") if E[k] == "PREENCHER"]
    print(f"PDF gerado em {destino}")
    if pend:
        print("ATENCAO: campos pendentes em config/entrega.json:", ", ".join(pend))
