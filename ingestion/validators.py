"""Validação fail-fast de um documento bruto do SAGI antes de qualquer gravação.

Barra dado sujo na borda: um documento inteiro é rejeitado (ValidationError)
se o código do município ou a competência forem inválidos. Um valor de campo
individual problemático (não numérico) é descartado isoladamente — não derruba
o documento inteiro, mas é sempre registrado em `avisos`, nunca silenciado.
"""

import hashlib
from dataclasses import dataclass, field

from ingestion.normalizers import (
    NormalizationError,
    normaliza_codigo_ibge_sagi,
    normaliza_competencia,
)


class ValidationError(Exception):
    """Documento inteiro rejeitado — município ou competência inválidos."""


@dataclass
class ResultadoValidacao:
    linhas: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _fonte_hash(chave: str, anomes_s: str, campo: str, valor: float) -> str:
    bruto = f"{chave}|{anomes_s}|{campo}|{valor}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _extrai_linhas(
    doc: dict,
    indicador_id_por_campo: dict[str, int],
    competencia,
    chave_log: str,
    campos_fixos: dict,
) -> ResultadoValidacao:
    """Extrai uma linha por campo de indicador presente no documento.

    Compartilhado entre as validações município/mês e estado/mês: a única
    diferença entre as duas é qual chave extra (municipio_id ou uf) entra
    em cada linha — isso vem em `campos_fixos`.
    """
    resultado = ResultadoValidacao()
    anomes_s = doc["anomes_s"]

    for campo, indicador_id in indicador_id_por_campo.items():
        if campo not in doc:
            continue  # fonte não reportou este indicador neste mês — não é erro

        valor = doc[campo]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            resultado.avisos.append(
                f"{chave_log}/{anomes_s}/{campo}: valor não numérico descartado: {valor!r}"
            )
            continue

        if valor < 0:
            resultado.avisos.append(
                f"{chave_log}/{anomes_s}/{campo}: valor negativo inesperado: {valor}"
            )

        resultado.linhas.append(
            {
                **campos_fixos,
                "indicador_id": indicador_id,
                "competencia": competencia,
                "valor": valor,
                "fonte_hash": _fonte_hash(chave_log, anomes_s, campo, valor),
            }
        )

    return resultado


def valida_doc_municipio_mes(
    doc: dict,
    indicador_id_por_campo: dict[str, int],
    municipio_id_por_codigo6: dict[str, int],
) -> ResultadoValidacao:
    """Valida um documento município/mês e monta as linhas prontas pro loader.

    Levanta ValidationError se o documento inteiro deve ser rejeitado
    (código do município ou competência malformados, ou município fora do
    escopo conhecido em dim_municipio). Um campo individual com valor não
    numérico é descartado isoladamente (registrado em `avisos`), sem
    rejeitar o documento inteiro.
    """
    try:
        codigo6 = normaliza_codigo_ibge_sagi(doc["codigo_ibge"])
        competencia = normaliza_competencia(doc["anomes_s"])
    except (KeyError, NormalizationError) as exc:
        raise ValidationError(f"documento rejeitado: {exc}") from exc

    municipio_id = municipio_id_por_codigo6.get(codigo6)
    if municipio_id is None:
        raise ValidationError(
            f"codigo_ibge {codigo6!r} não existe em dim_municipio (fora do escopo do piloto)"
        )

    return _extrai_linhas(
        doc,
        indicador_id_por_campo,
        competencia,
        chave_log=codigo6,
        campos_fixos={"municipio_id": municipio_id},
    )


def valida_doc_estado_mes(
    doc: dict,
    indicador_id_por_campo: dict[str, int],
    ufs_validas: set[str],
) -> ResultadoValidacao:
    """Valida um documento estado/mês e monta as linhas prontas pro loader.

    `sigla_uf` é sempre ASCII (BA/PE/RN, sem acento) — diferente do
    município, não precisa de normalizador nem de tabela de mapeamento,
    só confirmar que é uma das UFs do escopo do piloto.
    """
    uf = doc.get("sigla_uf")
    if uf not in ufs_validas:
        raise ValidationError(f"sigla_uf {uf!r} fora do escopo do piloto")

    try:
        competencia = normaliza_competencia(doc["anomes_s"])
    except (KeyError, NormalizationError) as exc:
        raise ValidationError(f"documento rejeitado: {exc}") from exc

    return _extrai_linhas(
        doc,
        indicador_id_por_campo,
        competencia,
        chave_log=uf,
        campos_fixos={"uf": uf},
    )
