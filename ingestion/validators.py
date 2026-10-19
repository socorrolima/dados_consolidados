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


def _fonte_hash(codigo6: str, anomes_s: str, campo: str, valor: float) -> str:
    bruto = f"{codigo6}|{anomes_s}|{campo}|{valor}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


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

    resultado = ResultadoValidacao()
    for campo, indicador_id in indicador_id_por_campo.items():
        if campo not in doc:
            continue  # fonte não reportou este indicador neste mês — não é erro

        valor = doc[campo]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            resultado.avisos.append(
                f"{codigo6}/{doc['anomes_s']}/{campo}: valor não numérico descartado: {valor!r}"
            )
            continue

        if valor < 0:
            resultado.avisos.append(
                f"{codigo6}/{doc['anomes_s']}/{campo}: valor negativo inesperado: {valor}"
            )

        resultado.linhas.append(
            {
                "municipio_id": municipio_id,
                "indicador_id": indicador_id,
                "competencia": competencia,
                "valor": valor,
                "fonte_hash": _fonte_hash(codigo6, doc["anomes_s"], campo, valor),
            }
        )

    return resultado
