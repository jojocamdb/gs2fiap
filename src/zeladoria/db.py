"""Carga e acesso ao banco SQLite. Toda consulta com entrada externa e parametrizada."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

SCHEMA = config.RAIZ / "sql" / "schema.sql"


@contextmanager
def conectar(caminho: Path | None = None, somente_leitura: bool = False):
    caminho = Path(caminho or config.BANCO)
    if somente_leitura:
        con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(caminho)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _haversine_km(lat, lon, lat0, lon0):
    r = 6371.0
    p1, p2 = np.radians(lat), np.radians(lat0)
    dphi, dl = p2 - p1, np.radians(lon0) - np.radians(lon)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def criar_banco(df: pd.DataFrame, funil: dict, perfis: list, caminho: Path | None = None) -> Path:
    caminho = Path(caminho or config.BANCO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        caminho.unlink()
    with conectar(caminho) as con:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))

        dist = (
            df.groupby("distrito")
            .agg(subprefeitura=("subprefeitura", lambda s: s.mode().iat[0] if s.notna().any() else None),
                 lat_centro=("latitude", "median"), lon_centro=("longitude", "median"))
            .reset_index().rename(columns={"distrito": "nome"})
        )
        dist["dist_centro_km"] = _haversine_km(
            dist["lat_centro"], dist["lon_centro"], config.SE_LAT, config.SE_LON).round(2)
        dist.insert(0, "id_distrito", range(1, len(dist) + 1))
        dist.to_sql("dim_distrito", con, if_exists="append", index=False)

        def rotulo(s: pd.Series) -> str:
            # prefere a grafia com travessao preservado (arquivos em UTF-8)
            com_traco = s[s.str.contains("–|-", regex=True)]
            base = com_traco if len(com_traco) else s
            return base.mode().iat[0].replace("–", "-")

        serv = (
            df.groupby("servico_norm")
            .agg(servico=("servico", rotulo), assunto=("assunto", lambda s: s.mode().iat[0]),
                 tema=("tema", lambda s: s.mode().iat[0]))
            .reset_index()
        )
        serv.insert(0, "id_servico", range(1, len(serv) + 1))
        serv.to_sql("dim_servico", con, if_exists="append", index=False)

        canal = pd.DataFrame({"canal": sorted(df["canal"].fillna("NAO INFORMADO").unique())})
        canal.insert(0, "id_canal", range(1, len(canal) + 1))
        canal.to_sql("dim_canal", con, if_exists="append", index=False)

        fato = df.assign(canal=df["canal"].fillna("NAO INFORMADO"))
        fato = fato.merge(dist[["id_distrito", "nome"]], left_on="distrito", right_on="nome")
        fato = fato.merge(serv[["id_servico", "servico_norm"]], on="servico_norm")
        fato = fato.merge(canal, on="canal")
        for c in ("data_abertura", "data_finalizacao", "data_corte"):
            fato[c] = fato[c].dt.strftime("%Y-%m-%d")
        fato["latitude"] = fato["latitude"].round(3)
        fato["longitude"] = fato["longitude"].round(3)
        cols = ["id_distrito", "id_servico", "id_canal", "data_abertura", "data_finalizacao",
                "data_corte", "status", "finalizada", "dias", "dias_observaveis",
                "elegivel_janela", "resolvida_janela", "registros", "latitude", "longitude"]
        fato[cols].to_sql("fato_demanda", con, if_exists="append", index=False, chunksize=50_000)

        con.executemany("INSERT INTO auditoria_funil VALUES (?, ?, ?)",
                        [(i, k, int(v)) for i, (k, v) in enumerate(funil.items(), 1)])
        con.executemany(
            "INSERT INTO auditoria_arquivo VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(p.arquivo, p.codificacao, p.separador, p.formato_data, p.linhas,
              str(p.abertura_min.date()), str(p.abertura_max.date()), str(p.data_corte.date()))
             for p in perfis])
    return caminho


def ler(sql: str, params: tuple = (), caminho: Path | None = None) -> pd.DataFrame:
    with conectar(caminho, somente_leitura=True) as con:
        return pd.read_sql_query(sql, con, params=params)


def demandas(caminho: Path | None = None) -> pd.DataFrame:
    df = ler("SELECT * FROM vw_demanda", caminho=caminho)
    df["data_abertura"] = pd.to_datetime(df["data_abertura"])
    return df


def registrar_consulta(origem: str, id_servico=None, id_distrito=None, tamanho_texto=None,
                       caminho: Path | None = None) -> None:
    """Log de uso sem conteudo: guarda apenas origem, ids e tamanho do texto digitado."""
    with conectar(caminho) as con:
        con.execute(
            "INSERT INTO log_consulta (origem, id_servico, id_distrito, tamanho_texto) VALUES (?, ?, ?, ?)",
            (origem, id_servico, id_distrito, tamanho_texto))
