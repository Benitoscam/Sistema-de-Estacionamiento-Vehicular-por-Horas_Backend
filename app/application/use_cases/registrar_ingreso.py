"""Caso de uso RegistrarIngreso walk-in (RF-03) — Fase 2B.

El operador elige el espacio y digita la placa (manual en Fase 1).
Transacción con FOR UPDATE: exige espacio 'disponible', crea el registro
abierto (sin hora_salida) y pasa el espacio a 'ocupado'.
Un espacio 'reservado' se rechaza: las reservas entran por su propio flujo.
"""

from datetime import datetime, timezone

from app.adapters.db.models import Espacio, Reserva, RegistroIngresoSalida
from app.domain.excepciones import EspacioNoDisponible, RecursoNoEncontrado
from app.domain.value_objects import Placa
from app.extensions import db


def ejecutar(operador, espacio_id, placa):
    placa_normal = str(Placa(placa))

    espacio = (
        db.session.query(Espacio)
        .filter_by(id=espacio_id)
        .with_for_update()
        .one_or_none()
    )
    if espacio is None:
        raise RecursoNoEncontrado("espacio no encontrado")
    if str(espacio.estado) != "disponible":
        raise EspacioNoDisponible(
            f"espacio en estado '{espacio.estado}', no admite ingreso walk-in"
        )

    ahora = datetime.now(timezone.utc)
    tiene_reserva_futura = (
        Reserva.query.filter(
            Reserva.espacio_id == espacio.id,
            Reserva.estado == "confirmada",
            Reserva.hora_fin_planeada > ahora,
        )
        .first()
        is not None
    )
    if tiene_reserva_futura:
        raise EspacioNoDisponible(
            "espacio tiene una reserva confirmada pendiente, no admite ingreso walk-in"
        )

    registro = RegistroIngresoSalida(
        espacio_id=espacio.id,
        placa=placa_normal,
        operador_id=operador.id,
        hora_entrada=ahora,
        hora_salida=None,
        monto_cobrado=None,
    )
    espacio.estado = "ocupado"
    db.session.add(registro)
    db.session.commit()
    return registro
