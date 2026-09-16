"""Caso de uso CancelarReserva (RF-02) — Fase 2A.

Solo reservas confirmadas. Solo el dueño o admin. Libera el espacio
a 'disponible' en la misma transacción (con FOR UPDATE).
"""

from app.adapters.db.models import Espacio, Reserva
from app.domain.excepciones import (
    PermisoDenegado,
    RecursoNoEncontrado,
    ReservaNoCancelabe,
)
from app.extensions import db


def ejecutar(usuario, reserva_id):
    reserva = db.session.get(Reserva, reserva_id)
    if reserva is None:
        raise RecursoNoEncontrado("reserva no encontrada")
    if str(reserva.estado) != "confirmada":
        raise ReservaNoCancelabe("solo se pueden cancelar reservas confirmadas")
    if str(usuario.rol) != "admin" and reserva.usuario_id != usuario.id:
        raise PermisoDenegado("solo el dueño o un admin puede cancelar la reserva")

    espacio = (
        db.session.query(Espacio)
        .filter_by(id=reserva.espacio_id)
        .with_for_update()
        .one_or_none()
    )
    reserva.estado = "cancelada"
    if espacio is not None:
        espacio.estado = "disponible"
    db.session.commit()
    return reserva
