from datetime import datetime, timezone

from app.extensions import db

PAPEL_GESTOR_MUNICIPAL = "gestor_municipal"
PAPEL_ADMIN = "admin"


class DimUsuario(db.Model):
    __tablename__ = "dim_usuario"

    # id = auth.users.id do Supabase Auth (não gerado por nós).
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    nome = db.Column(db.String(200), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default=PAPEL_GESTOR_MUNICIPAL)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            f"papel IN ('{PAPEL_GESTOR_MUNICIPAL}', '{PAPEL_ADMIN}')",
            name="ck_dim_usuario_papel",
        ),
    )


class UsuarioMunicipio(db.Model):
    __tablename__ = "usuario_municipio"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.String(36),
        db.ForeignKey("dim_usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    municipio_id = db.Column(
        db.Integer,
        db.ForeignKey("dim_municipio.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "municipio_id", name="uq_usuario_municipio"),
    )
