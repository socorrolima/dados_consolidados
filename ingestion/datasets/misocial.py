"""Ingestão do recurso 'misocial' (SUASWEB), granularidade município/mês.

O catálogo de campos vem de dim_indicador (fonte única), não duplicado
aqui: cada código tem o formato 'misocial.<campo_sagi>' (ver
scripts/seed_indicadores.py), então o nome do campo real na API é só
remover o prefixo. Assim, adicionar um indicador novo deste mesmo recurso
é só inserir uma linha em dim_indicador — este módulo não muda.

Nunca pedimos o campo `municipio` (texto): a API devolve esse campo com
mojibake real no servidor para nomes acentuados — o nome do município
vem só de dim_municipio.
"""

from app.models.indicador import GRANULARIDADE_MUNICIPIO_MES, DimIndicador
from ingestion.sagi_client import buscar_documentos

RECURSO = "misocial"
PREFIXO_CODIGO = f"{RECURSO}."


def campo_sagi(indicador: DimIndicador) -> str:
    if not indicador.codigo.startswith(PREFIXO_CODIGO):
        raise ValueError(
            f"código de indicador fora do padrão '{PREFIXO_CODIGO}*': {indicador.codigo}"
        )
    return indicador.codigo[len(PREFIXO_CODIGO) :]


def indicadores_municipio_mes() -> list[DimIndicador]:
    return (
        DimIndicador.query.filter_by(
            dataset_origem=RECURSO,
            granularidade=GRANULARIDADE_MUNICIPIO_MES,
            ativo=True,
        )
        .order_by(DimIndicador.id)
        .all()
    )


def buscar_municipio_mes(
    ufs: list[str], anomes_s: str
) -> tuple[list[DimIndicador], list[dict]]:
    """Busca os documentos município/mês do SUASWEB para as UFs e competência dadas.

    `anomes_s` é uma competência exata (ex.: '202509'), não um wildcard —
    uma ingestão busca um mês por vez (ver run_ingestion.py para o CLI
    que itera sobre competências).
    """
    indicadores = indicadores_municipio_mes()
    if not indicadores:
        raise RuntimeError(
            "nenhum indicador ativo para misocial/municipio_mes em dim_indicador — "
            "rode scripts.seed_indicadores antes de ingerir"
        )

    campos = [campo_sagi(i) for i in indicadores]
    fl = ["codigo_ibge", "anomes_s", "sigla_uf"] + campos
    fq = [f"anomes_s:{anomes_s}", "sigla_uf:(" + " OR ".join(ufs) + ")"]

    docs = buscar_documentos(RECURSO, fl=fl, fq=fq)
    return indicadores, docs
