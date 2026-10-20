"""Monta a comparação de um indicador para o dashboard: município vs médias.

A forma da comparação depende da granularidade do indicador — não dá pra
usar um DTO único sem mentir sobre o que existe:
- municipio_mes (SUASWEB, CNEAS): só temos BA/PE/RN a nível de município
  (não o Brasil inteiro), então a comparação é município vs média da UF
  vs média do piloto (BA+PE+RN) — nunca "média Brasil", que exigiria
  ingerir município de todo o país.
- estado_mes (repasse UF, IGD-E, ADA, SIMPETI): ingerimos as 27 UFs desde
  a Fase 3, então aqui SIM dá pra comparar com a média do piloto e com o
  Brasil inteiro — mas não existe "valor de município", o dado já é por UF.

Autorização por município é responsabilidade desta camada, não da rota:
admin vê qualquer município; gestor_municipal só vê os municípios
vinculados em dim_usuario/usuario_municipio. Agregados (médias) nunca
expõem dado de município individual fora do que o usuário tem acesso —
mas a própria média da UF/piloto/Brasil é estatística agregada, não dado
de município, e por isso não passa por essa checagem.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.indicador import (
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_MES,
    DimIndicador,
)
from app.models.municipio import DimMunicipio
from app.models.usuario import PAPEL_ADMIN, DimUsuario
from app.repositories import indicador_repository, municipio_repository

UFS_PILOTO = ("BA", "PE", "RN")
UFS_BRASIL = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
)  # fmt: skip


class ForbiddenError(Exception):
    """Usuário autenticado, mas sem acesso a este município."""


class IndicadorNaoEncontradoError(Exception):
    """Código de indicador não existe em dim_indicador."""


class MunicipioNaoEncontradoError(Exception):
    """municipio_id não existe em dim_municipio."""


class GranularidadeNaoSuportadaError(Exception):
    """Granularidade sem comparação implementada (ex.: municipio_ano, sem
    nenhum indicador cadastrado hoje — ver scripts/seed_indicadores.py)."""


@dataclass
class ComparacaoMunicipioMes:
    indicador_codigo: str
    competencia: date
    valor_municipio: Decimal | None
    media_uf: Decimal | None
    media_piloto: Decimal | None


@dataclass
class ComparacaoEstadoMes:
    indicador_codigo: str
    competencia: date
    valor_estado: Decimal | None
    media_piloto: Decimal | None
    media_brasil: Decimal | None


def _checa_acesso_ao_municipio(usuario: DimUsuario, municipio_id: int) -> None:
    if usuario.papel == PAPEL_ADMIN:
        return

    municipios_permitidos = {v.municipio_id for v in usuario.vinculos_municipio}
    if municipio_id not in municipios_permitidos:
        raise ForbiddenError(
            f"usuário {usuario.id!r} não tem acesso ao município {municipio_id!r}"
        )


def _resolve_indicador(indicador_codigo: str) -> DimIndicador:
    indicador = DimIndicador.query.filter_by(
        codigo=indicador_codigo, ativo=True
    ).first()
    if indicador is None:
        raise IndicadorNaoEncontradoError(
            f"indicador {indicador_codigo!r} não encontrado"
        )
    return indicador


def _comparar_municipio_mes(
    usuario: DimUsuario,
    municipio: DimMunicipio,
    indicador: DimIndicador,
    competencia: date,
) -> ComparacaoMunicipioMes:
    _checa_acesso_ao_municipio(usuario, municipio.id)

    valor = indicador_repository.valor_municipio(
        municipio.id, indicador.id, competencia
    )
    media_uf = indicador_repository.media_municipios(
        municipio_repository.ids_municipios_da_uf(municipio.uf),
        indicador.id,
        competencia,
    )
    media_piloto = indicador_repository.media_municipios(
        municipio_repository.ids_municipios_do_piloto(), indicador.id, competencia
    )

    return ComparacaoMunicipioMes(
        indicador_codigo=indicador.codigo,
        competencia=competencia,
        valor_municipio=valor,
        media_uf=media_uf,
        media_piloto=media_piloto,
    )


def _comparar_estado_mes(
    municipio: DimMunicipio, indicador: DimIndicador, competencia: date
) -> ComparacaoEstadoMes:
    # Agregado estadual/nacional: estatística, não dado de município — não
    # passa pela checagem de acesso por município (ver docstring do módulo).
    valor_estado = indicador_repository.valor_estado_agregado(
        municipio.uf, indicador.id, competencia
    )
    media_piloto = indicador_repository.media_estados(
        list(UFS_PILOTO), indicador.id, competencia
    )
    media_brasil = indicador_repository.media_estados(
        list(UFS_BRASIL), indicador.id, competencia
    )

    return ComparacaoEstadoMes(
        indicador_codigo=indicador.codigo,
        competencia=competencia,
        valor_estado=valor_estado,
        media_piloto=media_piloto,
        media_brasil=media_brasil,
    )


def comparar(
    usuario: DimUsuario, municipio_id: int, indicador_codigo: str, competencia: date
) -> ComparacaoMunicipioMes | ComparacaoEstadoMes:
    """Monta a comparação de `indicador_codigo` na `competencia` para o
    município `municipio_id`, checando acesso do `usuario`.

    O "município" aqui também serve pra resolver a UF quando o indicador é
    estado_mes (compara o estado do município pedido, não um município
    específico) — por isso `municipio_id` é sempre obrigatório, mesmo nas
    comparações que não expõem valor de município.
    """
    municipio = municipio_repository.municipio_por_id(municipio_id)
    if municipio is None:
        raise MunicipioNaoEncontradoError(
            f"municipio_id {municipio_id!r} não encontrado"
        )

    indicador = _resolve_indicador(indicador_codigo)

    if indicador.granularidade == GRANULARIDADE_MUNICIPIO_MES:
        return _comparar_municipio_mes(usuario, municipio, indicador, competencia)

    if indicador.granularidade == GRANULARIDADE_ESTADO_MES:
        # Estatística agregada por UF, não dado de município — qualquer
        # usuário autenticado pode consultar (ver docstring do módulo).
        return _comparar_estado_mes(municipio, indicador, competencia)

    raise GranularidadeNaoSuportadaError(
        f"comparação não implementada para granularidade {indicador.granularidade!r}"
    )
