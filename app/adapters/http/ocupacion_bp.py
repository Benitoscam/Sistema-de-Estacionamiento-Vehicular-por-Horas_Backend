"""Ocupación para polling del dashboard — Fase 1 (solo lectura)."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import case, func

from app.adapters.db.models import Espacio, Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
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
