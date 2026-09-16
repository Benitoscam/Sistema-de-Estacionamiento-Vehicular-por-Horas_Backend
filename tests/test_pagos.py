"""Pagos checkout — Fase 3A (modo fake). Crea, confirma y limpia lo creado."""

from datetime import datetime, timedelta, timezone

from app.adapters.db.models import Espacio, Pago, Reserva, Usuario


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def _reservar(client, headers, codigo="A-04"):
    espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == codigo)
    inicio = datetime.now(timezone.utc) + timedelta(days=3)
    fin = inicio + timedelta(hours=4)
    res = client.post(
        "/api/reservas",
        json={
            "espacio_id": espacio_id,
            "hora_inicio_planeada": inicio.isoformat(),
            "hora_fin_planeada": fin.isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.get_json()["data"]["id"]


def test_checkout_webhook_fake_confirmar_con_limpieza(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    reserva_id = _reservar(client, headers)
    pago_id = None
    try:
        checkout = client.post(
            "/api/pagos/checkout", json={"reserva_id": reserva_id}, headers=headers
        )
        assert checkout.status_code == 201
        datos = checkout.get_json()["data"]
        assert datos["estado"] == "pendiente"
        assert datos["monto"] == "14.00"
        assert datos["checkout_url"].startswith("http")
        assert "password" not in checkout.get_data(as_text=True).lower()
        pago_id = datos["id"]
        referencia = datos["referencia_transaccion"]

        dupe = client.post(
            "/api/pagos/checkout", json={"reserva_id": reserva_id}, headers=headers
        )
        assert dupe.status_code == 409

        webhook = client.post("/api/webhooks/stripe", json={"referencia": referencia})
        assert webhook.status_code == 200
        assert webhook.get_json()["data"]["confirmado"] is True

        reintento = client.post("/api/webhooks/stripe", json={"referencia": referencia})
        assert reintento.status_code == 200
        assert reintento.get_json()["data"]["nuevo"] is False

        confirmada = client.post(
            "/api/pagos/fake-confirmar", json={"pago_id": pago_id}, headers=headers
        )
        assert confirmada.status_code == 200
        assert confirmada.get_json()["data"]["estado"] == "confirmado"

        detalle = client.get(f"/api/reservas/{reserva_id}", headers=headers)
        assert detalle.status_code == 200
        assert detalle.get_json()["data"]["monto_pagado"] == "14.00"

        mios = client.get("/api/pagos/mios", headers=headers)
        assert mios.status_code == 200
        assert any(p["id"] == pago_id for p in mios.get_json()["data"])

        malo = client.post("/api/webhooks/stripe", json={"sin": "referencia"})
        assert malo.status_code == 400
    finally:
        if pago_id is not None:
            db.session.query(Pago).filter_by(id=pago_id).delete()
        db.session.query(Reserva).filter_by(id=reserva_id).delete()
        db.session.query(Espacio).filter_by(codigo="A-04").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_checkout_ajena_prohibido(client, db):
    token_a = _token(client, "cliente@parqueo.test")
    head_a = {"Authorization": f"Bearer {token_a}"}
    reserva_id = _reservar(client, head_a)
    correo_b = "test_pago@parqueo.test"
    try:
        reg = client.post(
            "/api/auth/register",
            json={"nombre": "Pago", "correo": correo_b, "password": "Test123*"},
        )
        assert reg.status_code == 201
        token_b = _token(client, correo_b)
        ajena = client.post(
            "/api/pagos/checkout",
            json={"reserva_id": reserva_id},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert ajena.status_code == 403

        anon = client.post("/api/pagos/checkout", json={"reserva_id": reserva_id})
        assert anon.status_code == 401
    finally:
        db.session.query(Pago).filter(Pago.reserva_id == reserva_id).delete()
        db.session.query(Reserva).filter_by(id=reserva_id).delete()
        db.session.query(Espacio).filter_by(codigo="A-04").update(
            {"estado": "disponible"}
        )
        db.session.query(Usuario).filter_by(correo=correo_b).delete()
        db.session.commit()
