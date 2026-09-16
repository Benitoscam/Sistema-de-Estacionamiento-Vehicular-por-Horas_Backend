"""Validación mínima de payloads — Fase 1 (sin dependencias extra)."""

import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZONA_NOMBRES = ("cubierto", "descubierto", "motos")
ESPACIO_ESTADOS = ("disponible", "reservado", "ocupado", "mantenimiento")


def json_body(request):
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def missing_fields(data, fields):
    return [
        f for f in fields if not (data.get(f) not in (None, "") and str(data.get(f)).strip() != "")
    ]


def parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def to_tarifa(value):
    """Decimal(10,2) positivo o None si inválido."""
    try:
        tarifa = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return None
    return tarifa if tarifa > 0 else None
