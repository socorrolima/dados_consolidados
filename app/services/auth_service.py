"""Autenticação via Supabase Auth.

Valida o JWT recebido no header `Authorization: Bearer <token>` e resolve
o usuário de negócio correspondente em dim_usuario. O Supabase assina os
tokens com chaves assimétricas (JWKS) desde 2025 — padrão para projeto
novo, por isso é o único modo suportado aqui (não HS256/segredo
compartilhado). O backend verifica a assinatura com a chave pública
publicada em `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, sem nunca
guardar segredo de assinatura nem chamar a Supabase a cada request — só
a biblioteca de rede busca e cacheia as chaves públicas.

dim_usuario guarda o vínculo de negócio (papel, quais municípios o gestor
enxerga) que o próprio Supabase Auth não modela — um token válido sem
linha correspondente em dim_usuario é 403, não 401: a pessoa se autenticou,
mas ainda não foi cadastrada como gestora deste sistema.
"""

from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from jwt import PyJWKClient

from app.extensions import db
from app.models.usuario import DimUsuario

AUDIENCE_ESPERADA = "authenticated"
ALGORITMOS_PERMITIDOS = ["ES256", "RS256"]

_jwks_client_instance: PyJWKClient | None = None


class AuthenticationError(Exception):
    """Token ausente, malformado ou com assinatura/audience inválida."""


class UsuarioNaoCadastradoError(Exception):
    """Token válido, mas sem cadastro de negócio ativo em dim_usuario."""


def _jwks_url() -> str:
    supabase_url = current_app.config["SUPABASE_URL"]
    return f"{supabase_url}/auth/v1/.well-known/jwks.json"


def _jwks_client() -> PyJWKClient:
    global _jwks_client_instance
    if _jwks_client_instance is None:
        _jwks_client_instance = PyJWKClient(_jwks_url())
    return _jwks_client_instance


def _extrai_token(authorization_header: str | None) -> str:
    prefixo = "Bearer "
    if not authorization_header or not authorization_header.startswith(prefixo):
        raise AuthenticationError("header Authorization ausente ou sem 'Bearer '")
    return authorization_header[len(prefixo) :]


def resolver_usuario(token: str, jwks_client: PyJWKClient | None = None) -> DimUsuario:
    """Valida o JWT e retorna o DimUsuario correspondente ao claim 'sub'.

    `jwks_client` é injetável para testes (evita bater na rede real da
    Supabase); em produção o padrão busca/cacheia a chave pública real.
    """
    cliente = jwks_client or _jwks_client()

    try:
        chave_assinatura = cliente.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            chave_assinatura.key,
            algorithms=ALGORITMOS_PERMITIDOS,
            audience=AUDIENCE_ESPERADA,
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError(f"token inválido: {exc}") from exc

    usuario_id = payload.get("sub")
    if not usuario_id:
        raise AuthenticationError("token sem claim 'sub'")

    usuario = db.session.get(DimUsuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise UsuarioNaoCadastradoError(
            f"usuário {usuario_id!r} autenticado mas sem cadastro de negócio ativo"
        )

    return usuario


def requer_autenticacao(view):
    """Decorator de rota: exige um JWT Supabase válido e com cadastro em
    dim_usuario, disponibilizando o usuário resolvido em `flask.g.usuario_atual`."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            token = _extrai_token(request.headers.get("Authorization"))
            g.usuario_atual = resolver_usuario(token)
        except AuthenticationError as exc:
            return jsonify(erro=str(exc)), 401
        except UsuarioNaoCadastradoError as exc:
            return jsonify(erro=str(exc)), 403

        return view(*args, **kwargs)

    return wrapper
