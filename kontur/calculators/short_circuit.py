"""КОНТУР-ПРО: расчёт токов короткого замыкания по ГОСТ 28249-93.

Схема замещения: питающая энергосистема (представлена реактивным
сопротивлением x_s, приведённым к стороне НН по мощности КЗ на шинах ВН) +
понижающий трансформатор (R_t, X_t по каталожным данным опыта КЗ) + кабельная
линия (r_c, x_c по длине и сечению).

Упрощения расчётной модели (см. ГОСТ 28249-93, который рекомендует их
учитывать при необходимости повышенной точности):
- не учитывается переходное сопротивление контактов и коммутационных
  аппаратов в цепи КЗ;
- не учитывается сопротивление электрической дуги в месте КЗ;
- сопротивление нулевой последовательности трансформатора Д/Ун-11 принято
  приближённо равным сопротивлению прямой последовательности
  (Z0_t ≈ Z1_t), что справедливо для трёхстержневых трансформаторов этой
  схемы соединения и обычно применяется в инженерных расчётах.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, TypedDict

# --- Параметры схемы замещения ---
COPPER_RESISTIVITY_OHM_MM2_PER_M = 0.0175  # удельное сопротивление меди, Ом·мм²/м
INDUCTIVE_REACTANCE_OHM_PER_M = 0.0001  # погонное индуктивное сопротивление кабеля, Ом/м
SHOCK_CURRENT_PEAK_FACTOR = 1.8  # коэффициент ударного тока для дальнего КЗ
BREAKER_CURVE_MULTIPLIER = {"B": 5, "C": 10, "D": 20}  # кратность тока мгновенного расцепления

# --- Параметры питающего трансформатора по умолчанию (ТМГ-400/10-0,4 Д/Ун-11) ---
DEFAULT_TRANSFORMER_KVA: Final = 400.0  # номинальная мощность, кВА
DEFAULT_TRANSFORMER_UK_PCT: Final = 4.5  # напряжение КЗ, %
DEFAULT_TRANSFORMER_PK_KW: Final = 5.5  # потери КЗ, кВт
DEFAULT_SYSTEM_SC_MVA: Final = 200.0  # мощность КЗ энергосистемы на стороне ВН, МВА


@dataclass(frozen=True)
class SourceImpedance:
    """Сопротивление питающей сети + трансформатора, приведённое к стороне НН (Ом)."""

    r_ohm: float
    x_ohm: float

    @classmethod
    def from_transformer(
        cls,
        s_kva: float = DEFAULT_TRANSFORMER_KVA,
        uk_pct: float = DEFAULT_TRANSFORMER_UK_PCT,
        pk_kw: float = DEFAULT_TRANSFORMER_PK_KW,
        voltage: float = 380,
        system_short_circuit_mva: float = DEFAULT_SYSTEM_SC_MVA,
    ) -> SourceImpedance:
        """Сопротивление трансформатора (по опыту КЗ) + энергосистемы, приведённое к стороне НН.

        R_t = ΔP_k·U²/S², Z_t = (u_k/100)·U²/S, X_t = sqrt(Z_t² − R_t²) — ГОСТ 28249-93.
        Реактивное сопротивление системы x_s = U²/S_kz складывается с X_t.
        """
        if s_kva <= 0:
            raise ValueError("s_kva must be positive")
        if uk_pct <= 0:
            raise ValueError("uk_pct must be positive")
        if pk_kw <= 0:
            raise ValueError("pk_kw must be positive")
        if voltage <= 0:
            raise ValueError("voltage must be positive")
        if system_short_circuit_mva <= 0:
            raise ValueError("system_short_circuit_mva must be positive")

        s_va = s_kva * 1000
        pk_w = pk_kw * 1000
        r_t = pk_w * voltage**2 / s_va**2
        z_t = (uk_pct / 100) * voltage**2 / s_va
        x_t = math.sqrt(max(z_t**2 - r_t**2, 0.0))

        system_sc_va = system_short_circuit_mva * 1_000_000
        x_system = voltage**2 / system_sc_va

        return cls(r_ohm=r_t, x_ohm=x_t + x_system)


DEFAULT_SOURCE: Final = SourceImpedance.from_transformer()


class BreakerCheckResult(TypedDict):
    ok: bool
    i_instant: float
    i_3ph: float
    message: str


class ShortCircuitCalculator:
    """Расчёт токов короткого замыкания по ГОСТ 28249-93"""

    @staticmethod
    def calc_3phase(
        cable_length_m: float,
        cable_section: float = 2.5,
        voltage: float = 380,
        source: SourceImpedance = DEFAULT_SOURCE,
    ) -> float:
        """Ток трёхфазного КЗ в конце кабельной линии, А."""
        if cable_section <= 0:
            raise ValueError("cable_section must be positive")
        r_cable = COPPER_RESISTIVITY_OHM_MM2_PER_M * cable_length_m / cable_section
        x_cable = INDUCTIVE_REACTANCE_OHM_PER_M * cable_length_m
        z_total = math.sqrt((source.r_ohm + r_cable) ** 2 + (source.x_ohm + x_cable) ** 2)
        if z_total == 0:
            return 0
        i_3ph = voltage / (math.sqrt(3) * z_total)
        return round(i_3ph, 1)

    @staticmethod
    def calc_1phase(
        cable_length_m: float,
        cable_section: float = 2.5,
        voltage: float = 220,
        source: SourceImpedance = DEFAULT_SOURCE,
    ) -> float:
        """Ток однофазного КЗ (петля фаза-ноль) в конце кабельной линии, А.

        Для трансформатора со схемой соединения Д/Ун-11 сопротивление нулевой
        последовательности приближённо равно сопротивлению прямой
        последовательности (Z0_t ≈ Z1_t), поэтому полное сопротивление петли
        трансформатора принимается равным source (без деления/утроения).
        Сечение нулевого проводника принято равным сечению фазного.
        """
        if cable_section <= 0:
            raise ValueError("cable_section must be positive")
        r_cable = 2 * COPPER_RESISTIVITY_OHM_MM2_PER_M * cable_length_m / cable_section  # фаза + ноль
        x_cable = 2 * INDUCTIVE_REACTANCE_OHM_PER_M * cable_length_m
        z_total = math.sqrt((source.r_ohm + r_cable) ** 2 + (source.x_ohm + x_cable) ** 2)
        if z_total == 0:
            return 0
        i_1ph = voltage / z_total
        return round(i_1ph, 1)

    @staticmethod
    def calc_iudar(i_3ph: float) -> float:
        """Ударный ток КЗ (1.8 — коэффициент для дальнего КЗ)"""
        return round(i_3ph * math.sqrt(2) * SHOCK_CURRENT_PEAK_FACTOR, 1)

    @staticmethod
    def check_breaker(breaker_a: int, i_3ph: float, curve: str = "C") -> BreakerCheckResult:
        """Проверка отключающей способности автомата"""
        i_instant = breaker_a * BREAKER_CURVE_MULTIPLIER.get(curve, 10)
        ok = i_3ph >= i_instant
        return {
            "ok": ok,
            "i_instant": i_instant,
            "i_3ph": i_3ph,
            "message": f"{'OK' if ok else 'Недостаточно'}: Iкз={i_3ph}А, Iоткл={i_instant}А",
        }
