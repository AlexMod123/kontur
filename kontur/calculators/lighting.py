"""КОНТУР-ПРО: расчёт освещённости по СП 52.13330 (метод коэффициента использования)."""

from __future__ import annotations

import math
from typing import ClassVar, TypedDict

# --- Резервный коэффициент использования, если комбинация (тип, индекс) не найдена в таблице ---
FALLBACK_UTILIZATION = 0.5
DEFAULT_NORM_LUX = 300


class LightingResult(TypedDict):
    lux: int
    lamps: int
    utilization: float


class LightingCalculator:
    """Расчёт освещённости по СП 52.13330 (метод коэффициента использования)"""

    # Таблица коэффициентов использования (упрощённая)
    UTILIZATION_TABLE: ClassVar[dict[tuple[str, float], float]] = {
        ("room", 0.5): 0.28,
        ("room", 0.7): 0.42,
        ("room", 0.8): 0.49,
        ("room", 0.9): 0.56,
        ("room", 1.0): 0.63,
        ("office", 0.5): 0.35,
        ("office", 0.7): 0.48,
        ("office", 0.8): 0.55,
        ("office", 0.9): 0.62,
        ("office", 1.0): 0.69,
        ("storage", 0.5): 0.22,
        ("storage", 0.7): 0.35,
        ("storage", 0.8): 0.42,
        ("storage", 0.9): 0.48,
        ("storage", 1.0): 0.55,
    }

    NORM_LUX: ClassVar[dict[str, int]] = {
        "room": 300,
        "office": 500,
        "storage": 200,
        "corridor": 150,
        "server": 500,
        "industrial": 300,
        "default": 300,
    }

    @staticmethod
    def calc(
        room_area: float,
        room_type: str = "office",
        ceiling_height: float = 3.0,
        lamp_flux: float = 3000,
        maintenance_factor: float = 0.8,
    ) -> LightingResult:
        if lamp_flux <= 0:
            raise ValueError("lamp_flux must be positive")
        if maintenance_factor <= 0:
            raise ValueError("maintenance_factor must be positive")
        norm = LightingCalculator.NORM_LUX.get(room_type, DEFAULT_NORM_LUX)
        ceiling_idx = min(ceiling_height / room_area**0.5, 1.0) if room_area > 0 else 0.5
        u = LightingCalculator.UTILIZATION_TABLE.get((room_type, round(ceiling_idx, 1)), FALLBACK_UTILIZATION)
        if u <= 0:
            u = FALLBACK_UTILIZATION
        n_lamps = math.ceil((norm * room_area) / (lamp_flux * u * maintenance_factor))
        return {"lux": norm, "lamps": n_lamps, "utilization": round(u, 2)}
