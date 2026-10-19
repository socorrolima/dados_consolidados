"""Ingestão do recurso 'misocial_mes_estado', granularidade estado/mês.

Cobre: repasse estadual do SUASWEB, IGD-E (PBF/PAB), ADA (totais) e SIMPETI
por estado — ver scripts/seed_indicadores.py para o catálogo completo e o
que ficou fora do escopo desta fase.

`codigo_ibge` aqui é o código de 2 dígitos da UF (ex.: '29' para BA), não o
código de município — por isso usamos `sigla_uf` (sempre ASCII, sem
acento) como chave, sem precisar de nenhuma tabela de mapeamento. O campo
`tipo_s` discrimina o tipo de documento dentro da coleção compartilhada do
Solr; filtramos por ele para nunca misturar com outro tipo de documento
que por acaso tenha o mesmo sigla_uf.
"""

from app.models.indicador import GRANULARIDADE_ESTADO_MES, DimIndicador
from ingestion.sagi_client import buscar_documentos

RECURSO = "misocial_mes_estado"
PREFIXO_CODIGO = f"{RECURSO}."
TIPO_DOCUMENTO = "mes_estado"


def campo_sagi(indicador: DimIndicador) -> str:
    if not indicador.codigo.startswith(PREFIXO_CODIGO):
        raise ValueError(
            f"código de indicador fora do padrão '{PREFIXO_CODIGO}*': {indicador.codigo}"
        )
    return indicador.codigo[len(PREFIXO_CODIGO) :]


def indicadores_estado_mes() -> list[DimIndicador]:
    return (
        DimIndicador.query.filter_by(
            dataset_origem=RECURSO, granularidade=GRANULARIDADE_ESTADO_MES, ativo=True
        )
        .order_by(DimIndicador.id)
        .all()
    )


def buscar_estado_mes(
    ufs: list[str], anomes_s: str
) -> tuple[list[DimIndicador], list[dict]]:
    indicadores = indicadores_estado_mes()
    if not indicadores:
        raise RuntimeError(
            "nenhum indicador ativo para misocial_mes_estado em dim_indicador — "
            "rode scripts.seed_indicadores antes de ingerir"
        )

    campos = [campo_sagi(i) for i in indicadores]
    fl = ["sigla_uf", "anomes_s"] + campos
    fq = [
        f"anomes_s:{anomes_s}",
        f"tipo_s:{TIPO_DOCUMENTO}",
        "sigla_uf:(" + " OR ".join(ufs) + ")",
    ]

    docs = buscar_documentos(RECURSO, fl=fl, fq=fq)
    return indicadores, docs
