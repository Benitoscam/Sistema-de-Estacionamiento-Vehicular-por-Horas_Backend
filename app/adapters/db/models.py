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

reserva_estado = db.Enum(
    "confirmada", "cancelada", "completada",
    name="reserva_estado",
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


# ──────────────────────────────────────────────
# Modelo: Reserva (Fase 2A, RF-02)
# ──────────────────────────────────────────────

class Reserva(db.Model):
    __tablename__ = "reservas"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    espacio_id = db.Column(
        db.Uuid,
        db.ForeignKey("espacios.id"),
        nullable=False,
    )
    usuario_id = db.Column(
        db.Uuid,
        db.ForeignKey("usuarios.id"),
        nullable=False,
    )
    fecha = db.Column(db.Date, nullable=False)
    hora_inicio_planeada = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
    hora_fin_planeada = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
    placa = db.Column(db.String(15), nullable=True)
    monto_pagado = db.Column(db.Numeric(10, 2), nullable=True)
    estado = db.Column(
        reserva_estado,
        nullable=False,
        server_default="confirmada",
    )

    # Relationships
    espacio = db.relationship("Espacio")
    cliente = db.relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<Reserva {self.espacio_id} [{self.estado}]>"


# ──────────────────────────────────────────────
# Modelo: RegistroIngresoSalida (Fase 2B, RF-03)
# ──────────────────────────────────────────────

class RegistroIngresoSalida(db.Model):
    __tablename__ = "registros_ingreso_salida"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    espacio_id = db.Column(
        db.Uuid,
        db.ForeignKey("espacios.id"),
        nullable=False,
    )
    placa = db.Column(db.String(15), nullable=False)
    operador_id = db.Column(
        db.Uuid,
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )
    hora_entrada = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
    hora_salida = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )
    monto_cobrado = db.Column(db.Numeric(10, 2), nullable=True)

    # Relationships
    espacio = db.relationship("Espacio")
    operador = db.relationship("Usuario", foreign_keys=[operador_id])

    def __repr__(self):
        return f"<Ingreso {self.placa} {self.hora_entrada}>"


metodo_pago = db.Enum(
    "tarjeta", "efectivo",
    name="metodo_pago",
    create_constraint=True,
    native_enum=True,
)

pago_estado = db.Enum(
    "pendiente", "confirmado", "reembolsado",
    name="pago_estado",
    create_constraint=True,
    native_enum=True,
)


# ──────────────────────────────────────────────
# Modelo: Pago (Fase 3A)
# ──────────────────────────────────────────────

class Pago(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    reserva_id = db.Column(
        db.Uuid,
        db.ForeignKey("reservas.id"),
        nullable=True,
        unique=True,
    )
    registro_ingreso_id = db.Column(
        db.Uuid,
        db.ForeignKey("registros_ingreso_salida.id"),
        nullable=True,
        unique=True,
    )
    referencia_transaccion = db.Column(db.String(255), unique=True, nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(metodo_pago, nullable=False)
    estado = db.Column(
        pago_estado,
        nullable=False,
        server_default="pendiente",
    )

    # Relationships
    reserva = db.relationship("Reserva", foreign_keys=[reserva_id])
    registro = db.relationship("RegistroIngresoSalida", foreign_keys=[registro_ingreso_id])

    def __repr__(self):
        return f"<Pago {self.referencia_transaccion} [{self.estado}]>"