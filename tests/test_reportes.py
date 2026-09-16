"""Dashboard, comprobantes y reportes — Fase 3B. Lectura + PDFs en memoria."""


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def test_dashboard_roles(client):
    admin = {"Authorization": "Bearer " + _token(client, "admin@parqueo.test")}
    res = client.get("/api/dashboard", headers=admin)
    assert res.status_code == 200
    datos = res.get_json()["data"]
    assert datos["ocupacion"]["total_espacios"] >= 12
    assert set(datos["ocupacion"]["por_estado"]) == {
        "disponible",
        "reservado",
        "ocupado",
        "mantenimiento",
    }
    assert "total" in datos["ingresos"]

    operario = {"Authorization": "Bearer " + _token(client, "operador@parqueo.test")}
    assert client.get("/api/dashboard", headers=operario).status_code == 200

    cliente = {"Authorization": "Bearer " + _token(client, "cliente@parqueo.test")}
    assert client.get("/api/dashboard", headers=cliente).status_code == 403
    assert client.get("/api/dashboard").status_code == 401


def test_comprobante_reserva_con_limpieza(client, db):
    from datetime import datetime, timedelta, timezone

    from app.adapters.db.models import Espacio, Pago, Reserva

    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == "M-01")
    inicio = datetime.now(timezone.utc) + timedelta(days=6)
    reserva_id = pago_id = None
    try:
        reserva = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio.isoformat(),
                "hora_fin_planeada": (inicio + timedelta(hours=2)).isoformat(),
            },
            headers=headers,
        ).get_json()["data"]
        reserva_id = reserva["id"]

        antes = client.get(f"/api/comprobantes/reservas/{reserva_id}", headers=headers)
        assert antes.status_code == 409

        pago = client.post(
            "/api/pagos/checkout", json={"reserva_id": reserva_id}, headers=headers
        ).get_json()["data"]
        pago_id = pago["id"]
        client.post("/api/webhooks/stripe", json={"referencia": pago["referencia_transaccion"]})

        pdf = client.get(f"/api/comprobantes/reservas/{reserva_id}", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content_type == "application/pdf"
        assert pdf.data[:5] == b"%PDF-"
        assert "attachment" in pdf.headers.get("Content-Disposition", "")
    finally:
        if pago_id is not None:
            db.session.query(Pago).filter_by(id=pago_id).delete()
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
        db.session.query(Espacio).filter_by(codigo="M-01").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_comprobante_sesion_y_reportes(client, db):
    from app.adapters.db.models import Espacio, RegistroIngresoSalida

    token_op = _token(client, "operador@parqueo.test")
    head_op = {"Authorization": f"Bearer {token_op}"}
    espacios = client.get("/api/espacios", headers=head_op).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == "M-02")
    registro_id = None
    try:
        creado = client.post(
            "/api/ingresos",
            json={"espacio_id": espacio_id, "placa": "TST-7777"},
            headers=head_op,
        ).get_json()["data"]
        registro_id = creado["id"]

        sin_liquidar = client.get(
            f"/api/comprobantes/sesiones/{registro_id}", headers=head_op
        )
        assert sin_liquidar.status_code == 409

        client.put(f"/api/salidas/{registro_id}", headers=head_op)
        pdf = client.get(f"/api/comprobantes/sesiones/{registro_id}", headers=head_op)
        assert pdf.status_code == 200
        assert pdf.data[:5] == b"%PDF-"

        token_admin = _token(client, "admin@parqueo.test")
        head_admin = {"Authorization": f"Bearer {token_admin}"}
        rep = client.get("/api/reportes/ingresos", headers=head_admin)
        assert rep.status_code == 200
        datos = rep.get_json()["data"]
        assert len(datos["zonas"]) == 3
        assert "total" in datos["totales"]

        rep_pdf = client.get("/api/reportes/ingresos?formato=pdf", headers=head_admin)
        assert rep_pdf.status_code == 200
        assert rep_pdf.data[:5] == b"%PDF-"

        assert client.get("/api/reportes/ingresos?desde=mala-fecha", headers=head_admin).status_code == 400

        token_cli = _token(client, "cliente@parqueo.test")
        assert (
            client.get(
                "/api/reportes/ingresos",
                headers={"Authorization": f"Bearer {token_cli}"},
            ).status_code
            == 403
        )
    finally:
        if registro_id is not None:
            db.session.query(RegistroIngresoSalida).filter_by(id=registro_id).delete()
        db.session.query(Espacio).filter_by(codigo="M-02").update(
            {"estado": "disponible"}
        )
        db.session.commit()
