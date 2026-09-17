"""Fase 4 — Pago efectivo walk-in, analítica RF-10, expiración por comando."""

import uuid
from datetime import datetime, timedelta, timezone


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def _espacio_id(client, headers, codigo):
    res = client.get("/api/espacios", headers=headers)
    assert res.status_code == 200
    return next(e["id"] for e in res.get_json()["data"] if e["codigo"] == codigo)


# ──────────────────────────────────────────────
# Efectivo walk-in
# ──────────────────────────────────────────────


def test_salida_efectivo_crea_pago(client, db):
    from app.adapters.db.models import Espacio, Pago, RegistroIngresoSalida

    token = _token(client, "operador@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacio_id = _espacio_id(client, headers, "B-03")
    registro_id = pago_id = None
    try:
        creado = client.post(
            "/api/ingresos",
            json={"espacio_id": espacio_id, "placa": "EFV-1234"},
            headers=headers,
        )
        assert creado.status_code == 201
        registro_id = creado.get_json()["data"]["id"]

        salida = client.put(
            f"/api/salidas/{registro_id}",
            json={"metodo_pago": "efectivo"},
            headers=headers,
        )
        assert salida.status_code == 200
        sdatos = salida.get_json()["data"]
        assert sdatos["monto_cobrado"] is not None

        pagos = Pago.query.filter_by(registro_ingreso_id=registro_id).all()
        assert len(pagos) == 1
        pago_id = pagos[0].id
        assert str(pagos[0].metodo) == "efectivo"
        assert str(pagos[0].estado) == "confirmado"
        assert pagos[0].referencia_transaccion.startswith("efectivo-")
    finally:
        if pago_id is not None:
            db.session.query(Pago).filter_by(id=pago_id).delete()
        if registro_id is not None:
            db.session.query(RegistroIngresoSalida).filter_by(id=registro_id).delete()
        db.session.query(Espacio).filter_by(codigo="B-03").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_salida_metodo_invalido(client):
    token = _token(client, "operador@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacio_id = _espacio_id(client, headers, "B-04")
    creado = client.post(
        "/api/ingresos",
        json={"espacio_id": espacio_id, "placa": "INV-5678"},
        headers=headers,
    )
    assert creado.status_code == 201
    registro_id = creado.get_json()["data"]["id"]
    try:
        salida = client.put(
            f"/api/salidas/{registro_id}",
            json={"metodo_pago": "tarjeta"},
            headers=headers,
        )
        assert salida.status_code == 400
    finally:
        from app.adapters.db.models import Espacio, RegistroIngresoSalida
        from app.extensions import db
        db.session.query(RegistroIngresoSalida).filter_by(id=registro_id).delete()
        db.session.query(Espacio).filter_by(codigo="B-04").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_salida_sin_metodo_sin_pago(client, db):
    from app.adapters.db.models import Espacio, Pago, RegistroIngresoSalida

    token = _token(client, "operador@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacio_id = _espacio_id(client, headers, "B-05")
    registro_id = None
    try:
        creado = client.post(
            "/api/ingresos",
            json={"espacio_id": espacio_id, "placa": "NOM-9999"},
            headers=headers,
        )
        assert creado.status_code == 201
        registro_id = creado.get_json()["data"]["id"]

        salida = client.put(f"/api/salidas/{registro_id}", headers=headers)
        assert salida.status_code == 200

        pagos = Pago.query.filter_by(registro_ingreso_id=registro_id).all()
        assert len(pagos) == 0
    finally:
        if registro_id is not None:
            db.session.query(RegistroIngresoSalida).filter_by(id=registro_id).delete()
        db.session.query(Espacio).filter_by(codigo="B-05").update(
            {"estado": "disponible"}
        )
        db.session.commit()


# ──────────────────────────────────────────────
# Analítica RF-10
# ──────────────────────────────────────────────


def test_analitica_admin(client):
    token = _token(client, "admin@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/analitica", headers=headers)
    assert res.status_code == 200
    datos = res.get_json()["data"]
    assert len(datos["horas_entrada"]) == 24
    assert len(datos["horas_salida"]) == 24
    assert "hora_pico_entrada" in datos
    assert "hora_pico_salida" in datos
    assert "permanencia_promedio_min" in datos
    assert "rotacion_por_espacio" in datos


def test_analitica_filtros(client):
    token = _token(client, "admin@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get(
        "/api/analitica?desde=2026-01-01&hasta=2026-12-31", headers=headers
    )
    assert res.status_code == 200

    res_bad = client.get("/api/analitica?desde=mala", headers=headers)
    assert res_bad.status_code == 400


def test_analitica_roles(client):
    token_op = _token(client, "operador@parqueo.test")
    assert client.get(
        "/api/analitica", headers={"Authorization": f"Bearer {token_op}"}
    ).status_code == 403

    token_cli = _token(client, "cliente@parqueo.test")
    assert client.get(
        "/api/analitica", headers={"Authorization": f"Bearer {token_cli}"}
    ).status_code == 403

    assert client.get("/api/analitica").status_code == 401


# ──────────────────────────────────────────────
# Comando expirar
# ──────────────────────────────────────────────


def test_comando_expirar(client, db, runner):
    """Crea reserva pasada directo por DB (la API la rechaza), luego expira."""
    from app.adapters.db.models import Espacio, Reserva, Usuario

    ahora = datetime.now(timezone.utc)
    usuario = Usuario.query.filter_by(correo="cliente@parqueo.test").first()
    espacio = Espacio.query.filter_by(codigo="M-03").first()
    assert usuario is not None and espacio is not None

    # Limpiar cualquier residuo previo en M-03
    Reserva.query.filter_by(espacio_id=espacio.id, estado="confirmada").delete()
    espacio.estado = "disponible"
    db.session.commit()

    reserva_id = None
    try:
        # Crear reserva pasada directo por DB
        r = Reserva(
            espacio_id=espacio.id,
            usuario_id=usuario.id,
            fecha=(ahora - timedelta(hours=3)).date(),
            hora_inicio_planeada=ahora - timedelta(hours=3),
            hora_fin_planeada=ahora - timedelta(hours=1),
            placa="EXP001",
            estado="confirmada",
        )
        db.session.add(r)
        db.session.commit()
        reserva_id = r.id

        res = runner.invoke(args=["reservas", "expirar"])
        assert res.exit_code == 0
        assert "1 reservas expiradas" in res.output

        reserva_db = db.session.get(Reserva, reserva_id)
        assert str(reserva_db.estado) == "completada"

        assert str(espacio.estado) == "disponible"
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
        db.session.query(Espacio).filter_by(codigo="M-03").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_comando_activar_reservas(client, db, runner):
    """Crea reserva iniciada hace 30 min directo por DB, el cron la activa."""
    from app.adapters.db.models import Espacio, Reserva, Usuario

    ahora = datetime.now(timezone.utc)
    usuario = Usuario.query.filter_by(correo="cliente@parqueo.test").first()
    espacio = Espacio.query.filter_by(codigo="M-02").first()
    assert usuario is not None and espacio is not None

    # Limpiar cualquier residuo previo en M-02
    Reserva.query.filter_by(espacio_id=espacio.id, estado="confirmada").delete()
    espacio.estado = "disponible"
    db.session.commit()

    reserva_id = None
    try:
        # Reserva cuya ventana empezó hace 30 min y termina en +3.5h
        r = Reserva(
            espacio_id=espacio.id,
            usuario_id=usuario.id,
            fecha=ahora.date(),
            hora_inicio_planeada=ahora - timedelta(minutes=30),
            hora_fin_planeada=ahora + timedelta(hours=3, minutes=30),
            placa="ACT001",
            estado="confirmada",
        )
        db.session.add(r)
        db.session.commit()
        reserva_id = r.id

        res = runner.invoke(args=["reservas", "expirar"])
        assert res.exit_code == 0
        assert "espacios activados" in res.output

        assert str(espacio.estado) == "reservado"
    finally:
        if reserva_id is not None:
            db.session.query(Reserva).filter_by(id=reserva_id).delete()
        db.session.query(Espacio).filter_by(codigo="M-02").update(
            {"estado": "disponible"}
        )
        db.session.commit()


def test_comando_expirar_sin_vencidas(client, runner):
    res = runner.invoke(args=["reservas", "expirar"])
    assert res.exit_code == 0
    assert "0 reservas expiradas" in res.output
