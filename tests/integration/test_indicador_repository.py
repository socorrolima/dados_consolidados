from datetime import date

from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
    FatoIndicadorEstadoMes,
    FatoIndicadorMunicipioMes,
)
from app.models.municipio import DimMunicipio
from app.repositories import indicador_repository

COMPETENCIA = date(2025, 9, 1)


def _cria_indicador(granularidade=GRANULARIDADE_MUNICIPIO_MES):
    indicador = DimIndicador(
        codigo=f"teste.indicador_{granularidade}",
        nome_exibicao="Teste",
        dataset_origem="teste",
        granularidade=granularidade,
        categoria="teste",
    )
    db.session.add(indicador)
    db.session.commit()
    return indicador


def _cria_municipio(codigo, nome, uf):
    municipio = DimMunicipio(codigo_ibge=codigo, nome=nome, uf=uf)
    db.session.add(municipio)
    db.session.commit()
    return municipio


def test_media_municipios_ignora_valores_nulos(app):
    with app.app_context():
        indicador = _cria_indicador()
        m1 = _cria_municipio("2900108", "A", "BA")
        m2 = _cria_municipio("2900207", "B", "BA")
        m3 = _cria_municipio("2900306", "C", "BA")
        m4 = _cria_municipio("2900355", "D", "BA")

        # m1=100, m2=200, m3 sem linha (fonte não reportou == NULL), m4=300
        # média correta: (100+200+300)/3 = 200, nunca 150 (que seria tratar
        # a ausência como zero).
        db.session.add_all(
            [
                FatoIndicadorMunicipioMes(
                    municipio_id=m1.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=100,
                    fonte_hash="a" * 64,
                ),
                FatoIndicadorMunicipioMes(
                    municipio_id=m2.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=200,
                    fonte_hash="b" * 64,
                ),
                FatoIndicadorMunicipioMes(
                    municipio_id=m4.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=300,
                    fonte_hash="c" * 64,
                ),
            ]
        )
        db.session.commit()

        media = indicador_repository.media_municipios(
            [m1.id, m2.id, m3.id, m4.id], indicador.id, COMPETENCIA
        )

        assert float(media) == 200.0


def test_media_municipios_sem_nenhuma_linha_retorna_none(app):
    with app.app_context():
        indicador = _cria_indicador()
        m1 = _cria_municipio("2900108", "A", "BA")

        media = indicador_repository.media_municipios(
            [m1.id], indicador.id, COMPETENCIA
        )

        assert media is None


def test_valor_municipio_sem_linha_retorna_none(app):
    with app.app_context():
        indicador = _cria_indicador()
        m1 = _cria_municipio("2900108", "A", "BA")

        valor = indicador_repository.valor_municipio(m1.id, indicador.id, COMPETENCIA)

        assert valor is None


def test_media_estados_ignora_valores_nulos(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_ESTADO_MES)

        db.session.add_all(
            [
                FatoIndicadorEstadoMes(
                    uf="BA",
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=10,
                    fonte_hash="a" * 64,
                ),
                FatoIndicadorEstadoMes(
                    uf="PE",
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=20,
                    fonte_hash="b" * 64,
                ),
                # RN sem linha — não entra na média como 0
            ]
        )
        db.session.commit()

        media = indicador_repository.media_estados(
            ["BA", "PE", "RN"], indicador.id, COMPETENCIA
        )

        assert float(media) == 15.0
