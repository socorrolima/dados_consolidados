from datetime import date

import pytest

from ingestion.validators import ValidationError, valida_doc_estado_mes

INDICADOR_ID_POR_CAMPO = {
    "suas_repasse_uf_vl_gestao_suas_f": 1,
    "igde_pbf_tac_d": 2,
}
UFS_VALIDAS = {"BA", "PE", "RN"}


def test_doc_valido_vira_uma_linha_por_campo_presente():
    doc = {
        "sigla_uf": "BA",
        "anomes_s": "202509",
        "suas_repasse_uf_vl_gestao_suas_f": 0.0,
        "igde_pbf_tac_d": 0.95,
    }

    resultado = valida_doc_estado_mes(doc, INDICADOR_ID_POR_CAMPO, UFS_VALIDAS)

    assert len(resultado.linhas) == 2
    assert resultado.avisos == []
    linha_tac = next(linha for linha in resultado.linhas if linha["indicador_id"] == 2)
    assert linha_tac["uf"] == "BA"
    assert linha_tac["competencia"] == date(2025, 9, 1)
    assert linha_tac["valor"] == 0.95


def test_uf_fora_do_escopo_rejeita_documento():
    doc = {"sigla_uf": "SP", "anomes_s": "202509"}

    with pytest.raises(ValidationError, match="fora do escopo"):
        valida_doc_estado_mes(doc, INDICADOR_ID_POR_CAMPO, UFS_VALIDAS)


def test_sigla_uf_ausente_rejeita_documento():
    doc = {"anomes_s": "202509"}

    with pytest.raises(ValidationError, match="fora do escopo"):
        valida_doc_estado_mes(doc, INDICADOR_ID_POR_CAMPO, UFS_VALIDAS)


def test_competencia_invalida_rejeita_documento():
    doc = {"sigla_uf": "BA", "anomes_s": "2025-09"}

    with pytest.raises(ValidationError, match="documento rejeitado"):
        valida_doc_estado_mes(doc, INDICADOR_ID_POR_CAMPO, UFS_VALIDAS)


def test_campo_ausente_nao_gera_linha_nem_aviso():
    doc = {
        "sigla_uf": "PE",
        "anomes_s": "202509",
        "suas_repasse_uf_vl_gestao_suas_f": 100.0,
    }

    resultado = valida_doc_estado_mes(doc, INDICADOR_ID_POR_CAMPO, UFS_VALIDAS)

    assert len(resultado.linhas) == 1
    assert resultado.avisos == []
