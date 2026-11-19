"""Indicadores de prazo com tratamento de censura.

Demandas ainda abertas na data de corte nao tem prazo conhecido. Calcular a
media so das finalizadas subestima o prazo e favorece periodos recentes, que
tiveram menos tempo para acumular casos longos. Por isso:

* a taxa de resolucao em N dias so considera demandas observadas por N dias ou mais;
* medianas e percentis usam o estimador de Kaplan-Meier, que aproveita as abertas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def kaplan_meier(dias, evento) -> pd.DataFrame:
    """Curva de 'ainda em aberto' S(t). dias: duracao observada; evento: 1 se finalizada."""
    dias = np.asarray(dias, dtype=float)
    evento = np.asarray(evento, dtype=int)
    if len(dias) == 0:
        return pd.DataFrame({"dia": [], "em_aberto": []})
    tempos = np.unique(dias)
    em_risco = len(dias) - np.searchsorted(np.sort(dias), tempos, side="left")
    eventos = np.array([evento[dias == t].sum() for t in tempos]) if len(tempos) < 2000 else \
        pd.Series(evento).groupby(dias).sum().reindex(tempos).to_numpy()
    s = np.cumprod(1 - eventos / em_risco)
    return pd.DataFrame({"dia": tempos, "em_aberto": s})


def percentil_km(dias, evento, p: float) -> float | None:
    """Menor numero de dias em que a fracao p das demandas ja foi finalizada.

    Devolve None quando a fracao p nao e atingida no periodo observado.
    """
    km = kaplan_meier(dias, evento)
    atingiu = km[km["em_aberto"] <= 1 - p]
    return None if atingiu.empty else float(atingiu["dia"].iloc[0])


def resumo_prazo(df: pd.DataFrame) -> dict:
    eleg = df[df["elegivel_janela"] == 1]
    return {
        "demandas": int(len(df)),
        "elegiveis": int(len(eleg)),
        "taxa_janela": float(eleg["resolvida_janela"].mean()) if len(eleg) else None,
        "p50_dias": percentil_km(df["dias"], df["finalizada"], 0.5),
        "p80_dias": percentil_km(df["dias"], df["finalizada"], 0.8),
        "pct_aberta": float(1 - df["finalizada"].mean()) if len(df) else None,
    }


def indice_por_distrito(df: pd.DataFrame) -> pd.DataFrame:
    """Indice de equidade padronizado pelo mix de servicos.

    Distritos pedem servicos diferentes, e cada servico tem um prazo tipico
    diferente. Comparar a taxa bruta mistura as duas coisas. O indice divide o
    numero de demandas resolvidas na janela (observado) pelo numero que seria
    esperado se cada servico do distrito tivesse a taxa media da cidade.
    Indice 1,00 = igual a cidade para o mesmo mix; abaixo de 1 = pior.
    """
    e = df[df["elegivel_janela"] == 1]
    taxa_serv = e.groupby("id_servico")["resolvida_janela"].mean().rename("p_cidade")
    e = e.join(taxa_serv, on="id_servico")
    g = e.groupby("distrito").agg(
        elegiveis=("resolvida_janela", "size"),
        observado=("resolvida_janela", "sum"),
        esperado=("p_cidade", "sum"),
        var=("p_cidade", lambda p: float((p * (1 - p)).sum())),
        taxa_bruta=("resolvida_janela", "mean"),
    )
    g["indice"] = g["observado"] / g["esperado"]
    # Intervalo aproximado (95%). Supoe demandas independentes, o que nao vale
    # para demandas do mesmo lote de execucao: o intervalo real e mais largo.
    dp = np.sqrt(g["var"]) / g["esperado"]
    g["ic_inf"] = g["indice"] - 1.96 * dp
    g["ic_sup"] = g["indice"] + 1.96 * dp
    g["taxa_esperada"] = g["esperado"] / g["elegiveis"]
    return g.drop(columns="var").reset_index()


def prazo_por_distrito(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome, parte in df.groupby("distrito"):
        r = resumo_prazo(parte)
        r["distrito"] = nome
        linhas.append(r)
    return pd.DataFrame(linhas)


def servico_distrito(df: pd.DataFrame, minimo: int = config.MIN_DEMANDAS) -> pd.DataFrame:
    """Taxa por par (servico, distrito) com volume minimo, para comparar o mesmo servico."""
    e = df[df["elegivel_janela"] == 1]
    g = e.groupby(["id_servico", "servico", "id_distrito", "distrito"]).agg(
        elegiveis=("resolvida_janela", "size"), taxa=("resolvida_janela", "mean")).reset_index()
    return g[g["elegiveis"] >= minimo]


def estimar_prazo(df: pd.DataFrame, id_servico: int, id_distrito: int,
                  minimo: int = config.MIN_DEMANDAS) -> dict:
    """Prazo provavel para o cidadao, com recuo explicito quando falta volume local."""
    serv = df[df["id_servico"] == id_servico]
    local = serv[serv["id_distrito"] == id_distrito]
    cidade = resumo_prazo(serv)
    if len(local) >= minimo:
        r = resumo_prazo(local)
        r["nivel"] = "distrito"
    else:
        r = dict(cidade)
        r["nivel"] = "cidade"
    r["demandas_locais"] = int(len(local))
    r["cidade"] = cidade
    return r


# --------------------------------------------------------------------------
# Prioridade para a gestao: onde agir primeiro
# --------------------------------------------------------------------------

def atraso_evitavel(df: pd.DataFrame, minimo: int = config.MIN_DEMANDAS,
                    min_distritos: int = 20) -> pd.DataFrame:
    """Pedidos a mais que seriam finalizados na janela se cada par (servico, distrito)
    abaixo da referencia alcancasse o distrito mediano da cidade naquele servico.

    A referencia e o distrito mediano, nao o melhor: metade dos distritos ja a atinge
    com a estrutura atual. E uma conta de ordem de grandeza para priorizar, nao uma
    previsao: nao sabe se o par tem condicao de chegar la.
    """
    sd = servico_distrito(df, minimo)
    ref = sd.groupby("id_servico")["taxa"].agg(referencia="median", distritos="size")
    g = sd.join(ref, on="id_servico")
    g = g[g["distritos"] >= min_distritos].copy()
    g["ganho"] = (g["referencia"] - g["taxa"]).clip(lower=0) * g["elegiveis"]
    g = g[g["ganho"] > 0].sort_values("ganho", ascending=False).reset_index(drop=True)
    g["posicao"] = g.index + 1
    g["acumulado"] = g["ganho"].cumsum() / g["ganho"].sum()
    return g


def limites_por_servico(df: pd.DataFrame, p: float = 0.8, padrao: int = 90) -> pd.Series:
    """Dias em que a fracao p dos pedidos de cada servico ja foi finalizada na cidade.

    Para servicos em que essa fracao nao e atingida no periodo, usa o limite padrao.
    """
    lim = {s: percentil_km(parte["dias"], parte["finalizada"], p) for s, parte in df.groupby("id_servico")}
    return pd.Series(lim, dtype="float").fillna(padrao).rename("limite_dias")


def fila_atrasada(abertas: pd.DataFrame, limites: pd.Series) -> pd.DataFrame:
    """Pedidos em aberto ha mais tempo do que o limite do proprio servico."""
    a = abertas.join(limites, on="id_servico")
    a = a[a["dias"] > a["limite_dias"]].copy()
    a["dias_alem_do_limite"] = a["dias"] - a["limite_dias"]
    return a


def pontos_de_reincidencia(abertas: pd.DataFrame, minimo: int = 3) -> pd.DataFrame:
    """Celulas de cerca de 100 m com varios pedidos em aberto do mesmo servico."""
    a = abertas.dropna(subset=["latitude", "longitude"])
    g = a.groupby(["id_servico", "servico", "distrito", "subprefeitura", "latitude", "longitude"]).agg(
        pedidos=("dias", "size"), registros=("registros", "sum"), dias_mais_antigo=("dias", "max")).reset_index()
    return g[g["pedidos"] >= minimo].sort_values(["pedidos", "dias_mais_antigo"], ascending=False)
