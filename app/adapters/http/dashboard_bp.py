"""Dashboard operativo (RF-08) — Fase 3B. Lectura para admin y operador."""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.adapters.http.decorators import roles_required
from app.application import reportes

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard", methods=["GET"])
@jwt_required()
@roles_required("admin", "operador")
def dashboard():
    return jsonify({"data": reportes.obtener_dashboard()}), 200
