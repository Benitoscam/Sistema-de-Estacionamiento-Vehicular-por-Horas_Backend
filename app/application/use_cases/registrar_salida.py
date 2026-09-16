"""Caso de uso RegistrarSalida (RF-03) — Fase 2B.

Calcula el monto por tiempo real (techo por hora iniciada) con la tarifa
de la zona, guarda hora_salida + monto_cobrado y libera el espacio a
'disponible' en la misma transacción (FOR UPDATE). Sin fila de pago:
el pago va en Fase 3.
"""

from datetime import datetime, timezone

from app.adapters.db.models import Espacio, RegistroIngresoSalida
from app.domain.excepciones import RecursoNoEncontrado, ReservaNoCancelabe
from app.domain.services import tarifas
from app.domain.value_objects import RangoHorario
from app.extensions import db


def ejecutar(registro_id):
    registro = (
        db.session.query(RegistroIngresoSalida)
        .filter_by(id=registro_id)
        .with_for_update()
        .one_or_none()
    )
    if registro is None:
        raise RecursoNoEncontrado("registro no encontrado")
    if registro.hora_salida is not None:
        raise ReservaNoCancelabe("el registro ya tiene salida (doble salida)")

    espacio = (
        db.session.query(Espacio)
        .filter_by(id=registro.espacio_id)
        .with_for_update()
        .one_or_none()
    )
    if espacio is None:
        raise RecursoNoEncontrado("espacio no encontrado")

    salida = datetime.now(timezone.utc)
    rango = RangoHorario(registro.hora_entrada, salida)
    monto = tarifas.monto_estimado(espacio.zona.tarifa_por_hora, rango)

    registro.hora_salida = salida
    registro.monto_cobrado = monto
    espacio.estado = "disponible"
    db.session.commit()
    return registro, monto
