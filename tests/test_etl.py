import pandas as pd
import pytest

from conftest import escrever, linha
from zeladoria import etl


def test_detecta_formato_brasileiro_cp1252(tmp_path):
    arq = escrever(tmp_path / "t1.csv", [linha("15/01/2026", "20/01/2026"),
                                         linha("31/03/2026", "")], ";", "cp1252")
    df, perfil = etl.ler_arquivo(arq)
    assert (perfil.codificacao, perfil.separador, perfil.formato_data) == ("cp1252", ";", "%d/%m/%Y")
    assert df["data_abertura"].iloc[0] == pd.Timestamp("2026-01-15")


def test_detecta_formato_americano_utf8(tmp_path):
    # mesmo conteudo logico, no layout do arquivo do 3o trimestre
    arq = escrever(tmp_path / "t3.csv", [linha("07/01/2026", "07/25/2026"),
                                         linha("09/30/2026", "")], ",", "utf-8")
    df, perfil = etl.ler_arquivo(arq)
    assert (perfil.codificacao, perfil.separador, perfil.formato_data) == ("utf-8", ",", "%m/%d/%Y")
    assert df["data_finalizacao"].iloc[0] == pd.Timestamp("2026-07-25")
    assert df["data_corte"].iloc[0] == pd.Timestamp("2026-07-25")


def test_formato_ambiguo_interrompe_a_carga(tmp_path):
    # 01/02 e 03/04 sao validos nos dois formatos: nao ha como decidir, entao nao adivinha
    arq = escrever(tmp_path / "amb.csv", [linha("01/02/2026", "03/02/2026"),
                                          linha("02/03/2026", "")], ";", "cp1252")
    with pytest.raises(etl.ErroDeDados):
        etl.ler_arquivo(arq)


def test_numero_errado_de_colunas(tmp_path):
    (tmp_path / "ruim.csv").write_text("a;b;c\n1;2;3\n", encoding="utf-8")
    with pytest.raises(etl.ErroDeDados):
        etl.ler_arquivo(tmp_path / "ruim.csv")


def test_diretorio_vazio(tmp_path):
    with pytest.raises(etl.ErroDeDados):
        etl.carregar_brutos(tmp_path)


def test_normalizar_unifica_travessao_acento_e_espacos():
    a = etl.normalizar("Árvore – Solicitar avaliação")
    b = etl.normalizar("Árvore \x96 Solicitar avaliação")   # 0x96 lido como latin-1
    c = etl.normalizar("ARVORE - SOLICITAR  AVALIACAO")
    assert a == b == c == "ARVORE SOLICITAR AVALIACAO"
    assert etl.normalizar(None) is None and etl.normalizar("  ") is None


def _base(tmp_path, linhas):
    arq = escrever(tmp_path / "t.csv", linhas, ";", "cp1252")
    return etl.limpar(etl.ler_arquivo(arq)[0])


def test_limpar_aplica_recorte_e_regras(tmp_path):
    linhas = [
        linha("01/01/2026", "05/01/2026"),                       # valida
        linha("01/01/2026", "05/01/2026"),                       # repetida: colapsa
        linha("02/01/2026", "20/03/2026", num="11"),             # valida, fora da janela
        linha("03/01/2026", "", status="Aberto", num="12"),      # aberta: censurada
        linha("04/01/2026", "06/01/2026", status="Cancelada", num="13"),
        linha("05/01/2026", "", status="Finalizada", num="14"),  # incoerente
        linha("06/01/2026", "07/01/2026", distrito="32", num="15"),   # distrito como codigo
        linha("07/01/2026", "08/01/2026", assunto="Poluição Sonora - PSIU", num="16"),
    ]
    df, funil = _base(tmp_path, linhas)
    assert funil["linhas_brutas"] == 8
    assert funil["recorte_zeladoria"] == 7
    assert funil["com_distrito_valido"] == 6
    assert funil["sem_canceladas"] == 5
    assert funil["sem_finalizada_sem_data"] == 4
    assert funil["demandas_distintas"] == 3 and funil["registros_repetidos_colapsados"] == 1
    assert sorted(df["registros"]) == [1, 1, 2]


def test_censura_e_janela(tmp_path):
    linhas = [linha("01/01/2026", "05/01/2026"),
              linha("02/01/2026", "20/03/2026", num="11"),
              linha("03/01/2026", "", status="Aberto", num="12"),
              linha("10/03/2026", "12/03/2026", num="13")]   # so 10 dias observaveis ate o corte
    df, _ = _base(tmp_path, linhas)
    df = df.set_index("numero")
    assert df.loc["10", ["dias", "finalizada", "resolvida_janela"]].tolist() == [4, 1, 1]
    assert df.loc["11", ["dias", "resolvida_janela"]].tolist() == [77, 0]
    # aberta: duracao vai ate a data de corte (20/03) e conta como nao resolvida
    assert df.loc["12", ["dias", "finalizada", "elegivel_janela", "resolvida_janela"]].tolist() == [76, 0, 1, 0]
    # resolvida rapido, mas observada por menos de 30 dias: fica fora do indicador
    assert df.loc["13", ["dias_observaveis", "elegivel_janela"]].tolist() == [10, 0]
