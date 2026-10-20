"""Único lugar com SQL sobre as tabelas fato de indicador.

A camada de serviço (app/services/indicador_service.py) nunca monta query
direto — só chama estas funções. AVG roda no banco (não traz N linhas pro
Python pra somar à mão) e já ignora NULL nativamente: "fonte não reportou"
não entra na média como zero.
"""

from decimal import Decimal

from app.extensions import db
from app.models.indicador import FatoIndicadorEstadoMes, FatoIndicadorMunicipioMes


def valor_municipio(
    municipio_id: int, indicador_id: int, competencia
) -> Decimal | None:
    fato = FatoIndicadorMunicipioMes.query.filter_by(
        municipio_id=municipio_id, indicador_id=indicador_id, competencia=competencia
    ).first()
    return fato.valor if fato else None


def media_municipios(
    municipio_ids: list[int], indicador_id: int, competencia
) -> Decimal | None:
    if not municipio_ids:
        return None

    (media,) = (
        db.session.query(db.func.avg(FatoIndicadorMunicipioMes.valor))
        .filter(
            FatoIndicadorMunicipioMes.municipio_id.in_(municipio_ids),
            FatoIndicadorMunicipioMes.indicador_id == indicador_id,
            FatoIndicadorMunicipioMes.competencia == competencia,
        )
        .one()
    )
    return media


def valor_estado_agregado(uf: str, indicador_id: int, competencia) -> Decimal | None:
    fato = FatoIndicadorEstadoMes.query.filter_by(
        uf=uf, indicador_id=indicador_id, competencia=competencia
    ).first()
    return fato.valor if fato else None


def media_estados(ufs: list[str], indicador_id: int, competencia) -> Decimal | None:
    if not ufs:
        return None

    (media,) = (
        db.session.query(db.func.avg(FatoIndicadorEstadoMes.valor))
        .filter(
            FatoIndicadorEstadoMes.uf.in_(ufs),
            FatoIndicadorEstadoMes.indicador_id == indicador_id,
            FatoIndicadorEstadoMes.competencia == competencia,
        )
        .one()
    )
    return media
