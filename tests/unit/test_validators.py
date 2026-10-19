from datetime import date

import pytest

from ingestion.validators import ValidationError, valida_doc_municipio_mes

INDICADOR_ID_POR_CAMPO = {
    "suas_repasse_mun_vl_gestao_suas_f": 1,
    "suas_repasse_mun_vl_psb_f": 2,
}
MUNICIPIO_ID_POR_CODIGO6 = {"240010": 99}


def test_doc_valido_vira_uma_linha_por_campo_presente():
    doc = {
        "codigo_ibge": "240010",
        "anomes_s": "202509",
        "sigla_uf": "RN",
        "suas_repasse_mun_vl_gestao_suas_f": 0.0,
        "suas_repasse_mun_vl_psb_f": 10256.83,
    }

    resultado = valida_doc_municipio_mes(
        doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6
    )

    assert len(resultado.linhas) == 2
    assert resultado.avisos == []
    linha_psb = next(linha for linha in resultado.linhas if linha["indicador_id"] == 2)
    assert linha_psb == {
        "municipio_id": 99,
        "indicador_id": 2,
        "competencia": date(2025, 9, 1),
        "valor": 10256.83,
        "fonte_hash": linha_psb["fonte_hash"],
    }
    assert len(linha_psb["fonte_hash"]) == 64


def test_campo_ausente_no_doc_nao_gera_linha_nem_aviso():
    doc = {
        "codigo_ibge": "240010",
        "anomes_s": "202509",
        "suas_repasse_mun_vl_gestao_suas_f": 0.0,
        # suas_repasse_mun_vl_psb_f ausente — fonte não reportou, não é erro
    }

    resultado = valida_doc_municipio_mes(
        doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6
    )

    assert len(resultado.linhas) == 1
    assert resultado.avisos == []


def test_valor_nao_numerico_e_descartado_com_aviso_sem_rejeitar_documento():
    doc = {
        "codigo_ibge": "240010",
        "anomes_s": "202509",
        "suas_repasse_mun_vl_gestao_suas_f": "indisponível",
        "suas_repasse_mun_vl_psb_f": 10256.83,
    }

    resultado = valida_doc_municipio_mes(
        doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6
    )

    assert len(resultado.linhas) == 1
    assert resultado.linhas[0]["indicador_id"] == 2
    assert len(resultado.avisos) == 1
    assert "não numérico" in resultado.avisos[0]


def test_valor_negativo_gera_aviso_mas_nao_e_descartado():
    doc = {
        "codigo_ibge": "240010",
        "anomes_s": "202509",
        "suas_repasse_mun_vl_gestao_suas_f": -100.0,
    }

    resultado = valida_doc_municipio_mes(
        doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6
    )

    assert len(resultado.linhas) == 1
    assert resultado.linhas[0]["valor"] == -100.0
    assert any("negativo" in aviso for aviso in resultado.avisos)


def test_codigo_ibge_invalido_rejeita_documento_inteiro():
    doc = {"codigo_ibge": "24001", "anomes_s": "202509"}

    with pytest.raises(ValidationError, match="documento rejeitado"):
        valida_doc_municipio_mes(doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6)


def test_municipio_fora_do_escopo_rejeita_documento_inteiro():
    doc = {"codigo_ibge": "999999", "anomes_s": "202509"}

    with pytest.raises(ValidationError, match="fora do escopo"):
        valida_doc_municipio_mes(doc, INDICADOR_ID_POR_CAMPO, MUNICIPIO_ID_POR_CODIGO6)
