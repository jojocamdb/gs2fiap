"""ZelaSP: painel interativo. Uso: streamlit run app.py"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from zeladoria import assistente, config, db, indicadores, modelo  # noqa: E402
from zeladoria.recomendador import Recomendador  # noqa: E402

ENTREGA = json.loads((Path(__file__).resolve().parent / "config" / "entrega.json").read_text(encoding="utf-8"))
NOME = ENTREGA.get("titulo", "ZelaSP")
st.set_page_config(page_title=NOME, layout="wide")

# ---------------------------------------------------------------- sistema visual
PRETO, SUPERFICIE, SUPERFICIE2, BORDA = "#000000", "#0F0F0F", "#191919", "#262626"
TEXTO, MUDO, CINZA = "#FFFFFF", "#A3A3A3", "#6B6B6B"
OURO, NEG, POS = "#E1C59D", "#B4544B", "#4E8C6A"
FONTE = '"Inter", "Helvetica Neue", Helvetica, Arial, sans-serif'
DIVERGENTE = [[0, NEG], [0.5, "#5E5C57"], [1, OURO]]      # abaixo da cidade, igual, acima
SEQUENCIAL = [[0, "#6E6252"], [1, OURO]]

pio.templates["zelasp"] = go.layout.Template(layout=dict(
    font=dict(family=FONTE, color=MUDO, size=13), paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", colorway=[OURO, CINZA, MUDO, NEG],
    xaxis=dict(gridcolor=BORDA, zerolinecolor=BORDA, linecolor=BORDA),
    yaxis=dict(gridcolor=BORDA, zerolinecolor=BORDA, linecolor=BORDA),
    hoverlabel=dict(bgcolor=SUPERFICIE2, bordercolor=BORDA, font=dict(family=FONTE, color=TEXTO)),
    legend=dict(font=dict(color=MUDO)), margin=dict(l=0, r=0, t=10, b=0)))
pio.templates.default = "zelasp"

CSS = f"""
<style>
:root {{
  --ph-surface: {SUPERFICIE}; --ph-surface-2: {SUPERFICIE2}; --ph-border: {BORDA};
  --ph-text: {TEXTO}; --ph-mute: {MUDO}; --ph-gold: {OURO}; --ph-neg: {NEG}; --ph-pos: {POS};
}}
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"], [data-baseweb="tab"], [data-baseweb="select"] {{font-family: {FONTE} !important;}}
[data-testid="stIconMaterial"] {{font-family: "Material Symbols Rounded" !important;}}
.block-container {{max-width: 1200px; padding-top: 2.4rem; padding-bottom: 5rem;}}
h1, h2, h3 {{font-weight: 500 !important; letter-spacing: -0.01em;}}
.z-top {{display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 1.6rem;}}
.z-marca {{font-size: 26px; font-weight: 500; letter-spacing: -0.02em; color: var(--ph-text);}}
.z-marca span {{color: var(--ph-gold);}}
.z-label {{font-size: 12px; font-weight: 500; letter-spacing: .06em; text-transform: uppercase; color: var(--ph-mute);}}
.z-hero {{text-align: center; padding: 56px 0 44px 0;}}
.z-hero h1 {{font-size: 50px; font-weight: 400 !important; letter-spacing: -0.02em; line-height: 1.12;
            max-width: 860px; margin: 14px auto 16px auto; padding: 0;}}
.z-hero p {{font-size: 16px; color: var(--ph-mute); max-width: 640px; margin: 0 auto; line-height: 1.5;}}
.z-sec {{margin: 64px 0 20px 0;}}
.z-sec h2 {{font-size: 26px; font-weight: 500 !important; line-height: 1.15; margin: 0; padding: 0;}}
.z-sec p {{font-size: 14px; color: var(--ph-mute); margin: 6px 0 0 0;}}
.z-grid {{display: grid; gap: 16px;}}
.z-g2 {{grid-template-columns: 1fr 1fr;}} .z-g3 {{grid-template-columns: repeat(3, 1fr);}}
.z-g4 {{grid-template-columns: repeat(4, 1fr);}}
.z-kpi {{background: var(--ph-surface); border-radius: 8px; padding: 20px;}}
.z-kpi .v {{font-size: 40px; font-weight: 400; letter-spacing: -0.02em; line-height: 1.1; margin-top: 10px;
           font-variant-numeric: tabular-nums;}}
