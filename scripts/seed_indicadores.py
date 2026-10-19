"""Carrega o catálogo de indicadores (dim_indicador) confirmados na API SAGI.

Uso: python -m scripts.seed_indicadores

Catalogamos aqui os campos de dois recursos cujo esquema completo já
confirmamos lendo a resposta real da API:
- "misocial" (SUASWEB): repasse e saldo municipais.
- "misocial_mes_estado": repasse estadual, IGD-E (PBF/PAB), ADA (totais) e
  SIMPETI por estado.

Descoberta da Fase 3: o repasse estadual do SUASWEB ("suas_repasse_uf_*")
não vem pelo mesmo recurso "misocial" do repasse municipal — vem por
"misocial_mes_estado", junto com IGD-E/ADA/SIMPETI. Por isso
dataset_origem desses campos é "misocial_mes_estado", não "misocial".

O recurso "misocial_mes_estado" real também expõe dezenas de outros
campos (Academia do Futebol, Alimenta Brasil, Brasil Fraterno, Auxílio
Gás, CEBAS, insegurança alimentar) e o ADA tem variantes por tipo de
família (indígena, quilombola, ribeirinha etc.), não só os totais — fora
do escopo aprovado para esta fase, ficam para quando houver demanda.

CNEAS (entidades socioassistenciais) não é catalogado aqui: descobrimos
que é um registro por entidade (CNPJ, razão social, endereço), não um
indicador agregado — não cabe no modelo fato/dimensão atual sem uma
decisão de schema à parte.
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
DATASET_MISOCIAL_MES_ESTADO = "misocial_mes_estado"
UNIDADE_REAIS = "reais"
UNIDADE_UNIDADES = "unidades"
UNIDADE_INDICE = "indice"
UNIDADE_PERCENTUAL = "percentual"
UNIDADE_KG = "kg"

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
CATEGORIA_IGD_E = "igd_e"
CATEGORIA_ACAO_DISTRIBUICAO_ALIMENTOS = "acao_distribuicao_alimentos"
CATEGORIA_PETI = "peti"

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


# Campos comuns às duas variantes do IGD-E (PBF e PAB), confirmados contra a
# API real. Definições de TAAS/TAC/TAFE conforme a Portaria MDS nº 1.041/2024
# (IGD-E/IGD-M): TAC tem peso 50%, TAAS e TAFE têm peso 25% cada. O índice
# final (indice_gestao_descentralizada_d) varia de 0 a 1, mas as taxas e o
# fator_calculo_1 em si vêm da API em escala percentual (0-100) — confirmado
# contra dado real: fator_calculo_1_d bate com indice_gestao_descentralizada_d
# * 100. Só fator_redutor_d (um multiplicador de penalidade, ex. 0.8) vem
# mesmo em 0-1.
_IGDE_CAMPOS_COMUNS = [
    (
        "taas_d",
        "Taxa de Acompanhamento da Agenda de Saúde (TAAS)",
        UNIDADE_PERCENTUAL,
    ),
    ("tac_d", "Taxa de Atualização Cadastral (TAC)", UNIDADE_PERCENTUAL),
    (
        "tafe_d",
        "Taxa de Acompanhamento da Frequência Escolar (TAFE)",
        UNIDADE_PERCENTUAL,
    ),
    ("fator_calculo_1_d", "Fator de cálculo 1", UNIDADE_PERCENTUAL),
    ("fator_redutor_d", "Fator redutor", UNIDADE_INDICE),
    ("vlr_teto_mensal_repasse_d", "Teto mensal de repasse", UNIDADE_REAIS),
    ("vlr_sem_incentivos_d", "Valor sem incentivos", UNIDADE_REAIS),
    ("vlr_incentivo_1_d", "Valor do incentivo 1", UNIDADE_REAIS),
    ("vlr_incentivo_2_d", "Valor do incentivo 2", UNIDADE_REAIS),
    ("vlr_incentivo_3_d", "Valor do incentivo 3", UNIDADE_REAIS),
    ("vlr_total_incentivos_d", "Valor total dos incentivos", UNIDADE_REAIS),
    (
        "vlr_repasse_com_incentivos_d",
        "Valor do repasse com incentivos",
        UNIDADE_REAIS,
    ),
    ("vlr_repassado_d", "Valor efetivamente repassado", UNIDADE_REAIS),
    (
        "qtde_pessoas_acomp_escolar_l",
        "Quantidade de pessoas acompanhadas (frequência escolar)",
        UNIDADE_UNIDADES,
    ),
    (
        "qtde_criancas_adolescentes_l",
        "Quantidade de crianças e adolescentes no público-alvo",
        UNIDADE_UNIDADES,
    ),
    (
        "qtde_familias_perfil_cadunico_inscritas_l",
        "Quantidade de famílias com perfil no Cadastro Único inscritas",
        UNIDADE_UNIDADES,
    ),
    (
        "qtde_atualizacoes_perfil_cadunico_l",
        "Quantidade de atualizações cadastrais no Cadastro Único",
        UNIDADE_UNIDADES,
    ),
    (
        "qtde_publico_com_cond_saude_informada_l",
        "Quantidade do público com condicionalidade de saúde informada",
        UNIDADE_UNIDADES,
    ),
    (
        "qtde_publico_perfil_saude_l",
        "Quantidade do público com perfil saúde",
        UNIDADE_UNIDADES,
    ),
]

# Campo exclusivo do IGD-E PBF — não existe para PAB no esquema real.
_IGDE_PBF_CAMPO_EXCLUSIVO = (
    "indice_gestao_descentralizada_d",
    "Índice de Gestão Descentralizada (IGD-E)",
    UNIDADE_INDICE,
)

_ADA_CAMPOS = [
    (
        "qtde_total_cestas_alimentos_entregues_d",
        "Quantidade total de cestas de alimentos entregues",
        UNIDADE_UNIDADES,
    ),
    (
        "total_kg_alimentos_entregues_d",
        "Total de quilos de alimentos entregues",
        UNIDADE_KG,
    ),
]

# Eixos do PETI conforme Resolução CNAS nº 8/2013.
_SIMPETI_EIXOS = [
    ("01", "Identificação"),
    ("02", "Informação e Mobilização"),
    ("03", "Proteção Social"),
    ("04", "Defesa e Responsabilização"),
    ("05", "Monitoramento"),
]


def _monta_catalogo_estado_mes() -> list[dict]:
    catalogo = []

    for programa, nome_programa in (("pbf", "IGD-E PBF"), ("pab", "IGD-E PAB")):
        campos = list(_IGDE_CAMPOS_COMUNS)
        if programa == "pbf":
            campos.append(_IGDE_PBF_CAMPO_EXCLUSIVO)
        for sufixo, nome, unidade in campos:
            catalogo.append(
                {
                    "codigo": f"misocial_mes_estado.igde_{programa}_{sufixo}",
                    "nome_exibicao": f"{nome_programa} — {nome}",
                    "dataset_origem": DATASET_MISOCIAL_MES_ESTADO,
                    "granularidade": GRANULARIDADE_ESTADO_MES,
                    "unidade": unidade,
                    "categoria": CATEGORIA_IGD_E,
                    "descricao": f"{nome_programa}: {nome}.",
                }
            )

    for sufixo, nome, unidade in _ADA_CAMPOS:
        catalogo.append(
            {
                "codigo": f"misocial_mes_estado.ada_{sufixo}",
                "nome_exibicao": f"ADA — {nome}",
                "dataset_origem": DATASET_MISOCIAL_MES_ESTADO,
                "granularidade": GRANULARIDADE_ESTADO_MES,
                "unidade": unidade,
                "categoria": CATEGORIA_ACAO_DISTRIBUICAO_ALIMENTOS,
                "descricao": f"Ação de Distribuição de Alimentos (ADA): {nome}.",
            }
        )

    for numero, nome_eixo in _SIMPETI_EIXOS:
        catalogo.append(
            {
                "codigo": f"misocial_mes_estado.simpeti_qtd_acoes_eixo_{numero}_uf_l",
                "nome_exibicao": f"PETI — Ações do Eixo {int(numero)} ({nome_eixo})",
                "dataset_origem": DATASET_MISOCIAL_MES_ESTADO,
                "granularidade": GRANULARIDADE_ESTADO_MES,
                "unidade": UNIDADE_UNIDADES,
                "categoria": CATEGORIA_PETI,
                "descricao": (
                    f"Quantidade de ações estratégicas do PETI no eixo "
                    f"'{nome_eixo}', por estado (Resolução CNAS nº 8/2013)."
                ),
            }
        )

    return catalogo


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
                "codigo": f"misocial_mes_estado.suas_repasse_uf_{sufixo}",
                "nome_exibicao": f"{nome} (repasse estadual — Fundo Estadual)",
                "dataset_origem": DATASET_MISOCIAL_MES_ESTADO,
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

    catalogo.extend(_monta_catalogo_estado_mes())

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
