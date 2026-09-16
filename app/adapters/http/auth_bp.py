"""Auth: registro público (solo cliente), login y perfil — Fase 1."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.adapters.db.models import Usuario
from app.adapters.http import schemas
from app.adapters.http.decorators import roles_required
from app.adapters.http.errors import error
from app.extensions import db
from app.application.auth_service import (
    JWT_EXPIRES_SECONDS,
    AuthError,
    authenticate,
    public_user,
    register,
    token_for,
)

bp = Blueprint("auth", __name__)


@bp.route("/auth/register", methods=["POST"])
def register_route():
    data = schemas.json_body(request)
    if data.get("rol", "cliente") != "cliente":
        return error("solo se permite registro como cliente", 403)
    missing = schemas.missing_fields(data, ("nombre", "correo", "password"))
    if missing:
        return error(f"campos requeridos: {', '.join(missing)}", 400)
    try:
        user = register(
            nombre=data.get("nombre"),
            correo=data.get("correo"),
            password=data.get("password"),
            telefono=data.get("telefono"),
        )
    except AuthError as exc:
        return error(exc.message, exc.status_code)
    return jsonify({"data": public_user(user)}), 201


@bp.route("/auth/login", methods=["POST"])
def login_route():
    data = schemas.json_body(request)
    missing = schemas.missing_fields(data, ("correo", "password"))
    if missing:
        return error(f"campos requeridos: {', '.join(missing)}", 400)
    try:
        user = authenticate(data.get("correo"), data.get("password"))
    except AuthError as exc:
        return error(exc.message, exc.status_code)
    return (
        jsonify(
            {
                "data": {
                    "access_token": token_for(user),
                    "token_type": "Bearer",
                    "expires_in": JWT_EXPIRES_SECONDS,
                    "user": public_user(user),
                }
            }
        ),
        200,
    )


@bp.route("/auth/me", methods=["GET"])
@jwt_required()
@roles_required("admin", "operador", "cliente")
def me_route():
    user_id = schemas.parse_uuid(get_jwt_identity())
    if user_id is None:
        return error("identidad inválida", 401)
    user = db.session.get(Usuario, user_id)
    if not user:
        return error("usuario no encontrado", 404)
    return jsonify({"data": public_user(user)}), 200
