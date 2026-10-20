from datetime import date

import pytest

from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_ANO,
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
    FatoIndicadorEstadoMes,
    FatoIndicadorMunicipioMes,
)
from app.models.municipio import DimMunicipio
from app.models.usuario import PAPEL_ADMIN, DimUsuario, UsuarioMunicipio
from app.services import indicador_service

COMPETENCIA = date(2025, 9, 1)


def _cria_municipio(codigo, nome, uf, ativo_piloto=True):
    municipio = DimMunicipio(
        codigo_ibge=codigo, nome=nome, uf=uf, ativo_piloto=ativo_piloto
    )
    db.session.add(municipio)
    db.session.commit()
    return municipio


def _cria_indicador(granularidade):
    indicador = DimIndicador(
        codigo=f"teste.{granularidade}",
        nome_exibicao="Teste",
        dataset_origem="teste",
        granularidade=granularidade,
        categoria="teste",
    )
    db.session.add(indicador)
    db.session.commit()
    return indicador


def _cria_usuario(usuario_id, papel="gestor_municipal", municipios=()):
    usuario = DimUsuario(
        id=usuario_id, email=f"{usuario_id}@x.com", nome="Teste", papel=papel
    )
    db.session.add(usuario)
    db.session.commit()
    for municipio in municipios:
        db.session.add(
            UsuarioMunicipio(usuario_id=usuario.id, municipio_id=municipio.id)
        )
    db.session.commit()
    return usuario


def test_comparar_municipio_mes_monta_valor_e_medias(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_MUNICIPIO_MES)
        meu_municipio = _cria_municipio("2900108", "A", "BA")
        outro_mesma_uf = _cria_municipio("2900207", "B", "BA")
        municipio_pe = _cria_municipio("2600054", "C", "PE")
        usuario = _cria_usuario("u1", municipios=[meu_municipio])

        db.session.add_all(
            [
                FatoIndicadorMunicipioMes(
                    municipio_id=meu_municipio.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=100,
                    fonte_hash="a" * 64,
                ),
                FatoIndicadorMunicipioMes(
                    municipio_id=outro_mesma_uf.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=200,
                    fonte_hash="b" * 64,
                ),
                FatoIndicadorMunicipioMes(
                    municipio_id=municipio_pe.id,
                    indicador_id=indicador.id,
                    competencia=COMPETENCIA,
                    valor=300,
                    fonte_hash="c" * 64,
                ),
            ]
        )
        db.session.commit()

        resultado = indicador_service.comparar(
            usuario, meu_municipio.id, indicador.codigo, COMPETENCIA
        )

        assert isinstance(resultado, indicador_service.ComparacaoMunicipioMes)
        assert float(resultado.valor_municipio) == 100.0
        assert float(resultado.media_uf) == 150.0  # (100+200)/2, só BA
        assert float(resultado.media_piloto) == 200.0  # (100+200+300)/3


def test_comparar_estado_mes_monta_valor_estado_e_medias(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_ESTADO_MES)
        municipio = _cria_municipio("2900108", "A", "BA")
        usuario = _cria_usuario("u1", municipios=[municipio])

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
            ]
        )
        db.session.commit()

        resultado = indicador_service.comparar(
            usuario, municipio.id, indicador.codigo, COMPETENCIA
        )

        assert isinstance(resultado, indicador_service.ComparacaoEstadoMes)
        assert float(resultado.valor_estado) == 10.0
        assert float(resultado.media_piloto) == 15.0  # (10+20)/2, BA e PE só
        assert not hasattr(resultado, "valor_municipio")


def test_gestor_sem_acesso_ao_municipio_e_bloqueado(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_MUNICIPIO_MES)
        meu_municipio = _cria_municipio("2900108", "A", "BA")
        municipio_alheio = _cria_municipio("2900207", "B", "BA")
        usuario = _cria_usuario("u1", municipios=[meu_municipio])

        with pytest.raises(indicador_service.ForbiddenError):
            indicador_service.comparar(
                usuario, municipio_alheio.id, indicador.codigo, COMPETENCIA
            )


def test_admin_acessa_qualquer_municipio(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_MUNICIPIO_MES)
        municipio = _cria_municipio("2900108", "A", "BA")
        admin = _cria_usuario("admin1", papel=PAPEL_ADMIN)

        resultado = indicador_service.comparar(
            admin, municipio.id, indicador.codigo, COMPETENCIA
        )

        assert resultado.valor_municipio is None  # sem dado, mas não bloqueou


def test_gestor_consulta_estado_mes_mesmo_sem_vinculo_ao_municipio_pedido(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_ESTADO_MES)
        meu_municipio = _cria_municipio("2900108", "A", "BA")
        municipio_alheio = _cria_municipio("2600054", "C", "PE")
        usuario = _cria_usuario("u1", municipios=[meu_municipio])

        # estado_mes é estatística agregada, não dado de município — não
        # bloqueia mesmo pedindo via um município fora do vínculo do gestor.
        resultado = indicador_service.comparar(
            usuario, municipio_alheio.id, indicador.codigo, COMPETENCIA
        )

        assert isinstance(resultado, indicador_service.ComparacaoEstadoMes)


def test_indicador_inexistente_levanta_erro(app):
    with app.app_context():
        municipio = _cria_municipio("2900108", "A", "BA")
        usuario = _cria_usuario("u1", municipios=[municipio])

        with pytest.raises(indicador_service.IndicadorNaoEncontradoError):
            indicador_service.comparar(usuario, municipio.id, "nao.existe", COMPETENCIA)


def test_municipio_inexistente_levanta_erro(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_MUNICIPIO_MES)
        admin = _cria_usuario("admin1", papel=PAPEL_ADMIN)

        with pytest.raises(indicador_service.MunicipioNaoEncontradoError):
            indicador_service.comparar(admin, 9999, indicador.codigo, COMPETENCIA)


def test_granularidade_sem_suporte_levanta_erro(app):
    with app.app_context():
        indicador = _cria_indicador(GRANULARIDADE_MUNICIPIO_ANO)
        municipio = _cria_municipio("2900108", "A", "BA")
        admin = _cria_usuario("admin1", papel=PAPEL_ADMIN)

        with pytest.raises(indicador_service.GranularidadeNaoSuportadaError):
            indicador_service.comparar(
                admin, municipio.id, indicador.codigo, COMPETENCIA
            )
