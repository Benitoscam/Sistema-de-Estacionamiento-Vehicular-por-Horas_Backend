"""Objetos de valor del dominio — Fase 2A (puros, sin frameworks)."""

import re
from datetime import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.domain.excepciones import RangoInvalido

PLACA_RE = re.compile(r"^[A-Z0-9-]{3,15}$")


class Placa:
    """Placa normalizada (mayúsculas, sin espacios)."""

    def __init__(self, valor):
        normal = (valor or "").strip().upper().replace(" ", "")
        if not PLACA_RE.match(normal):
            raise RangoInvalido("placa inválida")
        self.valor = normal

    def __str__(self):
        return self.valor


class RangoHorario:
    """Rango [inicio, fin) con inicio < fin. Ingenuos se asumen UTC."""

    def __init__(self, inicio, fin):
        inicio = self._consciente(inicio)
        fin = self._consciente(fin)
        if inicio is None or fin is None or not fin > inicio:
            raise RangoInvalido("hora_fin_planeada debe ser posterior a hora_inicio_planeada")
        self.inicio = inicio
        self.fin = fin

    @staticmethod
    def _consciente(momento):
        if momento is None:
            return None
        if momento.tzinfo is None:
            return momento.replace(tzinfo=timezone.utc)
        return momento

    def se_solapa(self, otro):
        return self.inicio < otro.fin and otro.inicio < self.fin

    def segundos(self):
        return (self.fin - self.inicio).total_seconds()


class Dinero:
    """Monto DECIMAL(10,2) no negativo."""

    def __init__(self, valor):
        try:
            monto = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            raise RangoInvalido("monto inválido")
        if monto < 0:
            raise RangoInvalido("monto inválido")
        self.valor = monto

    def __str__(self):
        return str(self.valor)
