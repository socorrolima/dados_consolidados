from app.models.indicador import GRANULARIDADES_VALIDAS
from scripts.seed_indicadores import _monta_catalogo


def test_catalogo_nao_tem_codigos_duplicados():
    catalogo = _monta_catalogo()
    codigos = [item["codigo"] for item in catalogo]

    assert len(codigos) == len(set(codigos))


def test_catalogo_so_usa_granularidades_validas():
    catalogo = _monta_catalogo()

    for item in catalogo:
        assert item["granularidade"] in GRANULARIDADES_VALIDAS


def test_catalogo_tem_repasses_municipais_e_estaduais_e_saldo():
    catalogo = _monta_catalogo()
    codigos = {item["codigo"] for item in catalogo}

    assert "misocial.suas_repasse_mun_vl_gestao_suas_f" in codigos
    assert "misocial.suas_repasse_uf_vl_gestao_suas_f" in codigos
    assert "misocial.suas_saldo_cc_mun_vl_total_geral_f" in codigos
    assert len(catalogo) == 12 + 12 + 15
