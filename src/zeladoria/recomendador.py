"""Recomendacao do servico certo a partir da descricao livre do cidadao.

A base aberta nao traz o texto digitado pelo cidadao, entao nao ha como treinar
um classificador supervisionado de descricoes. A solucao e recuperacao por
similaridade (TF-IDF + cosseno) sobre o catalogo de servicos, com um lexico
curado que liga o vocabulario do dia a dia aos termos administrativos.
"""
from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import FeatureUnion

from .etl import normalizar

# termo popular -> termos do catalogo. Curado manualmente pela equipe.
LEXICO = {
    "BURACO": "TAPA BURACO ASFALTO", "CRATERA": "TAPA BURACO ASFALTO",
    "ASFALTO": "TAPA BURACO", "RUA ESBURACADA": "TAPA BURACO",
    "GALHO": "ARVORE PODA", "PODA": "ARVORE AVALIACAO PODA REMOCAO", "PODAR": "ARVORE AVALIACAO PODA REMOCAO",
    "ARVORE CAINDO": "ARVORE AVALIACAO PODA REMOCAO", "RAIZ": "ARVORE AVALIACAO CALCADAS",
    "MATO": "CAPINACAO ROCADA", "MATAGAL": "CAPINACAO ROCADA", "GRAMA": "ROCADA PRACA CANTEIRO",
    "BUEIRO": "LIMPEZA BUEIROS BOCA DE LOBO", "ENTUPIDO": "LIMPEZA BUEIROS BOCA DE LOBO",
    "ALAGA": "GALERIAS AGUAS DE CHUVAS BUEIROS", "ALAGAMENTO": "GALERIAS AGUAS DE CHUVAS BUEIROS",
    "ENCHENTE": "LIMPEZA VIA PUBLICA APOS ENCHENTES", "ESGOTO": "GALERIAS AGUAS BUEIROS",
    "SOFA": "ENTULHO GRANDES OBJETOS REMOCAO", "MOVEL": "ENTULHO GRANDES OBJETOS REMOCAO",
    "COLCHAO": "ENTULHO GRANDES OBJETOS REMOCAO", "ENTULHO": "ENTULHO GRANDES OBJETOS REMOCAO",
    "DESCARTE": "DESCARTE IRREGULAR ENTULHO", "LIXAO": "DESCARTE IRREGULAR ENTULHO AREA PUBLICA",
    "CACAMBA": "CACAMBA IRREGULAR ENTULHO",
    "LIXEIRO": "COLETA DE LIXO DOMICILIAR", "CAMINHAO DE LIXO": "COLETA DE LIXO DOMICILIAR",
    "NAO PASSOU": "RECLAMAR COLETA DE LIXO DOMICILIAR", "RECICLAVEL": "COLETA SELETIVA",
    "RECICLAGEM": "COLETA SELETIVA", "LIXEIRA": "LIXEIRAS PUBLICAS INSTALACAO MANUTENCAO",
    "SUJA": "FALTA DE VARRICAO", "SUJEIRA": "FALTA DE VARRICAO", "VARRER": "FALTA DE VARRICAO",
    "GARI": "FALTA DE VARRICAO", "FOLHAS": "FALTA DE VARRICAO",
    "CALCADA QUEBRADA": "CALCADA DANIFICADA MANUTENCAO", "DEGRAU": "ACESSIBILIDADE OBSTACULO CALCADA",
    "CADEIRANTE": "ACESSIBILIDADE OBSTACULO CALCADA", "CADEIRA DE RODAS": "ACESSIBILIDADE OBSTACULO CALCADA",
    "RAMPA": "ACESSIBILIDADE OBSTACULO CALCADA",
    "MEIO FIO": "GUIAS SARJETAS MANUTENCAO", "SARJETA": "GUIAS SARJETAS MANUTENCAO",
    "FIO": "FIACAO SOLTA", "FIOS": "FIACAO SOLTA", "CABO": "FIACAO SOLTA", "POSTE": "POSTE EM MAU ESTADO",
    "RIO": "CORREGO LIMPEZA", "CORREGO": "CORREGO LIMPEZA", "RIACHO": "CORREGO LIMPEZA",
    "PARQUINHO": "PRACAS MANUTENCAO EQUIPAMENTOS BRINQUEDOS", "BALANCO": "PRACAS MANUTENCAO EQUIPAMENTOS BRINQUEDOS",
    "BANCO": "PRACAS MANUTENCAO EQUIPAMENTOS BANCOS", "ACADEMIA": "EQUIPAMENTOS DE GINASTICA PRACA",
    "ESCADAO": "VIELAS ESCADARIAS MANUTENCAO", "VIELA": "VIELAS ESCADARIAS MANUTENCAO",
    "PONTE": "REPAROS PONTES VIADUTOS", "VIADUTO": "REPAROS PONTES VIADUTOS",
    "CATA BAGULHO": "CATA BAGULHO", "PLANTAR": "PLANTIO DE ARVORES",
}

TAMANHO_MAX = 300


def expandir(texto: str) -> str:
    t = normalizar(texto) or ""
    extras = [v for k, v in LEXICO.items() if f" {k}" in f" {t}"]
    return " ".join([t] + extras)


class Recomendador:
    def __init__(self, catalogo: pd.DataFrame, volume: pd.Series | None = None):
        """catalogo: colunas id_servico, servico, assunto. volume: demandas por id_servico."""
        self.catalogo = catalogo.reset_index(drop=True)
        docs = (self.catalogo["servico"] + " " + self.catalogo["servico"] + " " +
                self.catalogo["assunto"]).map(normalizar)
        self.vet = FeatureUnion([
            ("palavra", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ])
        self.matriz = self.vet.fit_transform(docs)
        v = self.catalogo["id_servico"].map(volume) if volume is not None else None
        # desempate leve pela frequencia do servico (prior), sem dominar o texto
        self.prior = (v.fillna(0) / v.max()).to_numpy() * 0.05 if v is not None else 0.0

    def recomendar(self, texto: str, n: int = 3, limiar: float = 0.08) -> pd.DataFrame:
        texto = (texto or "")[:TAMANHO_MAX]
        consulta = expandir(texto)
        if len(consulta) < 3:
            return self.catalogo.head(0).assign(score=[])
        sim = cosine_similarity(self.vet.transform([consulta]), self.matriz)[0]
        saida = self.catalogo.assign(score=sim + self.prior * (sim > 0))
        saida = saida[saida["score"] >= limiar].sort_values("score", ascending=False)
        return saida.head(n).reset_index(drop=True)
