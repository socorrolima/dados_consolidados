from datetime import date

from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
    FatoIndicadorMunicipioMes,
)
from app.models.ingestao import IngestaoExecucao
from app.models.municipio import DimMunicipio
from ingestion.loader import TAMANHO_LOTE, upsert_fato_municipio_mes


def _prepara_municipio_e_indicador():
    municipio = DimMunicipio(codigo_ibge="2400109", nome="Acari", uf="RN")
    indicador = DimIndicador(
        codigo="misocial.suas_repasse_mun_vl_psb_f",
        nome_exibicao="Repasse PSB",
        dataset_origem="misocial",
        granularidade=GRANULARIDADE_MUNICIPIO_MES,
        categoria="protecao_social_basica",
    )
    ingestao = IngestaoExecucao(dataset_origem="misocial", parametros="teste")
    db.session.add_all([municipio, indicador, ingestao])
    db.session.commit()
    return municipio, indicador, ingestao


def test_upsert_e_idempotente(app):
    with app.app_context():
        municipio, indicador, ingestao = _prepara_municipio_e_indicador()
        linha = {
            "municipio_id": municipio.id,
            "indicador_id": indicador.id,
            "competencia": date(2025, 9, 1),
            "valor": 10256.83,
            "fonte_hash": "a" * 64,
        }

        upsert_fato_municipio_mes([linha], ingestao.id)
        db.session.commit()
        upsert_fato_municipio_mes([linha], ingestao.id)
        db.session.commit()

        linhas_gravadas = FatoIndicadorMunicipioMes.query.all()
        assert len(linhas_gravadas) == 1
        assert float(linhas_gravadas[0].valor) == 10256.83


def test_upsert_atualiza_valor_quando_fonte_retifica(app):
    with app.app_context():
        municipio, indicador, ingestao = _prepara_municipio_e_indicador()
        base = {
            "municipio_id": municipio.id,
            "indicador_id": indicador.id,
            "competencia": date(2025, 9, 1),
        }

        upsert_fato_municipio_mes(
            [{**base, "valor": 100.0, "fonte_hash": "a" * 64}], ingestao.id
        )
        db.session.commit()
        upsert_fato_municipio_mes(
            [{**base, "valor": 200.0, "fonte_hash": "b" * 64}], ingestao.id
        )
        db.session.commit()

        linhas_gravadas = FatoIndicadorMunicipioMes.query.all()
        assert len(linhas_gravadas) == 1
        assert float(linhas_gravadas[0].valor) == 200.0


def test_upsert_funciona_com_lote_maior_que_tamanho_do_lote_interno(app):
    with app.app_context():
        municipio = DimMunicipio(codigo_ibge="2400109", nome="Acari", uf="RN")
        ingestao = IngestaoExecucao(dataset_origem="misocial", parametros="teste")
        quantidade = TAMANHO_LOTE * 2 + 37  # atravessa 3 lotes internos
        indicadores = [
            DimIndicador(
                codigo=f"misocial.teste_{i}",
                nome_exibicao=f"Teste {i}",
                dataset_origem="misocial",
                granularidade=GRANULARIDADE_MUNICIPIO_MES,
                categoria="teste",
            )
            for i in range(quantidade)
        ]
        db.session.add_all([municipio, ingestao, *indicadores])
        db.session.commit()

        linhas = [
            {
                "municipio_id": municipio.id,
                "indicador_id": indicador.id,
                "competencia": date(2025, 9, 1),
                "valor": float(i),
                "fonte_hash": f"{i:064d}",
            }
            for i, indicador in enumerate(indicadores)
        ]

        gravadas = upsert_fato_municipio_mes(linhas, ingestao.id)
        db.session.commit()

        assert gravadas == quantidade
        assert FatoIndicadorMunicipioMes.query.count() == quantidade
