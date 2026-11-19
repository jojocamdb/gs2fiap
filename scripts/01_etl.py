"""Le os CSVs brutos do SP156, limpa e gera o banco. Uso: python scripts/01_etl.py [dir_brutos]"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zeladoria import config, db, etl  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else config.DIR_BRUTO
    try:
        bruto, perfis = etl.carregar_brutos(origem)
        limpo, funil = etl.limpar(bruto)
        destino = db.criar_banco(limpo, funil, perfis)
    except etl.ErroDeDados as exc:
        logging.error("Carga interrompida: %s", exc)
        sys.exit(1)
    for etapa, n in funil.items():
        print(f"{etapa:35s} {n:>10,}")
    print(f"Banco gerado em {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
