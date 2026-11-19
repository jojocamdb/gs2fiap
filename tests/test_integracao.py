"""Testes sobre o banco real. Sao pulados se o banco ainda nao foi gerado."""
import sqlite3

import pandas as pd
import pytest

from zeladoria import config, db
from zeladoria.etl import normalizar
from zeladoria.recomendador import Recomendador

pytestmark = pytest.mark.usefixtures("exige_banco")


def um(sql, params=()):
    return db.ler(sql, params).iloc[0, 0]


def test_funil_fecha_com_a_tabela_fato():
    assert um("SELECT linhas FROM auditoria_funil WHERE etapa = 'base_final'") == um(
        "SELECT COUNT(*) FROM fato_demanda")


def test_96_distritos_e_nenhum_codigo_numerico():
    assert um("SELECT COUNT(*) FROM dim_distrito") == 96
    assert um("SELECT COUNT(*) FROM dim_distrito WHERE nome GLOB '[0-9]*'") == 0


def test_invariantes_de_prazo():
    assert um("SELECT COUNT(*) FROM fato_demanda WHERE finalizada = 1 AND data_finalizacao < data_abertura") == 0
    assert um("SELECT COUNT(*) FROM fato_demanda WHERE resolvida_janela = 1 AND dias > ?", (config.JANELA_DIAS,)) == 0
    assert um("SELECT COUNT(*) FROM fato_demanda WHERE elegivel_janela = 1 AND dias_observaveis < ?",
              (config.JANELA_DIAS,)) == 0
    assert um("SELECT COUNT(*) FROM fato_demanda WHERE data_abertura > data_corte") == 0


def test_tres_arquivos_com_periodos_contiguos_e_formatos_distintos():
    a = db.ler("SELECT * FROM auditoria_arquivo ORDER BY abertura_min")
    assert a["abertura_min"].tolist() == ["2026-01-01", "2026-04-01", "2026-07-01"]
    assert set(a["formato_data"]) == {"%d/%m/%Y", "%m/%d/%Y"}


def test_servicos_nao_duplicados_por_grafia():
    s = db.ler("SELECT servico FROM dim_servico")["servico"].map(normalizar)
    assert s.is_unique


def test_banco_nao_guarda_endereco():
    colunas = set(db.ler("SELECT * FROM fato_demanda LIMIT 1").columns)
    assert not colunas & {"logradouro", "numero", "cep"}


def test_restricoes_do_esquema_rejeitam_dado_incoerente(tmp_path):
    con = sqlite3.connect(tmp_path / "t.db")
    con.executescript((config.RAIZ / "sql" / "schema.sql").read_text(encoding="utf-8"))
    con.execute("INSERT INTO dim_distrito (id_distrito, nome) VALUES (1, 'X')")
    con.execute("INSERT INTO dim_servico VALUES (1, 'S', 'S', 'A', 'T')")
    con.execute("INSERT INTO dim_canal VALUES (1, 'PORTAL')")
    ok = (1, 1, 1, "2026-01-01", "2026-01-02", "2026-03-01", "Finalizada", 1, 1, 59, 1, 1, 1, None, None)
    sql = ("INSERT INTO fato_demanda (id_distrito, id_servico, id_canal, data_abertura, data_finalizacao, "
           "data_corte, status, finalizada, dias, dias_observaveis, elegivel_janela, resolvida_janela, "
           "registros, latitude, longitude) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    con.execute(sql, ok)
    for ruim in ((99,) + ok[1:],                                   # distrito inexistente
                 ok[:4] + (None,) + ok[5:],                        # finalizada sem data
                 ok[:8] + (-1,) + ok[9:],                          # dias negativos
                 ok[:7] + (0,) + ok[8:]):                          # resolvida sem estar finalizada
        con.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(sql, ruim)


def test_consulta_parametrizada_trata_injecao_como_texto():
    n = um("SELECT COUNT(*) FROM vw_demanda WHERE distrito = ?", ("LAPA'; DROP TABLE fato_demanda; --",))
    assert n == 0 and um("SELECT COUNT(*) FROM fato_demanda") > 0


def test_conexao_de_leitura_nao_escreve():
    with db.conectar(somente_leitura=True) as con:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM fato_demanda")


def test_consultas_sql_de_referencia_executam():
    blocos = [b for b in (config.RAIZ / "sql" / "consultas.sql").read_text(encoding="utf-8").split(";")
              if "SELECT" in b]
    assert len(blocos) == 5
    for b in blocos:
        assert len(db.ler(b)) > 0


def test_recomendador_no_catalogo_real_acerta_top3_minimo():
    cat = db.ler("SELECT id_servico, servico, assunto FROM dim_servico")
    vol = db.ler("SELECT id_servico, COUNT(*) n FROM fato_demanda GROUP BY 1").set_index("id_servico")["n"]
    r = Recomendador(cat, vol)
    cons = pd.read_csv(config.RAIZ / "tests" / "consultas_simuladas.csv", sep=";")
    nomes = set(cat["servico"].map(normalizar))
    assert all(normalizar(e) in nomes for e in cons["servico_esperado"])   # gabarito existe no catalogo
    top3 = [normalizar(e) in [normalizar(x) for x in r.recomendar(t, 3)["servico"]]
            for t, e in cons.itertuples(index=False)]
    assert sum(top3) / len(top3) >= 0.85


def test_painel_abre_e_atende_um_pedido():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(config.RAIZ / "app.py"), default_timeout=300).run()
    assert not at.exception and not at.error
    at.text_input[0].set_value("buraco na rua, cpf 123.456.789-09").run()
    assert not at.exception
    assert any("CPF" in w.value for w in at.warning)
    assert "Tapa-buraco" in at.radio[-1].options
    assert any("156" in str(m.value) for m in at.markdown)
