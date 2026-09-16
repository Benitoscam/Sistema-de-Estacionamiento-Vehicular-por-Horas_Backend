"""Ingresos walk-in y salidas del operador (RF-03) — Fase 4.

Salida con pago en efectivo (opcional, default sin pago como en Fase 2B).
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.adapters.db.models import Pago, RegistroIngresoSalida
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.application.use_cases import registrar_ingreso, registrar_salida
from app.domain.excepciones import (
    ErrorDominio,
    EspacioNoDisponible,
    PermisoDenegado,
    RangoInvalido,
    RecursoNoEncontrado,
    ReservaNoCancelabe,
)
from app.extensions import db

bp = Blueprint("sesiones", __name__)
OPERATIVOS = ("operador", "admin")

CODIGOS = {
    RangoInvalido: "placa_invalida",
    EspacioNoDisponible: "espacio_no_disponible",
    ReservaNoCancelabe: "salida_duplicada",
    PermisoDenegado: "prohibido",
    RecursoNoEncontrado: "no_encontrado",
}


def _dominio_a_respuesta(exc):
    codigo = CODIGOS.get(type(exc), "error_dominio")
    return error(getattr(exc, "mensaje", str(exc)), exc.estado_http, codigo)


def registro_a_dict(registro, desglose=None):
    datos = {
        "id": str(registro.id),
        "espacio_id": str(registro.espacio_id),
        "espacio_codigo": registro.espacio.codigo if registro.espacio else None,
        "placa": registro.placa,
        "operador_id": str(registro.operador_id) if registro.operador_id else None,
        "hora_entrada": registro.hora_entrada.isoformat()
        if registro.hora_entrada
        else None,
        "hora_salida": registro.hora_salida.isoformat() if registro.hora_salida else None,
        "monto_cobrado": str(registro.monto_cobrado)
        if registro.monto_cobrado is not None
        else None,
    }
    if desglose:
        datos["desglose"] = desglose
    return datos


@bp.route("/ingresos", methods=["POST"])
@jwt_required()
@roles_required(*OPERATIVOS)
def crear_ingreso():
    from flask_jwt_extended import get_jwt_identity

    from app.adapters.db.models import Usuario

    usuario = db.session.get(Usuario, schemas.parse_uuid(get_jwt_identity()))
    if usuario is None:
        return error("usuario no encontrado", 401)
    datos = schemas.json_body(request)
    faltantes = schemas.missing_fields(datos, ("espacio_id", "placa"))
    if faltantes:
        return error(f"campos requeridos: {', '.join(faltantes)}", 400)
    espacio_id = schemas.parse_uuid(datos.get("espacio_id"))
    if espacio_id is None:
        return error("espacio_id inválido", 400)
    try:
        registro = registrar_ingreso.ejecutar(usuario, espacio_id, datos.get("placa"))
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    return jsonify({"data": registro_a_dict(registro)}), 201


@bp.route("/sesiones/activas", methods=["GET"])
@jwt_required()
@roles_required(*OPERATIVOS)
def sesiones_activas():
    consulta = RegistroIngresoSalida.query.filter(
        RegistroIngresoSalida.hora_salida.is_(None)
    )
    placa = (request.args.get("placa") or "").strip().upper()
    if placa:
        consulta = consulta.filter(RegistroIngresoSalida.placa == placa)
    registros = consulta.order_by(RegistroIngresoSalida.hora_entrada).all()
    return jsonify({"data": [registro_a_dict(r) for r in registros]}), 200


@bp.route("/salidas/<registro_id>", methods=["PUT"])
@jwt_required()
@roles_required(*OPERATIVOS)
def liquidar_salida(registro_id):
    rid = schemas.parse_uuid(registro_id)
    if rid is None:
        return error("registro_id inválido", 400)
    datos = schemas.json_body(request)
    metodo = (datos.get("metodo_pago") or "").strip().lower() or None
    if metodo and metodo != "efectivo":
        return error("metodo_pago inválido (solo efectivo o vacío)", 400)
    try:
        registro, monto = registrar_salida.ejecutar(rid)
    except ErrorDominio as exc:
        return _dominio_a_respuesta(exc)
    pago = None
    if metodo == "efectivo":
        from flask_jwt_extended import get_jwt_identity
        from app.adapters.db.models import Usuario

        operador = db.session.get(Usuario, schemas.parse_uuid(get_jwt_identity()))
        pago = Pago(
            registro_ingreso_id=registro.id,
            referencia_transaccion=f"efectivo-{registro.id}",
            monto=monto,
            metodo="efectivo",
            estado="confirmado",
        )
        db.session.add(pago)
        db.session.commit()
    tarifa = registro.espacio.zona.tarifa_por_hora if registro.espacio else None
    desglose = {
        "hora_entrada": registro.hora_entrada.isoformat(),
        "hora_salida": registro.hora_salida.isoformat(),
        "tarifa_por_hora": str(tarifa) if tarifa is not None else None,
        "monto_cobrado": str(monto),
    }
    return jsonify({"data": registro_a_dict(registro, desglose)}), 200
