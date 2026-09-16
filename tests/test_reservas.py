"""Reservas — Fase 2A. Crea, solapa, cancela y limpia lo creado."""

from datetime import datetime, timedelta, timezone

from app.adapters.db.models import Espacio, Reserva, Usuario


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def _horas_futuras(desde_horas=24, duracion=4):
    inicio = datetime.now(timezone.utc) + timedelta(hours=desde_horas)
    return inicio.isoformat(), (inicio + timedelta(hours=duracion)).isoformat()


def _estado_espacio(client, headers, codigo):
    res = client.get("/api/espacios", headers=headers)
    assert res.status_code == 200
    for espacio in res.get_json()["data"]:
        if espacio["codigo"] == codigo:
            return espacio["estado"]
    raise AssertionError(f"espacio {codigo} no encontrado")


def test_reservar_solapar_cancelar_con_limpieza(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    inicio, fin = _horas_futuras()
    reserva_id = None
    try:
        espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
        espacio_id = next(e["id"] for e in espacios if e["codigo"] == "A-01")

        creada = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
            },
            headers=headers,
        )
        assert creada.status_code == 201
        datos = creada.get_json()["data"]
        assert datos["estado"] == "confirmada"
        assert datos["monto_estimado"] == "14.00"
        assert datos["monto_pagado"] is None
        reserva_id = datos["id"]
        assert _estado_espacio(client, headers, "A-01") == "reservado"

        solape = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
            },
            headers=headers,
        )
        assert solape.status_code == 409

        rango_malo = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": fin,
                "hora_fin_planeada": inicio,
            },
            headers=headers,
        )
        assert rango_malo.status_code == 400

        propias = client.get("/api/mis-reservas", headers=headers)
        assert propias.status_code == 200
        assert any(r["id"] == reserva_id for r in propias.get_json()["data"])

        detalle = client.get(f"/api/reservas/{reserva_id}", headers=headers)
        assert detalle.status_code == 200

        anon = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
            },
        )
        assert anon.status_code == 401

        cancelada = client.delete(f"/api/reservas/{reserva_id}", headers=headers)
        assert cancelada.status_code == 200
        assert cancelada.get_json()["data"]["estado"] == "cancelada"
        assert _estado_espacio(client, headers, "A-01") == "disponible"
        reserva_id = None
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
            db.session.query(Espacio).filter_by(codigo="A-01").update(
                {"estado": "disponible"}
            )
            db.session.commit()


def test_cancelar_reserva_ajena_prohibido(client, db):
    token_a = _token(client, "cliente@parqueo.test")
    head_a = {"Authorization": f"Bearer {token_a}"}
    inicio, fin = _horas_futuras(desde_horas=48)
    reserva_id = None
    correo_b = "test_otro@parqueo.test"
    try:
        espacios = client.get("/api/espacios", headers=head_a).get_json()["data"]
        espacio_id = next(e["id"] for e in espacios if e["codigo"] == "A-02")
        creada = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
            },
            headers=head_a,
        )
        assert creada.status_code == 201
        reserva_id = creada.get_json()["data"]["id"]

        reg = client.post(
            "/api/auth/register",
            json={"nombre": "Otro", "correo": correo_b, "password": "Test123*"},
        )
        assert reg.status_code == 201
        token_b = _token(client, correo_b)
        ajena = client.delete(
            f"/api/reservas/{reserva_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert ajena.status_code == 403

        propia = client.delete(f"/api/reservas/{reserva_id}", headers=head_a)
        assert propia.status_code == 200
        reserva_id = None
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
            db.session.query(Espacio).filter_by(codigo="A-02").update(
                {"estado": "disponible"}
            )
            db.session.commit()
        db.session.query(Usuario).filter_by(correo=correo_b).delete()
        db.session.commit()
