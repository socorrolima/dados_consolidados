from datetime import datetime, timedelta, timezone

from app.models.ingestao import STATUS_EM_ANDAMENTO, STATUS_SUCESSO, IngestaoExecucao
from scripts.relatorio_ingestoes import _formata_linha


def test_formata_linha_execucao_concluida():
    inicio = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
    execucao = IngestaoExecucao(
        id=1,
        dataset_origem="misocial",
        parametros="uf=['BA'] competencia=202601",
        iniciado_em=inicio,
        finalizado_em=inicio + timedelta(seconds=12.3),
        status=STATUS_SUCESSO,
        linhas_lidas=769,
        linhas_gravadas=20736,
        linhas_rejeitadas=0,
    )

    linha = _formata_linha(execucao)

    assert "misocial" in linha
    assert "sucesso" in linha
    assert "12.3s" in linha
    assert "lidas=769" in linha


def test_formata_linha_execucao_em_andamento_sem_crashar():
    execucao = IngestaoExecucao(
        id=2,
        dataset_origem="misocial",
        parametros="uf=['BA']",
        iniciado_em=datetime(2026, 1, 1, tzinfo=timezone.utc),
        finalizado_em=None,
        status=STATUS_EM_ANDAMENTO,
        linhas_lidas=None,
        linhas_gravadas=None,
        linhas_rejeitadas=None,
    )

    linha = _formata_linha(execucao)

    assert "em_andamento" in linha
    assert "lidas=None" in linha
