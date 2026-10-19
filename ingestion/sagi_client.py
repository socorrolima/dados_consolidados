"""Cliente HTTP para a API SAGI (Solr) do MDS.

Descobertas confirmadas contra a API real (não documentação, fizemos as
chamadas de verdade):
- `wt=json` devolve números nativos (float/int), nunca string com vírgula
  decimal BR — não precisamos de parser de número BR para esta API.
- Campos ausentes num documento significam "fonte não reportou este
  indicador neste mês" (Solr é esparso) — isso bate com o design de
  `valor` aceitar NULL no banco.
- Campos de texto com acento (ex.: `municipio`) vêm com mojibake real do
  servidor (não é artefato de browser) — por isso nunca pedimos esse campo;
  o nome do município vem só de dim_municipio (fonte única, sem esse bug).
"""

import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://aplicacoes.mds.gov.br/sagi/servicos"
TIMEOUT_SEGUNDOS = 30
TAMANHO_PAGINA = 2000


class IngestionFetchError(Exception):
    """Erro ao buscar dados da API SAGI — sempre com contexto (recurso, fq)."""


def buscar_documentos(recurso: str, fl: list[str], fq: list[str]) -> list[dict]:
    """Busca todos os documentos de um recurso SAGI, paginando por `start`."""
    url = f"{BASE_URL}/{recurso}/"
    documentos: list[dict] = []
    start = 0

    while True:
        params = {
            "q": "*:*",
            "fq": fq,
            "fl": ",".join(fl),
            "rows": TAMANHO_PAGINA,
            "start": start,
            "sort": "codigo_ibge asc",
            "wt": "json",
        }
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)
            resp.raise_for_status()
            corpo = resp.json()["response"]
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise IngestionFetchError(
                f"falha ao buscar '{recurso}' (start={start}, fq={fq}): {exc}"
            ) from exc

        documentos.extend(corpo["docs"])
        start += TAMANHO_PAGINA
        if start >= corpo["numFound"]:
            break

    logger.info(
        "buscar_documentos: %d documentos de '%s' (fq=%s)", len(documentos), recurso, fq
    )
    return documentos
