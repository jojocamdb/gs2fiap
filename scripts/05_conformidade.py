"""Confere a entrega contra as regras do enunciado da Global Solution 2026.2.

Uso: python scripts/05_conformidade.py
Sai com codigo 1 se houver item obrigatorio pendente.
"""
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
E = json.loads((RAIZ / "config" / "entrega.json").read_text(encoding="utf-8"))
PDF = RAIZ / "docs" / "GS2_ZelaSP.pdf"
paginas = [p.extract_text() for p in PdfReader(str(PDF)).pages]
texto = " ".join(paginas)
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
log = (RAIZ / "docs" / "evidencias_pytest.txt").read_text(encoding="utf-8")
arquivos = [p for p in RAIZ.rglob("*") if p.is_file() and ".git/" not in str(p) and ".venv" not in str(p)]

itens = []


def checar(grupo, descricao, ok, detalhe=""):
    itens.append((grupo, descricao, bool(ok), detalhe))


yt = re.compile(r"https://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]{6,}")
integrantes_ok = all(i["nome"] in paginas[0] and i["rm"] in paginas[0] for i in E["integrantes"])

checar("PDF", "PDF único gerado", PDF.exists(), f"{len(paginas)} páginas")
checar("PDF", "Nome completo e RM de todos os integrantes na primeira página", integrantes_ok)
checar("PDF", "Turma na primeira página", E["turma"] != "PREENCHER" and E["turma"] in paginas[0], E["turma"])
for secao in ("Introdução", "Desenvolvimento", "Resultados obtidos", "Conclusões"):
    checar("PDF", f"Seção {secao}", re.search(rf"\d\. {secao}", texto))
checar("PDF", "Problema, público beneficiado e objetivo", all(k in texto for k in ("Público beneficiado", "Objetivo")))
checar("PDF", "Origem dos dados e tratamento", "Origem dos dados" in texto and "Tratamento" in texto)
checar("PDF", "Códigos principais explicados em texto", "Códigos principais" in texto and "def kaplan_meier" in texto)
checar("PDF", "Evidências de teste", "Evidências de teste" in texto and "PASSED" in texto)
checar("PDF", "Limitações do protótipo", "Limitações do protótipo" in texto)
checar("PDF", "ODS relacionado e medição de impacto", "ODS 11" in texto and "Como medir o impacto" in texto)
checar("PDF", "Bases simuladas identificadas como tais", "simulad" in texto)
checar("PDF", "Link do vídeo (YouTube)", yt.search(E["link_video"]) and E["link_video"] in texto, E["link_video"])
checar("PDF", "Link do repositório GitHub", "github.com/" in E["link_repositorio"] and E["link_repositorio"] in texto,
       E["link_repositorio"])
checar("PDF", "Sem campo PREENCHER", "PREENCHER" not in texto)
checar("PDF", "Frase de competição coerente com a opção do grupo",
       ("QUERO CONCORRER" in texto) == bool(E.get("quero_concorrer")))

checar("Repositório", "README na raiz com nome dos integrantes", all(i["nome"] in readme for i in E["integrantes"]))
for secao in ("Integrantes", "Professores", "Descrição", "Estrutura de pastas", "Links e Observações",
              "Decisões Técnicas", "Participação na Competição"):
    checar("Repositório", f"README com a seção {secao} do template", secao in readme)
checar("Repositório", "README sem campo PREENCHER", "PREENCHER" not in readme)
checar("Repositório", "Instruções de execução", "streamlit run app.py" in readme and "pip install" in readme)
checar("Repositório", "Sem arquivo .zip", not [a for a in arquivos if a.suffix == ".zip"])
grandes = [f"{a.name} {a.stat().st_size / 1e6:.0f} MB" for a in arquivos if a.stat().st_size > 95e6]
checar("Repositório", "Nenhum arquivo acima do limite do GitHub (100 MB)", not grandes, ", ".join(grandes))
checar("Repositório", "Dados brutos e segredos fora do versionamento",
       all(k in (RAIZ / ".gitignore").read_text() for k in ("data/raw/*.csv", ".env")))

passou, falhou = log.count(" PASSED"), log.count(" FAILED") + log.count(" ERROR")
checar("Programa", "Testes automatizados passando", passou > 0 and falhou == 0, f"{passou} testes")
checar("Programa", "Banco e modelo presentes para rodar sem os dados brutos",
       (RAIZ / "data/processed/zeladoria.db").exists() and (RAIZ / "data/processed/modelo_prazo.joblib").exists())

manuais = [
    "Repositório PRIVADO no GitHub",
    "fiap-tutoria adicionada como colaboradora (o convite expira em 7 dias)",
    "Vídeo de até 5 minutos, no YouTube, como NÃO LISTADO, abrindo em janela anônima",
    "Composição do grupo confirmada com a tutoria (o enunciado pede de 3 a 5 integrantes)",
    "PDF enviado na plataforma antes de 19/11/2026, 23h59, e status diferente de 'Entrega pendente'",
    "Nenhuma alteração no repositório depois do prazo",
]

grupo_atual = None
for grupo, descricao, ok, detalhe in itens:
    if grupo != grupo_atual:
        print(f"\n{grupo}")
        grupo_atual = grupo
    print(f"  [{'ok' if ok else 'PENDENTE'}] {descricao}" + (f" ({detalhe})" if detalhe else ""))
print("\nConferência manual (o script não tem como verificar)")
for m in manuais:
    print(f"  [ ] {m}")
pend = [d for _, d, ok, _ in itens if not ok]
print(f"\n{len(itens) - len(pend)} de {len(itens)} itens automáticos em conformidade." +
      (f" Pendentes: {len(pend)}." if pend else ""))
sys.exit(1 if pend else 0)
