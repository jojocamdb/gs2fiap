"""Gera o diagrama de arquitetura (assets/fig0_arquitetura.png). Uso: python scripts/04_diagrama.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

AZUL, LARANJA, TINTA, SUAVE, BORDA = "#111111", "#B08D5E", "#111111", "#6B6B6B", "#E5E3DD"
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=170)
ax.set_xlim(0, 110); ax.set_ylim(0, 56); ax.axis("off")


def caixa(x, y, w, h, titulo, linhas, cor=BORDA, fundo="#ffffff"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.4",
                                fc=fundo, ec=cor, lw=1.6))
    ax.text(x + 1.6, y + h - 2.6, titulo, fontsize=9.5, fontweight="bold", color=TINTA, va="top")
    for i, l in enumerate(linhas):
        ax.text(x + 1.6, y + h - 6.0 - i * 2.9, l, fontsize=7.6, color=SUAVE, va="top")


def seta(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
                                 lw=1.5, color=SUAVE, shrinkA=0, shrinkB=0))


def faixa(x, texto):
    ax.text(x, 54, texto, fontsize=8, color=SUAVE, fontweight="bold")


faixa(1, "1 · DADOS"); faixa(27, "2 · BANCO"); faixa(53, "3 · INTELIGÊNCIA"); faixa(86, "4 · USO")

caixa(1, 31, 21, 19, "Dados abertos SP156", ["3 arquivos trimestrais", "1,5 milhão de linhas", "formatos diferentes"])
caixa(1, 6, 21, 20, "ETL validado", ["detecta codificação,", "separador e data", "funil auditável", "para se houver dúvida"], AZUL)
seta(11.5, 31, 11.5, 26.4)

caixa(27, 17, 21, 24, "SQLite", ["modelo dimensional", "3 dimensões + 1 fato", "restrições CHECK", "sem endereço", "433 mil demandas"], AZUL)
seta(22.2, 16, 26.8, 26)

y = [40.5, 28.5, 16.5, 4.5]
tit = ["Indicadores de prazo", "K-Means", "Modelos preditivos", "Recomendador"]
lin = [["Kaplan-Meier", "índice padronizado"], ["3 grupos de distritos"],
       ["boosting, logística, MLP", "validação temporal"], ["TF-IDF + léxico", "64 serviços"]]
for yi, t, l in zip(y, tit, lin):
    caixa(53, yi, 27, 10.6, t, l)
    seta(48.2, 29, 52.8, yi + 5.3)
    seta(80.2, yi + 5.3, 85.8, 34 if yi > 20 else 15)

caixa(86, 27, 23, 23, "Painel interativo", ["Streamlit + Plotly", "mapa, comparações,", "curvas por distrito", "gestor e liderança"], AZUL)
caixa(86, 4, 23, 20, "Assistente do morador", ["serviço + prazo local", "IA generativa com trava", "dados pessoais", "mascarados"], LARANJA)

fig.savefig(Path(__file__).resolve().parents[1] / "assets" / "fig0_arquitetura.png", bbox_inches="tight",
            facecolor="white")
