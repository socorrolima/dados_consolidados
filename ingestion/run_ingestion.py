"""CLI de ingestão — chamado manualmente ou pelo GitHub Actions (ingest.yml).

Uso:
    python -m ingestion.run_ingestion --dataset misocial --uf BA,PE,RN --competencia latest
    python -m ingestion.run_ingestion --dataset misocial_mes_estado --uf BA,PE,RN --competencia 202509

Qualquer exceção não tratada propaga e termina o processo com exit code != 0
— isso é o que faz o job falhar visivelmente no GitHub Actions, em vez de
mascarar um erro de ingestão como sucesso.
"""

import argparse
import logging
import sys
from datetime import date, datetime, timezone

from app import create_app
from app.extensions import db
from app.models.indicador import DimIndicador
from app.models.ingestao import (
    STATUS_FALHOU,
    STATUS_SUCESSO,
    IngestaoExecucao,
)
from app.models.municipio import DimMunicipio
from ingestion.datasets.misocial import buscar_municipio_mes
from ingestion.datasets.misocial import campo_sagi as campo_sagi_misocial
from ingestion.datasets.misocial_mes_equipamento import (
    CODIGO_INDICADOR_QTD_ENTIDADES,
    contar_entidades_por_municipio,
)
from ingestion.datasets.misocial_mes_estado import buscar_estado_mes
from ingestion.datasets.misocial_mes_estado import campo_sagi as campo_sagi_estado
from ingestion.loader import upsert_fato_estado_mes, upsert_fato_municipio_mes
from ingestion.sagi_client import IngestionFetchError
from ingestion.validators import (
    ValidationError,
    valida_doc_estado_mes,
    valida_doc_municipio_mes,
)

logger = logging.getLogger(__name__)

LIMIAR_REJEICAO = 0.05  # acima disso, a ingestão inteira é marcada como falha


def _competencia_atual() -> str:
    hoje = date.today()
    return f"{hoje.year:04d}{hoje.month:02d}"


def _mapa_municipio_por_codigo6() -> dict[str, int]:
    return {m.codigo_ibge[:6]: m.id for m in DimMunicipio.query.all()}


def _processar_documentos(docs: list[dict], validar) -> tuple[list[dict], int]:
    """Valida cada documento (função `validar(doc) -> ResultadoValidacao`),
    agregando linhas e contando rejeições. Avisos são sempre logados, nunca
    silenciados; um documento rejeitado não derruba o lote inteiro (ver
    checagem de taxa de rejeição em `_ingerir`)."""
    linhas: list[dict] = []
    rejeitadas = 0

    for doc in docs:
        try:
            resultado = validar(doc)
        except ValidationError as exc:
            logger.warning("documento rejeitado: %s", exc)
            rejeitadas += 1
            continue

        for aviso in resultado.avisos:
            logger.warning(aviso)
        linhas.extend(resultado.linhas)

    return linhas, rejeitadas


def _ingerir(
    docs: list[dict],
    validar,
    gravar,
    ingestao: IngestaoExecucao,
) -> None:
    linhas, rejeitadas = _processar_documentos(docs, validar)

    total_docs = len(docs)
    taxa_rejeicao = (rejeitadas / total_docs) if total_docs else 0.0
    if taxa_rejeicao > LIMIAR_REJEICAO:
        raise RuntimeError(
            f"taxa de rejeição {taxa_rejeicao:.1%} acima do limiar de {LIMIAR_REJEICAO:.0%} "
            f"({rejeitadas}/{total_docs} documentos) — abortando sem gravar"
        )

    gravadas = gravar(linhas, ingestao.id)

    ingestao.linhas_lidas = total_docs
    ingestao.linhas_gravadas = gravadas
    ingestao.linhas_rejeitadas = rejeitadas


def _ingerir_misocial(
    ufs: list[str], anomes_s: str, ingestao: IngestaoExecucao
) -> None:
    indicadores, docs = buscar_municipio_mes(ufs, anomes_s)
    indicador_id_por_campo = {campo_sagi_misocial(i): i.id for i in indicadores}
    municipio_por_codigo6 = _mapa_municipio_por_codigo6()

    def validar(doc):
        return valida_doc_municipio_mes(
            doc, indicador_id_por_campo, municipio_por_codigo6
        )

    _ingerir(docs, validar, upsert_fato_municipio_mes, ingestao)


