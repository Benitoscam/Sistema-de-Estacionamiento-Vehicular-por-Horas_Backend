"""Caso de uso CrearCheckout (RF-02) — Fase 3A.

Solo reservas confirmadas del dueño (o admin). Un pago por reserva:
si ya existe (pendiente o confirmado) se rechaza 409. Monto = tarifa
actual × techo de horas planeadas. Crea el pago 'pendiente' con la
referencia que devuelve la pasarela (fake o Stripe test).
"""

from flask import current_app

from app.adapters.db.models import Pago, Reserva
from app.adapters.payment.pasarela import obtener_pasarela
from app.domain.excepciones import (
    PagoDuplicado,
    PermisoDenegado,
    RecursoNoEncontrado,
    ReservaNoCancelabe,
)
from app.domain.services import tarifas
from app.domain.value_objects import RangoHorario
from app.extensions import db


def ejecutar(usuario, reserva_id):
    reserva = db.session.get(Reserva, reserva_id)
    if reserva is None:
        raise RecursoNoEncontrado("reserva no encontrada")
    if str(usuario.rol) != "admin" and reserva.usuario_id != usuario.id:
        raise PermisoDenegado("solo el dueño o un admin puede pagar la reserva")
    if str(reserva.estado) != "confirmada":
        raise ReservaNoCancelabe("solo reservas confirmadas se pueden pagar")
    if Pago.query.filter_by(reserva_id=reserva.id).first():
        raise PagoDuplicado("la reserva ya tiene un pago")

    rango = RangoHorario(reserva.hora_inicio_planeada, reserva.hora_fin_planeada)
    monto = tarifas.monto_estimado(reserva.espacio.zona.tarifa_por_hora, rango)
    base = (current_app.config.get("FRONTEND_URL") or "").rstrip("/")
    pasarela = obtener_pasarela()
    sesion = pasarela.crear_sesion(
        monto=monto,
        descripcion=(
            f"Reserva {reserva.espacio.codigo} "
            f"{rango.inicio:%Y-%m-%d %H:%M}-{rango.fin:%H:%M}"
        ),
        exito_url=f"{base}/pago/exito?sesion={{CHECKOUT_SESSION_ID}}",
        cancela_url=f"{base}/pago/cancelado",
        referencia_interna=str(reserva.id),
    )
    pago = Pago(
        reserva_id=reserva.id,
        registro_ingreso_id=None,
        referencia_transaccion=sesion.referencia,
        monto=monto,
        metodo="tarjeta",
        estado="pendiente",
    )
    db.session.add(pago)
    db.session.commit()
    return pago, sesion.url
