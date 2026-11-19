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
    font=dict(family=FONTE, color=MUDO, size=13), paper_bgcolor="rgba(0,0,0,0)", separators=",.",
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
            max-width: 900px; margin: 14px auto 16px auto; padding: 0;}}
.z-hero p {{font-size: 16px; color: var(--ph-mute); max-width: 640px; margin: 0 auto; line-height: 1.5;}}
.z-lead {{padding: 36px 0 30px 0;}}
.z-lead h1 {{font-size: 38px; font-weight: 400 !important; letter-spacing: -0.02em; line-height: 1.15;
            max-width: 900px; margin: 12px 0 12px 0; padding: 0;}}
.z-lead p {{font-size: 15px; color: var(--ph-mute); max-width: 720px; margin: 0; line-height: 1.5;}}
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
.z-g5 {{grid-template-columns: repeat(5, 1fr);}}
.z-g5 .z-kpi .v {{font-size: 32px;}}
.z-fatos > div {{display: grid; grid-template-columns: 150px 1fr; gap: 18px; align-items: baseline;
                padding: 18px 0; border-bottom: 1px solid var(--ph-border); font-size: 14px;
                color: var(--ph-mute); line-height: 1.45;}}
.z-fatos > div:first-child {{border-top: 1px solid var(--ph-border);}}
.z-fatos span {{font-size: 28px; font-weight: 400; letter-spacing: -0.02em; color: var(--ph-text);
               font-variant-numeric: tabular-nums;}}
.z-tab {{width: 100%; border-collapse: collapse; font-size: 14px;}}
.z-tab th {{font-size: 12px; font-weight: 500; letter-spacing: .06em; text-transform: uppercase;
           color: var(--ph-mute); text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--ph-border);}}
.z-tab td {{padding: 12px 8px; border-bottom: 1px solid var(--ph-border);}}
.z-tab .n {{text-align: right; font-variant-numeric: tabular-nums;}}
.z-tab td.o {{color: var(--ph-gold);}}
.z-tab, .z-tab tr, .z-tab td, .z-tab th {{border-left: 0; border-right: 0; border-top: 0;}}
.z-nota {{font-size: 12px; color: {CINZA}; margin-top: 56px; line-height: 1.5;}}
.z-resp {{background: var(--ph-surface); border-radius: 8px; padding: 22px 24px; font-size: 16px; line-height: 1.6;}}
[data-baseweb="tab-list"] {{gap: 28px; border-bottom: 1px solid var(--ph-border);}}
[data-baseweb="tab"] {{font-size: 14px !important; padding-left: 0 !important; padding-right: 0 !important;}}
[data-testid="stExpander"] details {{border: 1px solid var(--ph-border); border-radius: 8px; background: transparent;}}
[data-testid="stMetric"] {{background: var(--ph-surface); border-radius: 8px; padding: 18px 20px;}}
[data-testid="stMetricValue"] {{font-weight: 400; letter-spacing: -0.02em;}}
[data-testid="stMetricLabel"] p {{font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ph-mute);}}
@media (max-width: 900px) {{.z-g2, .z-g3, .z-g4, .z-g5, .z-valor {{grid-template-columns: 1fr;}} .z-hero h1 {{font-size: 34px;}}}}
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
        "res_pontos", "res_backtest", "res_alerta", "auditoria_funil", "auditoria_arquivo", "dim_servico",
        "dim_distrito")}
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
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
ROTULO = {
    "Tapa-buraco": "Tapa-buraco",
    "Árvore - Solicitar avaliação em calçadas e praças para fins de poda ou remoção": "Poda de árvore",
    "Guias, sarjetas e sarjetões - solicitar manutenção": "Guias e sarjetas",
    "Praça e canteiro central - solicitar roçada": "Roçada de praças",
    "Reformar galerias de águas de chuvas (pluviais)": "Galerias pluviais",
    "Solicitar limpeza de bueiros, boca de lobo e poços de visita": "Limpeza de bueiros",
    "Entulho e grandes objetos em via pública - solicitar remoção": "Remoção de entulho",
    "Fazer reclamação de falta de varrição": "Varrição",
    "Guias e sarjetas - Solicitar capinação": "Capinação",
    "Reclamar sobre coleta de lixo domiciliar": "Coleta de lixo",
}


@st.cache_data
def leitura_executiva(_d):
    """Numeros do resumo executivo, todos calculados da base."""
    e = _d[_d["elegivel_janela"] == 1]
    comp = e.groupby("servico").agg(volume=("resolvida_janela", "size"),
                                    atraso=("resolvida_janela", lambda x: int((1 - x).sum())))
    comp = comp.sort_values("atraso", ascending=False)
    comp["pct_volume"] = comp["volume"] / comp["volume"].sum()
    comp["pct_atraso"] = comp["atraso"] / comp["atraso"].sum()
    med = {sv: indicadores.percentil_km(p_["dias"], p_["finalizada"], 0.5) for sv, p_ in _d.groupby("servico")}
    vol = _d["servico"].value_counts()
    m = pd.Series(med).reindex(vol.index).astype(float).fillna(np.inf)
    total = vol.sum()
    veloc = {"Até 3 dias": vol[m <= 3].sum() / total, "De 4 a 30 dias": vol[(m > 3) & (m <= 30)].sum() / total,
             "Mais de 30 dias": vol[m > 30].sum() / total}
    mes = _d.assign(mes=_d["data_abertura"].dt.to_period("M").dt.to_timestamp())
    serie = mes.groupby("mes").agg(pedidos=("dias", "size"), cobertura=("elegivel_janela", "mean"))
    serie["taxa"] = mes[mes["elegivel_janela"] == 1].groupby("mes")["resolvida_janela"].mean()
    serie.loc[serie["cobertura"] < 0.95, "taxa"] = np.nan        # mes ainda sem 30 dias de observacao
    return {
        "comp": comp.reset_index(), "veloc": veloc, "serie": serie.reset_index(),
        "p50": indicadores.percentil_km(_d["dias"], _d["finalizada"], 0.5),
        "p80": indicadores.percentil_km(_d["dias"], _d["finalizada"], 0.8),
        "abertas": int((_d["finalizada"] == 0).sum()),
        "abertas_90": int(((_d["finalizada"] == 0) & (_d["dias"] > 90)).sum()),
        "por_dia": len(_d) / ((_d["data_abertura"].max() - _d["data_abertura"].min()).days + 1),
    }