.z-kpi .v.ouro {{color: var(--ph-gold);}} .z-kpi .v.neg {{color: var(--ph-neg);}}
.z-kpi .d {{font-size: 13px; color: var(--ph-mute); margin-top: 8px; line-height: 1.45;}}
.z-kpi .t {{font-size: 16px; font-weight: 500; margin-top: 6px;}}
.z-kpi.grande .v {{font-size: 64px;}}
.z-valor {{display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px;}}
.z-valor h4 {{font-size: 16px; font-weight: 500 !important; margin: 0; padding: 0 0 12px 0;
             border-bottom: 1px solid var(--ph-border);}}
.z-valor p {{font-size: 14px; color: var(--ph-mute); margin: 12px 0 0 0; line-height: 1.5;}}
.z-nota {{font-size: 12px; color: {CINZA}; margin-top: 56px; line-height: 1.5;}}
.z-resp {{background: var(--ph-surface); border-radius: 8px; padding: 22px 24px; font-size: 16px; line-height: 1.6;}}
[data-baseweb="tab-list"] {{gap: 28px; border-bottom: 1px solid var(--ph-border);}}
[data-baseweb="tab"] {{font-size: 14px !important; padding-left: 0 !important; padding-right: 0 !important;}}
[data-testid="stExpander"] details {{border: 1px solid var(--ph-border); border-radius: 8px; background: transparent;}}
[data-testid="stMetric"] {{background: var(--ph-surface); border-radius: 8px; padding: 18px 20px;}}
[data-testid="stMetricValue"] {{font-weight: 400; letter-spacing: -0.02em;}}
[data-testid="stMetricLabel"] p {{font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ph-mute);}}
@media (max-width: 900px) {{.z-g2, .z-g3, .z-g4, .z-valor {{grid-template-columns: 1fr;}} .z-hero h1 {{font-size: 34px;}}}}
</style>
"""


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def secao(titulo, sub=""):
    html(f'<div class="z-sec"><h2>{titulo}</h2>' + (f"<p>{sub}</p>" if sub else "") + "</div>")


def kpi(label, valor, desc="", tom="", titulo="", grande=False):
    return (f'<div class="z-kpi{" grande" if grande else ""}"><div class="z-label">{label}</div>'
            + (f'<div class="t">{titulo}</div>' if titulo else "")
            + f'<div class="v {tom}">{valor}</div>' + (f'<div class="d">{desc}</div>' if desc else "") + "</div>")


def grade(blocos, n):
    html(f'<div class="z-grid z-g{n}">{"".join(blocos)}</div>')


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def curto(texto, n=46):
    return texto if len(texto) <= n else texto[: n - 1] + "…"


@st.cache_data(show_spinner="Carregando demandas...")
def carregar():
    d = db.demandas()
    res = {t: db.ler(f"SELECT * FROM {t}") for t in (
        "res_distrito", "res_servico_amplitude", "res_servico_distrito", "res_modelos",
        "res_calibracao", "res_kmeans_k", "res_recomendador", "res_prioridade", "res_fila",
        "res_pontos", "auditoria_funil", "auditoria_arquivo", "dim_servico", "dim_distrito")}
    resumo = json.loads((config.DIR_PROC / "resumo.json").read_text(encoding="utf-8"))
    return d, res, resumo


@st.cache_resource
def carregar_modelos(_d, _servicos):
    rec = Recomendador(_servicos[["id_servico", "servico", "assunto"]], _d["id_servico"].value_counts())
    try:
        clf = joblib.load(config.DIR_PROC / "modelo_prazo.joblib")
    except Exception:
        # modelo salvo com outra versao do scikit-learn: reajusta a partir do banco
        e = modelo.preparar(_d)
        clf = modelo.candidatos()["Gradient boosting"].fit(
            e[modelo.CATEGORICAS + modelo.NUMERICAS], e["resolvida_janela"])
    return rec, clf


@st.cache_data
def silhueta(_d):
    """Mancha da cidade: celulas de cerca de 500 m onde ha pelo menos um pedido registrado."""
    c = _d.dropna(subset=["latitude", "longitude"])
    h, ys, xs = np.histogram2d(c["latitude"], c["longitude"], bins=[130, 150],
                               range=[[-24.02, -23.35], [-46.84, -46.36]])
    return np.where(h > 0, 1.0, np.nan), (xs[:-1] + xs[1:]) / 2, (ys[:-1] + ys[1:]) / 2


def mapa(df, lat, lon, altura=560, **kw):
    """Mapa de bolhas de desenho proprio, sem depender de servico externo de mapas."""
    z, xs, ys = silhueta(d)
    fig = px.scatter(df, x=lon, y=lat, height=altura, **kw)
    fig.update_traces(marker=dict(line=dict(color=PRETO, width=1), opacity=0.95))
    fig.add_trace(go.Heatmap(z=z, x=xs, y=ys, showscale=False, hoverinfo="skip",
                             colorscale=[[0, "#161616"], [1, "#161616"]]))
    fig.data = (fig.data[-1],) + fig.data[:-1]            # mancha da cidade por baixo das bolhas
    fig.add_annotation(x=config.SE_LON, y=config.SE_LAT, text="Sé", showarrow=True, arrowhead=0,
                       ax=30, ay=-30, font=dict(size=11, color=MUDO), arrowcolor=CINZA)
    fig.update_xaxes(visible=False, range=[-46.84, -46.36])
    fig.update_yaxes(visible=False, range=[-24.02, -23.35], scaleanchor="x", scaleratio=1.09)
    fig.update_layout(coloraxis_colorbar=dict(thickness=10, len=0.6, title=None, outlinewidth=0),
                      legend=dict(title=None, orientation="h", y=1.02, x=0))
    return fig


if not config.BANCO.exists():
    st.error("Banco não encontrado. Rode `python scripts/01_etl.py` e `python scripts/02_analise.py`.")
    st.stop()

d, res, resumo = carregar()
rec, clf = carregar_modelos(d, res["dim_servico"])
dist = res["res_distrito"].merge(
    res["dim_distrito"][["id_distrito", "nome", "lat_centro", "lon_centro", "subprefeitura"]],
    left_on="distrito", right_on="nome")
dist["Distrito"] = dist["distrito"].str.title()
J = config.JANELA_DIAS
g, pr = resumo["geral"], resumo["prioridade"]
amp, sd = res["res_servico_amplitude"], res["res_servico_distrito"]

html(CSS)
marca = NOME[:-2] + f"<span>{NOME[-2:]}</span>" if NOME.endswith("SP") else NOME
html(f'<div class="z-top"><div class="z-marca">{marca}</div>'
     f'<div class="z-label">{ENTREGA.get("categoria", "")}</div></div>')

geral, agir, distritos, servicos, pedido, metodo = st.tabs(
    ["Visão geral", "Onde agir", "Distritos", "Serviços", "Abrir pedido", "Método"])

# ================================================================== Visao geral
with geral:
    html(f'<div class="z-hero"><div class="z-label">{ENTREGA.get("assinatura", "")}</div>'
         f'<h1>{ENTREGA.get("chamada", "")}</h1>'
         '<p>Quanto tempo a prefeitura leva para atender cada pedido de zeladoria, em cada distrito '
         'de São Paulo. E onde agir primeiro.</p></div>')
    grade([
        kpi("Pedidos analisados", f"{br(g['demandas'] / 1000)} mil", "Zeladoria, janeiro a setembro de 2026"),
        kpi(f"Finalizados em {J} dias", f"{br(100 * g['taxa_janela'])}%", "Média da cidade"),
        kpi("Entre distritos", f"{br(100 * resumo['taxa_bruta']['min'])}% a {br(100 * resumo['taxa_bruta']['max'])}%",
            "Do distrito mais lento ao mais rápido", tom="ouro"),
    ], 3)

    alvo = "Tapa-buraco"
    par = sd[sd["servico"] == alvo].sort_values("taxa")
    if len(par) >= 2:
        secao("O mesmo buraco, dois distritos", "Tapa-buraco. Dias até metade dos pedidos ser finalizada.")
        blocos = []
        for linha, tom, rotulo in ((par.iloc[-1], "", "Mais rápido"), (par.iloc[0], "neg", "Mais lento")):
            p_ = d[(d["servico"] == alvo) & (d["distrito"] == linha["distrito"])]
            med = indicadores.percentil_km(p_["dias"], p_["finalizada"], 0.5)
            blocos.append(kpi(rotulo, ("150+" if med is None else br(med)) + " dias",
                              f"{br(100 * linha['taxa'])}% em até {J} dias · {br(len(p_))} pedidos",
                              tom=tom, titulo=linha["distrito"].title(), grande=True))
        grade(blocos, 2)

    secao("Onde a diferença é maior",
          f"Pedidos finalizados em até {J} dias. Linha longa, atendimento desigual.")
    top = amp.head(10).sort_values("amplitude_p90_p10")
    nomes = [curto(n, 50) for n in top["servico"]]
    fig = go.Figure()
    for nome_, a_, b_ in zip(nomes, top["p10"], top["p90"]):
        fig.add_trace(go.Scatter(x=[100 * a_, 100 * b_], y=[nome_, nome_], mode="lines",
                                 line=dict(color=CINZA, width=2), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=100 * top["p10"], y=nomes, mode="markers+text", name="Distritos mais lentos",
                             marker=dict(color=NEG, size=14, line=dict(color=PRETO, width=2)),
                             text=[f"{br(100 * v)}%" for v in top["p10"]], textposition="middle left",
                             hovertemplate="%{y}<br>percentil 10: %{x:.0f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=100 * top["p90"], y=nomes, mode="markers+text", name="Distritos mais rápidos",
                             marker=dict(color=OURO, size=14, line=dict(color=PRETO, width=2)),
                             text=[f"{br(100 * v)}%" for v in top["p90"]], textposition="middle right",
                             hovertemplate="%{y}<br>percentil 90: %{x:.0f}%<extra></extra>"))
    fig.update_layout(height=460, legend=dict(orientation="h", y=1.1, x=0),
                      xaxis=dict(range=[-8, 110], ticksuffix="%", showgrid=False),
                      yaxis=dict(showgrid=True))
    st.plotly_chart(fig, width='stretch')

    secao("Para quem serve")
    html('<div class="z-valor">'
         f'<div><h4>Prefeitura</h4><p>Sabe onde agir primeiro. 100 combinações de serviço e distrito '
         f'concentram {br(100 * pr["acum_100"])}% do atraso evitável.</p></div>'
         '<div><h4>Morador</h4><p>Descreve o problema, recebe o serviço certo e o prazo provável '
         'no distrito dele.</p></div>'
         '<div><h4>Sociedade</h4><p>Cobra com número comparável: mesmo serviço, mesmo período, '
         'outro distrito.</p></div></div>')
    html('<div class="z-nota">Dados abertos do SP156, Prefeitura de São Paulo. Finalizado é o encerramento '
         'do pedido no sistema, não a confirmação de execução. Números históricos, não garantia de prazo.</div>')

# ================================================================== Onde agir
with agir:
    pares, fila, pontos = res["res_prioridade"], res["res_fila"], res["res_pontos"]
    secao("Onde agir primeiro", "O atraso está concentrado em poucas combinações de serviço e distrito.")
    grade([
        kpi("Atraso evitável", f"{br(pr['ganho_total'] / 1000, 1)} mil",
            f"Pedidos a mais finalizados em {J} dias se cada combinação alcançasse o distrito mediano"),
        kpi("Concentração", f"{br(100 * pr['acum_100'])}%",
            f"Do atraso evitável em 100 de {br(pr['pares_avaliados'])} combinações", tom="ouro"),
        kpi("Fila de atrasados", br(pr["atrasadas"]), "Pedidos em aberto além do prazo típico do serviço"),
        kpi("Pontos de reincidência", br(pr["pontos_3"]), "Locais com 3 ou mais pedidos iguais em 100 m"),
    ], 4)

    secao("Plano de ação", "Combinações ordenadas pelo atraso evitável.")
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        fig = go.Figure(go.Scatter(x=pares["posicao"], y=100 * pares["acumulado"], mode="lines",
                                   line=dict(color=OURO, width=2.5),
                                   hovertemplate="%{x} combinações: %{y:.0f}%<extra></extra>"))
        marcos = [20, 50, 100]
        fig.add_trace(go.Scatter(
            x=marcos, y=[100 * pares["acumulado"].iloc[m - 1] for m in marcos], mode="markers+text",
            marker=dict(color=TEXTO, size=9, line=dict(color=PRETO, width=2)),
            text=[f"{m} · {br(100 * pares['acumulado'].iloc[m - 1])}%" for m in marcos],
            textposition="middle right", textfont=dict(color=TEXTO), hoverinfo="skip"))
        fig.update_layout(height=380, showlegend=False, xaxis_title="Combinações priorizadas",
                          yaxis=dict(ticksuffix="%", range=[0, 103]))
        st.plotly_chart(fig, width='stretch')
    with c2:
        n = st.slider("Combinações a priorizar", 10, 200, 50, 10)
        sel = pares.head(n)
        st.markdown(f"**{br(100 * sel['acumulado'].iloc[-1])}%** do atraso evitável · "
                    f"**{br(sel['ganho'].sum())}** pedidos a mais em {J} dias")
        vis = sel[["posicao", "servico", "distrito", "elegiveis", "taxa", "referencia", "ganho"]].copy()
        vis["distrito"] = vis["distrito"].str.title()
        for col in ("taxa", "referencia"):
            vis[col] = (100 * vis[col]).round(0)
        vis["ganho"] = vis["ganho"].round(0)
        st.dataframe(vis.rename(columns={
            "posicao": "#", "servico": "Serviço", "distrito": "Distrito", "elegiveis": "Pedidos",
            "taxa": f"% em {J}d", "referencia": "Referência (%)", "ganho": "Pedidos a mais"}),
            hide_index=True, width='stretch', height=290)

    secao("Fila de atrasados", f"Retrato de {pd.Timestamp(pr['data_retrato']).strftime('%d/%m/%Y')}. "
          "Em aberto há mais tempo do que 8 em cada 10 pedidos do mesmo serviço levaram.")
    sub = st.selectbox("Subprefeitura", ["Todas"] + sorted(fila["subprefeitura"].dropna().unique()))
    f = fila if sub == "Todas" else fila[fila["subprefeitura"] == sub]
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        por = f.groupby("servico")["pedidos"].sum().sort_values().tail(8)
        fig = go.Figure(go.Bar(x=por.values, y=[curto(n_, 40) for n_ in por.index], orientation="h",
                               marker=dict(color=[CINZA] * (len(por) - 1) + [OURO], cornerradius=4),
                               text=por.values, textposition="outside", textfont=dict(color=MUDO),
                               hovertemplate="%{y}: %{x} pedidos<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=340, margin=dict(l=0, r=50, t=10, b=0),
                          xaxis=dict(visible=False, range=[0, float(por.max()) * 1.15 if len(por) else 1]),
                          yaxis=dict(showgrid=False))
        st.plotly_chart(fig, width='stretch')
    with c2:
        vf = f.head(200).copy()
        vf["distrito"] = vf["distrito"].str.title()
        st.dataframe(vf[["servico", "distrito", "pedidos", "limite_dias", "dias_mediano", "dias_maximo"]].rename(
            columns={"servico": "Serviço", "distrito": "Distrito", "pedidos": "Atrasados",
                     "limite_dias": "Prazo típico (dias)", "dias_mediano": "Em aberto há (mediana)",
                     "dias_maximo": "Mais antigo (dias)"}), hide_index=True, width='stretch', height=340)

    secao("Onde vários moradores pedem a mesma coisa",
          "Pedidos em aberto do mesmo serviço em um raio de 100 m. Uma ida da equipe resolve vários.")
    c1, c2 = st.columns([3, 2], gap="large")
    with c2:
        minimo = st.slider("Mínimo de pedidos no mesmo ponto", 3, 15, 5)
        pt = pontos[pontos["pedidos"] >= minimo].copy()
        pt["Distrito"] = pt["distrito"].str.title()
        st.markdown(f"**{br(len(pt))}** pontos · **{br(pt['pedidos'].sum())}** pedidos em aberto")
        st.dataframe(pt[["servico", "Distrito", "pedidos", "dias_mais_antigo"]].head(100).rename(
            columns={"servico": "Serviço", "pedidos": "Pedidos", "dias_mais_antigo": "Mais antigo (dias)"}),
            hide_index=True, width='stretch', height=380)
    with c1:
        fig = mapa(pt, "latitude", "longitude", altura=520, size="pedidos", color="dias_mais_antigo",
                   color_continuous_scale=SEQUENCIAL, hover_name="servico", size_max=18,
                   hover_data={"Distrito": True, "pedidos": True, "latitude": False, "longitude": False},
                   labels={"dias_mais_antigo": "Dias do mais antigo", "pedidos": "Pedidos"})
        st.plotly_chart(fig, width='stretch')

    with st.expander("Como ler com cuidado"):
        st.markdown("""
