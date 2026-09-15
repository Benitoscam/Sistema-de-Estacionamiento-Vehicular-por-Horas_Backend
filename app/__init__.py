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

    # Registrar blueprints (rutas HTTP)
    from app.adapters.http import reservation_routes
    app.register_blueprint(reservation_routes.bp, url_prefix="/api")

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "estacionamiento-backend"}, 200

    return app