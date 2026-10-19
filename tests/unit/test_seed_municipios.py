import pytest

from scripts.seed_municipios import _ler_linhas


def _escreve_csv(tmp_path, conteudo):
    caminho = tmp_path / "municipios.csv"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_le_linhas_validas(tmp_path):
    caminho = _escreve_csv(
        tmp_path,
        "codigo_ibge,nome,uf\n2900108,Abaíra,BA\n2611101,Recife,PE\n2408102,Natal,RN\n",
    )

    linhas = _ler_linhas(caminho)

    assert len(linhas) == 3
    assert linhas[0] == {"codigo_ibge": "2900108", "nome": "Abaíra", "uf": "BA"}


def test_rejeita_codigo_ibge_com_tamanho_errado(tmp_path):
    caminho = _escreve_csv(tmp_path, "codigo_ibge,nome,uf\n290010,Abaíra,BA\n")

    with pytest.raises(ValueError, match="codigo_ibge inválido"):
        _ler_linhas(caminho)


def test_rejeita_nome_vazio(tmp_path):
    caminho = _escreve_csv(tmp_path, "codigo_ibge,nome,uf\n2900108,,BA\n")

    with pytest.raises(ValueError, match="nome vazio"):
        _ler_linhas(caminho)


def test_rejeita_uf_fora_do_piloto(tmp_path):
    caminho = _escreve_csv(tmp_path, "codigo_ibge,nome,uf\n3550308,São Paulo,SP\n")

    with pytest.raises(ValueError, match="fora do escopo do piloto"):
        _ler_linhas(caminho)


def test_rejeita_csv_vazio(tmp_path):
    caminho = _escreve_csv(tmp_path, "codigo_ibge,nome,uf\n")

    with pytest.raises(ValueError, match="está vazio"):
        _ler_linhas(caminho)
