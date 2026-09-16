"""Caso de uso ReservarEspacio (RF-02) — Fase 2A.

Transacción con bloqueo de fila (FOR UPDATE) sobre el espacio:
valida disponibilidad, crea la reserva confirmada y pasa el espacio
a 'reservado' en la misma transacción. Sin cobro (Fase 3).
"""

from app.adapters.db.models import Espacio, Reserva, Usuario
from app.domain.excepciones import RecursoNoEncontrado
from app.domain.services import disponibilidad, tarifas
from app.domain.value_objects import RangoHorario
from app.extensions import db


def ejecutar(usuario_id, espacio_id, inicio, fin):
    rango = RangoHorario(inicio, fin)

    espacio = (
        db.session.query(Espacio)
        .filter_by(id=espacio_id)
        .with_for_update()
        .one_or_none()
    )
    if espacio is None:
        raise RecursoNoEncontrado("espacio no encontrado")

    conflictivas = (
        Reserva.query.filter_by(espacio_id=espacio.id, estado="confirmada")
        .filter(
            Reserva.hora_inicio_planeada < rango.fin,
            Reserva.hora_fin_planeada > rango.inicio,
        )
        .all()
    )
    disponibilidad.verificar(str(espacio.estado), conflictivas, rango)

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNoEncontrado("usuario no encontrado")

    monto = tarifas.monto_estimado(espacio.zona.tarifa_por_hora, rango)
    reserva = Reserva(
        espacio_id=espacio.id,
        usuario_id=usuario.id,
        fecha=rango.inicio.date(),
        hora_inicio_planeada=rango.inicio,
        hora_fin_planeada=rango.fin,
        monto_pagado=None,
        estado="confirmada",
    )
    espacio.estado = "reservado"
    db.session.add(reserva)
    db.session.commit()
    return reserva, monto
