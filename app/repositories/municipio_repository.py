from app.extensions import db
from app.models.municipio import DimMunicipio


def municipio_por_id(municipio_id: int) -> DimMunicipio | None:
    return db.session.get(DimMunicipio, municipio_id)


def ids_municipios_da_uf(uf: str) -> list[int]:
    return [m.id for m in DimMunicipio.query.filter_by(uf=uf).all()]


def ids_municipios_do_piloto() -> list[int]:
    return [m.id for m in DimMunicipio.query.filter_by(ativo_piloto=True).all()]
