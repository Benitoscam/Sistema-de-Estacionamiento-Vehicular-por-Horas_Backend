"""CLI: flask reservas expirar — Fase 4.

Marca como completada las reservas confirmadas cuya hora_fin_planeada ya pasó.
Libera el espacio si no tiene otra reserva activa. Idempotente.
Ejecutar con cron del SO cada 10–15 minutos.
"""

import click
from flask import cli


@click.group("reservas")
def reservas_cli():
    """Gestión de reservas vencidas."""
    pass


@reservas_cli.command("expirar")
@cli.with_appcontext
def expirar():
    from datetime import datetime, timezone

    from sqlalchemy import and_

    from app.adapters.db.models import Espacio, Reserva
    from app.extensions import db

    ahora = datetime.now(timezone.utc)
    vencidas = (
        Reserva.query.filter(
            and_(
                Reserva.estado == "confirmada",
                Reserva.hora_fin_planeada < ahora,
            )
        )
        .with_for_update()
        .all()
    )
    if not vencidas:
        click.echo("0 reservas expiradas")
        return

    espacios_liberados = 0
    for reserva in vencidas:
        reserva.estado = "completada"
        espacio = db.session.get(Espacio, reserva.espacio_id)
        if espacio and espacio.estado == "reservado":
            otra = (
                Reserva.query.filter(
                    and_(
                        Reserva.espacio_id == espacio.id,
                        Reserva.estado == "confirmada",
                        Reserva.hora_fin_planeada >= ahora,
                    )
                ).count()
            )
            if otra == 0:
                espacio.estado = "disponible"
                espacios_liberados += 1

    db.session.commit()
    click.echo(f"{len(vencidas)} reservas expiradas, {espacios_liberados} espacios liberados")


def register_commands(app):
    app.cli.add_command(reservas_cli)
