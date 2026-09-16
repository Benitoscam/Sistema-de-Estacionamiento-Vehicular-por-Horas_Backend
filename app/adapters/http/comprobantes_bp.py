"""Comprobantes PDF con QR (RF-05) — Fase 3B. En memoria, sin archivos."""

from flask import Blueprint, Response
from flask_jwt_extended import jwt_required

from app.adapters.db.models import Pago, RegistroIngresoSalida, Reserva, Usuario
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.adapters.pdf import comprobantes as pdf
from app.extensions import db

bp = Blueprint("comprobantes", __name__)


def _actor():
    from flask_jwt_extended import get_jwt_identity

    usuario_id = schemas.parse_uuid(get_jwt_identity())
    if usuario_id is None:
        return None, error("identidad inválida", 401)
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return None, error("usuario no encontrado", 401)
    return usuario, None


def _pdf(datos, nombre):
    return Response(
        datos,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre}"},
    )


@bp.route("/comprobantes/reservas/<reserva_id>", methods=["GET"])
@jwt_required()
@roles_required("cliente", "admin")
def comprobante_reserva(reserva_id):
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
        return error("solo el dueño o un admin puede ver el comprobante", 403, "prohibido")
    pago = Pago.query.filter_by(reserva_id=reserva.id, estado="confirmado").first()
    if pago is None:
        return error("la reserva no tiene pago confirmado", 409, "sin_pago")
    contenido = pdf.comprobante_reserva(
        {
            "referencia": pago.referencia_transaccion,
            "plaza": reserva.espacio.codigo,
            "zona": str(reserva.espacio.zona.nombre),
            "cliente": reserva.cliente.nombre,
            "correo": reserva.cliente.correo,
            "inicio": reserva.hora_inicio_planeada.isoformat(),
            "fin": reserva.hora_fin_planeada.isoformat(),
            "tarifa": str(reserva.espacio.zona.tarifa_por_hora),
            "monto_pagado": str(pago.monto),
            "estado": str(reserva.estado),
            "codigo_qr": f"RESERVA:{reserva.id}:{pago.referencia_transaccion}",
        }
    )
    return _pdf(contenido, f"comprobante-reserva-{reserva.espacio.codigo}.pdf")


@bp.route("/comprobantes/sesiones/<registro_id>", methods=["GET"])
@jwt_required()
@roles_required("operador", "admin")
def comprobante_sesion(registro_id):
    rid = schemas.parse_uuid(registro_id)
    if rid is None:
        return error("registro_id inválido", 400)
    registro = db.session.get(RegistroIngresoSalida, rid)
    if registro is None:
        return error("registro no encontrado", 404, "no_encontrado")
    if registro.hora_salida is None or registro.monto_cobrado is None:
        return error("la sesión aún no está liquidada", 409, "sin_liquidar")
    contenido = pdf.comprobante_sesion(
        {
            "plaza": registro.espacio.codigo,
            "zona": str(registro.espacio.zona.nombre),
            "placa": registro.placa,
            "operador": registro.operador.nombre if registro.operador else "—",
            "entrada": registro.hora_entrada.isoformat(),
            "salida": registro.hora_salida.isoformat(),
            "tarifa": str(registro.espacio.zona.tarifa_por_hora),
            "monto_cobrado": str(registro.monto_cobrado),
            "codigo_qr": f"SESION:{registro.id}:{registro.placa}",
        }
    )
    return _pdf(contenido, f"comprobante-sesion-{registro.placa}.pdf")
