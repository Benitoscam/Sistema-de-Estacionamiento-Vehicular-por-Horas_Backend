"""Caso de uso ConfirmarPago — Fase 3A.

Idempotente: si el pago ya está confirmado, no duplica nada.
Al confirmar, refleja el monto en reserva.monto_pagado.
"""

from app.adapters.db.models import Pago, Reserva
from app.domain.excepciones import RecursoNoEncontrado
from app.extensions import db


def ejecutar_por_referencia(referencia):
    pago = Pago.query.filter_by(referencia_transaccion=referencia).first()
    if pago is None:
        raise RecursoNoEncontrado("pago no encontrado")
    if str(pago.estado) == "confirmado":
        return pago, False
    pago.estado = "confirmado"
    if pago.reserva_id is not None:
        reserva = db.session.get(Reserva, pago.reserva_id)
        if reserva is not None:
            reserva.monto_pagado = pago.monto
    db.session.commit()
    return pago, True
