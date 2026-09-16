"""Respuestas de error JSON uniformes — Fase 1."""

from flask import jsonify


def error(message, status, code=None):
    payload = {"error": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status


def register_error_handlers(app, jwt):
    @app.errorhandler(400)
    def bad_request(_e):
        return error("solicitud_invalida", 400)

    @app.errorhandler(404)
    def not_found(_e):
        return error("no_encontrado", 404)

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return error("metodo_no_permitido", 405)

    @app.errorhandler(500)
    def internal(_e):
        app.logger.exception("unhandled error")
        return error("error_interno", 500)

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "autorizacion_requerida", "detail": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "token_invalido", "detail": reason}), 422

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "token_expirado"}), 401
