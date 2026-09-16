# app/adapters/db/seed.py
"""Seed mínimo Fase 1 — idempotente (se puede correr varias veces)."""

import bcrypt
from app import create_app
from app.extensions import db
from app.adapters.db.models import Usuario, Zona, Espacio

USERS = [
    ("Administrador", "admin@parqueo.test", "Test123*", "admin"),
    ("Operador Uno", "operador@parqueo.test", "Test123*", "operador"),
    ("Cliente Uno", "cliente@parqueo.test", "Test123*", "cliente"),
]

ZONAS = [
    ("cubierto", "Zona techada, autos", 3.50),
    ("descubierto", "Playa exterior, autos", 2.50),
    ("motos", "Sector exclusivo motos", 1.20),
]

ESPACIOS = [
    ("A-01", "cubierto"), ("A-02", "cubierto"),
    ("A-03", "cubierto"), ("A-04", "cubierto"),
    ("B-01", "descubierto"), ("B-02", "descubierto"),
    ("B-03", "descubierto"), ("B-04", "descubierto"),
    ("B-05", "descubierto"),
    ("M-01", "motos"), ("M-02", "motos"), ("M-03", "motos"),
]


def run():
    app = create_app()
    with app.app_context():
        for nombre, correo, clave, rol in USERS:
            if not Usuario.query.filter_by(correo=correo).first():
                ph = bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()
                db.session.add(Usuario(
                    nombre=nombre, correo=correo,
                    telefono=None, password_hash=ph, rol=rol,
                ))
        db.session.commit()

        zona_map = {}
        for nombre, desc, tarifa in ZONAS:
            z = Zona.query.filter_by(nombre=nombre).first()
            if not z:
                z = Zona(nombre=nombre, descripcion=desc, tarifa_por_hora=tarifa)
                db.session.add(z)
                db.session.commit()
            zona_map[nombre] = z

        for codigo, zona_nombre in ESPACIOS:
            if not Espacio.query.filter_by(codigo=codigo).first():
                db.session.add(Espacio(
                    zona_id=zona_map[zona_nombre].id,
                    codigo=codigo, estado="disponible",
                ))
        db.session.commit()

        print("SEED_OK:",
              Usuario.query.count(), "usuarios,",
              Zona.query.count(), "zonas,",
              Espacio.query.count(), "espacios")


if __name__ == "__main__":
    run()