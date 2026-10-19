from datetime import datetime, timezone

from app.extensions import db


class DimMunicipio(db.Model):
    __tablename__ = "dim_municipio"

    id = db.Column(db.Integer, primary_key=True)
    codigo_ibge = db.Column(db.String(7), nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    ativo_piloto = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (db.Index("ix_dim_municipio_uf", "uf"),)
