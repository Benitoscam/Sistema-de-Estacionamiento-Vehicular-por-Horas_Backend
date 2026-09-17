"""CLI: flask reservas expirar — Fase 4.

Dos pases en un solo ciclo (cron del SO cada 10-15 minutos):
  1. EXPIRAR: marca como completada las reservas cuya hora_fin_planeada ya pasó.
     Libera el espacio si no tiene otra reserva activa.
  2. ACTIVAR: reserva confirmada con hora_inicio_planeada <= ahora < hora_fin_planeada
     y espacio todavia 'disponible' → cambia a 'reservado'.
Idempotente.
"""

import click
from flask import cli


@click.group("reservas")
def reservas_cli():
    """Gestion de reservas vencidas y activacion."""
    pass


@reservas_cli.command("expirar")
@cli.with_appcontext
def expirar():
    from datetime import datetime, timezone

    from sqlalchemy import and_

    from app.adapters.db.models import Espacio, Reserva
    from app.extensions import db

    ahora = datetime.now(timezone.utc)

    # ── Pase 1: expirar vencidas ──────────────────────────────
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

    # ── Pase 2: activar reservas iniciadas ────────────────────
    espacios_activados = 0
    iniciadas = (
        Reserva.query.filter(
            and_(
                Reserva.estado == "confirmada",
                Reserva.hora_inicio_planeada <= ahora,
                Reserva.hora_fin_planeada > ahora,
            )
        )
        .all()
    )
    for reserva in iniciadas:
        espacio = db.session.get(Espacio, reserva.espacio_id)
        if espacio and espacio.estado == "disponible":
            espacio.estado = "reservado"
            espacios_activados += 1

    db.session.commit()
    click.echo(
        f"{len(vencidas)} reservas expiradas, {espacios_liberados} espacios liberados, "
        f"{espacios_activados} espacios activados"
    )


def register_commands(app):
    app.cli.add_command(reservas_cli)
