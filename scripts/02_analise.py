"""Calcula indicadores, grupos e modelos; grava tabelas de resultado, figuras e o modelo final.

Uso: python scripts/02_analise.py
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zeladoria import clusters, config, db, indicadores, modelo  # noqa: E402
from zeladoria import recomendador as rec  # noqa: E402
from zeladoria.etl import normalizar  # noqa: E402

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
COR, COR2, CINZA = "#B08D5E", "#B4544B", "#A3A3A3"


def main():
    d = db.demandas()
    d["trimestre"] = d["data_abertura"].dt.quarter
    config.DIR_ASSETS.mkdir(exist_ok=True)
    resumo = {"geral": indicadores.resumo_prazo(d), "distritos": int(d["distrito"].nunique()),
              "servicos": int(d["id_servico"].nunique())}

    # --- indicadores por distrito -------------------------------------------------
    m = clusters.matriz_distritos(d)
    pz = indicadores.prazo_por_distrito(d).set_index("distrito")
    ix = indicadores.indice_por_distrito(d).set_index("distrito")
    grupos, aval_k = clusters.agrupar(m)
    tab = grupos.merge(ix[["ic_inf", "ic_sup", "taxa_esperada"]].reset_index(), on="distrito")
    tab = tab.merge(pz[["p80_dias"]].reset_index(), on="distrito")
    for q in (1, 2, 3):
        parc = indicadores.indice_por_distrito(d[d["trimestre"] == q]).set_index("distrito")["indice"]
        tab[f"indice_t{q}"] = tab["distrito"].map(parc)
    estab = tab[["indice_t1", "indice_t2", "indice_t3"]].corr(method="spearman")
    rho, p = spearmanr(tab["indice"], tab["dist_centro_km"])
    resumo["estabilidade_spearman"] = {"t1_t2": estab.iloc[0, 1], "t2_t3": estab.iloc[1, 2],
                                       "t1_t3": estab.iloc[0, 2]}
    resumo["centralidade"] = {"spearman_indice_x_distancia": rho, "p_valor": p}
    resumo["indice"] = {"min": tab["indice"].min(), "max": tab["indice"].max(),
                        "p10": tab["indice"].quantile(.1), "p90": tab["indice"].quantile(.9)}
    resumo["taxa_bruta"] = {"min": tab["taxa_bruta"].min(), "max": tab["taxa_bruta"].max()}

    # --- mesmo servico, distritos diferentes --------------------------------------
    sd = indicadores.servico_distrito(d)
    amp = sd.groupby(["id_servico", "servico"]).agg(
        distritos=("distrito", "size"), pior=("taxa", "min"), p10=("taxa", lambda s: s.quantile(.1)),
        mediana=("taxa", "median"), p90=("taxa", lambda s: s.quantile(.9)), melhor=("taxa", "max"),
        demandas=("elegiveis", "sum")).reset_index()
    amp = amp[amp["distritos"] >= 20].assign(amplitude_p90_p10=lambda t: t["p90"] - t["p10"])
    amp = amp.sort_values("demandas", ascending=False)

    # --- sensibilidade: sem colapsar registros repetidos ---------------------------
    pesos = d.loc[d.index.repeat(d["registros"])]
    ix_peso = indicadores.indice_por_distrito(pesos).set_index("distrito")["indice"]
    resumo["sensibilidade_repetidos_spearman"] = spearmanr(
        tab.set_index("distrito")["indice"], ix_peso.reindex(tab["distrito"]).to_numpy())[0]
    # --- sensibilidade: janela de 60 dias -------------------------------------------
    d60 = d.assign(elegivel_janela=(d["dias_observaveis"] >= 60).astype(int),
                   resolvida_janela=((d["finalizada"] == 1) & (d["dias"] <= 60)).astype(int))
    ix60 = indicadores.indice_por_distrito(d60).set_index("distrito")["indice"]
    resumo["sensibilidade_janela60_spearman"] = spearmanr(
        tab.set_index("distrito")["indice"], ix60.reindex(tab["distrito"]).to_numpy())[0]

    # --- prioridade para a gestao ----------------------------------------------------
    pares = indicadores.atraso_evitavel(d)
    eleg = d[d["elegivel_janela"] == 1]
    ultimo = d["data_corte"].max()
    retrato = d[d["data_corte"] == ultimo]            # ultimo arquivo: retrato unico e coerente
    abertas = retrato[retrato["finalizada"] == 0]
    limites = indicadores.limites_por_servico(d)
    atrasadas = indicadores.fila_atrasada(abertas, limites)
    fila = atrasadas.groupby(["servico", "subprefeitura", "distrito"]).agg(
        pedidos=("dias", "size"), dias_mediano=("dias", "median"), dias_maximo=("dias", "max"),
        limite_dias=("limite_dias", "first")).reset_index().sort_values("pedidos", ascending=False)
    pontos = indicadores.pontos_de_reincidencia(abertas)
    resumo["prioridade"] = {
        "pares_avaliados": int(indicadores.servico_distrito(d).shape[0]),
        "pares_abaixo": int(len(pares)), "ganho_total": float(pares["ganho"].sum()),
        "nao_resolvidas_janela": int((eleg["resolvida_janela"] == 0).sum()),
        "acum_20": float(pares["acumulado"].iloc[19]), "acum_50": float(pares["acumulado"].iloc[49]),
        "acum_100": float(pares["acumulado"].iloc[99]),
        "data_retrato": str(ultimo), "abertas_retrato": int(len(abertas)),
        "atrasadas": int(len(atrasadas)), "pontos_3": int(len(pontos)),
        "pontos_5": int((pontos["pedidos"] >= 5).sum())}

    # --- alerta antecipado (sobrevivencia) -------------------------------------------
    testes_alerta = [indicadores.backtest_alerta(d, dt) for dt in (
        "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-30", "2026-08-31")]
    bt = pd.DataFrame([t for t in testes_alerta if t])
    bt["erro_total"] = bt["previsto"] / bt["real"] - 1
    bt["erro_total_referencia"] = bt["previsto_referencia"] / bt["real"] - 1
    recentes = abertas[abertas["dias"] < config.JANELA_DIAS].copy()
    recentes["prob"] = indicadores.prob_passar_da_janela(recentes, indicadores.ajustar_alerta(d))
    alerta = recentes.groupby(["servico", "subprefeitura", "distrito"]).agg(
        abertos=("prob", "size"), devem_passar=("prob", "sum"), risco_medio=("prob", "mean")).reset_index()
    alerta = alerta.sort_values("devem_passar", ascending=False)
    resumo["alerta"] = {
        "data_retrato": str(ultimo), "abertos_recentes": int(len(recentes)),
        "devem_passar": float(recentes["prob"].sum()),
        "simulacoes": int(len(bt)), "erro_total_max": float(bt["erro_total"].abs().max()),
        "erro_total_referencia_medio": float(bt["erro_total_referencia"].mean()),
        "auc_min": float(bt["auc"].min()), "auc_max": float(bt["auc"].max()),
        "auc_referencia_medio": float(bt["auc_referencia"].mean())}

    # --- modelos --------------------------------------------------------------------
    met, ajustados, cal = modelo.avaliar(d)
    e = modelo.preparar(d)
    final = modelo.candidatos()["Gradient boosting"].fit(
        e[modelo.CATEGORICAS + modelo.NUMERICAS], e["resolvida_janela"])
    joblib.dump(final, config.DIR_PROC / "modelo_prazo.joblib")

    # --- recomendador ------------------------------------------------------------------
    cat = db.ler("SELECT id_servico, servico, assunto FROM dim_servico")
    r = rec.Recomendador(cat, d["id_servico"].value_counts())
    cons = pd.read_csv(config.RAIZ / "tests" / "consultas_simuladas.csv", sep=";")
    acertos = []
    for texto, esperado in cons.itertuples(index=False):
        nomes = [normalizar(x) for x in r.recomendar(texto, 3)["servico"]]
        acertos.append({"texto": texto, "esperado": esperado, "top1": nomes[:1] == [normalizar(esperado)],
                        "top3": normalizar(esperado) in nomes})
    acertos = pd.DataFrame(acertos)
    resumo["recomendador"] = {"consultas": len(acertos), "top1": acertos["top1"].mean(),
                              "top3": acertos["top3"].mean()}

    # --- persistencia -------------------------------------------------------------------
    with db.conectar() as con:
        for nome, t in {"res_distrito": tab, "res_servico_amplitude": amp, "res_servico_distrito": sd,
                        "res_modelos": met, "res_calibracao": cal, "res_kmeans_k": aval_k,
                        "res_recomendador": acertos, "res_prioridade": pares, "res_fila": fila,
                        "res_backtest": bt, "res_alerta": alerta,
                        "res_pontos": pontos}.items():
            t.to_sql(nome, con, if_exists="replace", index=False)
    (config.DIR_PROC / "resumo.json").write_text(
        json.dumps(resumo, indent=2, default=float, ensure_ascii=False), encoding="utf-8")

    figuras(d, tab, amp, sd, met, cal, aval_k)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(pares["posicao"], pares["acumulado"] * 100, color="#B08D5E", lw=2)
    for n in (20, 50, 100):
        v = pares["acumulado"].iloc[n - 1] * 100
        ax.scatter([n], [v], color="#111111", s=40, zorder=3, edgecolor="white", linewidth=1.5)
        ax.annotate(f"{n} pares: {v:.0f}%", (n, v), xytext=(n + 18, v - 6), fontsize=8.5)
    ax.set_xlabel("Pares serviço x distrito, do maior para o menor atraso evitável")
    ax.set_ylabel("% acumulado do atraso evitável"); ax.set_ylim(0, 102); ax.set_xlim(0, len(pares))
    ax.set_title("Poucos pares concentram a maior parte do atraso evitável")
    fig.tight_layout(); fig.savefig(config.DIR_ASSETS / "fig8_pareto.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    pos = np.arange(len(bt)); larg = 0.36
    ax.bar(pos - larg / 2, bt["previsto_referencia"], larg, color="#A3A3A3", label="Taxa histórica do serviço")
    ax.bar(pos + larg / 2, bt["previsto"], larg, color="#B08D5E", label="Alerta (sobrevivência condicional)")
    ax.scatter(pos, bt["real"], marker="_", s=900, color="#111111", linewidths=2.2, zorder=3, label="Real")
    ax.set_xticks(pos); ax.set_xticklabels([pd.Timestamp(v).strftime("%d/%m") for v in bt["data"]])
    ax.set_xlabel("Data da simulação"); ax.set_ylabel("Pedidos que passaram de 30 dias")
    ax.set_title("Alerta antecipado: previsto e real em seis datas passadas"); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(config.DIR_ASSETS / "fig9_alerta.png"); plt.close(fig)
    print(json.dumps(resumo, indent=2, default=float, ensure_ascii=False))
    print(met.round(4).to_string(index=False))
    print(amp.head(12).round(3).to_string(index=False))


def figuras(d, tab, amp, sd, met, cal, aval_k):
    A = config.DIR_ASSETS
    # 1. indice por distrito
    t = tab.sort_values("indice")
    fig, ax = plt.subplots(figsize=(7.2, 11))
    cores = [COR2 if s < 1 else COR if i > 1 else CINZA for i, s in zip(t["ic_inf"], t["ic_sup"])]
    ax.hlines(t["distrito"], t["ic_inf"], t["ic_sup"], color=cores, lw=1.2)
    ax.scatter(t["indice"], t["distrito"], color=cores, s=12, zorder=3)
    ax.axvline(1, color="k", lw=.8, ls="--")
    ax.set_xlabel("Índice de resolução em 30 dias padronizado pelo mix de serviços (cidade = 1,00)")
    ax.set_title("Índice de equidade por distrito, jan-set 2026")
    ax.tick_params(axis="y", labelsize=6); ax.margins(y=.005)
    fig.tight_layout(); fig.savefig(A / "fig1_indice_distrito.png"); plt.close(fig)

    # 2. mesmo servico, distritos diferentes
    top = amp.head(8)
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    dados = [sd.loc[sd["id_servico"] == i, "taxa"] * 100 for i in top["id_servico"]]
    ax.boxplot(dados, vert=False, widths=.55, patch_artist=True,
               boxprops=dict(facecolor="#F5F4F0", color=COR), medianprops=dict(color=COR2),
               flierprops=dict(markersize=3, markerfacecolor=CINZA, markeredgecolor=CINZA))
    ax.set_yticklabels([s[:58] for s in top["servico"]], fontsize=7)
    ax.set_xlabel("% das demandas finalizadas em até 30 dias, por distrito")
    ax.set_title("Mesmo serviço, distritos diferentes (8 serviços de maior volume)")
    ax.invert_yaxis(); fig.tight_layout(); fig.savefig(A / "fig2_servico_distritos.png"); plt.close(fig)

    # 3. centralidade
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    sc = ax.scatter(tab["dist_centro_km"], tab["indice"], color=COR, s=18, edgecolor="white", linewidth=0.6)
    ax.axhline(1, color="k", lw=.8, ls="--")
    ax.set_xlabel("Distância do distrito à Praça da Sé (km)"); ax.set_ylabel("Índice de equidade")
    ax.set_title("Índice x distância ao centro")
    fig.tight_layout(); fig.savefig(A / "fig3_centralidade.png"); plt.close(fig)

    # 4. estabilidade
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ax.scatter(tab["indice_t2"], tab["indice_t3"], s=14, color=COR)
    lim = [0.75, 1.3]; ax.plot(lim, lim, color="k", lw=.8, ls="--")
    ax.set_xlabel("Índice no 2º trimestre"); ax.set_ylabel("Índice no 3º trimestre")
    ax.set_title("Estabilidade do índice entre trimestres")
    fig.tight_layout(); fig.savefig(A / "fig4_estabilidade.png"); plt.close(fig)

    # 5. Kaplan-Meier tapa-buraco: melhor x pior distrito com volume
    tb = d[d["servico"] == "Tapa-buraco"]
    vol = sd[sd["servico"] == "Tapa-buraco"].sort_values("taxa")
    if len(vol) >= 2:
        fig, ax = plt.subplots(figsize=(5.6, 3.6))
        for nome, cor in ((vol.iloc[0]["distrito"], COR2), (vol.iloc[-1]["distrito"], COR)):
            p = tb[tb["distrito"] == nome]
            km = indicadores.kaplan_meier(p["dias"], p["finalizada"])
            ax.step(km["dia"], km["em_aberto"] * 100, where="post", color=cor,
                    label=f"{nome.title()} (n={len(p)})")
        km = indicadores.kaplan_meier(tb["dias"], tb["finalizada"])
        ax.step(km["dia"], km["em_aberto"] * 100, where="post", color=CINZA, ls="--", label="Cidade")
        ax.set_xlim(0, 150); ax.set_ylim(0, 100)
        ax.set_xlabel("Dias desde a abertura"); ax.set_ylabel("% das demandas ainda em aberto")
        ax.set_title("Tapa-buraco: curva de permanência em aberto (Kaplan-Meier)"); ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(A / "fig5_km_tapa_buraco.png"); plt.close(fig)

    # 6. modelos e calibracao
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 3.3))
    a1.barh(met["modelo"], met["auc"], color=[CINZA, "#6B6B6B", "#6B6B6B", CINZA, COR])
    a1.set_xlim(.78, .86); a1.set_xlabel("AUC no teste (3º trimestre)"); a1.invert_yaxis()
    a1.tick_params(axis="y", labelsize=7); a1.set_title("Comparação de modelos")
    a2.plot([0, 1], [0, 1], color="k", lw=.8, ls="--")
    a2.plot(cal["previsto"], cal["observado"], marker="o", color=COR2, ms=4)
    a2.set_xlabel("Probabilidade prevista"); a2.set_ylabel("Frequência observada")
    a2.set_title("Calibração do gradient boosting")
    fig.tight_layout(); fig.savefig(A / "fig6_modelos.png"); plt.close(fig)

    # 7. escolha de k
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    ax.plot(aval_k["k"], aval_k["silhueta"], marker="o", color=COR)
    ax.set_xlabel("Número de grupos (k)"); ax.set_ylabel("Silhueta média")
    ax.set_title("Escolha de k no K-Means")
    fig.tight_layout(); fig.savefig(A / "fig7_kmeans_k.png"); plt.close(fig)


if __name__ == "__main__":
    main()
