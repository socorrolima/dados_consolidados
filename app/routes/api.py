from dataclasses import asdict

from flask import Blueprint, g, jsonify, request

from app.models.indicador import DimIndicador
from app.services import indicador_service
from app.services.auth_service import requer_autenticacao
from ingestion.normalizers import NormalizationError, normaliza_competencia

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


def _serializa_comparacao(comparacao) -> dict:
    """JSON não tem Decimal nem date — converte pra tipos nativos. `None`
    (fonte não reportou aquele mês) passa direto, não vira 0."""
    bruto = asdict(comparacao)
    bruto["competencia"] = comparacao.competencia.isoformat()
    for chave, valor in bruto.items():
        if valor is not None and chave != "competencia" and chave != "indicador_codigo":
            bruto[chave] = float(valor)
    return bruto


@api_bp.get("/dashboard/<int:municipio_id>")
@requer_autenticacao
def dashboard(municipio_id: int):
    """Comparação de um indicador pro município pedido: valor próprio vs
    médias (UF/piloto/Brasil, conforme a granularidade do indicador — ver
    app.services.indicador_service). `indicador` e `competencia` (AAAAMM)
    são obrigatórios na query string."""
    indicador_codigo = request.args.get("indicador")
    competencia_bruta = request.args.get("competencia")

    if not indicador_codigo:
        return jsonify(erro="parâmetro 'indicador' é obrigatório"), 400
    if not competencia_bruta:
        return jsonify(erro="parâmetro 'competencia' é obrigatório"), 400

    try:
        competencia = normaliza_competencia(competencia_bruta)
    except NormalizationError as exc:
        return jsonify(erro=f"'competencia' inválida: {exc}"), 400

    try:
        comparacao = indicador_service.comparar(
            g.usuario_atual, municipio_id, indicador_codigo, competencia
        )
    except indicador_service.MunicipioNaoEncontradoError as exc:
        return jsonify(erro=str(exc)), 404
    except indicador_service.IndicadorNaoEncontradoError as exc:
        return jsonify(erro=str(exc)), 400
    except indicador_service.ForbiddenError as exc:
        return jsonify(erro=str(exc)), 403
    except indicador_service.GranularidadeNaoSuportadaError as exc:
        return jsonify(erro=str(exc)), 501

    return jsonify(_serializa_comparacao(comparacao))


@api_bp.get("/indicadores")
@requer_autenticacao
def indicadores():
    """Catálogo de indicadores ativos — o front usa isso pra montar as
    abas/seletor do dashboard, sem precisar hardcodar código de indicador."""
    catalogo = (
        DimIndicador.query.filter_by(ativo=True).order_by(DimIndicador.categoria).all()
    )
    return jsonify(
        [
            {
                "codigo": i.codigo,
                "nome_exibicao": i.nome_exibicao,
                "categoria": i.categoria,
                "granularidade": i.granularidade,
                "unidade": i.unidade,
            }
            for i in catalogo
        ]
    )
