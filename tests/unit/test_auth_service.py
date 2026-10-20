import time
from dataclasses import dataclass

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.extensions import db
from app.models.usuario import DimUsuario
from app.services.auth_service import (
    AuthenticationError,
    UsuarioNaoCadastradoError,
    resolver_usuario,
)

USUARIO_ID = "11111111-1111-1111-1111-111111111111"


@dataclass
class _ChaveFalsa:
    key: object


class _JwksClientFalso:
    """Substitui PyJWKClient nos testes — nunca bate na rede real da Supabase."""

    def __init__(self, chave_publica):
        self._chave_publica = chave_publica

    def get_signing_key_from_jwt(self, token):
        return _ChaveFalsa(key=self._chave_publica)


@pytest.fixture
def par_de_chaves():
    chave_privada = ec.generate_private_key(ec.SECP256R1())
    return chave_privada, chave_privada.public_key()


def _gera_token(
    chave_privada, sub=USUARIO_ID, audience="authenticated", exp_delta=3600
):
    payload = {"sub": sub, "aud": audience, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, chave_privada, algorithm="ES256")


def test_resolver_usuario_com_token_valido_e_cadastro_ativo(app, par_de_chaves):
    chave_privada, chave_publica = par_de_chaves
    token = _gera_token(chave_privada)

    with app.app_context():
        db.session.add(
            DimUsuario(
                id=USUARIO_ID, email="gestora@exemplo.gov.br", nome="Gestora Teste"
            )
        )
        db.session.commit()

        usuario = resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))

        assert usuario.id == USUARIO_ID
        assert usuario.email == "gestora@exemplo.gov.br"


def test_resolver_usuario_rejeita_assinatura_de_outra_chave(app, par_de_chaves):
    _, chave_publica = par_de_chaves
    outra_chave_privada = ec.generate_private_key(ec.SECP256R1())
    token = _gera_token(outra_chave_privada)

    with app.app_context():
        with pytest.raises(AuthenticationError, match="token inválido"):
            resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))


def test_resolver_usuario_rejeita_audience_errada(app, par_de_chaves):
    chave_privada, chave_publica = par_de_chaves
    token = _gera_token(chave_privada, audience="outra-audience")

    with app.app_context():
        with pytest.raises(AuthenticationError, match="token inválido"):
            resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))


def test_resolver_usuario_rejeita_token_expirado(app, par_de_chaves):
    chave_privada, chave_publica = par_de_chaves
    token = _gera_token(chave_privada, exp_delta=-10)

    with app.app_context():
        with pytest.raises(AuthenticationError, match="token inválido"):
            resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))


def test_resolver_usuario_sem_cadastro_em_dim_usuario(app, par_de_chaves):
    chave_privada, chave_publica = par_de_chaves
    token = _gera_token(chave_privada, sub="22222222-2222-2222-2222-222222222222")

    with app.app_context():
        with pytest.raises(UsuarioNaoCadastradoError):
            resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))


def test_resolver_usuario_com_cadastro_inativo(app, par_de_chaves):
    chave_privada, chave_publica = par_de_chaves
    token = _gera_token(chave_privada)

    with app.app_context():
        db.session.add(
            DimUsuario(
                id=USUARIO_ID,
                email="inativa@exemplo.gov.br",
                nome="Inativa",
                ativo=False,
            )
        )
        db.session.commit()

        with pytest.raises(UsuarioNaoCadastradoError):
            resolver_usuario(token, jwks_client=_JwksClientFalso(chave_publica))
