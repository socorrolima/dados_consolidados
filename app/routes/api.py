from flask import Blueprint, g, jsonify

from app.services.auth_service import requer_autenticacao

api_bp = Blueprint("api", __name__)


@api_bp.get("/saude")
def saude():
    return jsonify(status="ok")


@api_bp.get("/me")
@requer_autenticacao
def me():
    """Prova a autenticação de ponta a ponta: devolve o usuário resolvido
    do JWT e os municípios que ele pode ver. Útil pro frontend bootstrapar
    a sessão e pra verificar a configuração do Supabase em produção."""
    usuario = g.usuario_atual
    return jsonify(
        id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        papel=usuario.papel,
        municipios=[vinculo.municipio_id for vinculo in usuario.vinculos_municipio],
    )


# Endpoints JSON do dashboard (/api/dashboard/<municipio_id>) — Fase 6 (ver plano).
