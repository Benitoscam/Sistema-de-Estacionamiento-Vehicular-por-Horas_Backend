"""Fábrica de pasarela según STRIPE_MODE — Fase 3A (fake por defecto)."""


def obtener_pasarela():
    from flask import current_app

    from app.adapters.payment.pasarela_fake import PasarelaFake

    modo = (current_app.config.get("STRIPE_MODE") or "fake").lower()
    if modo == "test":
        from app.adapters.payment.pasarela_stripe import PasarelaStripe

        return PasarelaStripe(
            current_app.config.get("STRIPE_SECRET_KEY", ""),
            current_app.config.get("STRIPE_WEBHOOK_SECRET", ""),
            current_app.config.get("FRONTEND_URL", ""),
        )
    return PasarelaFake(current_app.config.get("FRONTEND_URL", ""))
