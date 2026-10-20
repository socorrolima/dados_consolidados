import pytest
import requests

from ingestion.datasets.misocial_mes_equipamento import contar_entidades_por_municipio
from ingestion.sagi_client import IngestionFetchError


class _RespostaFalsa:
    def __init__(self, json_data, status_ok=True):
        self._json_data = json_data
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.HTTPError("erro simulado")

    def json(self):
        return self._json_data


def test_contar_entidades_por_municipio_parseia_facet_fields(monkeypatch):
    resposta = _RespostaFalsa(
        {
            "facet_counts": {
                "facet_fields": {
                    "codigo_ibge": ["240010", 5, "260010", 12, "290010", 3],
                }
            }
        }
    )
    monkeypatch.setattr(requests, "get", lambda *a, **k: resposta)

    contagens = contar_entidades_por_municipio(["BA", "PE", "RN"], "202509")

    assert contagens == {"240010": 5, "260010": 12, "290010": 3}


def test_contar_entidades_por_municipio_sem_resultados(monkeypatch):
    resposta = _RespostaFalsa({"facet_counts": {"facet_fields": {"codigo_ibge": []}}})
    monkeypatch.setattr(requests, "get", lambda *a, **k: resposta)

    contagens = contar_entidades_por_municipio(["BA"], "202509")

    assert contagens == {}


def test_contar_entidades_por_municipio_propaga_erro_http(monkeypatch):
    resposta = _RespostaFalsa({}, status_ok=False)
    monkeypatch.setattr(requests, "get", lambda *a, **k: resposta)

    with pytest.raises(IngestionFetchError, match="falha ao contar entidades CNEAS"):
        contar_entidades_por_municipio(["BA"], "202509")
