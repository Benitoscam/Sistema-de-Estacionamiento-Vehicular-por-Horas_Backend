"""Espacios: lectura 3 roles, gestión solo admin — Fase 1."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app.adapters.db.models import Espacio, Zona
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.extensions import db

bp = Blueprint("espacios", __name__)
READ_ROLES = ("admin", "operador", "cliente")


def espacio_to_dict(espacio):
    return {
        "id": str(espacio.id),
        "codigo": espacio.codigo,
        "estado": str(espacio.estado),
        "zona_id": str(espacio.zona_id),
        "zona_nombre": str(espacio.zona.nombre) if espacio.zona else None,
    }


def _zona_or_error(zona_id):
    uid = schemas.parse_uuid(zona_id)
    if uid is None:
        return None, error("zona_id inválido", 400)
    zona = db.session.get(Zona, uid)
    if not zona:
        return None, error("zona no encontrada", 404)
    return zona, None


@bp.route("/espacios", methods=["GET"])
@jwt_required()
@roles_required(*READ_ROLES)
def list_espacios():
    query = Espacio.query
    zona_id = request.args.get("zona_id")
    if zona_id:
        zona, err = _zona_or_error(zona_id)
        if err:
            _, status = err
            return err
        query = query.filter_by(zona_id=zona.id)
    estado = (request.args.get("estado") or "").strip()
    if estado:
        if estado not in schemas.ESPACIO_ESTADOS:
            return error(
                f"estado debe ser uno de: {', '.join(schemas.ESPACIO_ESTADOS)}", 400
            )
        query = query.filter_by(estado=estado)
    espacios = query.order_by(Espacio.codigo).all()
    return jsonify({"data": [espacio_to_dict(e) for e in espacios]}), 200


@bp.route("/espacios", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_espacio():
    data = schemas.json_body(request)
    missing = schemas.missing_fields(data, ("codigo", "zona_id"))
    if missing:
        return error(f"campos requeridos: {', '.join(missing)}", 400)
    codigo = (data.get("codigo") or "").strip().upper()
    if not codigo or len(codigo) > 10:
        return error("codigo inválido (máx 10 caracteres)", 400)
    zona, err = _zona_or_error(data.get("zona_id"))
    if err:
        return err
    estado = (data.get("estado") or "disponible").strip()
    if estado not in schemas.ESPACIO_ESTADOS:
        return error(f"estado debe ser uno de: {', '.join(schemas.ESPACIO_ESTADOS)}", 400)
    if Espacio.query.filter_by(codigo=codigo).first():
        return error("codigo ya existe", 409)
    espacio = Espacio(codigo=codigo, zona_id=zona.id, estado=estado)
    db.session.add(espacio)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("codigo ya existe", 409)
    return jsonify({"data": espacio_to_dict(espacio)}), 201


@bp.route("/espacios/<espacio_id>", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_espacio(espacio_id):
    uid = schemas.parse_uuid(espacio_id)
    if uid is None:
        return error("espacio_id inválido", 400)
    espacio = db.session.get(Espacio, uid)
    if not espacio:
        return error("espacio no encontrado", 404)
    data = schemas.json_body(request)
    if "codigo" in data:
        codigo = (data.get("codigo") or "").strip().upper()
        if not codigo or len(codigo) > 10:
            return error("codigo inválido (máx 10 caracteres)", 400)
        dupe = Espacio.query.filter_by(codigo=codigo).first()
        if dupe and dupe.id != espacio.id:
            return error("codigo ya existe", 409)
        espacio.codigo = codigo
    if "zona_id" in data:
        zona, err = _zona_or_error(data.get("zona_id"))
        if err:
            return err
        espacio.zona_id = zona.id
    if "estado" in data:
        estado = (data.get("estado") or "").strip()
        if estado not in schemas.ESPACIO_ESTADOS:
            return error(
                f"estado debe ser uno de: {', '.join(schemas.ESPACIO_ESTADOS)}", 400
            )
        espacio.estado = estado
    db.session.commit()
    return jsonify({"data": espacio_to_dict(espacio)}), 200
