"""Resumo das execuções de ingestão registradas em ingestao_execucao.

Uso:
    python -m scripts.relatorio_ingestoes [--limite 20] [--so-falhas]

Pensado pra revisão operacional (Fase 8): checar se o cron diário do
ingest.yml está rodando, se alguma ingestão falhou ou teve taxa de
rejeição alta, sem precisar abrir o banco na mão.
"""

import argparse

from app import create_app
from app.extensions import db
from app.models.ingestao import STATUS_FALHOU, IngestaoExecucao


def _formata_linha(execucao: IngestaoExecucao) -> str:
    duracao = "-"
    if execucao.finalizado_em:
        duracao = (
            f"{(execucao.finalizado_em - execucao.iniciado_em).total_seconds():.1f}s"
        )

    return (
        f"{execucao.id:>5}  {execucao.iniciado_em:%Y-%m-%d %H:%M}  "
        f"{execucao.dataset_origem:<28} {execucao.status:<12} "
        f"lidas={execucao.linhas_lidas!s:<6} gravadas={execucao.linhas_gravadas!s:<6} "
        f"rejeitadas={execucao.linhas_rejeitadas!s:<4} {duracao:>8}  "
        f"{execucao.parametros}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=20)
    parser.add_argument("--so-falhas", action="store_true")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        query = IngestaoExecucao.query.order_by(IngestaoExecucao.iniciado_em.desc())
        if args.so_falhas:
            query = query.filter_by(status=STATUS_FALHOU)

        execucoes = query.limit(args.limite).all()

        if not execucoes:
            print("nenhuma execução encontrada.")
            return

        for execucao in execucoes:
            print(_formata_linha(execucao))

        total_falhas = (
            db.session.query(IngestaoExecucao).filter_by(status=STATUS_FALHOU).count()
        )
        print(f"\ntotal de falhas no histórico completo: {total_falhas}")


if __name__ == "__main__":
    main()
