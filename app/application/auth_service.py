"""Servicio de autenticación — Fase 1.

Registro público solo como cliente (anti-escalamiento de privilegios),
login con bcrypt y JWT (claims: id en `sub`, `rol` en claims).
"""

import re

import bcrypt
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.adapters.db.models import Usuario

ALLOWED_ROLES = ("admin", "operador", "cliente")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JWT_EXPIRES_SECONDS = 8 * 3600


class AuthError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def public_user(user):
    """Serializa usuario sin exponer password_hash (regla de seguridad)."""
    return {
        "id": str(user.id),
        "nombre": user.nombre,
        "correo": user.correo,
        "telefono": user.telefono,
        "rol": str(user.rol),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _normalize_correo(correo):
    return (correo or "").strip().lower()


def _validate_email(correo):
    return bool(correo) and EMAIL_RE.match(correo) is not None


def register(nombre, correo, password, telefono=None):
    """Registro público. Siempre crea rol cliente."""
    nombre = (nombre or "").strip()
    correo = _normalize_correo(correo)
    telefono = (telefono or "").strip() or None

    if not nombre:
        raise AuthError("nombre es requerido", 400)
    if not _validate_email(correo):
        raise AuthError("correo inválido", 400)
    if not password or len(password) < 8:
        raise AuthError("password debe tener al menos 8 caracteres", 400)
    if Usuario.query.filter_by(correo=correo).first():
        raise AuthError("correo ya registrado", 409)

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = Usuario(
        nombre=nombre,
        correo=correo,
        telefono=telefono,
        password_hash=password_hash,
        rol="cliente",
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise AuthError("correo ya registrado", 409)
    return user


def authenticate(correo, password):
    correo = _normalize_correo(correo)
    user = Usuario.query.filter_by(correo=correo).first()
    if not user or not password:
        raise AuthError("credenciales inválidas", 401)
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        raise AuthError("credenciales inválidas", 401)
    return user


def token_for(user):
    return create_access_token(
        identity=str(user.id),
        additional_claims={"rol": str(user.rol)},
    )
