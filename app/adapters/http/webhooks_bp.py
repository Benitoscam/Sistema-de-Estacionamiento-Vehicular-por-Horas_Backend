"""Webhooks de la pasarela (RF-02) — Fase 3A. Públicos, autenticados por firma.

En modo fake la firma no se exige (solo dev). En modo test se verifica
la firma de Stripe; sin firma válida → 400.
"""

from flask import Blueprint, jsonify, request

from app.adapters.payment.pasarela import obtener_pasarela
from app.application.use_cases import confirmar_pago
from app.domain.excepciones import RecursoNoEncontrado
from app.ports.interfaces import WebhookInvalido

bp = Blueprint("webhooks", __name__)


@bp.route("/webhooks/stripe", methods=["POST"])
def stripe():
    pasarela = obtener_pasarela()
    try:
        evento = pasarela.verificar_webhook(
            request.get_data(), request.headers.get("Stripe-Signature")
        )
    except WebhookInvalido as exc:
        return jsonify({"error": "firma_invalida", "detail": str(exc)}), 400
    if not evento.pagado or not evento.referencia:
        return jsonify({"data": {"ignorado": True, "tipo": evento.tipo}}), 200
    try:
        pago, nuevo = confirmar_pago.ejecutar_por_referencia(evento.referencia)
    except RecursoNoEncontrado:
        return jsonify({"error": "pago_no_encontrado"}), 404
    return jsonify({"data": {"confirmado": True, "nuevo": nuevo, "pago_id": str(pago.id)}}), 200
