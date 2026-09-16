"""Pasarela Stripe (modo test) — Fase 3A. Cableada, inactiva sin llaves.

Requiere STRIPE_MODE=test + STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET en .env.
Solo se guarda el ID de sesión de Stripe (referencia_transaccion), nunca tarjetas.
"""

import stripe

from app.ports.interfaces import EventoPago, IPasarelaPago, SesionCheckout, WebhookInvalido


class PasarelaStripe(IPasarelaPago):
    MODO = "test"

    def __init__(self, secret_key, webhook_secret, base_url):
        if not secret_key:
            raise WebhookInvalido("falta STRIPE_SECRET_KEY")
        self.webhook_secret = webhook_secret
        self.base_url = (base_url or "").rstrip("/")
        stripe.api_key = secret_key

    def crear_sesion(self, monto, descripcion, exito_url, cancela_url, referencia_interna):
        centavos = int(monto * 100)
        sesion = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": centavos,
                        "product_data": {"name": descripcion},
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=exito_url,
            cancel_url=cancela_url,
            client_reference_id=referencia_interna,
            metadata={"reserva_id": referencia_interna},
        )
        return SesionCheckout(url=sesion.url, referencia=sesion.id, modo=self.MODO)

    def verificar_webhook(self, cuerpo, firma):
        try:
            evento = stripe.Webhook.construct_event(cuerpo, firma, self.webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            raise WebhookInvalido("firma del webhook inválida")
        tipo = evento.get("type", "")
        if tipo != "checkout.session.completed":
            return EventoPago(tipo=tipo, referencia="", pagado=False)
        objeto = evento["data"]["object"]
        return EventoPago(
            tipo=tipo,
            referencia=objeto.get("id", ""),
            pagado=objeto.get("payment_status") == "paid",
        )
