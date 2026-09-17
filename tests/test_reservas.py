"""Reservas — Fase 2A + fix ocupación + placa. Crea, solapa, cancela y limpia."""

from datetime import datetime, timedelta, timezone

from app.adapters.db.models import Espacio, Reserva, Usuario


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def _horas_futuras(desde_horas=24, duracion=4):
    inicio = datetime.now(timezone.utc) + timedelta(hours=desde_horas)
    return inicio.isoformat(), (inicio + timedelta(hours=duracion)).isoformat()


def _horas_ahora(duracion=4):
    inicio = datetime.now(timezone.utc) - timedelta(minutes=5)
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

        # Crear reserva con placa
        creada = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
                "placa": "ABC123",
            },
            headers=headers,
        )
        assert creada.status_code == 201
        datos = creada.get_json()["data"]
        assert datos["estado"] == "confirmada"
        assert datos["placa"] == "ABC123"
        assert datos["monto_estimado"] == "14.00"
        assert datos["monto_pagado"] is None
        reserva_id = datos["id"]
        # Reserva futura NO cambia el estado del espacio
        assert _estado_espacio(client, headers, "A-01") == "disponible"

        # Solapar con otra placa
        solape = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
                "placa": "XYZ789",
            },
            headers=headers,
        )
        assert solape.status_code == 409

        # Rango inválido
        rango_malo = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": fin,
                "hora_fin_planeada": inicio,
                "placa": "XYZ789",
            },
            headers=headers,
        )
        assert rango_malo.status_code == 400

        # Mis-reservas incluye placa y se puede filtrar
        propias = client.get("/api/mis-reservas", headers=headers)
        assert propias.status_code == 200
        assert any(r["id"] == reserva_id for r in propias.get_json()["data"])
        filtradas = client.get("/api/mis-reservas?placa=ABC123", headers=headers)
        assert filtradas.status_code == 200
        assert any(r["id"] == reserva_id for r in filtradas.get_json()["data"])

        # Detalle visible
        detalle = client.get(f"/api/reservas/{reserva_id}", headers=headers)
        assert detalle.status_code == 200

        # Sin token
        anon = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
                "placa": "ABC123",
            },
        )
        assert anon.status_code == 401

        # Cancelar → vuelve a disponible (sin otra reserva vigente)
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
                "placa": "BBB456",
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


def test_placa_requerida(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == "A-03")
    inicio, fin = _horas_futuras(desde_horas=72)

    # Sin placa → 400
    res = client.post(
        "/api/reservas",
        json={
            "espacio_id": espacio_id,
            "hora_inicio_planeada": inicio,
            "hora_fin_planeada": fin,
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "placa" in res.get_json()["error"]


def test_placa_invalida(client, db):
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
    espacio_id = next(e["id"] for e in espacios if e["codigo"] == "A-03")
    inicio, fin = _horas_futuras(desde_horas=72)

    res = client.post(
        "/api/reservas",
        json={
            "espacio_id": espacio_id,
            "hora_inicio_planeada": inicio,
            "hora_fin_planeada": fin,
            "placa": "AB",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "placa_invalida" in res.get_json()["code"] or "placa inválida" in res.get_json()["error"]


def test_reserva_futura_no_cambia_estado(client, db):
    """Reserva para mañana NO debería cambiar el estado del espacio a 'reservado'."""
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    inicio, fin = _horas_futuras(desde_horas=24)
    reserva_id = None
    try:
        espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
        espacio_id = next(e["id"] for e in espacios if e["codigo"] == "B-01")

        assert _estado_espacio(client, headers, "B-01") == "disponible"

        creada = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
                "placa": "FUTURA1",
            },
            headers=headers,
        )
        assert creada.status_code == 201
        reserva_id = creada.get_json()["data"]["id"]

        # El espacio sigue disponible porque la reserva es futura
        assert _estado_espacio(client, headers, "B-01") == "disponible"
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
            db.session.commit()


def test_reserva_activa_si_cambia_estado(client, db):
    """Reserva cuya ventana inicia pronto debería cambiar el estado a 'reservado'."""
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    inicio, fin = _horas_ahora(duracion=4)
    reserva_id = None
    try:
        espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
        espacio_id = next(e["id"] for e in espacios if e["codigo"] == "B-02")

        assert _estado_espacio(client, headers, "B-02") == "disponible"

        creada = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio,
                "hora_fin_planeada": fin,
                "placa": "NOW001",
            },
            headers=headers,
        )
        assert creada.status_code == 201
        reserva_id = creada.get_json()["data"]["id"]

        # La ventana ya empezó → estado reservado
        assert _estado_espacio(client, headers, "B-02") == "reservado"
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
            db.session.query(Espacio).filter_by(codigo="B-02").update(
                {"estado": "disponible"}
            )
            db.session.commit()


def test_cancelar_con_otra_vigente_no_libera(client, db):
    """Si hay otra reserva confirmada futura en el mismo espacio, cancelar una NO libera el estado."""
    token = _token(client, "cliente@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    # R1: ventana activa AHORA (estado → reservado), R2: futura sin solape
    ahora = datetime.now(timezone.utc)
    inicio1 = (ahora - timedelta(minutes=5)).isoformat()
    fin1 = (ahora + timedelta(hours=3)).isoformat()
    inicio2 = (ahora + timedelta(hours=4)).isoformat()
    fin2 = (ahora + timedelta(hours=8)).isoformat()

    r1_id = r2_id = None
    try:
        espacios = client.get("/api/espacios", headers=headers).get_json()["data"]
        espacio_id = next(e["id"] for e in espacios if e["codigo"] == "B-03")

        # Reserva 1 (activa ahora → estado reservado)
        c1 = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio1,
                "hora_fin_planeada": fin1,
                "placa": "MUL001",
            },
            headers=headers,
        )
        assert c1.status_code == 201
        r1_id = c1.get_json()["data"]["id"]
        assert _estado_espacio(client, headers, "B-03") == "reservado"

        # Reserva 2 futura sin solape
        c2 = client.post(
            "/api/reservas",
            json={
                "espacio_id": espacio_id,
                "hora_inicio_planeada": inicio2,
                "hora_fin_planeada": fin2,
                "placa": "MUL002",
            },
            headers=headers,
        )
        assert c2.status_code == 201
        r2_id = c2.get_json()["data"]["id"]

        # Cancelar R1: espacio sigue reservado por R2 futura
        cancelar = client.delete(f"/api/reservas/{r1_id}", headers=headers)
        assert cancelar.status_code == 200
        assert cancelar.get_json()["data"]["estado"] == "cancelada"
        assert _estado_espacio(client, headers, "B-03") == "reservado"

        # Cancelar R2 ahora sí libera
        cancelar2 = client.delete(f"/api/reservas/{r2_id}", headers=headers)
        assert cancelar2.status_code == 200
        assert _estado_espacio(client, headers, "B-03") == "disponible"
        r1_id = r2_id = None
    finally:
        for rid in (r1_id, r2_id):
            if rid is not None:
                db.session.query(Reserva).filter_by(id=rid).delete()
        if r1_id or r2_id:
            db.session.query(Espacio).filter_by(codigo="B-03").update(
                {"estado": "disponible"}
            )
            db.session.commit()
