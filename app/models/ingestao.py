from datetime import datetime, timezone

from app.extensions import db

STATUS_EM_ANDAMENTO = "em_andamento"
STATUS_SUCESSO = "sucesso"
STATUS_FALHOU = "falhou"


class IngestaoExecucao(db.Model):
    __tablename__ = "ingestao_execucao"

    id = db.Column(db.Integer, primary_key=True)
    dataset_origem = db.Column(db.String(60), nullable=False)
    parametros = db.Column(db.Text, nullable=False)
    iniciado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finalizado_em = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), nullable=False, default=STATUS_EM_ANDAMENTO)
    linhas_lidas = db.Column(db.Integer)
    linhas_gravadas = db.Column(db.Integer)
    linhas_rejeitadas = db.Column(db.Integer)
    erro_detalhe = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint(
            f"status IN ('{STATUS_EM_ANDAMENTO}', '{STATUS_SUCESSO}', '{STATUS_FALHOU}')",
            name="ck_ingestao_execucao_status",
        ),
    )
