"""Consultas agregadas: dashboard, reportes y analítica — Fase 4.

Regla de fechas: como pagos no tiene fecha propia, los ingresos se agrupan
por fecha de servicio (reservas: hora_inicio_planeada; walk-in: hora_salida).
"""

from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func

from app.adapters.db.models import (
    Espacio,
    Pago,
    RegistroIngresoSalida,
    Reserva,
    Zona,
)
from app.extensions import db


def _rango_fechas(desde, hasta):
    inicio = (
        datetime.combine(desde, time.min).replace(tzinfo=timezone.utc) if desde else None
    )
    fin = (
        datetime.combine(hasta, time.max).replace(tzinfo=timezone.utc) if hasta else None
    )
    return inicio, fin


def _parse_fecha(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def obtener_dashboard():
    total_espacios = Espacio.query.count()
    por_estado = {"disponible": 0, "reservado": 0, "ocupado": 0, "mantenimiento": 0}
    for estado, cantidad in (
        db.session.query(Espacio.estado, func.count(Espacio.id))
        .group_by(Espacio.estado)
        .all()
    ):
        por_estado[str(estado)] = cantidad

    pagos = Pago.query.filter_by(estado="confirmado").all()
    ingreso_reservas = sum((p.monto for p in pagos), start=Decimal("0"))
    liquidadas = RegistroIngresoSalida.query.filter(
        RegistroIngresoSalida.hora_salida.is_not(None)
    ).all()
    ingreso_walkin = sum(
        (r.monto_cobrado for r in liquidadas if r.monto_cobrado is not None),
        start=Decimal("0"),
    )

    return {
        "ocupacion": {
            "total_espacios": total_espacios,
            "por_estado": por_estado,
            "porcentaje_ocupado": round(
                100 * (total_espacios - por_estado["disponible"]) / total_espacios, 1
            )
            if total_espacios
            else 0,
        },
        "ingresos": {
            "reservas_confirmadas_n": len(pagos),
            "reservas_monto": str(ingreso_reservas),
            "walkin_liquidadas_n": len(liquidadas),
            "walkin_monto": str(ingreso_walkin),
            "total": str(ingreso_reservas + ingreso_walkin),
        },
        "reservas_confirmadas_n": Reserva.query.filter_by(estado="confirmada").count(),
        "sesiones_activas_n": RegistroIngresoSalida.query.filter(
            RegistroIngresoSalida.hora_salida.is_(None)
        ).count(),
    }


def ingresos_por_zona(desde=None, hasta=None, zona_id=None):
    inicio, fin = _rango_fechas(desde, hasta)
    zonas = Zona.query.order_by(Zona.nombre).all()
    if zona_id is not None:
        zonas = [z for z in zonas if z.id == zona_id]

    consulta_pagos = Pago.query.join(Reserva, Pago.reserva_id == Reserva.id).filter(
        Pago.estado == "confirmado"
    )
    if inicio is not None:
        consulta_pagos = consulta_pagos.filter(Reserva.hora_inicio_planeada >= inicio)
    if fin is not None:
        consulta_pagos = consulta_pagos.filter(Reserva.hora_inicio_planeada <= fin)

    consulta_walkin = RegistroIngresoSalida.query.filter(
        RegistroIngresoSalida.hora_salida.is_not(None),
        RegistroIngresoSalida.monto_cobrado.is_not(None),
    )
    if inicio is not None:
        consulta_walkin = consulta_walkin.filter(RegistroIngresoSalida.hora_salida >= inicio)
    if fin is not None:
        consulta_walkin = consulta_walkin.filter(RegistroIngresoSalida.hora_salida <= fin)

    pagos = consulta_pagos.all()
    caminantes = consulta_walkin.all()

    filas = []
    for zona in zonas:
        pr = [p for p in pagos if p.reserva.espacio.zona_id == zona.id]
        wk = [r for r in caminantes if r.espacio.zona_id == zona.id]
        monto_r = sum((p.monto for p in pr), start=Decimal("0"))
        monto_w = sum(
            (r.monto_cobrado for r in wk), start=Decimal("0")
        )
        filas.append(
            {
                "zona_id": str(zona.id),
                "zona": str(zona.nombre),
                "reservas_n": len(pr),
                "reservas_monto": str(monto_r),
                "walkin_n": len(wk),
                "walkin_monto": str(monto_w),
                "total": str(monto_r + monto_w),
            }
        )
    totales = {
        "reservas_n": sum(f["reservas_n"] for f in filas),
        "reservas_monto": str(
            sum(
                (Decimal(f["reservas_monto"]) for f in filas),
                start=Decimal("0"),
            )
        ),
        "walkin_n": sum(f["walkin_n"] for f in filas),
        "walkin_monto": str(
            sum(
                (Decimal(f["walkin_monto"]) for f in filas),
                start=Decimal("0"),
            )
        ),
        "total": str(
            sum(
                (Decimal(f["total"]) for f in filas),
                start=Decimal("0"),
            )
        ),
    }
    return filas, totales


def analitica_demanda(desde=None, hasta=None, zona_id=None):
    """RF-10: horas pico entrada/salida, permanencia promedio, rotación por espacio."""
    inicio, fin = _rango_fechas(desde, hasta)

    # Entradas por hora del día (0–23) — walk-in
    consulta_entradas = db.session.query(
        func.extract("hour", RegistroIngresoSalida.hora_entrada).label("hora"),
        func.count(RegistroIngresoSalida.id),
    )
    if inicio:
        consulta_entradas = consulta_entradas.filter(
            RegistroIngresoSalida.hora_entrada >= inicio
        )
    if fin:
        consulta_entradas = consulta_entradas.filter(
            RegistroIngresoSalida.hora_entrada <= fin
        )
    entradas_rows = consulta_entradas.group_by("hora").all()

    # Salidas por hora del día — walk-in
    consulta_salidas = db.session.query(
        func.extract("hour", RegistroIngresoSalida.hora_salida).label("hora"),
        func.count(RegistroIngresoSalida.id),
    ).filter(RegistroIngresoSalida.hora_salida.is_not(None))
    if inicio:
        consulta_salidas = consulta_salidas.filter(
            RegistroIngresoSalida.hora_salida >= inicio
        )
    if fin:
        consulta_salidas = consulta_salidas.filter(
            RegistroIngresoSalida.hora_salida <= fin
        )
    salidas_rows = consulta_salidas.group_by("hora").all()

    entradas = {int(h): c for h, c in entradas_rows}
    salidas = {int(h): c for h, c in salidas_rows}
    horas_entrada = [{"hora": h, "cantidad": entradas.get(h, 0)} for h in range(24)]
    horas_salida = [{"hora": h, "cantidad": salidas.get(h, 0)} for h in range(24)]
    hora_pico_entrada = max(horas_entrada, key=lambda x: x["cantidad"])
    hora_pico_salida = max(horas_salida, key=lambda x: x["cantidad"])

    # Permanencia promedio (walk-in liquidadas)
    consulta_permanencia = db.session.query(
        func.avg(
            func.extract("epoch", RegistroIngresoSalida.hora_salida)
            - func.extract("epoch", RegistroIngresoSalida.hora_entrada)
        )
    ).filter(RegistroIngresoSalida.hora_salida.is_not(None))
    if inicio:
        consulta_permanencia = consulta_permanencia.filter(
            RegistroIngresoSalida.hora_salida >= inicio
        )
    if fin:
        consulta_permanencia = consulta_permanencia.filter(
            RegistroIngresoSalida.hora_salida <= fin
        )
    promedio_seg = consulta_permanencia.scalar()
    permanencia_promedio_min = round(promedio_seg / 60, 1) if promedio_seg else 0

    # Rotación por espacio (walk-in liquidadas / espacios)
    consulta_rotacion = db.session.query(
        Espacio.codigo,
        func.count(RegistroIngresoSalida.id),
    ).join(
        RegistroIngresoSalida, Espacio.id == RegistroIngresoSalida.espacio_id
    ).filter(
        RegistroIngresoSalida.hora_salida.is_not(None)
    )
    if inicio:
        consulta_rotacion = consulta_rotacion.filter(
            RegistroIngresoSalida.hora_salida >= inicio
        )
    if fin:
        consulta_rotacion = consulta_rotacion.filter(
            RegistroIngresoSalida.hora_salida <= fin
        )
    if zona_id:
        consulta_rotacion = consulta_rotacion.filter(Espacio.zona_id == zona_id)
    rotacion_rows = consulta_rotacion.group_by(Espacio.codigo).all()
    rotacion = [
        {"espacio": codigo, "usos": usos}
        for codigo, usos in sorted(rotacion_rows, key=lambda x: -x[1])
    ]

    return {
        "horas_entrada": horas_entrada,
        "horas_salida": horas_salida,
        "hora_pico_entrada": hora_pico_entrada,
        "hora_pico_salida": hora_pico_salida,
        "permanencia_promedio_min": permanencia_promedio_min,
        "rotacion_por_espacio": rotacion,
    }
