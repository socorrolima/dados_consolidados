from datetime import datetime, timezone

from app.extensions import db

GRANULARIDADE_MUNICIPIO_MES = "municipio_mes"
GRANULARIDADE_ESTADO_MES = "estado_mes"
GRANULARIDADE_MUNICIPIO_ANO = "municipio_ano"
GRANULARIDADES_VALIDAS = (
    GRANULARIDADE_MUNICIPIO_MES,
    GRANULARIDADE_ESTADO_MES,
    GRANULARIDADE_MUNICIPIO_ANO,
)


class DimIndicador(db.Model):
    __tablename__ = "dim_indicador"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), nullable=False, unique=True)
    nome_exibicao = db.Column(db.String(200), nullable=False)
    dataset_origem = db.Column(db.String(60), nullable=False)
    granularidade = db.Column(db.String(20), nullable=False)
    unidade = db.Column(db.String(30))
    categoria = db.Column(db.String(60), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            "granularidade IN ({})".format(
                ", ".join(f"'{g}'" for g in GRANULARIDADES_VALIDAS)
            ),
            name="ck_dim_indicador_granularidade",
        ),
    )


class FatoIndicadorMunicipioMes(db.Model):
    __tablename__ = "fato_indicador_municipio_mes"

    # Integer (não BigInteger): no SQLite, só "INTEGER PRIMARY KEY" vira alias
    # do rowid com autoincrement; BigInteger compila para BIGINT e quebra o
    # autoincrement em dev/CI. Integer (31 bits) sobra para o volume previsto
    # (milhões de linhas, não bilhões) nas 3 tabelas fato.
    id = db.Column(db.Integer, primary_key=True)
    municipio_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_municipio.id", ondelete="RESTRICT"),
        nullable=False,
    )
    indicador_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_indicador.id", ondelete="RESTRICT"),
        nullable=False,
    )
    competencia = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(16, 2))
    fonte_hash = db.Column(db.String(64), nullable=False)
    ingestao_id = db.Column(
        db.Integer, db.ForeignKey("ingestao_execucao.id", ondelete="SET NULL")
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "municipio_id", "indicador_id", "competencia", name="uq_fato_municipio_mes"
        ),
    )


class FatoIndicadorEstadoMes(db.Model):
    __tablename__ = "fato_indicador_estado_mes"

    id = db.Column(db.Integer, primary_key=True)
    uf = db.Column(db.String(2), nullable=False)
    indicador_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_indicador.id", ondelete="RESTRICT"),
        nullable=False,
    )
    competencia = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(16, 2))
    fonte_hash = db.Column(db.String(64), nullable=False)
    ingestao_id = db.Column(
        db.Integer, db.ForeignKey("ingestao_execucao.id", ondelete="SET NULL")
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "uf", "indicador_id", "competencia", name="uq_fato_estado_mes"
        ),
    )


class FatoIndicadorMunicipioAno(db.Model):
    __tablename__ = "fato_indicador_municipio_ano"

    id = db.Column(db.Integer, primary_key=True)
    municipio_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_municipio.id", ondelete="RESTRICT"),
        nullable=False,
    )
    indicador_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_indicador.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ano = db.Column(db.SmallInteger, nullable=False)
    valor = db.Column(db.Numeric(16, 2))
    fonte_hash = db.Column(db.String(64), nullable=False)
    ingestao_id = db.Column(
        db.Integer, db.ForeignKey("ingestao_execucao.id", ondelete="SET NULL")
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "municipio_id", "indicador_id", "ano", name="uq_fato_municipio_ano"
        ),
    )
