import os
from pathlib import Path

# Raiz do projeto (pai do pacote app/). Usado para absolutizar DATABASE_URL
# quando é um sqlite:///caminho-relativo — ver resolve_database_url().
BASE_DIR = Path(__file__).resolve().parent.parent

_SQLITE_RELATIVE_PREFIX = "sqlite:///"


def resolve_database_url(url: str) -> str:
    """Converte um sqlite:///caminho-relativo em caminho absoluto.

    Flask-SQLAlchemy resolve um sqlite:/// relativo a partir de instance/,
    enquanto o Alembic (fora do contexto Flask) resolve a partir do cwd.
    Sem essa normalização, os dois apontam para arquivos .db diferentes para
    a mesma DATABASE_URL — foi exatamente isso que quebrou o seed local.
    Absolutizar aqui garante que ambos usem o mesmo arquivo físico.
    """
    if not url.startswith(_SQLITE_RELATIVE_PREFIX):
        return url

    caminho = url[len(_SQLITE_RELATIVE_PREFIX) :]
    if caminho in ("", ":memory:") or caminho.startswith("/"):
        return url

    caminho_absoluto = (BASE_DIR / caminho).resolve()
    return f"{_SQLITE_RELATIVE_PREFIX}{caminho_absoluto.as_posix()}"


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # URL do projeto Supabase — usado só para derivar o endpoint JWKS
    # ({SUPABASE_URL}/auth/v1/.well-known/jwks.json) em auth_service.py.
    # Não guardamos segredo de assinatura: a verificação é por chave
    # pública (JWKS), não HS256/segredo compartilhado.
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = resolve_database_url(
        os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    )
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-only-not-secret"


class ProdConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = resolve_database_url(os.environ.get("DATABASE_URL", ""))
    SECRET_KEY = os.environ.get("SECRET_KEY")
    REQUIRED_ENV_VARS = ("DATABASE_URL", "SECRET_KEY")


CONFIG_BY_NAME = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
}
