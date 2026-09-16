"""Puertos del dominio — Fase 3A. Contratos de salida (los implementan los adaptadores)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SesionCheckout:
    url: str
    referencia: str
    modo: str


@dataclass
class EventoPago:
    tipo: str
    referencia: str
    pagado: bool


class WebhookInvalido(Exception):
    """Firma o cuerpo del webhook no válido."""


class IPasarelaPago(ABC):
    """Contrato de pasarela de pago (fake en dev, Stripe en test/prod)."""

    @abstractmethod
    def crear_sesion(self, monto, descripcion, exito_url, cancela_url, referencia_interna):
        """Crea una sesión de checkout. Retorna SesionCheckout."""

    @abstractmethod
    def verificar_webhook(self, cuerpo, firma):
        """Valida el webhook y retorna EventoPago. Lanza WebhookInvalido."""
