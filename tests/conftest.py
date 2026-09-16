import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """App Flask para tests. Usa parqueo_db (única DB del proyecto)."""
    app = create_app()
    app.config.update(TESTING=True)
    yield app


@pytest.fixture(scope="function")
def client(app):
    """Cliente HTTP de Flask para tests de endpoints."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Acceso a la extensión db dentro de app_context.

    Fase 1: sin DB separada de tests y sin reasignar la sesión
    (Flask-SQLAlchemy 3.x ya no tiene create_scoped_session).
    Los tests que escriban vía `client` deben borrar sus datos
    (ej. usuario test_...) en teardown: el rollback aquí no los cubre.
    """
    with app.app_context():
        yield _db
        _db.session.remove()


@pytest.fixture(scope="function")
def runner(app):
    """Runner CLI para tests de comandos Flask."""
    return app.test_cli_runner()