"""Carrega data/municipios_ibge.csv em dim_municipio.

Uso: python -m scripts.seed_municipios
Idempotente: upsert por codigo_ibge, reexecutar não duplica.
"""

import csv
import logging
import sys
from pathlib import Path

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from app import create_app
from app.extensions import db
from app.models import DimMunicipio

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "municipios_ibge.csv"


def _ler_linhas(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))

    if not linhas:
        raise ValueError(f"{caminho} está vazio")

    for linha in linhas:
        codigo = linha["codigo_ibge"]
        if not (codigo.isdigit() and len(codigo) == 7):
            raise ValueError(f"codigo_ibge inválido: {linha!r}")
        if not linha["nome"].strip():
            raise ValueError(f"nome vazio: {linha!r}")
        if linha["uf"] not in ("BA", "PE", "RN"):
            raise ValueError(f"uf fora do escopo do piloto: {linha!r}")

    return linhas


def seed_municipios() -> int:
    linhas = _ler_linhas(CSV_PATH)

    dialeto = db.engine.dialect.name
    insert_fn = postgresql_insert if dialeto == "postgresql" else sqlite_insert

    stmt = insert_fn(DimMunicipio).values(
        [
            {
                "codigo_ibge": linha["codigo_ibge"],
                "nome": linha["nome"],
                "uf": linha["uf"],
            }
            for linha in linhas
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["codigo_ibge"],
        set_={"nome": stmt.excluded.nome, "uf": stmt.excluded.uf},
    )
    db.session.execute(stmt)
    db.session.commit()

    logger.info("seed_municipios: %d municípios gravados/atualizados", len(linhas))
    return len(linhas)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    with app.app_context():
        try:
            total = seed_municipios()
        except Exception:
            logger.exception("Falha ao semear dim_municipio")
            sys.exit(1)
    print(f"{total} municípios gravados/atualizados.")
