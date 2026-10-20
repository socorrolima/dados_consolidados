import time
from datetime import date
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
    FatoIndicadorMunicipioMes,
)
from app.models.municipio import DimMunicipio
from app.models.usuario import PAPEL_ADMIN, DimUsuario, UsuarioMunicipio

USUARIO_ID = "11111111-1111-1111-1111-111111111111"


class _ChaveFalsa:
    def __init__(self, key):
        self.key = key


class _JwksClientFalso:
    def __init__(self, chave_publica):
        self._chave_publica = chave_publica

    def get_signing_key_from_jwt(self, token):
        return _ChaveFalsa(self._chave_publica)


def _gera_token(chave_privada, sub=USUARIO_ID):
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return jwt.encode(payload, chave_privada, algorithm="ES256")


def _autenticado(app, papel="gestor_municipal", municipio_ids=()):
    """Cria o par de chaves, o usuário em dim_usuario e devolve
    (headers_autenticados, patch_jwks) pronto pra usar num `with`.

    Recebe IDs (não objetos ORM): cada `with app.app_context()` tem sua
    própria sessão, e um objeto criado num bloco fica detached assim que
    esse bloco termina — passar só o ID evita depender da sessão de quem
    chamou.
    """
    chave_privada = ec.generate_private_key(ec.SECP256R1())
    chave_publica = chave_privada.public_key()
    token = _gera_token(chave_privada)

    with app.app_context():
        usuario = DimUsuario(
            id=USUARIO_ID, email="g@x.com", nome="Gestora", papel=papel
        )
        db.session.add(usuario)
        db.session.commit()
        for municipio_id in municipio_ids:
            db.session.add(
                UsuarioMunicipio(usuario_id=usuario.id, municipio_id=municipio_id)
            )
        db.session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    patch_jwks = patch(
        "app.services.auth_service._jwks_client",
        return_value=_JwksClientFalso(chave_publica),
    )
    return headers, patch_jwks


def _cria_municipio_id(codigo, nome, uf) -> int:
    municipio = DimMunicipio(codigo_ibge=codigo, nome=nome, uf=uf)
    db.session.add(municipio)
    db.session.commit()
    return municipio.id


def _cria_indicador_id(codigo, granularidade=GRANULARIDADE_MUNICIPIO_MES) -> int:
    indicador = DimIndicador(
        codigo=codigo,
        nome_exibicao="Teste",
        dataset_origem="teste",
        granularidade=granularidade,
        categoria="teste",
    )
    db.session.add(indicador)
    db.session.commit()
    return indicador.id


def test_dashboard_sem_token_retorna_401(client):
    resp = client.get("/api/dashboard/1?indicador=x&competencia=202509")
    assert resp.status_code == 401


def test_dashboard_sem_parametro_indicador_retorna_400(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?competencia=202509", headers=headers
        )

    assert resp.status_code == 400
    assert "indicador" in resp.get_json()["erro"]


def test_dashboard_competencia_malformada_retorna_400(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
        _cria_indicador_id("teste.x")
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?indicador=teste.x&competencia=2025-09",
            headers=headers,
        )

    assert resp.status_code == 400
    assert "competencia" in resp.get_json()["erro"]


def test_dashboard_indicador_inexistente_retorna_400(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?indicador=nao.existe&competencia=202509",
            headers=headers,
        )

    assert resp.status_code == 400


def test_dashboard_municipio_inexistente_retorna_404(app, client):
    with app.app_context():
        _cria_indicador_id("teste.x")
        admin = DimUsuario(
            id=USUARIO_ID, email="a@x.com", nome="Admin", papel=PAPEL_ADMIN
        )
        db.session.add(admin)
        db.session.commit()

    chave_privada = ec.generate_private_key(ec.SECP256R1())
    token = _gera_token(chave_privada)
    patch_jwks = patch(
        "app.services.auth_service._jwks_client",
        return_value=_JwksClientFalso(chave_privada.public_key()),
    )

    with patch_jwks:
        resp = client.get(
            "/api/dashboard/9999?indicador=teste.x&competencia=202509",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404


def test_dashboard_sem_acesso_ao_municipio_retorna_403(app, client):
    with app.app_context():
        meu_municipio_id = _cria_municipio_id("2900108", "A", "BA")
        municipio_alheio_id = _cria_municipio_id("2900207", "B", "BA")
        _cria_indicador_id("teste.x")
    headers, patch_jwks = _autenticado(app, municipio_ids=[meu_municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_alheio_id}?indicador=teste.x&competencia=202509",
            headers=headers,
        )

    assert resp.status_code == 403


def test_dashboard_sucesso_municipio_mes(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
        indicador_id = _cria_indicador_id("teste.x")
        db.session.add(
            FatoIndicadorMunicipioMes(
                municipio_id=municipio_id,
                indicador_id=indicador_id,
                competencia=date(2025, 9, 1),
                valor=100,
                fonte_hash="a" * 64,
            )
        )
        db.session.commit()
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?indicador=teste.x&competencia=202509",
            headers=headers,
        )

    assert resp.status_code == 200
    corpo = resp.get_json()
    assert corpo["indicador_codigo"] == "teste.x"
    assert corpo["competencia"] == "2025-09-01"
    assert corpo["valor_municipio"] == 100.0
    assert corpo["media_uf"] == 100.0


def test_dashboard_sem_dado_na_competencia_retorna_200_com_nulls(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
        _cria_indicador_id("teste.x")
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?indicador=teste.x&competencia=202509",
            headers=headers,
        )

    assert resp.status_code == 200
    corpo = resp.get_json()
    assert corpo["valor_municipio"] is None
    assert corpo["media_uf"] is None


def test_dashboard_estado_mes_nao_tem_valor_municipio(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
        _cria_indicador_id("teste.estado", GRANULARIDADE_ESTADO_MES)
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get(
            f"/api/dashboard/{municipio_id}?indicador=teste.estado&competencia=202509",
            headers=headers,
        )

    assert resp.status_code == 200
    corpo = resp.get_json()
    assert "valor_estado" in corpo
    assert "valor_municipio" not in corpo


def test_indicadores_sem_token_retorna_401(client):
    resp = client.get("/api/indicadores")
    assert resp.status_code == 401


def test_indicadores_lista_catalogo_ativo(app, client):
    with app.app_context():
        municipio_id = _cria_municipio_id("2900108", "A", "BA")
        _cria_indicador_id("teste.x")
    headers, patch_jwks = _autenticado(app, municipio_ids=[municipio_id])

    with patch_jwks:
        resp = client.get("/api/indicadores", headers=headers)

    assert resp.status_code == 200
    codigos = {item["codigo"] for item in resp.get_json()}
    assert "teste.x" in codigos
