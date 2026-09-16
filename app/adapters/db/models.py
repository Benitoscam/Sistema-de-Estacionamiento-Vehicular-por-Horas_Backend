# app/adapters/db/models.py
"""
Modelos SQLAlchemy — Fase 1 (MER §7)
Solo 4 tablas: usuarios, zonas, espacios, bloqueos_mantenimiento.
Reservas, registros_ingreso_salida, pagos → Fase 2.
"""

import uuid
from app.extensions import db

# ──────────────────────────────────────────────
# Enums Postgres
# ──────────────────────────────────────────────

user_role = db.Enum(
    "admin", "operador", "cliente",
    name="user_role",
    create_constraint=True,
    native_enum=True,
)

zona_tipo = db.Enum(
    "cubierto", "descubierto", "motos",
    name="zona_tipo",
    create_constraint=True,
    native_enum=True,
)

espacio_estado = db.Enum(
    "disponible", "reservado", "ocupado", "mantenimiento",
    name="espacio_estado",
    create_constraint=True,
    native_enum=True,
)


# ──────────────────────────────────────────────
# Modelo: Usuario
# ──────────────────────────────────────────────

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(user_role, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False,
    )

    # Relationships (Fase 2)
    # reservas = db.relationship("Reserva", back_populates="cliente")
    # registros = db.relationship("RegistroIngresoSalida", back_populates="operador")

    def __repr__(self):
        return f"<Usuario {self.correo} ({self.rol})>"


# ──────────────────────────────────────────────
# Modelo: Zona
# ──────────────────────────────────────────────

class Zona(db.Model):
    __tablename__ = "zonas"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    nombre = db.Column(zona_tipo, unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    tarifa_por_hora = db.Column(db.Numeric(10, 2), nullable=False)

    # Relationship
    espacios = db.relationship("Espacio", back_populates="zona", lazy="select")

    def __repr__(self):
        return f"<Zona {self.nombre} ${self.tarifa_por_hora}/h>"


# ──────────────────────────────────────────────
# Modelo: Espacio
# ──────────────────────────────────────────────

class Espacio(db.Model):
    __tablename__ = "espacios"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    zona_id = db.Column(
        db.Uuid,
        db.ForeignKey("zonas.id"),
        nullable=False,
    )
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    estado = db.Column(
        espacio_estado,
        nullable=False,
        server_default="disponible",
    )

    # Relationships
    zona = db.relationship("Zona", back_populates="espacios")
    bloqueos = db.relationship(
        "BloqueoMantenimiento",
        back_populates="espacio",
        lazy="select",
    )

    # Fase 2: reservas, registros_ingreso_salida

    def __repr__(self):
        return f"<Espacio {self.codigo} [{self.estado}]>"


# ──────────────────────────────────────────────
# Modelo: BloqueoMantenimiento
# ──────────────────────────────────────────────

class BloqueoMantenimiento(db.Model):
    __tablename__ = "bloqueos_mantenimiento"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    espacio_id = db.Column(
        db.Uuid,
        db.ForeignKey("espacios.id"),
        nullable=False,
    )
    creado_por = db.Column(
        db.Uuid,
        db.ForeignKey("usuarios.id"),
        nullable=False,
    )
    fecha_inicio = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
    fecha_fin = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
    motivo = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False,
    )

    # Relationships
    espacio = db.relationship("Espacio", back_populates="bloqueos")
    admin = db.relationship("Usuario", foreign_keys=[creado_por])

    def __repr__(self):
        return f"<Bloqueo {self.espacio_id} {self.fecha_inicio}–{self.fecha_fin}>"