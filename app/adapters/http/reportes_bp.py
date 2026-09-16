"""Reportes de ingresos por zona (RF-09) — Fase 3B. Solo admin. JSON o PDF."""

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from app.adapters.db.models import Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.adapters.pdf import comprobantes as pdf
from app.application import reportes

bp = Blueprint("reportes", __name__)


def _filtros():
    desde = reportes._parse_fecha(request.args.get("desde"))
    hasta = reportes._parse_fecha(request.args.get("hasta"))
    if (request.args.get("desde") and desde is None) or (
        request.args.get("hasta") and hasta is None
    ):
        return None, error("fechas inválidas (usar YYYY-MM-DD)", 400)
    zona_id = request.args.get("zona_id")
    zona = None
    if zona_id:
        uid = schemas.parse_uuid(zona_id)
        if uid is None:
            return None, error("zona_id inválido", 400)
        from app.extensions import db

        zona = db.session.get(Zona, uid)
        if zona is None:
            return None, error("zona no encontrada", 404, "no_encontrado")
    return (desde, hasta, zona.id if zona else None), None


@bp.route("/reportes/ingresos", methods=["GET"])
@jwt_required()
@roles_required("admin")
def ingresos():
    filtros, err = _filtros()
    if err:
        return err
    desde, hasta, zona_id = filtros
    filas, totales = reportes.ingresos_por_zona(desde, hasta, zona_id)
    formato = (request.args.get("formato") or "json").strip().lower()
    if formato == "pdf":
        contenido = pdf.reporte_ingresos(
            str(desde or "inicio"), str(hasta or "hoy"), filas, totales
        )
        nombre = f"reporte-ingresos-{desde or 'inicio'}-{hasta or 'hoy'}.pdf"
        return Response(
            contenido,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={nombre}"},
        )
    return (
        jsonify(
            {
                "data": {
                    "desde": str(desde) if desde else None,
                    "hasta": str(hasta) if hasta else None,
                    "zonas": filas,
                    "totales": totales,
                }
            }
        ),
        200,
    )
