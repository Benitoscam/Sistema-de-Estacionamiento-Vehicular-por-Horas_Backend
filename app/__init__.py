from flask import Flask
from app.config import config
from app.extensions import db, jwt, cors, migrate


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Inicializar extensiones con la app
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_URL"]}})
    migrate.init_app(app, db)

    # Importar modelos para que Flask-Migrate los detecte
    from app.adapters.db import models # noqa: F401

    # Registrar blueprints (rutas HTTP)
    from app.adapters.http import (
        auth_bp,
        espacios_bp,
        ocupacion_bp,
        pagos_bp,
        reservas_bp,
        sesiones_bp,
        webhooks_bp,
        zonas_bp,
    )
    from app.adapters.http.errors import register_error_handlers

    app.register_blueprint(auth_bp.bp, url_prefix="/api")
    app.register_blueprint(zonas_bp.bp, url_prefix="/api")
    app.register_blueprint(espacios_bp.bp, url_prefix="/api")
    app.register_blueprint(ocupacion_bp.bp, url_prefix="/api")
    app.register_blueprint(reservas_bp.bp, url_prefix="/api")
    app.register_blueprint(sesiones_bp.bp, url_prefix="/api")
    app.register_blueprint(pagos_bp.bp, url_prefix="/api")
    app.register_blueprint(webhooks_bp.bp, url_prefix="/api")
    register_error_handlers(app, jwt)

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "estacionamiento-backend"}, 200

    return app