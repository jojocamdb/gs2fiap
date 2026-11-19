"""Parametros centrais do projeto. Toda decisao metodologica ajustavel fica aqui."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_BRUTO = RAIZ / "data" / "raw"
DIR_PROC = RAIZ / "data" / "processed"
BANCO = DIR_PROC / "zeladoria.db"
DIR_ASSETS = RAIZ / "assets"

COLUNAS = [
    "data_abertura", "data_finalizacao", "canal", "tema", "assunto", "servico",
    "status", "orgao", "logradouro", "numero", "cep", "latitude", "longitude",
    "subprefeitura", "distrito",
]

# Recorte de zeladoria: assuntos com execucao fisica no territorio.
# Ficam fora fiscalizacao (PSIU, ambulantes), certidoes e ouvidoria.
ASSUNTOS_ZELADORIA = [
    "PONTO VICIADO, ENTULHO E CACAMBA DE ENTULHO",
    "REPAROS EM ASFALTO, PONTES, VIADUTOS E TUNEIS",
    "ARVORE",
    "CAPINACAO E ROCADA DE AREAS VERDES",
    "DRENAGEM DE AGUA DE CHUVA",
    "VARRICAO E LIMPEZA URBANA",
    "FIACAO E POSTES",
    "CALCADAS, GUIAS E POSTES",
    "COLETA DE LIXO DOMICILIAR",
    "LIXEIRAS PUBLICAS",
    "REMOCAO DE GRANDES OBJETOS",
    "PRACAS",
    "RIOS E CORREGOS",
    "COLETA SELETIVA",
    "RUAS, VILAS, VIELAS E ESCADARIAS",
]

# Janela do indicador principal: demanda resolvida em ate N dias.
JANELA_DIAS = 30
# Minimo de demandas para um par (servico, distrito) entrar em comparacoes.
MIN_DEMANDAS = 30
# Marco zero de Sao Paulo (Praca da Se), usado como referencia de centralidade.
SE_LAT, SE_LON = -23.5505, -46.6333
SEMENTE = 42
