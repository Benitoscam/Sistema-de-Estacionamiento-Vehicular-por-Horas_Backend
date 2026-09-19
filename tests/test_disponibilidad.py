"""Disponibilidad por rango — tests del endpoint GET /api/disponibilidad."""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.adapters.db.models import Espacio, Reserva, Usuario


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def test_disponibilidad_slot_libre(client, db):
    """Sin reservas en el rango → todos los espacios libres."""
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    ahora = datetime.now(timezone.utc)
    inicio = quote((ahora + timedelta(hours=24)).isoformat())
    fin = quote((ahora + timedelta(hours=28)).isoformat())

    res = client.get(f"/api/disponibilidad?inicio={inicio}&fin={fin}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total_disponibles"] > 0
    assert len(data["espacios"]) > 0
    for e in data["espacios"]:
        assert "zona_nombre" in e
        assert "tarifa_por_hora" in e


def test_disponibilidad_con_solape(client, db):
    """Reserva confirmada solapada → ese espacio no aparece."""
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    ahora = datetime.now(timezone.utc)
    inicio_r = (ahora + timedelta(hours=36)).isoformat()
    fin_r = (ahora + timedelta(hours=40)).isoformat()

    espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == "A-01")

    # Crear reserva
    c = client.post(
        "/api/reservas",
        json={
            "espacio_id": espacio_id,
            "hora_inicio_planeada": inicio_r,
            "hora_fin_planeada": fin_r,
            "placa": "DISP01",
        },
        headers=headers,
    )
    assert c.status_code == 201

    try:
        # Buscar en ese rango exacto
        res = client.get(
            f"/api/disponibilidad?inicio={quote(inicio_r)}&fin={quote(fin_r)}",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        ids = [e["id"] for e in data["espacios"]]
        assert espacio_id not in ids
    finally:
        db.session.query(Reserva).filter_by(espacio_id=espacio_id, estado="confirmada").delete()
        db.session.commit()


def test_disponibilidad_rango_invalido(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    ahora = datetime.now(timezone.utc)
    inicio = quote((ahora + timedelta(hours=28)).isoformat())
    fin = quote((ahora + timedelta(hours=24)).isoformat())

    res = client.get(f"/api/disponibilidad?inicio={inicio}&fin={fin}", headers=headers)
    assert res.status_code == 400


def test_disponibilidad_sin_parametros(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/disponibilidad", headers=headers)
    assert res.status_code == 400


def test_disponibilidad_filtro_zona(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    ahora = datetime.now(timezone.utc)
    inicio = quote((ahora + timedelta(hours=24)).isoformat())
    fin = quote((ahora + timedelta(hours=28)).isoformat())

    res = client.get(
        f"/api/disponibilidad?inicio={inicio}&fin={fin}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["por_zona"]) >= 1


def test_disponibilidad_sin_auth(client, db):
    ahora = datetime.now(timezone.utc)
    inicio = quote((ahora + timedelta(hours=24)).isoformat())
    fin = quote((ahora + timedelta(hours=28)).isoformat())

    res = client.get(f"/api/disponibilidad?inicio={inicio}&fin={fin}")
    assert res.status_code == 401
