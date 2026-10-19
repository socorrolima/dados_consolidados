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
    assert "misocial_mes_estado.suas_repasse_uf_vl_gestao_suas_f" in codigos
    assert "misocial.suas_saldo_cc_mun_vl_total_geral_f" in codigos
    # misocial: 12 repasse_mun + 15 saldo_cc_mun
    # misocial_mes_estado: 12 repasse_uf + 39 igd-e (20 pbf + 19 pab) + 2 ada + 5 simpeti
    assert len(catalogo) == (12 + 15) + (12 + 39 + 2 + 5)


def test_catalogo_so_tem_dataset_origem_misocial_ou_misocial_mes_estado():
    catalogo = _monta_catalogo()

    for item in catalogo:
        assert item["dataset_origem"] in ("misocial", "misocial_mes_estado")
        if item["dataset_origem"] == "misocial_mes_estado":
            assert item["granularidade"] == "estado_mes"


def test_igde_pbf_tem_indice_gestao_descentralizada_mas_pab_nao():
    catalogo = _monta_catalogo()
    codigos = {item["codigo"] for item in catalogo}

    assert "misocial_mes_estado.igde_pbf_indice_gestao_descentralizada_d" in codigos
    assert "misocial_mes_estado.igde_pab_indice_gestao_descentralizada_d" not in codigos
