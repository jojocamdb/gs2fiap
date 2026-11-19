import numpy as np
import pandas as pd
import pytest

from zeladoria import indicadores as ind


def test_kaplan_meier_confere_com_calculo_manual():
    # dias: 1(f) 2(f) 2(aberta) 4(f) 5(aberta)
    km = ind.kaplan_meier([1, 2, 2, 4, 5], [1, 1, 0, 1, 0]).set_index("dia")["em_aberto"]
    assert km[1] == pytest.approx(4 / 5)
    assert km[2] == pytest.approx(4 / 5 * 3 / 4)
    assert km[4] == pytest.approx(4 / 5 * 3 / 4 * 1 / 2)
    assert km[5] == pytest.approx(0.3)


def test_sem_censura_km_igual_a_mediana_empirica():
    dias = np.arange(1, 102)
    assert ind.percentil_km(dias, np.ones_like(dias), 0.5) == 51


def test_percentil_nao_atingido_devolve_none():
    assert ind.percentil_km([10, 10, 10, 10], [1, 0, 0, 0], 0.5) is None


def test_media_das_finalizadas_subestima_com_censura():
    # 5 resolvidas em 2 dias, 5 abertas ha 100 dias: a media ingenua diria 2 dias
    dias, ev = [2] * 5 + [100] * 5, [1] * 5 + [0] * 5
    assert ind.percentil_km(dias, ev, 0.5) == 2
    assert ind.percentil_km(dias, ev, 0.8) is None


def _base():
    linhas = []
    # servico 1 (rapido): 90% na cidade. servico 2 (lento): 30% na cidade.
    for distrito, s1_ok, s1_n, s2_ok, s2_n in (("A", 90, 100, 30, 100), ("B", 90, 100, 30, 100)):
        linhas += [(distrito, 1, 1)] * s1_ok + [(distrito, 1, 0)] * (s1_n - s1_ok)
        linhas += [(distrito, 2, 1)] * s2_ok + [(distrito, 2, 0)] * (s2_n - s2_ok)
    df = pd.DataFrame(linhas, columns=["distrito", "id_servico", "resolvida_janela"])
    df["elegivel_janela"] = 1
    return df


def test_indice_vale_um_quando_distrito_igual_a_cidade():
    ix = ind.indice_por_distrito(_base()).set_index("distrito")
    assert ix["indice"].tolist() == pytest.approx([1.0, 1.0])


def test_indice_neutraliza_o_mix_de_servicos():
    df = _base()
    # C so pede o servico lento e resolve na taxa da cidade: taxa bruta baixa, indice 1
    c = pd.DataFrame({"distrito": "C", "id_servico": 2, "resolvida_janela": [1] * 30 + [0] * 70,
                      "elegivel_janela": 1})
    ix = ind.indice_por_distrito(pd.concat([df, c])).set_index("distrito")
    assert ix.loc["C", "taxa_bruta"] == pytest.approx(0.30)
    assert ix.loc["C", "indice"] == pytest.approx(1.0)
    assert ix.loc["C", "ic_inf"] < 1 < ix.loc["C", "ic_sup"]


def test_nao_elegiveis_ficam_fora_da_taxa():
    df = _base()
    extra = pd.DataFrame({"distrito": "A", "id_servico": 1, "resolvida_janela": [0] * 500,
                          "elegivel_janela": 0})
    ix = ind.indice_por_distrito(pd.concat([df, extra])).set_index("distrito")
    assert ix.loc["A", "elegiveis"] == 200 and ix.loc["A", "indice"] == pytest.approx(1.0)


def test_estimar_prazo_recua_para_cidade_com_pouco_volume():
    df = pd.DataFrame({"id_servico": 1, "id_distrito": [1] * 200 + [2] * 5, "dias": 3,
                       "finalizada": 1, "elegivel_janela": 1, "resolvida_janela": 1})
    assert ind.estimar_prazo(df, 1, 1)["nivel"] == "distrito"
    r = ind.estimar_prazo(df, 1, 2)
    assert r["nivel"] == "cidade" and r["demandas_locais"] == 5 and r["demandas"] == 205


def _pares():
    linhas = []
    # 25 distritos no servico 1: 24 com 80% e o distrito "RUIM" com 40%, 100 pedidos cada
    for i in range(24):
        linhas += [(f"D{i:02d}", i, 1, "S1", 1)] * 80 + [(f"D{i:02d}", i, 1, "S1", 0)] * 20
    linhas += [("RUIM", 99, 1, "S1", 1)] * 40 + [("RUIM", 99, 1, "S1", 0)] * 60
    df = pd.DataFrame(linhas, columns=["distrito", "id_distrito", "id_servico", "servico", "resolvida_janela"])
    df["elegivel_janela"] = 1
    return df


