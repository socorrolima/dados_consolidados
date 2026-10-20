import os

from dotenv import load_dotenv

# Precisa rodar antes de qualquer import que leia variável de ambiente
# (app.config lê no corpo da classe, na hora do import). Carregar aqui —
# não só em wsgi.py — garante que todo mundo que chama create_app()
# (scripts/*, ingestion/run_ingestion.py, não só o servidor web) também
# lê o .env, em vez de só as variáveis já exportadas no shell.
load_dotenv()

from flask import Flask  # noqa: E402

from app.config import CONFIG_BY_NAME  # noqa: E402
from app.extensions import db  # noqa: E402


def _checar_env_obrigatorias(config_name: str) -> None:
    faltando = [
        var
        for var in getattr(CONFIG_BY_NAME[config_name], "REQUIRED_ENV_VARS", ())
        if not os.environ.get(var)
    ]
    if faltando:
        raise RuntimeError(
            f"Variáveis de ambiente obrigatórias ausentes para '{config_name}': "
            f"{', '.join(faltando)}"
        )


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME[config_name])
    _checar_env_obrigatorias(config_name)

    db.init_app(app)

    from app import models  # noqa: F401 — registra os modelos em db.metadata
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
