"""Zonas: lectura 3 roles, gestión solo admin — Fase 1."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app.adapters.db.models import Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.extensions import db

bp = Blueprint("zonas", __name__)
READ_ROLES = ("admin", "operador", "cliente")


def zona_to_dict(zona):
    return {
        "id": str(zona.id),
        "nombre": str(zona.nombre),
        "descripcion": zona.descripcion,
        "tarifa_por_hora": str(zona.tarifa_por_hora),
    }


@bp.route("/zonas", methods=["GET"])
@jwt_required()
@roles_required(*READ_ROLES)
def list_zonas():
    zonas = Zona.query.order_by(Zona.nombre).all()
    return jsonify({"data": [zona_to_dict(z) for z in zonas]}), 200


@bp.route("/zonas", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_zona():
    data = schemas.json_body(request)
    missing = schemas.missing_fields(data, ("nombre", "tarifa_por_hora"))
    if missing:
        return error(f"campos requeridos: {', '.join(missing)}", 400)
    nombre = (data.get("nombre") or "").strip()
    if nombre not in schemas.ZONA_NOMBRES:
        return error(f"nombre debe ser uno de: {', '.join(schemas.ZONA_NOMBRES)}", 400)
    tarifa = schemas.to_tarifa(data.get("tarifa_por_hora"))
    if tarifa is None:
        return error("tarifa_por_hora debe ser un monto positivo", 400)
    if Zona.query.filter_by(nombre=nombre).first():
        return error("zona ya existe", 409)
    zona = Zona(
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        tarifa_por_hora=tarifa,
    )
    db.session.add(zona)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("zona ya existe", 409)
    return jsonify({"data": zona_to_dict(zona)}), 201


@bp.route("/zonas/<zona_id>", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_zona(zona_id):
    uid = schemas.parse_uuid(zona_id)
    if uid is None:
        return error("zona_id inválido", 400)
    zona = db.session.get(Zona, uid)
    if not zona:
        return error("zona no encontrada", 404)
    data = schemas.json_body(request)
    if "nombre" in data:
        nombre = (data.get("nombre") or "").strip()
        if nombre not in schemas.ZONA_NOMBRES:
            return error(f"nombre debe ser uno de: {', '.join(schemas.ZONA_NOMBRES)}", 400)
        dupe = Zona.query.filter_by(nombre=nombre).first()
        if dupe and dupe.id != zona.id:
            return error("zona ya existe", 409)
        zona.nombre = nombre
    if "tarifa_por_hora" in data:
        tarifa = schemas.to_tarifa(data.get("tarifa_por_hora"))
        if tarifa is None:
            return error("tarifa_por_hora debe ser un monto positivo", 400)
        zona.tarifa_por_hora = tarifa
    if "descripcion" in data:
        zona.descripcion = (data.get("descripcion") or "").strip() or None
    db.session.commit()
    return jsonify({"data": zona_to_dict(zona)}), 200