def _ingerir_misocial_mes_estado(
    ufs: list[str], anomes_s: str, ingestao: IngestaoExecucao
) -> None:
    indicadores, docs = buscar_estado_mes(ufs, anomes_s)
    indicador_id_por_campo = {campo_sagi_estado(i): i.id for i in indicadores}
    ufs_validas = set(ufs)

    def validar(doc):
        return valida_doc_estado_mes(doc, indicador_id_por_campo, ufs_validas)

    _ingerir(docs, validar, upsert_fato_estado_mes, ingestao)


def _ingerir_misocial_mes_equipamento(
    ufs: list[str], anomes_s: str, ingestao: IngestaoExecucao
) -> None:
    """CNEAS: contagem de entidades por município/mês (ver docstring do
    módulo ingestion.datasets.misocial_mes_equipamento). Reaproveita
    valida_doc_municipio_mes montando "documentos" sintéticos com a
    contagem já calculada via facet, em vez de linhas brutas da API."""
    indicador = DimIndicador.query.filter_by(
        codigo=CODIGO_INDICADOR_QTD_ENTIDADES
    ).first()
    if indicador is None:
        raise RuntimeError(
            f"indicador {CODIGO_INDICADOR_QTD_ENTIDADES!r} não cadastrado em "
            "dim_indicador — rode scripts.seed_indicadores antes de ingerir"
        )

    contagens = contar_entidades_por_municipio(ufs, anomes_s)
    docs = [
        {"codigo_ibge": codigo6, "anomes_s": anomes_s, "qtd_entidades": contagem}
        for codigo6, contagem in contagens.items()
    ]
    indicador_id_por_campo = {"qtd_entidades": indicador.id}
    municipio_por_codigo6 = _mapa_municipio_por_codigo6()

    def validar(doc):
        return valida_doc_municipio_mes(
            doc, indicador_id_por_campo, municipio_por_codigo6
        )

    _ingerir(docs, validar, upsert_fato_municipio_mes, ingestao)


_DATASETS = {
    "misocial": _ingerir_misocial,
    "misocial_mes_estado": _ingerir_misocial_mes_estado,
    "misocial_mes_equipamento": _ingerir_misocial_mes_equipamento,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=sorted(_DATASETS))
    parser.add_argument("--uf", required=True, help="Ex.: BA,PE,RN")
    parser.add_argument("--competencia", required=True, help="AAAAMM ou 'latest'")
    args = parser.parse_args()

    ufs = [uf.strip().upper() for uf in args.uf.split(",") if uf.strip()]
    anomes_s = (
        _competencia_atual() if args.competencia == "latest" else args.competencia
    )

    app = create_app()
    with app.app_context():
        ingestao = IngestaoExecucao(
            dataset_origem=args.dataset,
            parametros=f"uf={ufs} competencia={anomes_s}",
        )
        db.session.add(ingestao)
        db.session.commit()

        try:
            _DATASETS[args.dataset](ufs, anomes_s, ingestao)
        except (IngestionFetchError, RuntimeError) as exc:
            logger.exception("ingestão falhou (execucao_id=%s)", ingestao.id)
            db.session.rollback()
            ingestao.status = STATUS_FALHOU
            ingestao.erro_detalhe = str(exc)
            ingestao.finalizado_em = datetime.now(timezone.utc)
            db.session.commit()
            sys.exit(1)

        ingestao.status = STATUS_SUCESSO
        ingestao.finalizado_em = datetime.now(timezone.utc)
        db.session.commit()

        # Captura os valores antes de sair do app_context — fora dele a
        # sessão é encerrada e o objeto fica detached (atributos expirados
        # pelo commit não podem mais ser recarregados).
        resumo = (
            f"ingestão concluída: dataset={args.dataset} competencia={anomes_s} "
            f"lidas={ingestao.linhas_lidas} gravadas={ingestao.linhas_gravadas} "
            f"rejeitadas={ingestao.linhas_rejeitadas}"
        )

    print(resumo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