def test_atraso_evitavel_usa_distrito_mediano_e_ignora_quem_esta_acima():
    g = ind.atraso_evitavel(_pares())
    assert g["distrito"].tolist() == ["RUIM"]                   # so quem esta abaixo da referencia
    assert g["referencia"].iloc[0] == pytest.approx(0.80)
    assert g["ganho"].iloc[0] == pytest.approx(40.0)            # (0,80 - 0,40) x 100 pedidos
    assert g["acumulado"].iloc[-1] == pytest.approx(1.0)


def test_fila_atrasada_e_relativa_ao_servico():
    hist = pd.DataFrame({"id_servico": [1] * 10 + [2] * 10, "dias": [2] * 10 + [50] * 10, "finalizada": 1})
    lim = ind.limites_por_servico(hist)
    assert lim[1] == 2 and lim[2] == 50
    abertas = pd.DataFrame({"id_servico": [1, 1, 2, 2], "dias": [2, 10, 40, 60]})
    fila = ind.fila_atrasada(abertas, lim)
    # 10 dias e atraso no servico rapido; 40 dias nao e atraso no servico lento
    assert fila["dias"].tolist() == [10, 60]


def test_limite_padrao_quando_p80_nao_e_atingido():
    hist = pd.DataFrame({"id_servico": 1, "dias": [5] * 10, "finalizada": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
    assert ind.limites_por_servico(hist, padrao=90)[1] == 90


def test_pontos_de_reincidencia_agrupam_mesmo_servico_e_local():
    a = pd.DataFrame({"id_servico": [1, 1, 1, 2, 1], "servico": ["A", "A", "A", "B", "A"], "distrito": "X",
                      "subprefeitura": "Y", "latitude": [-23.5] * 4 + [-23.6], "longitude": -46.6,
                      "dias": [5, 9, 7, 3, 1], "registros": [1, 2, 1, 1, 1]})
    p = ind.pontos_de_reincidencia(a, minimo=3)
    assert len(p) == 1 and p["pedidos"].iloc[0] == 3 and p["registros"].iloc[0] == 4
    assert p["dias_mais_antigo"].iloc[0] == 9


def test_curva_sobrevivencia_em_degraus():
    s = ind.curva_sobrevivencia([1, 2, 2, 4, 5], [1, 1, 0, 1, 0], ate=6)
    assert s[0] == 1.0 and s[1] == pytest.approx(0.8) and s[3] == pytest.approx(0.6)
    assert s[4] == pytest.approx(0.3) and s[6] == pytest.approx(0.3)


def _historico():
    # servico 1: metade fecha no dia 2, a outra metade fica em aberto ate o dia 40
    return pd.DataFrame({"id_servico": 1, "id_distrito": 1, "dias": [2] * 50 + [40] * 50,
                         "finalizada": [1] * 50 + [0] * 50})


def test_idade_do_pedido_aumenta_o_risco():
    m = ind.ajustar_alerta(_historico(), ate=30)
    novos = pd.DataFrame({"id_servico": [1, 1], "id_distrito": [1, 1], "dias": [0, 10]})
    p = ind.prob_passar_da_janela(novos, m, ate=30)
    assert p[0] == pytest.approx(0.5)      # recem aberto: metade estoura
    assert p[1] == pytest.approx(1.0)      # ja passou do dia 2 sem fechar: estoura
    sem = ind.prob_passar_da_janela(novos, m, ate=30, usar_idade=False)
    assert sem.tolist() == pytest.approx([0.5, 0.5])


def test_alerta_recua_para_o_servico_e_para_a_cidade():
    m = ind.ajustar_alerta(_historico(), ate=30)
    outros = pd.DataFrame({"id_servico": [1, 99], "id_distrito": [77, 77], "dias": [0, 0]})
    p = ind.prob_passar_da_janela(outros, m, ate=30)
    assert p.tolist() == pytest.approx([0.5, 0.5])


def test_retrato_esconde_o_que_aconteceu_depois():
    df = pd.DataFrame({
        "data_abertura": pd.to_datetime(["2026-01-01", "2026-01-10", "2026-02-01"]),
        "data_finalizacao": ["2026-01-05", "2026-01-25", None],
        "data_corte": "2026-03-01", "finalizada": [1, 1, 0], "dias": [4, 15, 28]})
    r = ind.retrato_em(df, "2026-01-15")
    assert len(r) == 2                                   # o pedido de fevereiro ainda nao existia
    assert r["finalizada"].tolist() == [1, 0]            # o segundo so fecharia no dia 25
    assert r["dias"].tolist() == [4, 5]
