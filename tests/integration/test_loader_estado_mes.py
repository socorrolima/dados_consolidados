from datetime import date

from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    DimIndicador,
    FatoIndicadorEstadoMes,
)
from app.models.ingestao import IngestaoExecucao
from ingestion.loader import upsert_fato_estado_mes


def _prepara_indicador_e_ingestao():
    indicador = DimIndicador(
        codigo="misocial_mes_estado.igde_pbf_tac_d",
        nome_exibicao="IGD-E PBF — TAC",
        dataset_origem="misocial_mes_estado",
        granularidade=GRANULARIDADE_ESTADO_MES,
        categoria="igd_e",
    )
    ingestao = IngestaoExecucao(
        dataset_origem="misocial_mes_estado", parametros="teste"
    )
    db.session.add_all([indicador, ingestao])
    db.session.commit()
    return indicador, ingestao


def test_upsert_estado_mes_e_idempotente(app):
    with app.app_context():
        indicador, ingestao = _prepara_indicador_e_ingestao()
        linha = {
            "uf": "BA",
            "indicador_id": indicador.id,
            "competencia": date(2025, 9, 1),
            "valor": 0.95,
            "fonte_hash": "a" * 64,
        }

        upsert_fato_estado_mes([linha], ingestao.id)
        db.session.commit()
        upsert_fato_estado_mes([linha], ingestao.id)
        db.session.commit()

        linhas_gravadas = FatoIndicadorEstadoMes.query.all()
        assert len(linhas_gravadas) == 1
        assert float(linhas_gravadas[0].valor) == 0.95


def test_upsert_estado_mes_nao_mistura_ufs_diferentes(app):
    with app.app_context():
        indicador, ingestao = _prepara_indicador_e_ingestao()
        base = {
            "indicador_id": indicador.id,
            "competencia": date(2025, 9, 1),
            "fonte_hash": "a" * 64,
        }

        upsert_fato_estado_mes([{**base, "uf": "BA", "valor": 0.9}], ingestao.id)
        upsert_fato_estado_mes([{**base, "uf": "PE", "valor": 0.8}], ingestao.id)
        db.session.commit()

        linhas_gravadas = FatoIndicadorEstadoMes.query.all()
        assert len(linhas_gravadas) == 2
        valores_por_uf = {linha.uf: float(linha.valor) for linha in linhas_gravadas}
        assert valores_por_uf == {"BA": 0.9, "PE": 0.8}
