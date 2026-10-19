"""Carrega o catálogo de indicadores (dim_indicador) confirmados na API SAGI.

Uso: python -m scripts.seed_indicadores

Nesta fase só catalogamos os campos do dataset SUASWEB ("misocial"), porque
foi o único cujo esquema completo de campos já confirmamos lendo a resposta
real da API (ver conversa de mapeamento do MDS). Os demais datasets (CNEAS,
Auxílio Gás, ADA, IGD-E, SIMPETI) só tiveram títulos de recurso confirmados,
não a lista completa de campos — serão catalogados quando o respectivo
módulo de ingestão for construído (Fase 3 do plano) e os campos exatos forem
reconfirmados contra a API, em vez de adivinhados aqui.
"""

import logging
import sys

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app import create_app
from app.extensions import db
from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
)

logger = logging.getLogger(__name__)

DATASET_MISOCIAL = "misocial"
UNIDADE_REAIS = "reais"

CATEGORIA_GESTAO_SUAS = "gestao_suas"
CATEGORIA_PROTECAO_BASICA = "protecao_social_basica"
CATEGORIA_PROTECAO_ESPECIAL = "protecao_social_especial"
CATEGORIA_BOLSA_FAMILIA_CADUNICO = "bolsa_familia_cadunico"
CATEGORIA_CRIANCA_FELIZ = "crianca_feliz"
CATEGORIA_AUXILIO_BRASIL = "auxilio_brasil"
CATEGORIA_GRUPO_PROGRAMAS = "grupo_programas"
CATEGORIA_SEM_CLASSIFICACAO = "sem_classificacao"
CATEGORIA_CONVENIO = "convenio"
CATEGORIA_PROCAD_SUAS = "procad_suas"
CATEGORIA_ACAO_CONTINUADA = "acao_continuada"

# (sufixo do campo sem o prefixo de escopo, nome de exibição, categoria)
_REPASSE_CAMPOS = [
    ("vl_gestao_suas_f", "Repasse para a Gestão do SUAS", CATEGORIA_GESTAO_SUAS),
    ("vl_psb_f", "Repasse para a Proteção Social Básica", CATEGORIA_PROTECAO_BASICA),
    (
        "vl_pse_alta_complexidade_f",
        "Repasse para a Proteção Social Especial de Alta Complexidade",
        CATEGORIA_PROTECAO_ESPECIAL,
    ),
    (
        "vl_pse_media_complexidade_f",
        "Repasse para a Proteção Social Especial de Média Complexidade",
        CATEGORIA_PROTECAO_ESPECIAL,
    ),
    (
        "vl_grupo_programas_f",
        "Repasse para Grupo de Programas",
        CATEGORIA_GRUPO_PROGRAMAS,
    ),
    (
        "vl_sem_classificacao_f",
        "Repasse sem classificação",
        CATEGORIA_SEM_CLASSIFICACAO,
    ),
    (
        "vl_fundo_a_fundo_f",
        "Transferências voluntárias Fundo a Fundo",
        CATEGORIA_GESTAO_SUAS,
    ),
    ("vl_total_fundo_f", "Valor total repassado via Fundo", CATEGORIA_GESTAO_SUAS),
    (
        "vl_gestao_pbf_cadun_f",
        "Repasse para a Gestão do Bolsa Família e do Cadastro Único",
        CATEGORIA_BOLSA_FAMILIA_CADUNICO,
    ),
    ("vl_pcf_f", "Repasse para Criança Feliz", CATEGORIA_CRIANCA_FELIZ),
    (
        "vl_gestao_pab_f",
        "Repasse para a Gestão do Programa Auxílio Brasil",
        CATEGORIA_AUXILIO_BRASIL,
    ),
    (
        "vl_pse_f",
        "Repasse para a Proteção Social Especial (Média e Alta Complexidade)",
        CATEGORIA_PROTECAO_ESPECIAL,
    ),
]

