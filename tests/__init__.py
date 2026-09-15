import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def db(app):
    """Cada test corre dentro de una transacción que se revierte al final."""
    connection = _db.engine.connect()
    transaction = connection.begin()

    # Bind de la sesión a esa conexión
    _db.session = _db.create_scoped_session(
        options={"bind": connection, "binds": {}}
    )

    yield _db

    _db.session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()