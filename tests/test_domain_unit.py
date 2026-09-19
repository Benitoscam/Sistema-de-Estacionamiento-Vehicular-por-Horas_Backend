"""Pruebas unitarias del dominio puro — Fase de cierre (rúbrica de pruebas).

Deliberadamente NO usan fixtures de Flask ni la base de datos: prueban
solo `app.domain.value_objects` y `app.domain.services.tarifas`, que no
dependen de ningún framework. Rápidas, aisladas, repetibles y
auto-validantes (FIRST).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.excepciones import RangoInvalido
from app.domain.services import tarifas
from app.domain.value_objects import Dinero, Placa, RangoHorario


# ──────────────────────────────────────────────
# Placa
# ──────────────────────────────────────────────

class TestPlaca:
    def test_camino_feliz_normaliza_mayusculas_y_espacios(self):
        placa = Placa(" abc123 ")
        assert str(placa) == "ABC123"

    def test_camino_feliz_acepta_guion(self):
        placa = Placa("ABC-123")
        assert str(placa) == "ABC-123"

    def test_limite_longitud_minima_tres_caracteres(self):
        placa = Placa("ABC")
        assert str(placa) == "ABC"

    def test_limite_longitud_maxima_quince_caracteres(self):
        valor = "A" * 15
        placa = Placa(valor)
        assert str(placa) == valor

    def test_error_menos_de_tres_caracteres(self):
        with pytest.raises(RangoInvalido):
            Placa("AB")

    def test_error_mas_de_quince_caracteres(self):
        with pytest.raises(RangoInvalido):
            Placa("A" * 16)

    def test_error_caracteres_no_permitidos(self):
        with pytest.raises(RangoInvalido):
            Placa("ABC@123")

    def test_error_valor_vacio_o_none(self):
        with pytest.raises(RangoInvalido):
            Placa("")
        with pytest.raises(RangoInvalido):
            Placa(None)


# ──────────────────────────────────────────────
# RangoHorario
# ──────────────────────────────────────────────

class TestRangoHorario:
    def test_camino_feliz_rango_valido(self):
        inicio = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
        fin = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
        rango = RangoHorario(inicio, fin)
        assert rango.inicio == inicio
        assert rango.fin == fin

    def test_camino_feliz_datetime_naive_se_asume_utc(self):
        inicio = datetime(2026, 9, 19, 8, 0)  # sin tzinfo
        fin = datetime(2026, 9, 19, 9, 0)
        rango = RangoHorario(inicio, fin)
        assert rango.inicio.tzinfo == timezone.utc
        assert rango.fin.tzinfo == timezone.utc

    def test_limite_un_segundo_de_diferencia_es_valido(self):
        inicio = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)
        fin = inicio + timedelta(seconds=1)
        rango = RangoHorario(inicio, fin)
        assert rango.segundos() == 1

    def test_error_fin_igual_a_inicio(self):
        momento = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
        with pytest.raises(RangoInvalido):
            RangoHorario(momento, momento)

    def test_error_fin_anterior_a_inicio(self):
        inicio = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
        fin = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
        with pytest.raises(RangoInvalido):
            RangoHorario(inicio, fin)

    def test_error_valores_none(self):
        momento = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
        with pytest.raises(RangoInvalido):
            RangoHorario(None, momento)
        with pytest.raises(RangoInvalido):
            RangoHorario(momento, None)

    def test_se_solapa_camino_feliz_rangos_cruzados(self):
        a = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        )
        b = RangoHorario(
            datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 11, 0, tzinfo=timezone.utc),
        )
        assert a.se_solapa(b) is True
        assert b.se_solapa(a) is True

    def test_se_solapa_limite_rangos_contiguos_no_se_solapan(self):
        # [8:00, 10:00) y [10:00, 12:00): tocan pero no se solapan
        a = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        )
        b = RangoHorario(
            datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
        )
        assert a.se_solapa(b) is False
        assert b.se_solapa(a) is False

    def test_se_solapa_camino_feliz_rangos_separados(self):
        a = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
        )
        b = RangoHorario(
            datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
        )
        assert a.se_solapa(b) is False

    def test_segundos_calcula_duracion_correcta(self):
        rango = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 10, 30, tzinfo=timezone.utc),
        )
        assert rango.segundos() == 2 * 3600 + 30 * 60


# ──────────────────────────────────────────────
# Dinero
# ──────────────────────────────────────────────

class TestDinero:
    def test_camino_feliz_monto_valido(self):
        dinero = Dinero("14.00")
        assert str(dinero) == "14.00"

    def test_camino_feliz_acepta_numero(self):
        dinero = Dinero(3.5)
        assert str(dinero) == "3.50"

    def test_limite_monto_cero_es_valido(self):
        dinero = Dinero(0)
        assert str(dinero) == "0.00"

    def test_limite_redondeo_half_up_dos_decimales(self):
        dinero = Dinero("10.005")
        assert str(dinero) == "10.01"

    def test_error_monto_negativo(self):
        with pytest.raises(RangoInvalido):
            Dinero("-1.00")

    def test_error_valor_no_numerico(self):
        with pytest.raises(RangoInvalido):
            Dinero("no-es-un-numero")

    def test_error_valor_none(self):
        with pytest.raises(RangoInvalido):
            Dinero(None)


# ──────────────────────────────────────────────
# tarifas.monto_estimado — regla de negocio "techo por hora iniciada"
# ──────────────────────────────────────────────

class TestMontoEstimado:
    def test_camino_feliz_horas_exactas(self):
        rango = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        )
        monto = tarifas.monto_estimado("3.50", rango)
        assert monto == Decimal("7.00")

    def test_limite_un_segundo_pasado_la_hora_cobra_hora_completa(self):
        # 1h 0m 1s → debe cobrar 2 horas completas (techo)
        rango = RangoHorario(
            datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 9, 0, 1, tzinfo=timezone.utc),
        )
        monto = tarifas.monto_estimado("3.50", rango)
        assert monto == Decimal("7.00")  # 2 horas, no 1

    def test_limite_duracion_minima_de_un_segundo_cobra_una_hora(self):
        rango = RangoHorario(
            datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 8, 0, 1, tzinfo=timezone.utc),
        )
        monto = tarifas.monto_estimado("3.50", rango)
        assert monto == Decimal("3.50")  # 1 hora, no fracción

    def test_camino_feliz_redondeo_a_dos_decimales(self):
        rango = RangoHorario(
            datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
        )
        monto = tarifas.monto_estimado("1.20", rango)  # tarifa real de zona "motos"
        assert monto == Decimal("1.20")