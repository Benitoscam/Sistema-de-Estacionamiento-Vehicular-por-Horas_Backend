"""Sesiones walk-in — Fase 2B. Crea registros de prueba y los liquida/limpia."""


def _token(client, correo, password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def _espacio_id(client, headers, codigo):
    res = client.get("/api/espacios", headers=headers)
    assert res.status_code == 200
    return next(e["id"] for e in res.get_json()["data"] if e["codigo"] == codigo)


def test_ingreso_y_salida_con_limpieza(client, db):
    from app.adapters.db.models import Espacio, RegistroIngresoSalida

    token = _token(client, "operador@parqueo.test")
    headers = {"Authorization": f"Bearer {token}"}
    espacio_id = _espacio_id(client, headers, "B-01")
    registro_id = None
    try:
        creado = client.post(
            "/api/ingresos",
            json={"espacio_id": espacio_id, "placa": "xyz-9124"},
            headers=headers,
        )
        assert creado.status_code == 201
        datos = creado.get_json()["data"]
        assert datos["placa"] == "XYZ-9124"
        assert datos["hora_salida"] is None
        assert datos["monto_cobrado"] is None
        registro_id = datos["id"]

        activas = client.get("/api/sesiones/activas?placa=xyz-9124", headers=headers)
        assert activas.status_code == 200
        assert any(r["id"] == registro_id for r in activas.get_json()["data"])

        duplicado = client.post(
            "/api/ingresos",
            json={"espacio_id": espacio_id, "placa": "ABC-1111"},
            headers=headers,
        )
        assert duplicado.status_code == 409

        salida = client.put(f"/api/salidas/{registro_id}", headers=headers)
        assert salida.status_code == 200
        sdatos = salida.get_json()["data"]
        assert sdatos["monto_cobrado"] is not None
        assert sdatos["desglose"]["monto_cobrado"] == sdatos["monto_cobrado"]
        assert sdatos["desglose"]["tarifa_por_hora"] == "2.50"

        repetida = client.put(f"/api/salidas/{registro_id}", headers=headers)
        assert repetida.status_code == 409
    finally:
        if registro_id is not None:
            db.session.query(RegistroIngresoSalida).filter_by(id=registro_id).delete()
            db.session.query(Espacio).filter_by(codigo="B-01").update(
                {"estado": "disponible"}
            )
            db.session.commit()


def test_ingreso_rechazos_y_roles(client):
    token_op = _token(client, "operador@parqueo.test")
    head_op = {"Authorization": f"Bearer {token_op}"}
    espacio_id = _espacio_id(client, head_op, "B-02")

    mala_placa = client.post(
        "/api/ingresos",
        json={"espacio_id": espacio_id, "placa": "!!"},
        headers=head_op,
    )
    assert mala_placa.status_code == 400

    token_cli = _token(client, "cliente@parqueo.test")
    cliente = client.post(
        "/api/ingresos",
        json={"espacio_id": espacio_id, "placa": "ABC-2222"},
        headers={"Authorization": f"Bearer {token_cli}"},
    )
    assert cliente.status_code == 403

    anon = client.get("/api/sesiones/activas")
    assert anon.status_code == 401
