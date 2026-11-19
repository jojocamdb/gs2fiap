"""Leitura, validacao e limpeza dos arquivos trimestrais do SP156.

Os arquivos do portal nao seguem um padrao unico: no conjunto de 2026 ha
arquivos em latin-1 com ';' e datas dd/mm/aaaa, e arquivos em UTF-8 com ','
e datas mm/dd/aaaa. Assumir um formato fixo corrompe as datas sem gerar erro,
entao cada arquivo tem separador, codificacao e formato de data detectados
e validados antes da carga.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

log = logging.getLogger("zeladoria.etl")


class ErroDeDados(Exception):
    """Arquivo fora do contrato esperado. A carga para em vez de adivinhar."""


@dataclass
class PerfilArquivo:
    arquivo: str
    codificacao: str
    separador: str
    formato_data: str
    linhas: int
    abertura_min: pd.Timestamp
    abertura_max: pd.Timestamp
    data_corte: pd.Timestamp


def normalizar(texto) -> str | None:
    """Maiusculas, sem acento, sem travessao e com espacos colapsados."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return None
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(" " if unicodedata.category(c).startswith("C") else c
                for c in t if not unicodedata.combining(c))
    t = re.sub(r"[–—\-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip().upper()
    return t or None


def detectar_codificacao(caminho: Path) -> str:
    with open(caminho, "rb") as f:
        amostra = f.read(200_000)
    try:
        amostra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # cp1252, e nao latin-1: o travessao dos nomes de servico e o byte 0x96,
        # que em latin-1 vira caractere de controle e duplica servicos.
        return "cp1252"


def detectar_separador(caminho: Path, codificacao: str) -> str:
    with open(caminho, encoding=codificacao, errors="replace") as f:
        cabecalho = f.readline()
    return ";" if cabecalho.count(";") > cabecalho.count(",") else ","


def detectar_formato_data(abertura: pd.Series, finalizacao: pd.Series) -> str:
    """Escolhe entre dd/mm e mm/dd pelo unico formato coerente com o arquivo.

    Criterios: todas as datas de abertura precisam ser validas, o periodo de
    abertura precisa caber em um trimestre e nenhuma finalizacao pode ser
    anterior a abertura.
    """
    aprovados = []
    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        ab = pd.to_datetime(abertura, format=fmt, errors="coerce")
        fi = pd.to_datetime(finalizacao, format=fmt, errors="coerce")
        if ab.isna().any():
            continue
        if fi.isna().sum() != finalizacao.isna().sum():
            continue
        if (ab.max() - ab.min()).days > 93:
            continue
        if (fi < ab).any():
            continue
        aprovados.append(fmt)
    if len(aprovados) != 1:
        raise ErroDeDados(
            f"Formato de data ambiguo ou invalido (candidatos aprovados: {aprovados})."
        )
    return aprovados[0]


def ler_arquivo(caminho: Path) -> tuple[pd.DataFrame, PerfilArquivo]:
    caminho = Path(caminho)
    cod = detectar_codificacao(caminho)
    sep = detectar_separador(caminho, cod)
    try:
        df = pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, encoding_errors="replace")
    except Exception as exc:  # arquivo truncado, aspas quebradas etc.
        raise ErroDeDados(f"Falha ao ler {caminho.name}: {exc}") from exc
    if df.shape[1] != len(config.COLUNAS):
        raise ErroDeDados(
            f"{caminho.name}: esperadas {len(config.COLUNAS)} colunas, vieram {df.shape[1]}."
        )
    df.columns = config.COLUNAS
    fmt = detectar_formato_data(df["data_abertura"], df["data_finalizacao"])
    df["data_abertura"] = pd.to_datetime(df["data_abertura"], format=fmt)
    df["data_finalizacao"] = pd.to_datetime(df["data_finalizacao"], format=fmt)
    # O portal nao informa a data de extracao. A maior data de finalizacao do
    # arquivo e o limite inferior dela, e e usada como data de corte.
    corte = df["data_finalizacao"].max()
    df["data_corte"] = corte
    df["arquivo"] = caminho.name
    perfil = PerfilArquivo(
        caminho.name, cod, sep, fmt, len(df),
        df["data_abertura"].min(), df["data_abertura"].max(), corte,
    )
    log.info("Lido %s: %s", caminho.name, perfil)
    return df, perfil


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica o recorte de zeladoria e as regras de qualidade.

    Devolve a base limpa e um funil com a contagem de cada etapa, para que
    toda exclusao fique auditavel.
    """
    funil = {"linhas_brutas": len(df)}
    df = df.copy()
    df["assunto_norm"] = df["assunto"].map(normalizar)
    df = df[df["assunto_norm"].isin(config.ASSUNTOS_ZELADORIA)]
    funil["recorte_zeladoria"] = len(df)

    df["distrito"] = df["distrito"].map(normalizar)
    valido = df["distrito"].notna() & ~df["distrito"].fillna("").str.fullmatch(r"\d+")
    df = df[valido]
    funil["com_distrito_valido"] = len(df)

    df = df[df["status"] != "Cancelada"]
    funil["sem_canceladas"] = len(df)

    incoerente = (df["status"] == "Finalizada") & df["data_finalizacao"].isna()
    df = df[~incoerente]
    funil["sem_finalizada_sem_data"] = len(df)

    # Sem identificador de protocolo, linhas identicas nas 15 colunas sao
    # tratadas como uma unica demanda. A contagem original fica preservada.
    chave = [c for c in config.COLUNAS]
    df["registros"] = 1
    antes = len(df)
    agreg = {c: "first" for c in df.columns if c not in chave + ["registros"]}
    agreg["registros"] = "sum"
    df = df.groupby(chave, dropna=False, sort=False).agg(agreg).reset_index()
    funil["demandas_distintas"] = len(df)
    funil["registros_repetidos_colapsados"] = antes - len(df)

    df["servico_norm"] = df["servico"].map(normalizar)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    fora = ~df["latitude"].between(-24.1, -23.3) | ~df["longitude"].between(-46.9, -46.3)
    df.loc[fora, ["latitude", "longitude"]] = np.nan

    df["finalizada"] = (df["status"] == "Finalizada").astype(int)
    fim = df["data_finalizacao"].where(df["finalizada"] == 1, df["data_corte"])
    df["dias"] = (fim - df["data_abertura"]).dt.days
    df["dias_observaveis"] = (df["data_corte"] - df["data_abertura"]).dt.days
    df = df[df["dias_observaveis"] >= 0]
    funil["base_final"] = len(df)

    j = config.JANELA_DIAS
    df["elegivel_janela"] = (df["dias_observaveis"] >= j).astype(int)
    df["resolvida_janela"] = ((df["finalizada"] == 1) & (df["dias"] <= j)).astype(int)
    return df.reset_index(drop=True), funil


def carregar_brutos(diretorio: Path | None = None) -> tuple[pd.DataFrame, list[PerfilArquivo]]:
    diretorio = Path(diretorio or config.DIR_BRUTO)
    arquivos = sorted(diretorio.glob("*.csv"))
    if not arquivos:
        raise ErroDeDados(f"Nenhum CSV encontrado em {diretorio}.")
    partes, perfis = [], []
    for arq in arquivos:
        df, perfil = ler_arquivo(arq)
        partes.append(df)
        perfis.append(perfil)
    perfis.sort(key=lambda p: p.abertura_min)
    for a, b in zip(perfis, perfis[1:]):
        if b.abertura_min <= a.abertura_max:
            raise ErroDeDados(f"Periodos sobrepostos entre {a.arquivo} e {b.arquivo}.")
    return pd.concat(partes, ignore_index=True), perfis