- **Ordem de grandeza, não previsão.** A conta não sabe por que uma combinação está abaixo da referência.
- **Volume favorece quem reclama mais.** Por isso a comparação é com a referência do próprio serviço, não com o volume bruto.
- **Retrato da última extração publicada**, não de hoje.
- **Gravidade não está nos dados.** Um peso por risco precisa ser definido pela prefeitura.
- **Mapa:** a área cinza é a mancha urbana formada pelos próprios pedidos. Limites de distrito não são desenhados.
""")

# ================================================================== Distritos
with distritos:
    secao("Índice de equidade por distrito",
          "1,00 é igual à cidade para o mesmo conjunto de serviços. Abaixo, o distrito resolve menos que o esperado.")
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        cor = st.radio("Colorir por", ["Índice", "Grupo"], horizontal=True, label_visibility="collapsed")
        dist["Grupo"] = "Grupo " + dist["grupo"].astype(str)
        comum = dict(size="demandas", hover_name="Distrito", size_max=22,
                     hover_data={"indice": ":.2f", "taxa_bruta": ":.0%", "p50_dias": True, "demandas": True,
                                 "lat_centro": False, "lon_centro": False},
                     labels={"indice": "Índice", "taxa_bruta": f"Em {J} dias", "p50_dias": "Mediana (dias)",
                             "demandas": "Pedidos"})
        if cor == "Índice":
            fig = mapa(dist, "lat_centro", "lon_centro", color="indice", color_continuous_scale=DIVERGENTE,
                       color_continuous_midpoint=1, range_color=(0.85, 1.15), **comum)
        else:
            fig = mapa(dist.sort_values("Grupo"), "lat_centro", "lon_centro", color="Grupo",
                       color_discrete_sequence=[NEG, MUDO, OURO], **comum)
        st.plotly_chart(fig, width='stretch')
    with c2:
        ordem = st.radio("Mostrar", ["Menores índices", "Maiores índices"], horizontal=True,
                         label_visibility="collapsed")
        t = dist.sort_values("indice", ascending=ordem == "Menores índices").head(15)
        tab = t[["Distrito", "indice", "taxa_bruta", "p50_dias", "elegiveis"]].copy()
        tab["taxa_bruta"] = (100 * tab["taxa_bruta"]).round(0)
        st.dataframe(tab.rename(columns={"indice": "Índice", "taxa_bruta": f"% em {J}d",
                                         "p50_dias": "Mediana (dias)", "elegiveis": "Pedidos"}),
                     hide_index=True, width='stretch', height=520,
                     column_config={"Índice": st.column_config.NumberColumn(format="%.2f")})

    ce = resumo["centralidade"]
    secao("Não é centro contra periferia",
          f"Correlação entre índice e distância ao centro: {br(ce['spearman_indice_x_distancia'], 2)}. "
          "Fraca, e no sentido contrário ao esperado.")
    fig = px.scatter(dist, x="dist_centro_km", y="indice", hover_name="Distrito", trendline="ols",
                     color_discrete_sequence=[OURO], height=380,
                     labels={"dist_centro_km": "Distância à Praça da Sé (km)", "indice": "Índice"})
    fig.update_traces(marker=dict(size=9, line=dict(color=PRETO, width=1)), selector=dict(mode="markers"))
    fig.update_traces(line=dict(color=CINZA, width=1.5), selector=dict(mode="lines"))
    fig.add_hline(y=1, line_dash="dot", line_color=CINZA)
    st.plotly_chart(fig, width='stretch')

    with st.expander("Como ler"):
        st.markdown(
            "O índice divide o que o distrito resolveu em 30 dias pelo que seria esperado se cada serviço "
            "pedido ali tivesse a taxa média da cidade. Isso separa desempenho de tipo de pedido.\n\n"
            "A correlação fraca com a distância não prova que a periferia é mais bem atendida. A base só "
            "contém o que foi registrado, e finalizado é encerramento administrativo, não execução confirmada.")
    with st.expander("Grupos de distritos (K-Means)"):
        k = res["res_kmeans_k"]
        st.caption(f"k escolhido pela maior silhueta ({br(k['silhueta'].max(), 2)}). Valor baixo: os grupos são "
                   "uma segmentação de leitura, não tipos bem separados.")
        mixcols = [c for c in dist.columns if c.startswith("mix_")]
        perfil = dist.groupby("Grupo").agg(
            Distritos=("distrito", "size"), Índice=("indice", "mean"), Mediana_dias=("p50_dias", "mean"),
            Pct_em_aberto=("pct_aberta", "mean"), Pct_app=("pct_app", "mean"),
            Km_do_centro=("dist_centro_km", "mean"),
            **{c.replace("mix_", "Mix ")[:28]: (c, "mean") for c in mixcols}).round(2)
        st.dataframe(perfil.T, width='stretch')
        for nome, parte in dist.groupby("Grupo"):
            st.markdown(f"**{nome}** · " + ", ".join(sorted(parte["Distrito"])))

# ================================================================== Servicos
with servicos:
    secao("Mesmo serviço, distritos diferentes", f"Pedidos finalizados em até {J} dias, por distrito.")
    escolha = st.selectbox("Serviço", amp["servico"], index=min(2, len(amp) - 1), label_visibility="collapsed")
    s = sd[sd["servico"] == escolha].sort_values("taxa").copy()
    s["Distrito"] = s["distrito"].str.title()
    linha = amp[amp["servico"] == escolha].iloc[0]
    grade([
        kpi("Distritos mais lentos", f"{br(100 * linha['p10'])}%", "Percentil 10", tom="neg"),
        kpi("Distrito mediano", f"{br(100 * linha['mediana'])}%", "Referência da cidade"),
        kpi("Distritos mais rápidos", f"{br(100 * linha['p90'])}%", "Percentil 90", tom="ouro"),
        kpi("Diferença", f"{br(100 * linha['amplitude_p90_p10'])} p.p.", f"{br(linha['demandas'])} pedidos"),
    ], 4)
    fig = px.bar(s, x="Distrito", y=s["taxa"] * 100, color=s["taxa"] * 100, height=360,
                 color_continuous_scale=DIVERGENTE, color_continuous_midpoint=100 * linha["mediana"],
                 labels={"y": f"% em {J} dias", "color": "%"}, hover_data={"elegiveis": True})
    fig.update_layout(coloraxis_showscale=False, xaxis=dict(tickangle=-60, title=None, tickfont=dict(size=9)),
                      yaxis=dict(ticksuffix="%", title=None), bargap=0.25)
    st.plotly_chart(fig, width='stretch')

    secao("Quanto tempo o pedido fica em aberto", "Compare dois distritos. A linha tracejada é a cidade.")
    opcoes = sorted(s["Distrito"])
    c1, c2 = st.columns(2)
    a = c1.selectbox("Distrito A", opcoes, index=opcoes.index(s.iloc[0]["Distrito"]))
    b = c2.selectbox("Distrito B", opcoes, index=opcoes.index(s.iloc[-1]["Distrito"]))
    base = d[d["servico"] == escolha]
    fig = go.Figure()
    for nome, cor_ in ((a, NEG), (b, OURO)):
        p = base[base["distrito"] == nome.upper()]
        km = indicadores.kaplan_meier(p["dias"], p["finalizada"])
        fig.add_trace(go.Scatter(x=km["dia"], y=km["em_aberto"] * 100, line_shape="hv",
                                 name=f"{nome} ({br(len(p))})", line=dict(color=cor_, width=2.5)))
    km = indicadores.kaplan_meier(base["dias"], base["finalizada"])
    fig.add_trace(go.Scatter(x=km["dia"], y=km["em_aberto"] * 100, line_shape="hv", name="Cidade",
                             line=dict(color=CINZA, dash="dot", width=1.5)))
    fig.update_layout(height=380, xaxis=dict(title="Dias desde a abertura", range=[0, 150]),
                      yaxis=dict(title=None, ticksuffix="%", range=[0, 100]),
                      legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, width='stretch')
    with st.expander("Todos os serviços"):
        vis = amp[["servico", "demandas", "distritos", "p10", "mediana", "p90", "amplitude_p90_p10"]].copy()
        for col in ("p10", "mediana", "p90", "amplitude_p90_p10"):
            vis[col] = (100 * vis[col]).round(0)
        st.dataframe(vis.rename(columns={
            "servico": "Serviço", "demandas": "Pedidos", "distritos": "Distritos", "p10": "Percentil 10 (%)",
            "mediana": "Mediano (%)", "p90": "Percentil 90 (%)", "amplitude_p90_p10": "Diferença (p.p.)"}),
            hide_index=True, width='stretch')
        st.caption("A curva usa o estimador de Kaplan-Meier, que considera também os pedidos ainda em aberto.")

# ================================================================== Abrir pedido
with pedido:
    secao("Vou abrir um pedido", "Descreva o problema. O sistema indica o serviço e o prazo no seu distrito.")
    c1, c2 = st.columns([3, 1], gap="large")
    relato_bruto = c1.text_input("O que está acontecendo?", max_chars=300,
                                 placeholder="Ex.: buraco grande na rua em frente à escola")
    distrito = c2.selectbox("Distrito", sorted(dist["Distrito"]))
    st.caption("Não informe nome, CPF, telefone ou e-mail. O texto não é armazenado.")
    if relato_bruto:
        relato, pessoais = assistente.higienizar(relato_bruto)
        if pessoais:
            st.warning("Dados pessoais detectados e removidos do texto: " + ", ".join(pessoais) + ".")
        sugestoes = rec.recomendar(relato, 3)
        if sugestoes.empty:
            st.info("Não encontrei um serviço de zeladoria parecido. Tente descrever com outras "
                    "palavras ou consulte o catálogo completo no portal SP156.")
        else:
            nome_serv = st.radio("Serviço mais provável", sugestoes["servico"])
            id_serv = int(sugestoes.loc[sugestoes["servico"] == nome_serv, "id_servico"].iloc[0])
            id_dist = int(dist.loc[dist["Distrito"] == distrito, "id_distrito"].iloc[0])
            prazo = indicadores.estimar_prazo(d, id_serv, id_dist)
            hoje = pd.Timestamp.today()
            x = pd.DataFrame([{"id_servico": id_serv, "id_distrito": id_dist, "canal": "PORTAL",
                               "dia_semana": hoje.day_of_week, "dia_do_mes": hoje.day}])
            prob = float(clf.predict_proba(x[modelo.CATEGORICAS + modelo.NUMERICAS])[0, 1])
            ficha = assistente.montar_ficha(nome_serv, distrito, prazo, prob)

            def fmt(v, suf=""):
                return "não atingido" if v is None else f"{v}{suf}"

            dif = None if ficha["pct_resolvidas_na_janela"] is None else \
                ficha["pct_resolvidas_na_janela"] - ficha["pct_resolvidas_na_janela_cidade"]
            html('<div style="height:20px"></div>')
            grade([
                kpi("Metade finalizada em", fmt(ficha["metade_resolvida_em_dias"], " dias"),
                    f"Em {distrito}", tom="ouro"),
                kpi("8 em cada 10 em", fmt(ficha["oito_em_dez_resolvidas_em_dias"], " dias")),
                kpi(f"Finalizados em {J} dias", fmt(ficha["pct_resolvidas_na_janela"], "%"),
                    "" if dif is None else f"{dif:+d} p.p. em relação à cidade"),
                kpi("Chance pelo modelo", f"{ficha['chance_modelo_pct']}%", f"De finalizar em {J} dias"),
            ], 4)
            resposta = assistente.responder(ficha, relato, cliente=assistente.cliente_llm())
            secao("Orientação")
            html(f'<div class="z-resp">{resposta["texto"]}</div>')
            origem = "IA generativa restrita à ficha de fatos" if resposta["origem"] == "ia_generativa" \
                else f"redação padrão ({resposta['motivo']})"
            st.caption(f"Base: {ficha['base_da_estimativa']}, {ficha['demandas_analisadas']} pedidos. "
                       f"Origem do texto: {origem}.")
            with st.expander("Ficha de fatos usada na resposta"):
                st.json(ficha)
            try:
                db.registrar_consulta("app", id_serv, id_dist, len(relato))
            except Exception:
                pass  # banco somente leitura no deploy: o log e opcional

# ================================================================== Metodo
with metodo:
    secao("Método", "De onde vêm os números e até onde eles valem.")
    with st.expander("Dados e tratamento", expanded=True):
        st.markdown("Fonte: Portal de Dados Abertos da Prefeitura de São Paulo, conjunto "
                    "*Dados do SP156 - Solicitações*, 1º, 2º e 3º trimestres de 2026.")
        c1, c2 = st.columns(2, gap="large")
        c1.caption("Arquivos lidos, com formato detectado e validado")
        c1.dataframe(res["auditoria_arquivo"], hide_index=True, width='stretch')
        c2.caption("Funil de tratamento")
        c2.dataframe(res["auditoria_funil"][["etapa", "linhas"]], hide_index=True, width='stretch')
    with st.expander(f"Modelos: chance de finalização em {J} dias"):
        st.caption("Treino com pedidos de janeiro a junho, teste com os de julho a setembro. "
                   "A comparação com e sem distrito mede quanto o território acrescenta.")
        c1, c2 = st.columns(2, gap="large")
        c1.dataframe(res["res_modelos"].round(4), hide_index=True, width='stretch')
        cal = res["res_calibracao"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], line=dict(dash="dot", color=CINZA), name="Ideal"))
        fig.add_trace(go.Scatter(x=cal["previsto"], y=cal["observado"], mode="lines+markers",
                                 name="Gradient boosting", line=dict(color=OURO, width=2.5)))
        fig.update_layout(height=300, xaxis_title="Probabilidade prevista", yaxis_title="Frequência observada",
                          legend=dict(orientation="h", y=1.15, x=0))
        c2.plotly_chart(fig, width='stretch')
    r = resumo["recomendador"]
    with st.expander("Recomendador de serviço"):
        st.caption(f"{r['consultas']} consultas simuladas, escritas pela equipe: acerto na primeira sugestão em "
                   f"{br(100 * r['top1'])}% e entre as três primeiras em {br(100 * r['top3'], 1)}%.")
        st.dataframe(res["res_recomendador"], hide_index=True, width='stretch', height=240)
    with st.expander("Limitações"):
        st.markdown("""
- **Finalizado não é resolvido.** O status indica encerramento administrativo, não execução confirmada.
- **Só existe o que foi registrado.** Onde se registra menos, o problema aparece menos.
- **Data de corte inferida.** O portal não informa a data de extração.
- **Sem protocolo.** Registros idênticos foram tratados como um pedido.
- **Associação, não causa.** O índice mostra onde o prazo difere, não por quê.
- **Nove meses de um ano.** Não separa sazonalidade de tendência.
- **Datas sem hora.** Prazos abaixo de um dia aparecem como zero.
""")
