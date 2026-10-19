"""Upsert idempotente das linhas validadas nas tabelas fato.

Reexecutar a ingestão da mesma competência não duplica linha — isso é
garantido pela UNIQUE constraint de cada tabela fato, não por lógica da
aplicação. O dialeto (Postgres em produção, SQLite em dev/CI) é resolvido
em runtime para que o mesmo loader funcione nos dois.
"""

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.extensions import db
from app.models.indicador import FatoIndicadorEstadoMes, FatoIndicadorMunicipioMes

# ~7 colunas por linha — em lotes de 100 fica em ~700 parâmetros, seguro
# mesmo no limite mais conservador do SQLite (999 variáveis por statement).
# Descoberto na prática: um upsert único com ~15 mil linhas (769 municípios
# x ~20 campos) estourava esse limite com "too many SQL variables".
TAMANHO_LOTE = 100


def _insert_fn():
    return (
        postgresql_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
    )


def _upsert(
    model, linhas: list[dict], ingestao_id: int, index_elements: list[str]
) -> int:
    if not linhas:
        return 0

    valores = [{**linha, "ingestao_id": ingestao_id} for linha in linhas]

    for inicio in range(0, len(valores), TAMANHO_LOTE):
        lote = valores[inicio : inicio + TAMANHO_LOTE]
        stmt = _insert_fn()(model).values(lote)
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={
                "valor": stmt.excluded.valor,
                "fonte_hash": stmt.excluded.fonte_hash,
                "ingestao_id": stmt.excluded.ingestao_id,
            },
        )
        db.session.execute(stmt)

    return len(valores)


def upsert_fato_municipio_mes(linhas: list[dict], ingestao_id: int) -> int:
    return _upsert(
        FatoIndicadorMunicipioMes,
        linhas,
        ingestao_id,
        index_elements=["municipio_id", "indicador_id", "competencia"],
    )


def upsert_fato_estado_mes(linhas: list[dict], ingestao_id: int) -> int:
    return _upsert(
        FatoIndicadorEstadoMes,
        linhas,
        ingestao_id,
        index_elements=["uf", "indicador_id", "competencia"],
    )
