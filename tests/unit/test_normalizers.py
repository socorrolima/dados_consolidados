from datetime import date

import pytest

from ingestion.normalizers import (
    NormalizationError,
    normaliza_codigo_ibge_sagi,
    normaliza_competencia,
)


def test_normaliza_codigo_ibge_sagi_aceita_6_digitos():
    assert normaliza_codigo_ibge_sagi("240010") == "240010"


@pytest.mark.parametrize("invalido", ["24001", "2400100", "ABCDEF", "", None, 240010])
def test_normaliza_codigo_ibge_sagi_rejeita_formato_invalido(invalido):
    with pytest.raises(NormalizationError):
        normaliza_codigo_ibge_sagi(invalido)


def test_normaliza_competencia_converte_anomes_para_date():
    assert normaliza_competencia("202509") == date(2025, 9, 1)


@pytest.mark.parametrize("invalido", ["2025-09", "20259", "202513", "202500", "", None])
def test_normaliza_competencia_rejeita_formato_invalido(invalido):
    with pytest.raises(NormalizationError):
        normaliza_competencia(invalido)
