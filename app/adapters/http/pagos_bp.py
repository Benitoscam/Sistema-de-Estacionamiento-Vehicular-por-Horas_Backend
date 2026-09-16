"""Pagos del cliente (RF-02) — Fase 3A. Checkout + historial + confirmación fake."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from app.adapters.db.models import Pago, Reserva, Usuario
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.application.use_cases import confirmar_pago, crear_checkout
from app.domain.excepciones import (
    ErrorDominio,
    PagoDuplicado,
    PermisoDenegado,
    RecursoNoEncontrado,
    ReservaNoCancelabe,
)
from app.extensions import db

bp = Blueprint("pagos", __name__)
PAGADORES = ("cliente", "admin")

CODIGOS = {
    PagoDuplicado: "pago_duplicado",
    ReservaNoCancelabe: "reserva_no_pagable",
    PermisoDenegado: "prohibido",
    RecursoNoEncontrado: "no_encontrado",
}


def _dominio_a_respuesta(exc):
    codigo = CODIGOS.get(type(exc), "error_dominio")
    return error(getattr(exc, "mensaje", str(exc)), exc.estado_http, codigo)


def _actor():
    from flask_jwt_extended import get_jwt_identity

    usuario_id = schemas.parse_uuid(get_jwt_identity())
    if usuario_id is None:
        return None, error("identidad inválida", 401)
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return None, error("usuario no encontrado", 401)
    return usuario, None


def pago_a_dict(pago):
    return {
        "id": str(pago.id),
        "reserva_id": str(pago.reserva_id) if pago.reserva_id else None,
        "registro_ingreso_id": str(pago.registro_ingreso_id)
        if pago.registro_ingreso_id
        else None,
        "referencia_transaccion": pago.referencia_transaccion,
        "monto": str(pago.monto),
        "metodo": str(pago.metodo),
        "estado": str(pago.estado),
        "reserva_codigo": pago.reserva.espacio.codigo
        if pago.reserva and pago.reserva.espacio
        else None,
    }


@bp.route("/pagos/checkout", methods=["POST"])
@jwt_required()
@roles_required(*PAGADORES)
def checkout():
    usuario, err = _actor()
    if err:
        return err
    datos = schemas.json_body(request)
    if not datos.get("reserva_id"):
        return error("campos requeridos: reserva_id", 400)
    reserva_id = schemas.parse_uuid(datos.get("reserva_id"))
    if reserva_id is None:
        return error("reserva_id inválido", 400)
    try:
        pago, url = crear_checkout.ejecutar(usuario, reserva_id)
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    return jsonify({"data": {**pago_a_dict(pago), "checkout_url": url}}), 201


@bp.route("/pagos/mios", methods=["GET"])
@jwt_required()
@roles_required("cliente")
def mis_pagos():
    usuario, err = _actor()
    if err:
        return err
    pagos = (
        Pago.query.join(Reserva, Pago.reserva_id == Reserva.id)
        .filter(Reserva.usuario_id == usuario.id)
        .all()
    )
    return jsonify({"data": [pago_a_dict(p) for p in pagos]}), 200


@bp.route("/pagos/fake-confirmar", methods=["POST"])
@jwt_required()
@roles_required(*PAGADORES)
def fake_confirmar():
    """Solo dev (STRIPE_MODE=fake): simula la confirmación del webhook con JWT."""
    if (current_app.config.get("STRIPE_MODE") or "fake").lower() != "fake":
        return error("solo disponible en modo fake", 404, "no_disponible")
    usuario, err = _actor()
    if err:
        return err
    datos = schemas.json_body(request)
    if not datos.get("pago_id"):
        return error("campos requeridos: pago_id", 400)
    pago_id = schemas.parse_uuid(datos.get("pago_id"))
    if pago_id is None:
        return error("pago_id inválido", 400)
    pago = db.session.get(Pago, pago_id)
    if pago is None:
        return error("pago no encontrado", 404, "no_encontrado")
    if pago.reserva_id is not None:
        reserva = db.session.get(Reserva, pago.reserva_id)
        if str(usuario.rol) != "admin" and (
            reserva is None or reserva.usuario_id != usuario.id
        ):
            return error("solo el dueño o un admin puede confirmar el pago", 403, "prohibido")
    try:
        pago, _nuevo = confirmar_pago.ejecutar_por_referencia(pago.referencia_transaccion)
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    return jsonify({"data": pago_a_dict(pago)}), 200
