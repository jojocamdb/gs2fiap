"""Agrupamento de distritos por perfil de demanda e de atendimento (K-Means)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import config, indicadores

VARIAVEIS_ATENDIMENTO = ["indice", "pct_aberta", "p50_dias"]


def matriz_distritos(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por distrito: atendimento, volume, canal e mix de assuntos."""
    ix = indicadores.indice_por_distrito(df).set_index("distrito")
    pz = indicadores.prazo_por_distrito(df).set_index("distrito")
    m = ix[["indice", "taxa_bruta", "elegiveis"]].join(pz[["p50_dias", "pct_aberta", "demandas"]])
    m["pct_app"] = df.groupby("distrito")["canal"].apply(lambda s: (s == "MOBILE").mean())
    m["dist_centro_km"] = df.groupby("distrito")["dist_centro_km"].first()
    mix = pd.crosstab(df["distrito"], df["assunto"], normalize="index")
    principais = df["assunto"].value_counts().head(6).index
    mix = mix[principais].add_prefix("mix_")
    return m.join(mix).reset_index()


def agrupar(m: pd.DataFrame, k: int | None = None, faixa=range(2, 8)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Roda K-Means padronizado. Sem k, escolhe pelo maior coeficiente de silhueta."""
    colunas = VARIAVEIS_ATENDIMENTO + ["pct_app", "log_demandas"] + \
        [c for c in m.columns if c.startswith("mix_")]
    base = m.assign(log_demandas=np.log(m["demandas"]))
    x = StandardScaler().fit_transform(base[colunas])
    avaliacao = []
    modelos = {}
    for n in faixa:
        km = KMeans(n_clusters=n, n_init=25, random_state=config.SEMENTE).fit(x)
        modelos[n] = km
        avaliacao.append({"k": n, "silhueta": silhouette_score(x, km.labels_), "inercia": km.inertia_})
    avaliacao = pd.DataFrame(avaliacao)
    if k is None:
        k = int(avaliacao.loc[avaliacao["silhueta"].idxmax(), "k"])
    saida = m.copy()
    saida["grupo"] = modelos[k].labels_
    # renumera do pior para o melhor indice medio, para a leitura ficar estavel
    ordem = saida.groupby("grupo")["indice"].mean().sort_values().index
    saida["grupo"] = saida["grupo"].map({g: i + 1 for i, g in enumerate(ordem)})
    return saida, avaliacao
