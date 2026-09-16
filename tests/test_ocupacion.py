"""Ocupación — Fase 1. Solo lectura (GET) sobre parqueo_db con seed."""


def _token(client, correo="cliente@parqueo.test", password="Test123*"):
    res = client.post("/api/auth/login", json={"correo": correo, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


def test_ocupacion_requiere_jwt(client):
    assert client.get("/api/ocupacion").status_code == 401


def test_ocupacion_resumen_y_filtro(client):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/ocupacion", headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total"] >= 12
    assert set(data["por_estado"]) == {
        "disponible",
        "reservado",
        "ocupado",
        "mantenimiento",
    }
    assert sum(data["por_estado"].values()) == data["total"]
    assert len(data["por_zona"]) == 3

    zona_id = data["por_zona"][0]["zona_id"]
    filtrada = client.get(f"/api/ocupacion?zona_id={zona_id}", headers=headers)
    assert filtrada.status_code == 200
    fdata = filtrada.get_json()["data"]
    assert fdata["total"] == filtrada.get_json()["data"]["total"]
    assert all(e["zona_id"] == zona_id for e in fdata["espacios"])

    assert client.get("/api/zonas", headers=headers).status_code == 200
    assert client.get("/api/espacios", headers=headers).status_code == 200
