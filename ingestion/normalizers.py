"""Normalização de campos brutos vindos da API SAGI.

O código_ibge da API SAGI tem 6 dígitos (sem o dígito verificador), diferente
do código oficial do IBGE (7 dígitos). Confirmado comparando respostas reais
da API com data/municipios_ibge.csv: o valor da SAGI é sempre igual aos 6
primeiros dígitos do código oficial. Por isso a validação aqui é só de
formato (6 dígitos numéricos) — a resolução para o município correto
(comparando com os 6 primeiros dígitos de dim_municipio.codigo_ibge) é
responsabilidade de quem faz a ingestão, não deste módulo.
"""

from datetime import date


class NormalizationError(Exception):
    """Dado bruto da fonte não pôde ser normalizado — nunca falha em silêncio."""


def normaliza_codigo_ibge_sagi(codigo: str) -> str:
    if not (isinstance(codigo, str) and codigo.isdigit() and len(codigo) == 6):
        raise NormalizationError(f"codigo_ibge da SAGI inválido: {codigo!r}")
    return codigo


def normaliza_competencia(anomes_s: str) -> date:
    if not (isinstance(anomes_s, str) and anomes_s.isdigit() and len(anomes_s) == 6):
        raise NormalizationError(f"anomes_s inválido: {anomes_s!r}")

    ano, mes = int(anomes_s[:4]), int(anomes_s[4:])
    if not (1 <= mes <= 12):
        raise NormalizationError(f"mês inválido em anomes_s: {anomes_s!r}")

    return date(ano, mes, 1)
