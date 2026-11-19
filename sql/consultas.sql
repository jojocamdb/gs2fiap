-- Consultas analiticas de referencia. Todas rodam sobre data/processed/zeladoria.db.

-- Q1. Taxa de resolucao em 30 dias por distrito (so demandas com 30+ dias observaveis).
SELECT distrito,
       COUNT(*)                                  AS demandas_elegiveis,
       ROUND(100.0 * AVG(resolvida_janela), 1)   AS pct_resolvida_30d
FROM vw_demanda
WHERE elegivel_janela = 1
GROUP BY distrito
ORDER BY pct_resolvida_30d;

-- Q2. Mesmo servico, distritos diferentes: amplitude da taxa de resolucao.
WITH base AS (
    SELECT servico, distrito, COUNT(*) AS n, AVG(resolvida_janela) AS taxa
    FROM vw_demanda
    WHERE elegivel_janela = 1
    GROUP BY servico, distrito
    HAVING COUNT(*) >= 30
)
SELECT servico,
       COUNT(*)                         AS distritos,
       ROUND(100 * MIN(taxa), 1)        AS pior_pct,
       ROUND(100 * MAX(taxa), 1)        AS melhor_pct,
       ROUND(100 * (MAX(taxa) - MIN(taxa)), 1) AS amplitude_pp
FROM base
GROUP BY servico
HAVING COUNT(*) >= 20
ORDER BY amplitude_pp DESC;

-- Q3. Estoque em aberto ha mais de 60 dias por subprefeitura.
SELECT subprefeitura, COUNT(*) AS abertas_mais_60d
FROM vw_demanda
WHERE finalizada = 0 AND dias > 60
GROUP BY subprefeitura
ORDER BY abertas_mais_60d DESC;

-- Q4. Canal de entrada por distrito (participacao do aplicativo).
SELECT distrito,
       ROUND(100.0 * SUM(canal = 'MOBILE') / COUNT(*), 1) AS pct_app
FROM vw_demanda
GROUP BY distrito
ORDER BY pct_app DESC;

-- Q5. Enderecos com registros repetidos (proxy de reincidencia ou carga em lote).
SELECT servico, distrito, SUM(registros) AS registros, COUNT(*) AS demandas_distintas
FROM vw_demanda
GROUP BY servico, distrito
HAVING SUM(registros) > 2 * COUNT(*)
ORDER BY registros DESC
LIMIT 20;
