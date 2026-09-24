"""Тесты расчёта токов КЗ (ShortCircuitCalculator) по ГОСТ 28249-93."""

from __future__ import annotations

import math
import unittest

import pytest

from kontur.calculators import DEFAULT_SOURCE, ShortCircuitCalculator, SourceImpedance
from kontur.calculators.short_circuit import COPPER_RESISTIVITY_OHM_MM2_PER_M, INDUCTIVE_REACTANCE_OHM_PER_M


class TestShortCircuitCalculator(unittest.TestCase):
    def test_3phase(self):
        i = ShortCircuitCalculator.calc_3phase(30, 2.5)
        self.assertGreater(i, 0)

    def test_1phase(self):
        i = ShortCircuitCalculator.calc_1phase(30, 2.5)
        self.assertGreater(i, 0)

    def test_iudar(self):
        i = ShortCircuitCalculator.calc_iudar(1000)
        self.assertGreater(i, 1000)

    def test_check_breaker_ok(self):
        r = ShortCircuitCalculator.check_breaker(16, 500)
        self.assertTrue(r["ok"])


class TestShortCircuitReference:
    """Опорные значения пересчитаны независимой формулой для новой модели."""

    def test_calc_3phase_reference_independent_formula(self):
        # Независимый расчёт "с нуля" для L=30 м, s=2.5 мм², U=380 В.
        r_c = COPPER_RESISTIVITY_OHM_MM2_PER_M * 30 / 2.5
        x_c = INDUCTIVE_REACTANCE_OHM_PER_M * 30
        z = math.sqrt((DEFAULT_SOURCE.r_ohm + r_c) ** 2 + (DEFAULT_SOURCE.x_ohm + x_c) ** 2)
        expected = round(380 / (math.sqrt(3) * z), 1)
        assert ShortCircuitCalculator.calc_3phase(30, 2.5) == expected
        assert expected == 1016.6

    def test_calc_1phase_reference_independent_formula(self):
        # Петля фаза-ноль: сопротивление кабеля удваивается, источника - нет
        # (Z0_t ≈ Z1_t для Д/Ун-11).
        r_c = 2 * COPPER_RESISTIVITY_OHM_MM2_PER_M * 30 / 2.5
        x_c = 2 * INDUCTIVE_REACTANCE_OHM_PER_M * 30
        z = math.sqrt((DEFAULT_SOURCE.r_ohm + r_c) ** 2 + (DEFAULT_SOURCE.x_ohm + x_c) ** 2)
        expected = round(220 / z, 1)
        assert ShortCircuitCalculator.calc_1phase(30, 2.5) == expected
        assert expected == 517.0

    def test_calc_iudar_reference(self):
        assert ShortCircuitCalculator.calc_iudar(1000) == 2545.6

    def test_check_breaker_reference(self):
        r = ShortCircuitCalculator.check_breaker(16, 500)
        assert r == {
            "ok": True,
            "i_instant": 160,
            "i_3ph": 500,
            "message": "OK: Iкз=500А, Iоткл=160А",
        }


class TestShortCircuitSanity:
    def test_3phase_at_zero_length_matches_source_impedance(self):
        # I(3) при L=0 определяется только сопротивлением сети+трансформатора:
        # U / (sqrt(3) * |Z_src|). Для ТМГ-400/10 при 380 В это ~13 кА
        # (проверено расчётом; попадает в типичный для ТМГ-400 диапазон
        # порядка 10-15 кА при мощности КЗ энергосистемы 200 МВА).
        z_src = math.sqrt(DEFAULT_SOURCE.r_ohm**2 + DEFAULT_SOURCE.x_ohm**2)
        expected = 380 / (math.sqrt(3) * z_src)
        i = ShortCircuitCalculator.calc_3phase(0, 2.5)
        assert 10_000 < i < 15_000
        assert i == pytest.approx(expected, rel=1e-3)

    def test_1phase_less_than_3phase_for_long_cable(self):
        i3 = ShortCircuitCalculator.calc_3phase(100, 2.5)
        i1 = ShortCircuitCalculator.calc_1phase(100, 2.5)
        assert i1 < i3

    def test_current_decreases_monotonically_with_length(self):
        lengths = [0, 10, 30, 50, 100, 200]
        currents_3ph = [ShortCircuitCalculator.calc_3phase(length, 2.5) for length in lengths]
        currents_1ph = [ShortCircuitCalculator.calc_1phase(length, 2.5) for length in lengths]
        assert currents_3ph == sorted(currents_3ph, reverse=True)
        assert currents_1ph == sorted(currents_1ph, reverse=True)

    def test_bigger_transformer_gives_bigger_current(self):
        small = SourceImpedance.from_transformer(s_kva=250)
        big = SourceImpedance.from_transformer(s_kva=630)
        i_small = ShortCircuitCalculator.calc_3phase(30, 2.5, source=small)
        i_big = ShortCircuitCalculator.calc_3phase(30, 2.5, source=big)
        assert i_big > i_small


class TestSourceImpedance:
    def test_from_transformer_default_matches_default_source(self):
        assert SourceImpedance.from_transformer() == DEFAULT_SOURCE

    def test_from_transformer_reactance_non_negative(self):
        source = SourceImpedance.from_transformer(s_kva=1000, uk_pct=5.5, pk_kw=10.5)
        assert source.x_ohm >= 0

    def test_from_transformer_rejects_non_positive_s_kva(self):
        with pytest.raises(ValueError):
            SourceImpedance.from_transformer(s_kva=0)

    def test_from_transformer_rejects_non_positive_uk_pct(self):
        with pytest.raises(ValueError):
            SourceImpedance.from_transformer(uk_pct=-1)

    def test_from_transformer_rejects_non_positive_pk_kw(self):
        with pytest.raises(ValueError):
            SourceImpedance.from_transformer(pk_kw=0)

    def test_from_transformer_rejects_non_positive_voltage(self):
        with pytest.raises(ValueError):
            SourceImpedance.from_transformer(voltage=0)

    def test_from_transformer_rejects_non_positive_system_sc_mva(self):
        with pytest.raises(ValueError):
            SourceImpedance.from_transformer(system_short_circuit_mva=0)


class TestShortCircuitGuards:
    def test_calc_3phase_rejects_zero_section(self):
        with pytest.raises(ValueError):
            ShortCircuitCalculator.calc_3phase(30, 0)

    def test_calc_1phase_rejects_zero_section(self):
        with pytest.raises(ValueError):
            ShortCircuitCalculator.calc_1phase(30, 0)
