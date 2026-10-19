from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.get("/saude")
def saude():
    return jsonify(status="ok")


# Endpoints JSON do dashboard (/api/dashboard/<municipio_id>) — Fase 6 (ver plano).
