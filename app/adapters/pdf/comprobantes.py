"""Generación de PDFs en memoria con ReportLab — Fase 3B.

Sin templates HTML ni archivos: todo se construye en código y se devuelve
como bytes. Incluye QR en comprobantes (RF-05).
"""

from io import BytesIO

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ENCABEZADO_FONDO = colors.HexColor("#1e3a5f")
TITULO = {"fontSize": 16, "leading": 20, "textColor": ENCABEZADO_FONDO}
ETIQUETA = {"fontSize": 10, "leading": 14, "textColor": colors.grey}


def _base(titulo):
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=letter, title=titulo)
    estilos = getSampleStyleSheet()
    return buffer, documento, estilos


def _tabla_datos(pares, estilos):
    filas = [
        [Paragraph(f"<b>{etiqueta}</b>", estilos["Normal"]), Paragraph(valor, estilos["Normal"])]
        for etiqueta, valor in pares
    ]
    tabla = Table(filas, colWidths=[150, 330])
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tabla


def _qr(texto):
    figura = QrCodeWidget(texto)
    x0, y0, x1, y1 = figura.getBounds()
    lienzo = Drawing(x1 - x0, y1 - y0)
    lienzo.add(figura)
    return lienzo


def comprobante_reserva(datos):
    """datos: referencia, plaza, zona, tarifa, cliente, correo, inicio, fin,
    monto_pagado, estado, codigo_qr."""
    buffer, documento, estilos = _base("Comprobante de reserva")
    historia = [
        Paragraph("Comprobante de reserva — Parqueo", estilos["Title"]),
        Spacer(1, 12),
        _tabla_datos(
            [
                ("Referencia", datos["referencia"]),
                ("Plaza", f"{datos['plaza']} ({datos['zona']})"),
                ("Cliente", f"{datos['cliente']} — {datos['correo']}"),
                ("Entrada planeada", datos["inicio"]),
                ("Salida planeada", datos["fin"]),
                ("Tarifa por hora", datos["tarifa"]),
                ("Monto pagado", datos["monto_pagado"]),
                ("Estado", datos["estado"]),
            ],
            estilos,
        ),
        Spacer(1, 16),
        Paragraph("Presente este código al ingresar:", estilos["Normal"]),
        Spacer(1, 8),
        _qr(datos["codigo_qr"]),
    ]
    documento.build(historia)
    return buffer.getvalue()


def comprobante_sesion(datos):
    """datos: plaza, zona, placa, operador, entrada, salida, tarifa, monto_cobrado, codigo_qr."""
    buffer, documento, _estilos = _base("Comprobante de estadía")
    estilos = getSampleStyleSheet()
    historia = [
        Paragraph("Comprobante de estadía — Parqueo", estilos["Title"]),
        Spacer(1, 12),
        _tabla_datos(
            [
                ("Plaza", f"{datos['plaza']} ({datos['zona']})"),
                ("Placa", datos["placa"]),
                ("Registrado por", datos["operador"]),
                ("Hora de entrada", datos["entrada"]),
                ("Hora de salida", datos["salida"]),
                ("Tarifa por hora", datos["tarifa"]),
                ("Monto cobrado", datos["monto_cobrado"]),
            ],
            estilos,
        ),
        Spacer(1, 16),
        Paragraph("Comprobante:", estilos["Normal"]),
        Spacer(1, 8),
        _qr(datos["codigo_qr"]),
    ]
    documento.build(historia)
    return buffer.getvalue()


def reporte_ingresos(desde, hasta, filas, totales):
    """filas: [{zona, reservas_n, reservas_monto, walkin_n, walkin_monto, total}].
    totales: {reservas_n, reservas_monto, walkin_n, walkin_monto, total}."""
    buffer, documento, estilos = _base("Reporte de ingresos")
    encabezado = ["Zona", "Reservas", "Monto res.", "Walk-in", "Monto w-i", "Total"]
    cuerpo = [encabezado]
    for fila in filas:
        cuerpo.append(
            [
                fila["zona"],
                str(fila["reservas_n"]),
                fila["reservas_monto"],
                str(fila["walkin_n"]),
                fila["walkin_monto"],
                fila["total"],
            ]
        )
    cuerpo.append(
        [
            "TOTAL",
            str(totales["reservas_n"]),
            totales["reservas_monto"],
            str(totales["walkin_n"]),
            totales["walkin_monto"],
            totales["total"],
        ]
    )
    tabla = Table(cuerpo, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ENCABEZADO_FONDO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    historia = [
        Paragraph("Reporte de ingresos — Parqueo", estilos["Title"]),
        Spacer(1, 6),
        Paragraph(f"Período: {desde} al {hasta}", estilos["Normal"]),
        Spacer(1, 12),
        tabla,
    ]
    documento.build(historia)
    return buffer.getvalue()
