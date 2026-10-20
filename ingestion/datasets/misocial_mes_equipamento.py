"""Ingestão agregada do CNEAS (misocial_mes_equipamento): contagem de entidades.

Diferente de misocial/misocial_mes_estado, aqui não copiamos um valor
reportado pela fonte: CONTAMOS quantas entidades CNEAS existem por
município/mês, porque o recurso real é um registro por entidade (CNPJ,
razão social, endereço, situação de cadastro) — decisão em
scripts/seed_indicadores.py de não guardar esse detalhe.

A contagem usa `facet.field` do Solr sobre `codigo_ibge`, com `rows=0`:
nunca buscamos nenhuma linha de entidade, só o total por município vindo
do próprio Solr. Isso evita qualquer campo de texto do recurso (nome,
endereço, situação de cadastro vêm com mojibake real do servidor) e evita
trazer CNPJ/endereço de terceiros que não precisamos guardar.
"""

import requests

from ingestion.sagi_client import BASE_URL, TIMEOUT_SEGUNDOS, IngestionFetchError

RECURSO = "misocial_mes_equipamento"
CODIGO_INDICADOR_QTD_ENTIDADES = f"{RECURSO}.cneas_qtd_entidades_cadastradas"


def contar_entidades_por_municipio(ufs: list[str], anomes_s: str) -> dict[str, int]:
    """Retorna {codigo_ibge da SAGI (6 dígitos): quantidade de entidades CNEAS}."""
    url = f"{BASE_URL}/{RECURSO}/"
    fq = [f"anomes_s:{anomes_s}", "sigla_uf:(" + " OR ".join(ufs) + ")"]
    params = {
        "q": "*:*",
        "fq": fq,
        "rows": 0,
        "facet": "true",
        "facet.field": "codigo_ibge",
        "facet.limit": -1,
        "facet.mincount": 1,
        "wt": "json",
    }

    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        pares_facet = resp.json()["facet_counts"]["facet_fields"]["codigo_ibge"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise IngestionFetchError(
            f"falha ao contar entidades CNEAS (fq={fq}): {exc}"
        ) from exc

    # facet_fields vem como lista achatada [valor1, contagem1, valor2, contagem2, ...]
    return dict(zip(pares_facet[0::2], pares_facet[1::2]))
