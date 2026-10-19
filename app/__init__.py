import os

from flask import Flask

from app.config import CONFIG_BY_NAME
from app.extensions import db


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
