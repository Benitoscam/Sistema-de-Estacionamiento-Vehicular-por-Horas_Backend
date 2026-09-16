"""Pasarela fake — Fase 3A. Modo dev sin llaves: URLs y referencias simuladas."""

import json
import uuid

from app.ports.interfaces import EventoPago, IPasarelaPago, SesionCheckout, WebhookInvalido


class PasarelaFake(IPasarelaPago):
    MODO = "fake"

    def __init__(self, base_url):
        self.base_url = (base_url or "").rstrip("/")

    def crear_sesion(self, monto, descripcion, exito_url, cancela_url, referencia_interna):
        referencia = referencia_interna or f"fake_{uuid.uuid4().hex[:12]}"
        return SesionCheckout(
            url=f"{self.base_url}/pago/{referencia}",
            referencia=referencia,
            modo=self.MODO,
        )

    def verificar_webhook(self, cuerpo, firma):
        try:
            datos = json.loads(cuerpo.decode("utf-8") if isinstance(cuerpo, bytes) else cuerpo)
        except (ValueError, TypeError, AttributeError):
            raise WebhookInvalido("cuerpo del webhook inválido")
        if not isinstance(datos, dict) or not datos.get("referencia"):
            raise WebhookInvalido("webhook sin referencia")
        return EventoPago(
            tipo=datos.get("tipo", "checkout.session.completed"),
            referencia=datos["referencia"],
            pagado=bool(datos.get("pagado", True)),
        )
