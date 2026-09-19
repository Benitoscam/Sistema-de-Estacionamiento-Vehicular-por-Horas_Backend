"""Reservas del cliente (RF-02) — Fase 2A. Sin cobro (Fase 3)."""

from datetime import timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.domain.services import tarifas
from app.domain.value_objects import RangoHorario

from app.adapters.db.models import Reserva, Usuario
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.application.use_cases import cancelar_reserva, reservar_espacio
from app.domain.excepciones import (
    ErrorDominio,
    EspacioNoDisponible,
    PermisoDenegado,
    RangoInvalido,
    RecursoNoEncontrado,
    ReservaNoCancelabe,
)
from app.extensions import db

bp = Blueprint("reservas", __name__)

CODIGOS = {
    RangoInvalido: "rango_horario_invalido",
    EspacioNoDisponible: "espacio_no_disponible",
    ReservaNoCancelabe: "reserva_no_cancelable",
    PermisoDenegado: "prohibido",
    RecursoNoEncontrado: "no_encontrado",
}


def _dominio_a_respuesta(exc):
    codigo = CODIGOS.get(type(exc), "error_dominio")
    return error(getattr(exc, "mensaje", str(exc)), exc.estado_http, codigo)


def _actor():
    usuario_id = schemas.parse_uuid(get_jwt_identity())
    if usuario_id is None:
        return None, error("identidad inválida", 401)
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return None, error("usuario no encontrado", 401)
    return usuario, None


def _parse_fecha(valor):
    try:
        texto = str(valor or "").strip()
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        from datetime import datetime

        momento = datetime.fromisoformat(texto)
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        return momento
    except (ValueError, TypeError, AttributeError):
        return None

def _calcular_monto_estimado(reserva):
    if reserva.espacio is None or reserva.espacio.zona is None:
        return None
    rango = RangoHorario(reserva.hora_inicio_planeada, reserva.hora_fin_planeada)
    return tarifas.monto_estimado(reserva.espacio.zona.tarifa_por_hora, rango)

def reserva_a_dict(reserva, monto_estimado=None):
    return {
        "id": str(reserva.id),
        "espacio_id": str(reserva.espacio_id),
        "espacio_codigo": reserva.espacio.codigo if reserva.espacio else None,
        "usuario_id": str(reserva.usuario_id),
        "placa": getattr(reserva, "placa", None),
        "fecha": reserva.fecha.isoformat() if reserva.fecha else None,
        "hora_inicio_planeada": reserva.hora_inicio_planeada.isoformat()
        if reserva.hora_inicio_planeada
        else None,
        "hora_fin_planeada": reserva.hora_fin_planeada.isoformat()
        if reserva.hora_fin_planeada
        else None,
        "monto_pagado": str(reserva.monto_pagado) if reserva.monto_pagado else None,
        "monto_estimado": str(monto_estimado) if monto_estimado else None,
        "estado": str(reserva.estado),
    }


@bp.route("/reservas", methods=["POST"])
@jwt_required()
@roles_required("cliente")
def crear_reserva():
    usuario, err = _actor()
    if err:
        return err
    datos = schemas.json_body(request)
    faltantes = schemas.missing_fields(
        datos, ("espacio_id", "hora_inicio_planeada", "hora_fin_planeada", "placa")
    )
    if faltantes:
        return error(f"campos requeridos: {', '.join(faltantes)}", 400)
    espacio_id = schemas.parse_uuid(datos.get("espacio_id"))
    if espacio_id is None:
        return error("espacio_id inválido", 400)
    inicio = _parse_fecha(datos.get("hora_inicio_planeada"))
    fin = _parse_fecha(datos.get("hora_fin_planeada"))
    if inicio is None or fin is None:
        return error("fechas inválidas (usar ISO 8601)", 400)
    placa = (datos.get("placa") or "").strip()
    if not placa:
        return error("placa requerida", 400)
    try:
        reserva, monto = reservar_espacio.ejecutar(
            usuario.id, espacio_id, inicio, fin, placa
        )
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    return jsonify({"data": reserva_a_dict(reserva, monto)}), 201


@bp.route("/mis-reservas", methods=["GET"])
@jwt_required()
@roles_required("cliente")
def mis_reservas():
    usuario, err = _actor()
    if err:
        return err
    consulta = Reserva.query.filter_by(usuario_id=usuario.id)
    placa = (request.args.get("placa") or "").strip().upper()
    if placa:
        consulta = consulta.filter(Reserva.placa == placa)
    reservas = consulta.order_by(Reserva.hora_inicio_planeada).all()
    return jsonify({
        "data": [reserva_a_dict(r, _calcular_monto_estimado(r)) for r in reservas]
    }), 200


@bp.route("/reservas/<reserva_id>", methods=["GET"])
@jwt_required()
@roles_required("cliente", "admin")
def detalle_reserva(reserva_id):
    usuario, err = _actor()
    if err:
        return err
    rid = schemas.parse_uuid(reserva_id)
    if rid is None:
        return error("reserva_id inválido", 400)
    reserva = db.session.get(Reserva, rid)
    if reserva is None:
        return error("reserva no encontrada", 404, "no_encontrado")
    if str(usuario.rol) != "admin" and reserva.usuario_id != usuario.id:
        return error("solo el dueño o un admin puede ver la reserva", 403, "prohibido")
    return jsonify({
        "data": reserva_a_dict(reserva, _calcular_monto_estimado(reserva))
    }), 200


@bp.route("/reservas/<reserva_id>", methods=["DELETE"])
@jwt_required()
@roles_required("cliente", "admin")
def borrar_reserva(reserva_id):
    usuario, err = _actor()
    if err:
        return err
    rid = schemas.parse_uuid(reserva_id)
    if rid is None:
        return error("reserva_id inválido", 400)
    try:
        reserva = cancelar_reserva.ejecutar(usuario, rid)
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    return jsonify({"data": reserva_a_dict(reserva)}), 200
