"""Tarifas: monto estimado por hora iniciada — Fase 2A (puro).

Regla: toda hora iniciada se cobra completa (techo), con la tarifa_por_hora
de la zona. Sin cobro real: el pago va en Fase 3.
"""

import math
from decimal import Decimal, ROUND_HALF_UP


def monto_estimado(tarifa_por_hora, rango):
    tarifa = Decimal(str(tarifa_por_hora))
    horas = math.ceil(rango.segundos() / 3600)
    return (tarifa * horas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
