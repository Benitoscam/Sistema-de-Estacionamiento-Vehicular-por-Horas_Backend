"""Auth — Fase 1. No destructivo: crea test_... y lo borra en teardown."""

import uuid

from app.adapters.db.models import Usuario


def _unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@parqueo.test"


def test_register_login_me_con_limpieza(client, db):
    correo = _unique_email()
    try:
        res = client.post(
            "/api/auth/register",
            json={"nombre": "Test", "correo": correo, "password": "Test123*"},
        )
        assert res.status_code == 201
        body = res.get_json()["data"]
        assert body["correo"] == correo
        assert body["rol"] == "cliente"
        assert "password_hash" not in res.get_data(as_text=True)

        dupe = client.post(
            "/api/auth/register",
            json={"nombre": "Test", "correo": correo, "password": "Test123*"},
        )
        assert dupe.status_code == 409

        login = client.post(
            "/api/auth/login",
            json={"correo": correo, "password": "Test123*"},
        )
        assert login.status_code == 200
        token = login.get_json()["data"]["access_token"]

        bad = client.post(
            "/api/auth/login",
            json={"correo": correo, "password": "ClaveMala123"},
        )
        assert bad.status_code == 401

        me = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 200
        assert me.get_json()["data"]["correo"] == correo

        anon = client.get("/api/auth/me")
        assert anon.status_code == 401
    finally:
        db.session.query(Usuario).filter_by(correo=correo).delete()
        db.session.commit()


def test_register_rechaza_rol_admin(client):
    res = client.post(
        "/api/auth/register",
        json={
            "nombre": "Test",
            "correo": _unique_email(),
            "password": "Test123*",
            "rol": "admin",
        },
    )
    assert res.status_code == 403