_SALDO_CC_MUNICIPAL_CAMPOS = [
    (
        "vl_bloco_gestao_pbf_cadun_f",
        "Saldo — Bloco da Gestão do Bolsa Família e do Cadastro Único",
        CATEGORIA_BOLSA_FAMILIA_CADUNICO,
    ),
    (
        "vl_bloco_gestao_suas_f",
        "Saldo — Bloco da Gestão do SUAS",
        CATEGORIA_GESTAO_SUAS,
    ),
    (
        "vl_bloco_psb_f",
        "Saldo — Bloco da Proteção Social Básica",
        CATEGORIA_PROTECAO_BASICA,
    ),
    (
        "vl_bloco_pse_media_complexidade_f",
        "Saldo — Bloco da Proteção Social Especial de Média Complexidade",
        CATEGORIA_PROTECAO_ESPECIAL,
    ),
    (
        "vl_bloco_pse_alta_complexidade_f",
        "Saldo — Bloco da Proteção Social Especial de Alta Complexidade",
        CATEGORIA_PROTECAO_ESPECIAL,
    ),
    ("vl_convenio_f", "Saldo — Convênio", CATEGORIA_CONVENIO),
    ("vl_gestao_f", "Saldo — Gestão", CATEGORIA_GESTAO_SUAS),
    ("vl_grupo_programas_f", "Saldo — Grupo de Programas", CATEGORIA_GRUPO_PROGRAMAS),
    ("vl_programas_f", "Saldo — Programas", CATEGORIA_GRUPO_PROGRAMAS),
    ("vl_psb_f", "Saldo — Proteção Social Básica", CATEGORIA_PROTECAO_BASICA),
    ("vl_pse_f", "Saldo — Proteção Social Especial", CATEGORIA_PROTECAO_ESPECIAL),
    (
        "vl_serv_acao_continuada_f",
        "Saldo — Serviço de Ação Continuada",
        CATEGORIA_ACAO_CONTINUADA,
    ),
    (
        "vl_total_geral_f",
        "Saldo total geral em conta corrente",
        CATEGORIA_GESTAO_SUAS,
    ),
    (
        "vl_pcf_f",
        "Saldo — Criança Feliz (parte do Grupo de Programas)",
        CATEGORIA_CRIANCA_FELIZ,
    ),
    (
        "vl_procad_suas_f",
        "Saldo — PROCAD-SUAS (parte do Grupo de Programas)",
        CATEGORIA_PROCAD_SUAS,
    ),
]


def _monta_catalogo() -> list[dict]:
    catalogo = []

    for sufixo, nome, categoria in _REPASSE_CAMPOS:
        catalogo.append(
            {
                "codigo": f"misocial.suas_repasse_mun_{sufixo}",
                "nome_exibicao": f"{nome} (repasse municipal — Fundo Municipal)",
                "dataset_origem": DATASET_MISOCIAL,
                "granularidade": GRANULARIDADE_MUNICIPIO_MES,
                "unidade": UNIDADE_REAIS,
                "categoria": categoria,
                "descricao": f"{nome}, via Fundo Municipal de Assistência Social (SUASWEB).",
            }
        )
        catalogo.append(
            {
                "codigo": f"misocial.suas_repasse_uf_{sufixo}",
                "nome_exibicao": f"{nome} (repasse estadual — Fundo Estadual)",
                "dataset_origem": DATASET_MISOCIAL,
                "granularidade": GRANULARIDADE_ESTADO_MES,
                "unidade": UNIDADE_REAIS,
                "categoria": categoria,
                "descricao": f"{nome}, via Fundo Estadual de Assistência Social (SUASWEB).",
            }
        )

    for sufixo, nome, categoria in _SALDO_CC_MUNICIPAL_CAMPOS:
        catalogo.append(
            {
                "codigo": f"misocial.suas_saldo_cc_mun_{sufixo}",
                "nome_exibicao": nome,
                "dataset_origem": DATASET_MISOCIAL,
                "granularidade": GRANULARIDADE_MUNICIPIO_MES,
                "unidade": UNIDADE_REAIS,
                "categoria": categoria,
                "descricao": f"{nome}, saldo em conta corrente SUAS (SUASWEB).",
            }
        )

    codigos = [item["codigo"] for item in catalogo]
    if len(codigos) != len(set(codigos)):
        raise ValueError(
            "códigos de indicador duplicados no catálogo — corrija antes de semear"
        )

    return catalogo


def seed_indicadores() -> int:
    catalogo = _monta_catalogo()

    dialeto = db.engine.dialect.name
    insert_fn = postgresql_insert if dialeto == "postgresql" else sqlite_insert

    stmt = insert_fn(DimIndicador).values(catalogo)
    stmt = stmt.on_conflict_do_update(
        index_elements=["codigo"],
        set_={
            "nome_exibicao": stmt.excluded.nome_exibicao,
            "dataset_origem": stmt.excluded.dataset_origem,
            "granularidade": stmt.excluded.granularidade,
            "unidade": stmt.excluded.unidade,
            "categoria": stmt.excluded.categoria,
            "descricao": stmt.excluded.descricao,
        },
    )
    db.session.execute(stmt)
    db.session.commit()

    logger.info("seed_indicadores: %d indicadores gravados/atualizados", len(catalogo))
    return len(catalogo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    with app.app_context():
        try:
            total = seed_indicadores()
        except Exception:
            logger.exception("Falha ao semear dim_indicador")
            sys.exit(1)
    print(f"{total} indicadores gravados/atualizados.")
