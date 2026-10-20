import time
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.extensions import db
from app.models.municipio import DimMunicipio
from app.models.usuario import DimUsuario, UsuarioMunicipio

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


def test_me_sem_token_retorna_401(client):
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_me_com_token_valido_retorna_usuario_e_municipios(app, client):
    chave_privada = ec.generate_private_key(ec.SECP256R1())
    chave_publica = chave_privada.public_key()
    token = _gera_token(chave_privada)

    with app.app_context():
        municipio = DimMunicipio(codigo_ibge="2927408", nome="Salvador", uf="BA")
        db.session.add(municipio)
        db.session.commit()
        municipio_id = municipio.id
        usuario = DimUsuario(
            id=USUARIO_ID, email="gestora@exemplo.gov.br", nome="Gestora"
        )
        db.session.add(usuario)
        db.session.commit()
        db.session.add(
            UsuarioMunicipio(usuario_id=usuario.id, municipio_id=municipio_id)
        )
        db.session.commit()

    with patch(
        "app.services.auth_service._jwks_client",
        return_value=_JwksClientFalso(chave_publica),
    ):
        resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    corpo = resp.get_json()
    assert corpo["id"] == USUARIO_ID
    assert corpo["email"] == "gestora@exemplo.gov.br"
    assert corpo["municipios"] == [{"id": municipio_id, "nome": "Salvador", "uf": "BA"}]


def test_me_com_token_de_usuario_nao_cadastrado_retorna_403(app, client):
    chave_privada = ec.generate_private_key(ec.SECP256R1())
    chave_publica = chave_privada.public_key()
    token = _gera_token(chave_privada, sub="22222222-2222-2222-2222-222222222222")

    with patch(
        "app.services.auth_service._jwks_client",
        return_value=_JwksClientFalso(chave_publica),
    ):
        resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
