"""Upsert idempotente das linhas validadas nas tabelas fato.

Reexecutar a ingestão da mesma competência não duplica linha — isso é
garantido pela UNIQUE constraint de cada tabela fato (municipio_id,
indicador_id, competencia), não por lógica da aplicação. O dialeto
(Postgres em produção, SQLite em dev/CI) é resolvido em runtime para que
o mesmo loader funcione nos dois.
"""

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.extensions import db
from app.models.indicador import FatoIndicadorMunicipioMes

# 7 colunas por linha (municipio_id, indicador_id, competencia, valor,
# fonte_hash, ingestao_id, created_at via default) — em lotes de 100 linhas
# fica em ~700 parâmetros, seguro mesmo no limite mais conservador do
# SQLite (999 variáveis por statement). Descoberto na prática: um upsert
# único com ~15 mil linhas (769 municípios x ~20 campos) estourava esse
# limite com "too many SQL variables".
TAMANHO_LOTE = 100


def _insert_fn():
    return (
        postgresql_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
    )


def _upsert_lote(valores: list[dict]) -> None:
    stmt = _insert_fn()(FatoIndicadorMunicipioMes).values(valores)
    stmt = stmt.on_conflict_do_update(
        index_elements=["municipio_id", "indicador_id", "competencia"],
        set_={
            "valor": stmt.excluded.valor,
            "fonte_hash": stmt.excluded.fonte_hash,
            "ingestao_id": stmt.excluded.ingestao_id,
        },
    )
    db.session.execute(stmt)


def upsert_fato_municipio_mes(linhas: list[dict], ingestao_id: int) -> int:
    if not linhas:
        return 0

    valores = [{**linha, "ingestao_id": ingestao_id} for linha in linhas]

    for inicio in range(0, len(valores), TAMANHO_LOTE):
        _upsert_lote(valores[inicio : inicio + TAMANHO_LOTE])

    return len(valores)
