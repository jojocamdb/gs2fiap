"""Gera o diagrama de arquitetura (assets/figuras/arquitetura.png). Uso: python scripts/04_diagrama.py

Os numeros exibidos saem de data/processed (resumo.json e banco), para o diagrama
nao divergir do painel.
"""
import json
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from zeladoria import config, db  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams["font.family"] = ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]

PRETO, SUPERFICIE, BORDA = "#000000", "#0F0F0F", "#2A2A2A"
TEXTO, MUDO, CINZA, OURO = "#FFFFFF", "#A3A3A3", "#6B6B6B", "#E1C59D"


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


R = json.loads((config.DIR_PROC / "resumo.json").read_text(encoding="utf-8"))
funil = db.ler("SELECT etapa, linhas FROM auditoria_funil").set_index("etapa")["linhas"]
auc = db.ler("SELECT auc FROM res_modelos WHERE modelo = 'Gradient boosting'").iloc[0, 0]
testes = (RAIZ / "docs" / "evidencias_pytest.txt").read_text(encoding="utf-8").count(" PASSED")

L, A = 120, 66
fig, ax = plt.subplots(figsize=(13.2, 7.26), dpi=150)
fig.patch.set_facecolor(PRETO)
ax.set_facecolor(PRETO)
ax.set_xlim(0, L); ax.set_ylim(0, A); ax.axis("off")


def caixa(x, y, w, h, titulo, linhas, destaque=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=SUPERFICIE, ec=OURO if destaque else BORDA, lw=1.1))
    ax.text(x + 1.5, y + h - 1.9, titulo, fontsize=10.2, color=TEXTO, va="top", fontweight=500)
    for i, l in enumerate(linhas):
        ax.text(x + 1.5, y + h - 4.9 - i * 2.35, l, fontsize=8.1, color=MUDO, va="top")


def linha(pontos, seta=True):
    xs, ys = zip(*pontos)
    ax.plot(xs, ys, color=CINZA, lw=1.0, solid_capstyle="round", zorder=1)
    if seta:
        (x1, y1), (x2, y2) = pontos[-2], pontos[-1]
        ax.add_patch(FancyArrowPatch((x2 - (x2 - x1) * 1e-3, y2 - (y2 - y1) * 1e-3), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=9, lw=0, color=CINZA, zorder=2))


def coluna(x, w, numero, nome):
    ax.text(x, 62.3, numero, fontsize=8.5, color=OURO, fontweight=500)
    ax.text(x + 3.4, 62.3, nome, fontsize=8.5, color=MUDO, fontweight=500)
    ax.plot([x, x + w], [60.6, 60.6], color=BORDA, lw=0.9)


# colunas
C1, C2, C3, C4 = 2, 30, 58, 91
W1, W2, W3, W4 = 22, 22, 27, 27
coluna(C1, W1, "01", "D A D O S")
coluna(C2, W2, "02", "B A N C O")
coluna(C3, W3, "03", "I N T E L I G Ê N C I A")
coluna(C4, W4, "04", "U S O")

# 01 dados
caixa(C1, 42.5, W1, 14.5, "Dados abertos do SP156",
      ["Prefeitura de São Paulo", "3 arquivos trimestrais de 2026", f"{br(funil['linhas_brutas'] / 1e6, 1)} milhão de linhas"])
caixa(C1, 23, W1, 14.5, "ETL validado",
      ["Detecta codificação, separador", "e formato de data por arquivo", "Funil de exclusões auditável",
       "Interrompe se houver dúvida"])
linha([(C1 + W1 / 2, 42.5), (C1 + W1 / 2, 37.7)])

# 02 banco
caixa(C2, 28.5, W2, 17.5, "SQLite", ["Modelo dimensional", "3 dimensões e 1 fato", "Restrições CHECK e chaves",
                                   f"{br(funil['base_final'] / 1000)} mil pedidos", "Sem endereço armazenado"])
linha([(C1 + W1, 31), (C2 - 0.2, 31)])

# 03 inteligencia
al, rec = R["alerta"], R["recomendador"]
blocos = [
    ("Indicadores de prazo", ["Kaplan-Meier · índice de equidade"]),
    ("Alerta antecipado", [f"Sobrevivência condicional · erro até {br(100 * al['erro_total_max'], 1)}%"]),
    ("Perfis de distrito", ["K-Means · 3 perfis"]),
    ("Chance de finalização", [f"Boosting, logística e rede neural · AUC {br(auc, 3)}"]),
    ("Recomendador de serviço", [f"TF-IDF e cosseno · acerto de {br(100 * rec['top3'], 1)}%"]),
]
H3, PASSO = 8.6, 9.9
ys = [48.4 - i * PASSO for i in range(5)]
BARRA_E = C2 + W2 + 3
for (titulo, linhas), y in zip(blocos, ys):
    caixa(C3, y, W3, H3, titulo, linhas)
    linha([(BARRA_E, y + H3 / 2), (C3 - 0.2, y + H3 / 2)])
linha([(C2 + W2, 37), (BARRA_E, 37)], seta=False)
linha([(BARRA_E, ys[0] + H3 / 2), (BARRA_E, ys[-1] + H3 / 2)], seta=False)

# 04 uso
caixa(C4, 38.5, W4, 18.5, "Painel para a gestão",
      ["Visão geral · resumo executivo", "Onde agir · prioridade e alerta", "Distritos · equidade e perfis",
       "Serviços · comparação por distrito", "Streamlit e Plotly"], destaque=True)
caixa(C4, 8.8, W4, 15.6, "Assistente do morador",
      ["Abrir pedido · serviço e prazo", "IA generativa com verificador", "de números", "Dados pessoais mascarados"])
BARRA_D = C3 + W3 + 3
for y in ys[:3]:
    linha([(C3 + W3, y + H3 / 2), (BARRA_D, y + H3 / 2)], seta=False)
linha([(BARRA_D, ys[0] + H3 / 2), (BARRA_D, ys[2] + H3 / 2)], seta=False)
linha([(BARRA_D, 47.75), (C4 - 0.2, 47.75)])
for y in ys[3:]:
    linha([(C3 + W3, y + H3 / 2), (BARRA_D, y + H3 / 2)], seta=False)
linha([(BARRA_D, ys[3] + H3 / 2), (BARRA_D, ys[4] + H3 / 2)], seta=False)
linha([(BARRA_D, 16.6), (C4 - 0.2, 16.6)])

# base: qualidade e seguranca
ax.plot([C1, C4 + W4], [4.9, 4.9], color=BORDA, lw=0.9)
ax.text(C1, 2.2, "Q U A L I D A D E   E   S E G U R A N Ç A", fontsize=7.6, color=MUDO, fontweight=500)
ax.text(C4 + W4, 2.2, f"{testes} testes automatizados  ·  SQL parametrizado  ·  conexão somente leitura  ·  log sem conteúdo",
        fontsize=8.1, color=TEXTO, ha="right")

fig.subplots_adjust(left=0.012, right=0.988, top=0.985, bottom=0.015)
destino = config.DIR_ASSETS / "figuras" / "arquitetura.png"
destino.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(destino, facecolor=PRETO)
print(f"Diagrama gerado em {destino}")
