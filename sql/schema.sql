-- Modelo dimensional da base de zeladoria (SQLite).
-- Endereco (logradouro, numero, CEP) nao e persistido: a analise e por distrito
-- e a coordenada e arredondada a 3 casas (cerca de 100 m) por minimizacao de dados.
PRAGMA foreign_keys = ON;

CREATE TABLE dim_distrito (
    id_distrito      INTEGER PRIMARY KEY,
    nome             TEXT NOT NULL UNIQUE,
    subprefeitura    TEXT,
    lat_centro       REAL,
    lon_centro       REAL,
    dist_centro_km   REAL
);

CREATE TABLE dim_servico (
    id_servico   INTEGER PRIMARY KEY,
    servico_norm TEXT NOT NULL UNIQUE,
    servico      TEXT NOT NULL,
    assunto      TEXT NOT NULL,
    tema         TEXT NOT NULL
);

CREATE TABLE dim_canal (
    id_canal INTEGER PRIMARY KEY,
    canal    TEXT NOT NULL UNIQUE
);

CREATE TABLE fato_demanda (
    id_demanda        INTEGER PRIMARY KEY,
    id_distrito       INTEGER NOT NULL REFERENCES dim_distrito(id_distrito),
    id_servico        INTEGER NOT NULL REFERENCES dim_servico(id_servico),
    id_canal          INTEGER NOT NULL REFERENCES dim_canal(id_canal),
    data_abertura     TEXT NOT NULL,
    data_finalizacao  TEXT,
    data_corte        TEXT NOT NULL,
    status            TEXT NOT NULL,
    finalizada        INTEGER NOT NULL CHECK (finalizada IN (0, 1)),
    dias              INTEGER NOT NULL CHECK (dias >= 0),
    dias_observaveis  INTEGER NOT NULL CHECK (dias_observaveis >= 0),
    elegivel_janela   INTEGER NOT NULL CHECK (elegivel_janela IN (0, 1)),
    resolvida_janela  INTEGER NOT NULL CHECK (resolvida_janela IN (0, 1)),
    registros         INTEGER NOT NULL CHECK (registros >= 1),
    latitude          REAL,
    longitude         REAL,
    CHECK (finalizada = 0 OR data_finalizacao IS NOT NULL),
    CHECK (resolvida_janela <= finalizada)
);

CREATE INDEX ix_fato_distrito ON fato_demanda(id_distrito);
CREATE INDEX ix_fato_servico  ON fato_demanda(id_servico);
CREATE INDEX ix_fato_abertura ON fato_demanda(data_abertura);

CREATE TABLE auditoria_funil (
    ordem  INTEGER PRIMARY KEY,
    etapa  TEXT NOT NULL,
    linhas INTEGER NOT NULL
);

CREATE TABLE auditoria_arquivo (
    arquivo       TEXT PRIMARY KEY,
    codificacao   TEXT NOT NULL,
    separador     TEXT NOT NULL,
    formato_data  TEXT NOT NULL,
    linhas        INTEGER NOT NULL,
    abertura_min  TEXT NOT NULL,
    abertura_max  TEXT NOT NULL,
    data_corte    TEXT NOT NULL
);

CREATE TABLE log_consulta (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    momento     TEXT NOT NULL DEFAULT (datetime('now')),
    origem      TEXT NOT NULL,
    id_servico  INTEGER,
    id_distrito INTEGER,
    tamanho_texto INTEGER
);

CREATE VIEW vw_demanda AS
SELECT f.*, d.nome AS distrito, d.subprefeitura, d.dist_centro_km,
       s.servico, s.assunto, s.tema, c.canal
FROM fato_demanda f
JOIN dim_distrito d USING (id_distrito)
JOIN dim_servico  s USING (id_servico)
JOIN dim_canal    c USING (id_canal);
