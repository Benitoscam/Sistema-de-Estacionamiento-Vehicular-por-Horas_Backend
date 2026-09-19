"""Ocupación + disponibilidad por rango — Fase 1/2A (lectura)."""

from datetime import timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import case, func

from app.adapters.db.models import Espacio, Reserva, Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.domain.value_objects import RangoHorario
from app.extensions import db

bp = Blueprint("ocupacion", __name__)
READ_ROLES = ("admin", "operador", "cliente")


@bp.route("/ocupacion", methods=["GET"])
@jwt_required()
@roles_required(*READ_ROLES)
def ocupacion():
    zona = None
    zona_id = request.args.get("zona_id")
    if zona_id:
        uid = schemas.parse_uuid(zona_id)
        if uid is None:
            return error("zona_id inválido", 400)
        zona = db.session.get(Zona, uid)
        if not zona:
            return error("zona no encontrada", 404)

    base = Espacio.query.filter_by(zona_id=zona.id) if zona else Espacio.query
    total = base.count()

    por_estado = {e: 0 for e in schemas.ESPACIO_ESTADOS}
    rows = (
        base.with_entities(Espacio.estado, func.count(Espacio.id))
        .group_by(Espacio.estado)
        .all()
    )
    for estado, cantidad in rows:
        por_estado[str(estado)] = cantidad

    por_zona = []
    if zona is None:
        zrows = (
            db.session.query(
                Zona,
                func.count(Espacio.id),
                func.sum(case((Espacio.estado == "disponible", 1), else_=0)),
            )
            .outerjoin(Espacio, Espacio.zona_id == Zona.id)
            .group_by(Zona.id)
            .order_by(Zona.nombre)
            .all()
        )
        for z, ztotal, zdisp in zrows:
            por_zona.append(
                {
                    "zona_id": str(z.id),
                    "zona_nombre": str(z.nombre),
                    "tarifa_por_hora": str(z.tarifa_por_hora),
                    "total": ztotal or 0,
                    "disponibles": int(zdisp or 0),
                }
            )

    espacios = base.order_by(Espacio.codigo).all()
    return (
        jsonify(
            {
                "data": {
                    "total": total,
                    "por_estado": por_estado,
                    "por_zona": por_zona,
                    "espacios": [
                        {
                            "id": str(e.id),
                            "codigo": e.codigo,
                            "estado": str(e.estado),
                            "zona_id": str(e.zona_id),
                            "zona_nombre": str(e.zona.nombre) if e.zona else None,
                        }
                        for e in espacios
                    ],
                }
            }
        ),
        200,
    )


def _parse_iso(valor):
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


@bp.route("/disponibilidad", methods=["GET"])
@jwt_required()
@roles_required(*READ_ROLES)
def disponibilidad():
    """Espacios libres en un rango horario futuro.
    Excluye: mantenimiento + reservas confirmadas solapadas.
    """
    inicio = _parse_iso(request.args.get("inicio"))
    fin = _parse_iso(request.args.get("fin"))
    if inicio is None or fin is None:
        return error("parámetros inicio y fin requeridos (ISO 8601)", 400)
    try:
        rango = RangoHorario(inicio, fin)
    except Exception:
        return error("rango inválido: inicio debe ser anterior a fin", 400)

    zona_id = request.args.get("zona_id")
    if zona_id:
        uid = schemas.parse_uuid(zona_id)
        if uid is None:
            return error("zona_id inválido", 400)
        zona = db.session.get(Zona, uid)
        if not zona:
            return error("zona no encontrada", 404)

    base = Espacio.query.filter_by(zona_id=zona.id) if zona_id else Espacio.query

    espacios_base = base.filter(Espacio.estado != "mantenimiento").all()
    ids_disponibles = set()
    for e in espacios_base:
        ids_disponibles.add(e.id)

    conflictivas = (
        Reserva.query.filter(
            Reserva.estado == "confirmada",
            Reserva.hora_inicio_planeada < rango.fin,
            Reserva.hora_fin_planeada > rango.inicio,
        )
        .all()
    )
    for r in conflictivas:
        ids_disponibles.discard(r.espacio_id)

    espacios_filtrados = [
        e for e in espacios_base if e.id in ids_disponibles
    ]
    espacios_filtrados.sort(key=lambda e: e.codigo)

    por_zona = {}
    for e in espacios_filtrados:
        zid = str(e.zona_id)
        if zid not in por_zona:
            por_zona[zid] = {
                "zona_id": zid,
                "zona_nombre": str(e.zona.nombre) if e.zona else None,
                "tarifa_por_hora": str(e.zona.tarifa_por_hora) if e.zona else "0",
                "disponibles": 0,
            }
        por_zona[zid]["disponibles"] += 1

    return (
        jsonify(
            {
                "data": {
                    "inicio": rango.inicio.isoformat(),
                    "fin": rango.fin.isoformat(),
                    "total_disponibles": len(espacios_filtrados),
                    "por_zona": list(por_zona.values()),
                    "espacios": [
                        {
                            "id": str(e.id),
                            "codigo": e.codigo,
                            "zona_id": str(e.zona_id),
                            "zona_nombre": str(e.zona.nombre) if e.zona else None,
                            "tarifa_por_hora": str(e.zona.tarifa_por_hora) if e.zona else "0",
                        }
                        for e in espacios_filtrados
                    ],
                }
            }
        ),
        200,
    )
