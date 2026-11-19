"""Modelos que estimam a chance de uma demanda ser finalizada em ate N dias.

Validacao temporal: treina com demandas abertas no primeiro semestre e testa
nas abertas no terceiro trimestre, que e como o modelo seria usado na pratica.
Divisao aleatoria misturaria demandas do mesmo lote de execucao em treino e
teste e inflaria as metricas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from . import config

CATEGORICAS = ["id_servico", "id_distrito", "canal"]
NUMERICAS = ["dia_semana", "dia_do_mes"]
CORTE_TESTE = "2026-07-01"


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    e = df[df["elegivel_janela"] == 1].copy()
    e["dia_semana"] = e["data_abertura"].dt.dayofweek
    e["dia_do_mes"] = e["data_abertura"].dt.day
    return e


def dividir(e: pd.DataFrame, corte: str = CORTE_TESTE):
    treino = e[e["data_abertura"] < corte]
    teste = e[e["data_abertura"] >= corte]
    return treino, teste


class BaselineServico:
    """Referencia: taxa historica do servico na cidade, sem saber o distrito."""

    def fit(self, x, y):
        tab = pd.DataFrame({"s": x["id_servico"].to_numpy(), "y": np.asarray(y)})
        self.geral_ = tab["y"].mean()
        self.taxa_ = tab.groupby("s")["y"].mean()
        return self

    def predict_proba(self, x):
        p = x["id_servico"].map(self.taxa_).fillna(self.geral_).to_numpy()
        return np.column_stack([1 - p, p])


def _onehot(colunas):
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), colunas),
        ("num", StandardScaler(), NUMERICAS),
    ])


def _gb(colunas):
    pre = ColumnTransformer([
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), colunas),
        ("num", "passthrough", NUMERICAS),
    ])
    gb = HistGradientBoostingClassifier(
        categorical_features=list(range(len(colunas))), max_iter=200, learning_rate=0.08,
        random_state=config.SEMENTE)
    return make_pipeline(pre, gb)


def candidatos() -> dict:
    sem_distrito = ["id_servico", "canal"]
    return {
        "Baseline (taxa do servico)": BaselineServico(),
        "Regressao logistica": make_pipeline(_onehot(CATEGORICAS), LogisticRegression(max_iter=300, C=1.0)),
        "Rede neural MLP (32,16)": make_pipeline(
            _onehot(CATEGORICAS),
            MLPClassifier(hidden_layer_sizes=(32, 16), early_stopping=True, max_iter=40,
                          random_state=config.SEMENTE)),
        "Gradient boosting sem distrito": _gb(sem_distrito),
        "Gradient boosting": _gb(CATEGORICAS),
    }


def metricas(y, p) -> dict:
    return {"auc": roc_auc_score(y, p), "brier": brier_score_loss(y, p), "log_loss": log_loss(y, p)}


def calibracao(y, p, faixas: int = 10) -> pd.DataFrame:
    t = pd.DataFrame({"y": np.asarray(y), "p": p})
    t["faixa"] = pd.qcut(t["p"], faixas, duplicates="drop")
    return t.groupby("faixa", observed=True).agg(previsto=("p", "mean"), observado=("y", "mean"),
                                                 n=("y", "size")).reset_index(drop=True)


def avaliar(df: pd.DataFrame, amostra_mlp: int = 120_000) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    e = preparar(df)
    treino, teste = dividir(e)
    cols = CATEGORICAS + NUMERICAS
    y_tr, y_te = treino["resolvida_janela"], teste["resolvida_janela"]
    linhas, ajustados = [], {}
    for nome, modelo in candidatos().items():
        x_tr, y = treino[cols], y_tr
        if "MLP" in nome and len(treino) > amostra_mlp:
            x_tr = treino[cols].sample(amostra_mlp, random_state=config.SEMENTE)
            y = y_tr.loc[x_tr.index]
        modelo.fit(x_tr, y)
        p = modelo.predict_proba(teste[cols])[:, 1]
        linhas.append({"modelo": nome, "treino": len(x_tr), "teste": len(teste), **metricas(y_te, p)})
        ajustados[nome] = modelo
    tabela = pd.DataFrame(linhas)
    melhor = ajustados["Gradient boosting"]
    cal = calibracao(y_te, melhor.predict_proba(teste[cols])[:, 1])
    return tabela, ajustados, cal
