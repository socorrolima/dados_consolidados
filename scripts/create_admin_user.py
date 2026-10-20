"""Provisiona um gestor (ou admin) depois que a conta já existe no Supabase Auth.

A CRIAÇÃO da conta em si (e-mail/senha) acontece no painel da Supabase
(Authentication > Users > Add user) — este script não fala com a API da
Supabase, só grava o vínculo de NEGÓCIO em dim_usuario/usuario_municipio
(papel, quais municípios o gestor enxerga), que o Supabase Auth não
modela. Rode depois de criar o usuário no painel e copiar o UUID dele.

Uso:
    python -m scripts.create_admin_user \
        --id <uuid-do-usuario-no-supabase> \
        --email gestora@municipio.ba.gov.br \
        --nome "Maria da Silva" \
        --municipio-ibge 2927408 \
        [--papel gestor_municipal|admin]

--municipio-ibge aceita o código de 7 dígitos do IBGE (o mesmo de
data/municipios_ibge.csv) e pode repetir a flag para vincular mais de um
município ao mesmo gestor. Admin não precisa de --municipio-ibge (vê os
agregados estaduais/Brasil sem vínculo de município específico).
"""

import argparse
import logging
import sys

from app import create_app
from app.extensions import db
from app.models.municipio import DimMunicipio
from app.models.usuario import (
    PAPEL_ADMIN,
    PAPEL_GESTOR_MUNICIPAL,
    DimUsuario,
    UsuarioMunicipio,
)

logger = logging.getLogger(__name__)


def provisionar_usuario(
    usuario_id: str,
    email: str,
    nome: str,
    papel: str,
    codigos_ibge: list[str],
) -> DimUsuario:
    if papel == PAPEL_GESTOR_MUNICIPAL and not codigos_ibge:
        raise ValueError("gestor_municipal precisa de ao menos um --municipio-ibge")

    municipios = []
    for codigo in codigos_ibge:
        municipio = DimMunicipio.query.filter_by(codigo_ibge=codigo).first()
        if municipio is None:
            raise ValueError(
                f"codigo_ibge {codigo!r} não existe em dim_municipio — "
                "rode scripts.seed_municipios ou confira o código"
            )
        municipios.append(municipio)

    usuario = db.session.get(DimUsuario, usuario_id)
    if usuario is None:
        usuario = DimUsuario(id=usuario_id, email=email, nome=nome, papel=papel)
        db.session.add(usuario)
    else:
        usuario.email = email
        usuario.nome = nome
        usuario.papel = papel
        usuario.ativo = True

    db.session.flush()  # garante usuario.id disponível pro vínculo abaixo

    vinculados = {v.municipio_id for v in usuario.vinculos_municipio}
    for municipio in municipios:
        if municipio.id not in vinculados:
            db.session.add(
                UsuarioMunicipio(usuario_id=usuario.id, municipio_id=municipio.id)
            )

    db.session.commit()
    return usuario


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="UUID do usuário no Supabase Auth")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nome", required=True)
    parser.add_argument(
        "--papel",
        choices=[PAPEL_GESTOR_MUNICIPAL, PAPEL_ADMIN],
        default=PAPEL_GESTOR_MUNICIPAL,
    )
    parser.add_argument(
        "--municipio-ibge",
        action="append",
        default=[],
        dest="municipios_ibge",
        help="Código IBGE de 7 dígitos; repita a flag para mais de um município",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            usuario = provisionar_usuario(
                args.id, args.email, args.nome, args.papel, args.municipios_ibge
            )
        except ValueError as exc:
            logger.error("falha ao provisionar usuário: %s", exc)
            sys.exit(1)

        resumo = (
            f"usuário provisionado: id={usuario.id} email={usuario.email} "
            f"papel={usuario.papel} municipios={len(usuario.vinculos_municipio)}"
        )

    print(resumo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
