"""Disponibilidad: estado del espacio + solapamiento — Fase 2A (puro)."""

from app.domain.excepciones import EspacioNoDisponible
from app.domain.value_objects import RangoHorario


def verificar(estado_espacio, reservas_confirmadas, rango):
    """Lanza EspacioNoDisponible si el espacio no puede reservarse en el rango."""
    if estado_espacio != "disponible":
        raise EspacioNoDisponible(f"espacio en estado '{estado_espacio}', no disponible")
    for reserva in reservas_confirmadas:
        existente = RangoHorario(reserva.hora_inicio_planeada, reserva.hora_fin_planeada)
        if rango.se_solapa(existente):
            raise EspacioNoDisponible("espacio con reserva que se solapa en ese horario")
