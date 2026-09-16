"""Analítica de demanda (RF-10) — Fase 4. Solo admin. Horas pico, permanencia, rotación."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.adapters.db.models import Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.application import reportes

bp = Blueprint("analitica", __name__)


@bp.route("/analitica", methods=["GET"])
@jwt_required()
@roles_required("admin")
def analitica():
    desde = reportes._parse_fecha(request.args.get("desde"))
    hasta = reportes._parse_fecha(request.args.get("hasta"))
    if (request.args.get("desde") and desde is None) or (
        request.args.get("hasta") and hasta is None
    ):
        return error("fechas inválidas (usar YYYY-MM-DD)", 400)
    zona_id = None
    zona_id_param = request.args.get("zona_id")
    if zona_id_param:
        uid = schemas.parse_uuid(zona_id_param)
        if uid is None:
            return error("zona_id inválido", 400)
        from app.extensions import db
        zona = db.session.get(Zona, uid)
        if zona is None:
            return error("zona no encontrada", 404, "no_encontrado")
        zona_id = zona.id
    datos = reportes.analitica_demanda(desde, hasta, zona_id)
    return jsonify({"data": datos}), 200
