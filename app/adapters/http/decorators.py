"""RBAC — Fase 1. Lee `rol` del JWT, 403 si no corresponde."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def roles_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in allowed_roles:
                return (
                    jsonify(
                        {
                            "error": "prohibido",
                            "detail": "rol sin permiso para esta acción",
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
