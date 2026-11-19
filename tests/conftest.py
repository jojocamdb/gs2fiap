import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from zeladoria import config  # noqa: E402

CAB = ["Data de Abertura", "Data de Finalização", "Meio de Comunicação", "Tema", "Assunto", "Serviço",
       "Status", "Órgão", "Logradouro", "Número", "CEP", "Latitude", "Longitude",
       "Prefeitura Operacional", "Distrito"]


def linha(ab, fi, status="Finalizada", servico="Tapa-buraco", distrito="LAPA", num="10",
          assunto="Reparos em  Asfalto, Pontes, Viadutos e Túneis"):
    return [ab, fi, "PORTAL", "Rua e bairro", assunto, servico, status, "ORG", "Rua A", num,
            "05000000", "-23.52", "-46.70", "LAPA", distrito]


def escrever(caminho, linhas, sep, codificacao):
    import csv
    import io
    buf = io.StringIO()
    csv.writer(buf, delimiter=sep, lineterminator="\r\n").writerows([CAB] + linhas)
    caminho.write_bytes(buf.getvalue().encode(codificacao))
    return caminho


@pytest.fixture
def exige_banco():
    if not config.BANCO.exists():
        pytest.skip("banco nao gerado: rode scripts/01_etl.py e scripts/02_analise.py")