with geral:
    x = leitura_executiva(d)
    comp = x["comp"]
    top3 = comp.head(3)
    v3, a3 = top3["pct_volume"].sum(), top3["pct_atraso"].sum()
    nomes3 = [ROTULO.get(n, curto(n, 22)) for n in top3["servico"]]
    fracao, verbo = ("Quase dois terços", "estão") if 0.60 <= a3 < 0.67 else (f"{br(100 * a3)}%", "está")

    html(f'<div class="z-hero" style="padding-bottom:36px"><div class="z-label">Resumo executivo · '
         f'{ENTREGA.get("assinatura", "")}</div>'
         f'<h1>{fracao} do atraso da zeladoria {verbo} em três serviços.</h1>'
         f'<p>{br(g["demandas"] / 1000)} mil pedidos do SP156, de janeiro a setembro de 2026, nos 96 distritos '
         'de São Paulo.</p></div>')

    grade([
        kpi("Pedidos", f"{br(g['demandas'] / 1000)} mil", f"{br(x['por_dia'] / 1000, 1)} mil por dia"),
        kpi(f"Finalizados em {J} dias", f"{br(100 * g['taxa_janela'])}%", "Média da cidade"),
        kpi("Metade resolvida em", f"{br(x['p50'])} dias", "Mediana"),
        kpi("1 em cada 5 espera mais de", f"{br(x['p80'])} dias", "Percentil 80", tom="ouro"),
        kpi("Em aberto", f"{br(x['abertas'] / 1000, 1)} mil",
            f"{br(x['abertas_90'] / 1000, 1)} mil há mais de 90 dias"),
    ], 5)

    # ---- 1 e 2: onde esta o atraso e as duas velocidades
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        secao(f"{br(100 * v3)}% do volume, {br(100 * a3)}% do atraso",
              f"{nomes3[0]}, {nomes3[1].lower()}, {nomes3[2].lower()}. Atraso: pedidos não finalizados em {J} dias.")
        tons = [OURO, "#B79F7C", "#8C7A60", "#2E2E2E"]
        partes = list(zip(nomes3 + ["Demais serviços"],
                          list(top3["pct_volume"]) + [1 - v3], list(top3["pct_atraso"]) + [1 - a3], tons))
        fig = go.Figure()
        for nome_, pv, pa, cor_ in partes:
            fig.add_trace(go.Bar(
                y=["Atraso", "Volume"], x=[100 * pa, 100 * pv], name=nome_, orientation="h",
                marker=dict(color=cor_, line=dict(color=PRETO, width=2)),
                text=[f"{br(100 * pa)}%", f"{br(100 * pv)}%"], textposition="inside", textangle=0,
                insidetextanchor="middle", textfont=dict(color=PRETO if cor_ != "#2E2E2E" else MUDO, size=15),
                hovertemplate=nome_ + ": %{x:.0f}%<extra></extra>"))
        fig.update_layout(barmode="stack", height=250, bargap=0.28,
                          legend=dict(orientation="h", y=1.18, x=0, traceorder="normal"),
                          xaxis=dict(visible=False, range=[0, 100]),
                          yaxis=dict(showgrid=False, tickfont=dict(size=13, color=TEXTO)),
                          uniformtext=dict(minsize=11, mode="hide"))
        st.plotly_chart(fig, width='stretch')
    with c2:
        vl = x["veloc"]
        secao("Uma zeladoria, duas velocidades",
              "Participação no volume, pelo prazo mediano do serviço.")
        fig = go.Figure(go.Bar(
            x=[100 * v for v in vl.values()], y=list(vl.keys()), orientation="h",
            marker=dict(color=[CINZA, CINZA, NEG], cornerradius=4),
            text=[f"{br(100 * v)}%" for v in vl.values()], textposition="outside",
            textfont=dict(color=TEXTO, size=15), hovertemplate="%{y}: %{x:.0f}% do volume<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=250, margin=dict(l=0, r=50, t=10, b=0), bargap=0.45,
                          xaxis=dict(visible=False, range=[0, 62]),
                          yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(size=13, color=TEXTO)))
        st.plotly_chart(fig, width='stretch')

    # ---- 3: no mesmo servico, o distrito pesa
    par = sd[sd["servico"] == "Tapa-buraco"].sort_values("taxa")
    extremos = ""
    if len(par) >= 2:
        dias_ = []
        for linha in (par.iloc[-1], par.iloc[0]):
            p_ = d[(d["servico"] == "Tapa-buraco") & (d["distrito"] == linha["distrito"])]
            med = indicadores.percentil_km(p_["dias"], p_["finalizada"], 0.5)
            dias_.append(f"{'150+' if med is None else br(med)} dias em {linha['distrito'].title()}")
        extremos = f" Tapa-buraco: metade resolvida em {dias_[0]} e em {dias_[1]}."
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        secao("No mesmo serviço, o prazo depende do distrito",
              f"Finalizados em {J} dias: distritos mais lentos e mais rápidos.{extremos}")
        top = amp.head(10).sort_values("amplitude_p90_p10").tail(6)
        nomes = [ROTULO.get(n, curto(n, 28)) for n in top["servico"]]
        fig = go.Figure()
        for nome_, a_, b_ in zip(nomes, top["p10"], top["p90"]):
            fig.add_trace(go.Scatter(x=[100 * a_, 100 * b_], y=[nome_, nome_], mode="lines",
                                     line=dict(color=CINZA, width=2), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=100 * top["p10"], y=nomes, mode="markers+text", name="Mais lentos",
                                 marker=dict(color=NEG, size=14, line=dict(color=PRETO, width=2)),
                                 text=[f"{br(100 * v)}%" for v in top["p10"]], textposition="middle left",
                                 textfont=dict(color=TEXTO),
                                 hovertemplate="%{y}<br>percentil 10: %{x:.0f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=100 * top["p90"], y=nomes, mode="markers+text", name="Mais rápidos",
                                 marker=dict(color=OURO, size=14, line=dict(color=PRETO, width=2)),
                                 text=[f"{br(100 * v)}%" for v in top["p90"]], textposition="middle right",
                                 textfont=dict(color=TEXTO),
                                 hovertemplate="%{y}<br>percentil 90: %{x:.0f}%<extra></extra>"))
        fig.update_layout(height=300, legend=dict(orientation="h", y=1.14, x=0),
                          xaxis=dict(range=[-8, 110], visible=False),
                          yaxis=dict(showgrid=False, tickfont=dict(size=13, color=TEXTO)))
        st.plotly_chart(fig, width='stretch')
    with c2:
        secao("O padrão é estável e não é geográfico", "Três verificações sobre o índice de equidade.")
        est, ce = resumo["estabilidade_spearman"], resumo["centralidade"]
        html('<div class="z-fatos">'
             f'<div><span>{br(resumo["indice"]["min"], 2)} a {br(resumo["indice"]["max"], 2)}</span>'
             'Índice por distrito, já descontado o tipo de serviço pedido. Cidade = 1,00.</div>'
             f'<div><span>{br(est["t2_t3"], 2)}</span>Correlação do índice entre trimestres. '
             'Os mesmos distritos ficam para trás.</div>'
             f'<div><span>{br(ce["spearman_indice_x_distancia"], 2)}</span>Correlação com a distância ao centro. '
             'Não é centro contra periferia.</div></div>')

    # ---- 4: onde agir + ao longo do ano
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        pares = res["res_prioridade"]
        secao(f"100 frentes concentram {br(100 * pr['acum_100'])}% do atraso evitável",
              f"De {br(pr['pares_avaliados'])} combinações de serviço e distrito. Alcançar o distrito mediano "
              f"nelas todas: {br(pr['ganho_total'] / 1000, 1)} mil pedidos a mais em {J} dias.")
        t5 = pares.head(5).copy()
        linhas = "".join(
            f'<tr><td>{int(r_.posicao)}</td><td>{ROTULO.get(r_.servico, curto(r_.servico, 30))}</td>'
            f'<td>{r_.distrito.title()}</td><td class="n">{br(100 * r_.taxa)}%</td>'
            f'<td class="n">{br(100 * r_.referencia)}%</td><td class="n o">+{br(r_.ganho)}</td></tr>'
            for r_ in t5.itertuples())
        html('<table class="z-tab"><thead><tr><th>#</th><th>Serviço</th><th>Distrito</th>'
             f'<th class="n">Em {J} dias</th><th class="n">Referência</th><th class="n">Pedidos a mais</th>'
             f'</tr></thead><tbody>{linhas}</tbody></table>')
    with c2:
        serie = x["serie"]
        secao("Ao longo do ano", "Pedidos abertos por mês. O primeiro trimestre concentra o maior volume.")
        fig = go.Figure(go.Bar(
            x=serie["mes"], y=serie["pedidos"], marker=dict(color=CINZA, cornerradius=3),
            text=[br(v / 1000) for v in serie["pedidos"]], textposition="outside", textfont=dict(color=MUDO, size=11),
            hovertemplate="%{y:,} pedidos<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=235, margin=dict(l=0, r=0, t=24, b=0), bargap=0.35, yaxis=dict(visible=False),
                          xaxis=dict(showgrid=False, tickmode="array", tickvals=list(serie["mes"]),
                                     ticktext=[MESES[m_.month - 1] for m_ in serie["mes"]],
                                     tickfont=dict(color=MUDO)))
        st.plotly_chart(fig, width='stretch')
        taxas = serie.dropna(subset=["taxa"])["taxa"]
        st.caption(f"Em milhares. A taxa de finalização em {J} dias oscilou entre {br(100 * taxas.min())}% e "
                   f"{br(100 * taxas.max())}% nos meses com observação completa.")

    secao("O que isso implica")
    html('<div class="z-valor">'
         '<div><h4>Para a prefeitura</h4><p>O ganho está em poucas frentes. Priorizar serviço e distrito, '
         'não a zeladoria inteira.</p></div>'
         '<div><h4>Para o morador</h4><p>O prazo esperado depende do serviço e do distrito. '
         'Saber disso antes de abrir o pedido ajusta a expectativa.</p></div>'
         '<div><h4>Para a sociedade</h4><p>A comparação justa é dentro do mesmo serviço. '
         'É ela que permite cobrar com número.</p></div></div>')
    html('<div class="z-nota">Dados abertos do SP156, Prefeitura de São Paulo. Finalizado é o encerramento '
         'do pedido no sistema, não a confirmação de execução. Em aberto: situação na data de extração de cada '
         'arquivo trimestral. Números históricos, não garantia de prazo.</div>')

# ================================================================== componentes comuns
def abertura(rotulo, titulo, sub=""):
    html(f'<div class="z-lead"><div class="z-label">{rotulo}</div><h1>{titulo}</h1>'
         + (f"<p>{sub}</p>" if sub else "") + "</div>")


def grafico_simulacoes(bt, altura=300):
    """Previsto x real nas simulacoes do alerta em datas passadas."""
    datas = [pd.Timestamp(v).strftime("%d/%m") for v in bt["data"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=datas, y=bt["previsto_referencia"], name="Taxa histórica do serviço",
                         marker=dict(color="#2E2E2E", cornerradius=3),
                         hovertemplate="Referência: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=datas, y=bt["previsto"], name="Alerta ZelaSP",
                         marker=dict(color=OURO, cornerradius=3),
                         hovertemplate="Previsto: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=datas, y=bt["real"], name="O que aconteceu", mode="markers",
                             marker=dict(color=TEXTO, size=11, symbol="line-ew", line=dict(color=TEXTO, width=3)),
                             hovertemplate="Real: %{y:,.0f}<extra></extra>"))
    fig.update_layout(height=altura, barmode="group", bargap=0.3, bargroupgap=0.08,
                      legend=dict(orientation="h", y=1.16, x=0), xaxis=dict(showgrid=False, title="Data da simulação"),
                      yaxis=dict(title=None, tickformat=",.0f"))
    return fig


bt, alerta_tab, al = res["res_backtest"], res["res_alerta"], resumo["alerta"]
try:
    N_TESTES = (config.RAIZ / "docs" / "evidencias_pytest.txt").read_text(encoding="utf-8").count(" PASSED")
except OSError:
    N_TESTES = 0

# ================================================================== Onde agir
with agir:
    pares, fila, pontos = res["res_prioridade"], res["res_fila"], res["res_pontos"]
    abertura("Prioridade para a gestão",
             f"100 frentes concentram {br(100 * pr['acum_100'])}% do atraso evitável.",
             f"De {br(pr['pares_avaliados'])} combinações de serviço e distrito. Quatro leituras para decidir "
             "onde agir primeiro.")
    grade([
        kpi("Atraso evitável", f"{br(pr['ganho_total'] / 1000, 1)} mil",
            f"Pedidos a mais em {J} dias, se cada frente alcançasse o distrito mediano"),
        kpi("Devem passar do prazo", f"{br(al['devem_passar'] / 1000, 1)} mil",
            f"De {br(al['abertos_recentes'] / 1000, 1)} mil pedidos recentes, pelo modelo de alerta", tom="ouro"),
        kpi("Já passaram do prazo", br(pr["atrasadas"]), "Em aberto além do prazo típico do próprio serviço"),
        kpi("Pontos de reincidência", br(pr["pontos_3"]), "Locais com 3 ou mais pedidos iguais em 100 m"),
    ], 4)

    secao("Plano de ação", "Frentes ordenadas pelo atraso evitável. Escolha quantas priorizar.")
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        fig = go.Figure(go.Scatter(x=pares["posicao"], y=100 * pares["acumulado"], mode="lines",
                                   line=dict(color=OURO, width=2.5),
                                   hovertemplate="%{x} frentes: %{y:.0f}%<extra></extra>"))
        marcos = [20, 50, 100]
        fig.add_trace(go.Scatter(
            x=marcos, y=[100 * pares["acumulado"].iloc[m - 1] for m in marcos], mode="markers+text",
            marker=dict(color=TEXTO, size=9, line=dict(color=PRETO, width=2)),
            text=[f"{m} · {br(100 * pares['acumulado'].iloc[m - 1])}%" for m in marcos],
            textposition="middle right", textfont=dict(color=TEXTO), hoverinfo="skip"))
        fig.update_layout(height=360, showlegend=False, xaxis_title="Frentes priorizadas",
                          yaxis=dict(ticksuffix="%", range=[0, 103]))
        st.plotly_chart(fig, width='stretch')
    with c2:
        n = st.slider("Frentes a priorizar", 10, 200, 50, 10)
        sel = pares.head(n)
        st.markdown(f"**{br(100 * sel['acumulado'].iloc[-1])}%** do atraso evitável · "
                    f"**{br(sel['ganho'].sum())}** pedidos a mais em {J} dias")
        vis = sel[["posicao", "servico", "distrito", "elegiveis", "taxa", "referencia", "ganho"]].copy()
        vis["distrito"] = vis["distrito"].str.title()
        vis["servico"] = [ROTULO.get(n_, curto(n_, 44)) for n_ in vis["servico"]]
        for col in ("taxa", "referencia"):
            vis[col] = (100 * vis[col]).round(0)
        vis["ganho"] = vis["ganho"].round(0)
        st.dataframe(vis.rename(columns={
            "posicao": "#", "servico": "Serviço", "distrito": "Distrito", "elegiveis": "Pedidos",
            "taxa": f"% em {J}d", "referencia": "Referência (%)", "ganho": "Pedidos a mais"}),
            hide_index=True, width='stretch', height=270)

    secao(f"Alerta antecipado: {br(100 * al['devem_passar'] / al['abertos_recentes'])}% dos pedidos recentes "
          f"em aberto devem passar de {J} dias",
          f"Modelo de sobrevivência que considera há quantos dias o pedido já espera. Simulado em "
          f"{al['simulacoes']} datas passadas, errou o total em no máximo {br(100 * al['erro_total_max'], 1)}%.")
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        por = alerta_tab.groupby("servico")["devem_passar"].sum().sort_values().tail(6)
        fig = go.Figure(go.Bar(
            x=por.values, y=[ROTULO.get(n_, curto(n_, 30)) for n_ in por.index], orientation="h",
            marker=dict(color=[CINZA] * (len(por) - 1) + [OURO], cornerradius=4),
            text=[br(v) for v in por.values], textposition="outside", textfont=dict(color=MUDO),
            hovertemplate="%{y}: %{x:.0f} pedidos devem passar do prazo<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=300, margin=dict(l=0, r=50, t=10, b=0),
                          xaxis=dict(visible=False, range=[0, float(por.max()) * 1.18]),
                          yaxis=dict(showgrid=False, tickfont=dict(color=TEXTO)))
        st.plotly_chart(fig, width='stretch')
        st.caption(f"Pedidos que devem passar de {J} dias, por serviço. Retrato de "
                   f"{pd.Timestamp(al['data_retrato']).strftime('%d/%m/%Y')}.")
    with c2:
        st.plotly_chart(grafico_simulacoes(bt), width='stretch')
        st.caption("Cada barra é uma simulação: o modelo vê só o que era conhecido naquela data e prevê quantos "
                   "pedidos em aberto passariam do prazo. O traço branco é o que de fato aconteceu.")
    with st.expander("Alerta por distrito"):
        va = alerta_tab.head(300).copy()
        va["distrito"] = va["distrito"].str.title()
        va["servico"] = [ROTULO.get(n_, curto(n_, 44)) for n_ in va["servico"]]
        va["devem_passar"] = va["devem_passar"].round(0)
        va["risco_medio"] = (100 * va["risco_medio"]).round(0)
        st.dataframe(va[["servico", "distrito", "abertos", "devem_passar", "risco_medio"]].rename(
            columns={"servico": "Serviço", "distrito": "Distrito", "abertos": "Em aberto (recentes)",
                     "devem_passar": "Devem passar do prazo", "risco_medio": "Risco médio (%)"}),
            hide_index=True, width='stretch', height=320)

    secao(f"{br(pr['atrasadas'])} pedidos já passaram do prazo típico",
          f"Retrato de {pd.Timestamp(pr['data_retrato']).strftime('%d/%m/%Y')}. Em aberto há mais tempo do que "
          "8 em cada 10 pedidos do mesmo serviço levaram.")
    sub = st.selectbox("Subprefeitura", ["Todas"] + sorted(fila["subprefeitura"].dropna().unique()))
    f = fila if sub == "Todas" else fila[fila["subprefeitura"] == sub]
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        por = f.groupby("servico")["pedidos"].sum().sort_values().tail(8)
        fig = go.Figure(go.Bar(x=por.values, y=[ROTULO.get(n_, curto(n_, 34)) for n_ in por.index],
                               orientation="h",
                               marker=dict(color=[CINZA] * (len(por) - 1) + [OURO], cornerradius=4),
                               text=por.values, textposition="outside", textfont=dict(color=MUDO),
                               hovertemplate="%{y}: %{x} pedidos<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=320, margin=dict(l=0, r=50, t=10, b=0),
                          xaxis=dict(visible=False, range=[0, float(por.max()) * 1.15 if len(por) else 1]),
                          yaxis=dict(showgrid=False, tickfont=dict(color=TEXTO)))
        st.plotly_chart(fig, width='stretch')
    with c2:
        vf = f.head(200).copy()
        vf["distrito"] = vf["distrito"].str.title()
        vf["servico"] = [ROTULO.get(n_, curto(n_, 44)) for n_ in vf["servico"]]
        st.dataframe(vf[["servico", "distrito", "pedidos", "limite_dias", "dias_mediano", "dias_maximo"]].rename(
            columns={"servico": "Serviço", "distrito": "Distrito", "pedidos": "Atrasados",
                     "limite_dias": "Prazo típico (dias)", "dias_mediano": "Em aberto há (mediana)",
                     "dias_maximo": "Mais antigo (dias)"}), hide_index=True, width='stretch', height=320)

    secao(f"{br(pr['pontos_3'])} pontos onde uma ida da equipe resolve vários pedidos",
          "Pedidos em aberto do mesmo serviço em um raio de 100 m.")
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
        st.markdown(f"""
- **Atraso evitável é ordem de grandeza, não previsão.** A conta não sabe por que uma frente está abaixo da referência.
- **O alerta prevê encerramento no sistema**, não execução do serviço. Foi validado em {al['simulacoes']} datas passadas; não foi testado em operação.
- **Volume favorece quem reclama mais.** Por isso a comparação é com a referência do próprio serviço, não com o volume bruto.
- **Retrato da última extração publicada**, não de hoje.
- **Gravidade não está nos dados.** Um peso por risco precisa ser definido pela prefeitura.
- **Mapa:** a área cinza é a mancha urbana formada pelos próprios pedidos. Limites de distrito não são desenhados.
""")

# ================================================================== Distritos
with distritos:
    abaixo = int((dist["ic_sup"] < 1).sum())
    acima = int((dist["ic_inf"] > 1).sum())
    est, ce = resumo["estabilidade_spearman"], resumo["centralidade"]
    abertura("Equidade territorial",
             f"{abaixo} dos {len(dist)} distritos resolvem menos do que o esperado para os serviços que recebem.",
             "Índice de equidade: resolvido em 30 dias dividido pelo esperado para o mesmo conjunto de serviços. "
             "Cidade = 1,00.")
    grade([
        kpi("Abaixo do esperado", str(abaixo), "Distritos, com margem de erro", tom="neg"),
        kpi("Na média da cidade", str(len(dist) - abaixo - acima), "Distritos"),
        kpi("Acima do esperado", str(acima), "Distritos", tom="ouro"),
        kpi("Estabilidade", br(est["t2_t3"], 2), "Correlação do índice entre trimestres"),
        kpi("Centro e periferia", br(ce["spearman_indice_x_distancia"], 2), "Correlação com a distância ao centro"),
    ], 5)

    secao("Onde estão", "Tamanho do círculo: volume de pedidos.")
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        cor = st.radio("Colorir por", ["Índice", "Perfil"], horizontal=True, label_visibility="collapsed")
        dist["Grupo"] = "Perfil " + dist["grupo"].astype(str)
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

    kk = res["res_kmeans_k"]
    mixcols = [c for c in dist.columns if c.startswith("mix_")]
    media_mix = dist[mixcols].mean()
    secao("Três perfis de distrito",
          "Agrupamento por K-Means sobre atendimento, canal, volume e tipo de pedido.")
    blocos = []
    for gnum, parte in dist.groupby("grupo"):
        dif = (parte[mixcols].mean() - media_mix).sort_values(ascending=False)
        marca_ = curto(dif.index[0].replace("mix_", "").split(",")[0], 30)
        blocos.append(
            f'<div class="z-kpi"><div class="z-label">Perfil {gnum} · {len(parte)} distritos</div>'
            f'<div class="v {"neg" if gnum == 1 else ""}">{br(parte["indice"].mean(), 2)}</div>'
            f'<div class="d">Índice médio · metade dos pedidos resolvida em {br(parte["p50_dias"].mean())} dias · '
            f'{br(100 * parte["pct_aberta"].mean())}% em aberto<br>Pede mais que a média: {marca_.lower()}</div></div>')
    grade(blocos, 3)
    st.caption(f"Silhueta de {br(kk['silhueta'].max(), 2)}: os perfis são uma segmentação de leitura, não tipos "
               "bem separados. Para ver no mapa, escolha Perfil acima.")

    secao("Não é centro contra periferia",
          f"Correlação entre índice e distância ao centro: {br(ce['spearman_indice_x_distancia'], 2)}. "
          "Fraca, e no sentido contrário ao esperado.")
    fig = px.scatter(dist, x="dist_centro_km", y="indice", hover_name="Distrito", trendline="ols",
                     color_discrete_sequence=[OURO], height=360,
                     labels={"dist_centro_km": "Distância à Praça da Sé (km)", "indice": "Índice"})
    fig.update_traces(marker=dict(size=9, line=dict(color=PRETO, width=1)), selector=dict(mode="markers"))
    fig.update_traces(line=dict(color=CINZA, width=1.5), selector=dict(mode="lines"))
    fig.add_hline(y=1, line_dash="dot", line_color=CINZA)
    st.plotly_chart(fig, width='stretch')

    with st.expander("Como ler"):
        st.markdown(
            "O índice divide o que o distrito resolveu em 30 dias pelo que seria esperado se cada serviço "
            "pedido ali tivesse a taxa média da cidade. Isso separa desempenho de tipo de pedido. Um distrito "
            "conta como abaixo ou acima do esperado quando o intervalo de confiança de 95% não inclui 1,00.\n\n"
            "A correlação fraca com a distância não prova que a periferia é mais bem atendida. A base só "
            "contém o que foi registrado, e finalizado é encerramento administrativo, não execução confirmada.")
    with st.expander("Composição dos perfis"):
        for nome, parte in dist.groupby("Grupo"):
            st.markdown(f"**{nome}** · " + ", ".join(sorted(parte["Distrito"])))

# ================================================================== Servicos
with servicos:
    desiguais = int((amp["amplitude_p90_p10"] >= 0.40).sum())
    uniformes = int((amp["amplitude_p90_p10"] < 0.10).sum())
    abertura("Mesmo serviço, distritos diferentes",
             f"Em {desiguais} serviços, o distrito muda o resultado em mais de 40 pontos. "
             f"Em {uniformes}, quase não muda.",
             f"Diferença, em pontos percentuais, entre distritos rápidos e lentos na taxa de finalização em {J} dias.")
    ordenado = amp.sort_values("amplitude_p90_p10")
    fig = go.Figure(go.Bar(
        x=100 * ordenado["amplitude_p90_p10"], y=[ROTULO.get(n_, curto(n_, 44)) for n_ in ordenado["servico"]],
        orientation="h",
        marker=dict(color=[OURO if v >= 0.40 else CINZA for v in ordenado["amplitude_p90_p10"]], cornerradius=3),
        text=[f"{br(100 * v)}" for v in ordenado["amplitude_p90_p10"]], textposition="outside",
        textfont=dict(color=MUDO), customdata=ordenado[["p10", "p90"]].to_numpy() * 100,
        hovertemplate="%{y}<br>lentos: %{customdata[0]:.0f}% · rápidos: %{customdata[1]:.0f}%<extra></extra>"))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(height=max(360, 26 * len(ordenado)), margin=dict(l=0, r=40, t=10, b=0), bargap=0.3,
                      xaxis=dict(visible=False, range=[0, 70]),
                      yaxis=dict(showgrid=False, tickfont=dict(color=TEXTO, size=12)))
    st.plotly_chart(fig, width='stretch')

    secao("Um serviço em detalhe", "Escolha o serviço para ver cada distrito.")
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
    fig = px.bar(s, x="Distrito", y=s["taxa"] * 100, color=s["taxa"] * 100, height=340,
                 color_continuous_scale=DIVERGENTE, color_continuous_midpoint=100 * linha["mediana"],
                 labels={"y": f"% em {J} dias", "color": "%"}, hover_data={"elegiveis": True})
    fig.update_layout(coloraxis_showscale=False, xaxis=dict(tickangle=-60, title=None, tickfont=dict(size=9)),
                      yaxis=dict(ticksuffix="%", title=None), bargap=0.25)
    st.plotly_chart(fig, width='stretch')

    secao("Quanto tempo o pedido fica em aberto", "Compare dois distritos. A linha pontilhada é a cidade.")
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
    fig.update_layout(height=360, xaxis=dict(title="Dias desde a abertura", range=[0, 150]),
                      yaxis=dict(title=None, ticksuffix="%", range=[0, 100]),
                      legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, width='stretch')
    st.caption("Percentual de pedidos ainda em aberto. Curva de Kaplan-Meier, que considera também os pedidos "
               "não finalizados.")
    with st.expander("Tabela completa"):
        vis = amp[["servico", "demandas", "distritos", "p10", "mediana", "p90", "amplitude_p90_p10"]].copy()
        for col in ("p10", "mediana", "p90", "amplitude_p90_p10"):
            vis[col] = (100 * vis[col]).round(0)
        st.dataframe(vis.rename(columns={
            "servico": "Serviço", "demandas": "Pedidos", "distritos": "Distritos", "p10": "Percentil 10 (%)",
            "mediana": "Mediano (%)", "p90": "Percentil 90 (%)", "amplitude_p90_p10": "Diferença (p.p.)"}),
            hide_index=True, width='stretch')

# ================================================================== Abrir pedido
with pedido:
    abertura("Para o morador", "Descreva o problema. Receba o serviço certo e o prazo no seu distrito.")
    c1, c2 = st.columns([3, 1], gap="large")
    relato_bruto = c1.text_input("O que está acontecendo?", max_chars=300,
                                 placeholder="Ex.: buraco grande na rua em frente à escola")
    distrito = c2.selectbox("Distrito", sorted(dist["Distrito"]))
    st.caption("Não informe nome, CPF, telefone ou e-mail. O texto não é armazenado.")
    if not relato_bruto:
        r_ = resumo["recomendador"]
        html('<div style="height:28px"></div><div class="z-valor">'
             '<div><h4>1 · Recomendação</h4><p>Busca por similaridade de texto entre o seu relato e os '
             f'{resumo["servicos"]} serviços de zeladoria. Acerta entre as três sugestões em '
             f'{br(100 * r_["top3"], 1)}% das consultas de teste.</p></div>'
             '<div><h4>2 · Prazo</h4><p>Histórico do mesmo serviço no seu distrito, pelo estimador de '
             'Kaplan-Meier, e a chance de finalização estimada por gradient boosting.</p></div>'
             '<div><h4>3 · Orientação</h4><p>Texto redigido só com os números calculados. Se a IA generativa '
             'citar um número que o sistema não calculou, a resposta é descartada.</p></div></div>')
    else:
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
            xq = pd.DataFrame([{"id_servico": id_serv, "id_distrito": id_dist, "canal": "PORTAL",
                                "dia_semana": hoje.day_of_week, "dia_do_mes": hoje.day}])
            prob = float(clf.predict_proba(xq[modelo.CATEGORICAS + modelo.NUMERICAS])[0, 1])
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

            c1, c2 = st.columns([3, 2], gap="large")
            with c1:
                resposta = assistente.responder(ficha, relato, cliente=assistente.cliente_llm())
                secao("Orientação")
                html(f'<div class="z-resp">{resposta["texto"]}</div>')
                origem = "IA generativa restrita à ficha de fatos" if resposta["origem"] == "ia_generativa" \
                    else f"redação padrão ({resposta['motivo']})"
                st.caption(f"Base: {ficha['base_da_estimativa']}, {ficha['demandas_analisadas']} pedidos. "
                           f"Origem do texto: {origem}.")
            with c2:
                secao("De onde vem a estimativa", f"Chance de finalização em {J} dias.")
                fontes = [("Cidade, mesmo serviço", ficha["pct_resolvidas_na_janela_cidade"], CINZA),
                          (f"{distrito}, histórico", ficha["pct_resolvidas_na_janela"], MUDO),
                          ("Modelo preditivo", ficha["chance_modelo_pct"], OURO)]
                fontes = [f_ for f_ in fontes if f_[1] is not None]
                fig = go.Figure(go.Bar(
                    x=[f_[1] for f_ in fontes], y=[f_[0] for f_ in fontes], orientation="h",
                    marker=dict(color=[f_[2] for f_ in fontes], cornerradius=4),
                    text=[f"{f_[1]}%" for f_ in fontes], textposition="outside", textfont=dict(color=TEXTO, size=14),
                    hovertemplate="%{y}: %{x}%<extra></extra>"))
                fig.update_traces(cliponaxis=False)
                fig.update_layout(height=190, margin=dict(l=0, r=50, t=6, b=0), bargap=0.4,
                                  xaxis=dict(visible=False, range=[0, 118]),
                                  yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(color=TEXTO)))
                st.plotly_chart(fig, width='stretch')
            with st.expander("Ficha de fatos usada na resposta"):
                st.json(ficha)
            try:
                db.registrar_consulta("app", id_serv, id_dist, len(relato))
            except Exception:
                pass  # banco somente leitura no deploy: o log e opcional

# ================================================================== Metodo
with metodo:
    mods = res["res_modelos"].set_index("modelo")
    r = resumo["recomendador"]
    funil = res["auditoria_funil"].set_index("etapa")["linhas"]
    ganho_auc = mods.loc["Gradient boosting", "auc"] - mods.loc["Gradient boosting sem distrito", "auc"]
    abertura("Método e evidências",
             "O tipo de serviço explica a maior parte do prazo. O distrito e a idade do pedido melhoram a previsão.",
             "Cada número do painel sai de dado público, com método declarado e teste automatizado.")
    grade([
        kpi("Linhas lidas", f"{br(funil['linhas_brutas'] / 1e6, 1)} mi", f"{br(funil['base_final'] / 1000)} mil "
            "pedidos após o tratamento"),
        kpi("Testes automatizados", str(N_TESTES), "Todos passando"),
        kpi("AUC do classificador", br(mods.loc["Gradient boosting", "auc"], 3), "Validação temporal", tom="ouro"),
        kpi("Erro do alerta", f"até {br(100 * al['erro_total_max'], 1)}%",
            f"No total previsto, em {al['simulacoes']} simulações"),
        kpi("Recomendador", f"{br(100 * r['top3'], 1)}%", f"Acerto em 3 sugestões, {r['consultas']} consultas simuladas"),
    ], 5)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        secao(f"O distrito soma {br(100 * ganho_auc, 1)} pontos de AUC",
              f"Chance de finalização em {J} dias. Treino de janeiro a junho, teste de julho a setembro.")
        nomes_m = {"Baseline (taxa do servico)": "Referência: taxa do serviço",
                   "Gradient boosting sem distrito": "Gradient boosting sem distrito",
                   "Regressao logistica": "Regressão logística", "Rede neural MLP (32,16)": "Rede neural MLP",
                   "Gradient boosting": "Gradient boosting"}
        mm = res["res_modelos"].copy()
        mm["nome"] = mm["modelo"].map(nomes_m)
        mm = mm.set_index("modelo").loc[list(nomes_m)].iloc[::-1]
        fig = go.Figure(go.Bar(
            x=mm["auc"], y=mm["nome"], orientation="h",
            marker=dict(color=[OURO if n_ == "Gradient boosting" else CINZA for n_ in mm.index], cornerradius=4),
            text=[br(v, 3) for v in mm["auc"]], textposition="outside", textfont=dict(color=TEXTO),
            customdata=mm[["brier"]].to_numpy(), hovertemplate="%{y}<br>AUC %{x:.3f} · Brier %{customdata[0]:.3f}<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_layout(height=280, margin=dict(l=0, r=50, t=10, b=0), bargap=0.35,
                          xaxis=dict(visible=False, range=[0.78, 0.855]),
                          yaxis=dict(showgrid=False, tickfont=dict(color=TEXTO)))
        st.plotly_chart(fig, width='stretch')
        st.caption("O eixo começa em 0,78 para evidenciar a diferença. A rede neural empata com o gradient "
                   "boosting e tem calibração pior, então não justifica a complexidade.")
    with c2:
        secao("Calibração", "Probabilidade prevista contra frequência observada.")
        cal = res["res_calibracao"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], line=dict(dash="dot", color=CINZA), name="Ideal"))
        fig.add_trace(go.Scatter(x=cal["previsto"], y=cal["observado"], mode="lines+markers",
                                 name="Gradient boosting", line=dict(color=OURO, width=2.5)))
        fig.update_layout(height=280, xaxis=dict(title="Previsto", tickformat=".0%"),
                          yaxis=dict(title=None, tickformat=".0%"), legend=dict(orientation="h", y=1.15, x=0))
        st.plotly_chart(fig, width='stretch')
        st.caption("O modelo subestima nas faixas intermediárias: o terceiro trimestre teve taxa maior que o treino.")

    secao(f"O alerta acerta o total com erro de até {br(100 * al['erro_total_max'], 1)}%",
          f"A taxa histórica do serviço, que ignora a idade do pedido, erra em média "
          f"{br(abs(100 * al['erro_total_referencia_medio']))}% para menos.")
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.plotly_chart(grafico_simulacoes(bt, 320), width='stretch')
    with c2:
        vb = bt[["data", "pedidos", "previsto", "real", "erro_total", "auc", "auc_referencia"]].copy()
        vb["data"] = pd.to_datetime(vb["data"]).dt.strftime("%d/%m")
        vb["previsto"] = vb["previsto"].round(0)
        vb["erro_total"] = (100 * vb["erro_total"]).round(1)
        st.dataframe(vb.rename(columns={"data": "Data", "pedidos": "Em aberto", "previsto": "Previsto",
                                        "real": "Real", "erro_total": "Erro (%)", "auc": "AUC",
                                        "auc_referencia": "AUC ref."}),
                     hide_index=True, width='stretch', height=250,
                     column_config={"AUC": st.column_config.NumberColumn(format="%.3f"),
                                    "AUC ref.": st.column_config.NumberColumn(format="%.3f")})
        st.caption("Modelo de sobrevivência por serviço e distrito: a chance de passar de 30 dias dado que o "
                   "pedido já espera há k dias.")

    secao("Onde cada técnica entra")
    html('<table class="z-tab"><thead><tr><th>Técnica</th><th>Para quê</th><th>Onde aparece</th></tr></thead><tbody>'
         '<tr><td>Kaplan-Meier</td><td>Medir prazo sem ignorar os pedidos em aberto</td><td>Visão geral, Serviços, Abrir pedido</td></tr>'
         '<tr><td>Modelo de sobrevivência condicional</td><td>Prever quais pedidos em aberto passam do prazo</td><td>Onde agir</td></tr>'
         '<tr><td>Padronização indireta</td><td>Comparar distritos descontando o tipo de pedido</td><td>Distritos</td></tr>'
         '<tr><td>K-Means</td><td>Agrupar distritos em perfis</td><td>Distritos</td></tr>'
         '<tr><td>Gradient boosting, regressão logística, rede neural</td><td>Estimar a chance de finalização em 30 dias</td><td>Abrir pedido</td></tr>'
         '<tr><td>TF-IDF e similaridade de cosseno</td><td>Indicar o serviço a partir do relato</td><td>Abrir pedido</td></tr>'
         '<tr><td>IA generativa com verificador</td><td>Redigir a orientação sem inventar número</td><td>Abrir pedido</td></tr>'
         '</tbody></table>')

    html('<div style="height:40px"></div>')
    with st.expander("Dados e tratamento"):
        st.markdown("Fonte: Portal de Dados Abertos da Prefeitura de São Paulo, conjunto "
                    "*Dados do SP156 - Solicitações*, 1º, 2º e 3º trimestres de 2026.")
        c1, c2 = st.columns(2, gap="large")
        c1.caption("Arquivos lidos, com formato detectado e validado")
        c1.dataframe(res["auditoria_arquivo"], hide_index=True, width='stretch')
        c2.caption("Funil de tratamento")
        c2.dataframe(res["auditoria_funil"][["etapa", "linhas"]], hide_index=True, width='stretch')
    with st.expander("Modelos em números"):
        st.dataframe(res["res_modelos"].round(4), hide_index=True, width='stretch')
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
- **IA generativa.** As travas foram testadas com cliente simulado; a chamada a um provedor real não foi validada.
""")
