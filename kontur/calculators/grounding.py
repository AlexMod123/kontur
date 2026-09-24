"""КОНТУР-ПРО: заземление и молниезащита по СО 153-34.21.122-2003."""

from __future__ import annotations

import math
from typing import TypedDict

# --- Коэффициент использования электродов (СО 153) ---
ROD_UTILIZATION_DROP_PER_ROD = 0.05  # снижение коэффициента использования на электрод
MAX_ROD_COUNT = 50  # предел перебора количества электродов (защита от бесконечного цикла)

# --- Молниезащита ---
LIGHTNING_STRIKE_AREA_SCALE = 1e-6  # переводной коэффициент в формуле ожидаемого числа ударов N
LIGHTNING_LOW_RISK_STRIKES = 1  # N < 1 -> молниезащита не требуется
LIGHTNING_MID_RISK_STRIKES = 3  # N < 3 -> зона Б (III категория), иначе зона А (I категория)


class GroundResult(TypedDict):
    resistance: float
    rod_count: int
    single_resistance: float


class LightningResult(TypedDict):
    strikes_per_year: float
    zone: str
    risk: str
    building_area: float


class GroundCalculator:
    """Расчёт заземления по СО 153-34.21.122-2003"""

    @staticmethod
    def calc(
        rho_soil: float = 100,
        length_rod: float = 3.0,
        diameter_rod: float = 0.016,
        depth: float = 0.7,
        max_r: float = 4.0,
    ) -> GroundResult:
        single_r = GroundCalculator._single_rod(rho_soil, length_rod, diameter_rod, depth)
        n = 1
        while True:
            if n == 1:
                total_r = single_r
            else:
                # Коэффициент использования (СО 153)
                util = 1.0 - ROD_UTILIZATION_DROP_PER_ROD * (n - 1) / n
                total_r = single_r / (n * util)
            if total_r <= max_r or n >= MAX_ROD_COUNT:
                break
            n += 1
        return {"resistance": round(total_r, 2), "rod_count": n, "single_resistance": round(single_r, 2)}

    @staticmethod
    def _single_rod(rho: float, rod_length: float, d: float, t: float) -> float:
        if rod_length <= 0:
            raise ValueError("length_rod must be positive")
        if d <= 0:
            raise ValueError("diameter_rod must be positive")
        t_eff = t + rod_length / 2
        if 4 * t_eff - rod_length <= 0:
            return rho / (2 * math.pi * rod_length) * math.log(2 * rod_length / d)
        return (
            rho
            / (2 * math.pi * rod_length)
            * (
                math.log(2 * rod_length / d)
                + 0.5 * math.log(4 * t_eff + rod_length) / (4 * t_eff - rod_length)
            )
        )


class LightningProtection:
    """Расчёт молниезащиты по СО 153-34.21.122-2003"""

    @staticmethod
    def assess(
        building_length: float, building_width: float, building_height: float, region_thunderstorms: int = 40
    ) -> LightningResult:
        # Ожидаемое число ударов молнии (N)
        s = (
            building_length * building_width
            + 6 * building_height * (building_length + building_width)
            + 9 * math.pi * building_height**2
        )
        n = 0.0 if s <= 0 else region_thunderstorms * s * LIGHTNING_STRIKE_AREA_SCALE

        if n < LIGHTNING_LOW_RISK_STRIKES:
            zone = "Не требуется (N < 1)"
            risk = "Низкий"
        elif n < LIGHTNING_MID_RISK_STRIKES:
            zone = "Зона Б (III категория)"
            risk = "Средний"
        else:
            zone = "Зона А (I категория)"
            risk = "Высокий"

        return {"strikes_per_year": round(n, 2), "zone": zone, "risk": risk, "building_area": round(s, 1)}
