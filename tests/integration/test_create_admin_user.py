import pytest

from app.extensions import db
from app.models.municipio import DimMunicipio
from app.models.usuario import PAPEL_ADMIN, DimUsuario
from scripts.create_admin_user import provisionar_usuario

USUARIO_ID = "11111111-1111-1111-1111-111111111111"


def _cria_municipio(codigo="2927408", nome="Salvador", uf="BA"):
    municipio = DimMunicipio(codigo_ibge=codigo, nome=nome, uf=uf)
    db.session.add(municipio)
    db.session.commit()
    return municipio


def test_provisiona_gestor_municipal_novo(app):
    with app.app_context():
        _cria_municipio()

        usuario = provisionar_usuario(
            USUARIO_ID,
            "gestora@salvador.ba.gov.br",
            "Gestora Teste",
            "gestor_municipal",
            ["2927408"],
        )

        assert usuario.email == "gestora@salvador.ba.gov.br"
        assert len(usuario.vinculos_municipio) == 1


def test_gestor_municipal_sem_municipio_falha(app):
    with app.app_context():
        with pytest.raises(ValueError, match="precisa de ao menos um"):
            provisionar_usuario(USUARIO_ID, "x@x.com", "X", "gestor_municipal", [])


def test_provisiona_admin_sem_municipio(app):
    with app.app_context():
        usuario = provisionar_usuario(
            USUARIO_ID, "admin@exemplo.gov.br", "Admin", PAPEL_ADMIN, []
        )

        assert usuario.papel == PAPEL_ADMIN
        assert usuario.vinculos_municipio == []


def test_reexecutar_nao_duplica_vinculo(app):
    with app.app_context():
        _cria_municipio()

        provisionar_usuario(
            USUARIO_ID,
            "gestora@salvador.ba.gov.br",
            "Gestora Teste",
            "gestor_municipal",
            ["2927408"],
        )
        provisionar_usuario(
            USUARIO_ID,
            "gestora@salvador.ba.gov.br",
            "Gestora Teste",
            "gestor_municipal",
            ["2927408"],
        )

        usuario = db.session.get(DimUsuario, USUARIO_ID)
        assert len(usuario.vinculos_municipio) == 1


def test_municipio_inexistente_falha(app):
    with app.app_context():
        with pytest.raises(ValueError, match="não existe em dim_municipio"):
            provisionar_usuario(
                USUARIO_ID, "x@x.com", "X", "gestor_municipal", ["9999999"]
            )
