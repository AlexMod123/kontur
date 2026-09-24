"""КОНТУР-ПРО: модуль scale."""

from __future__ import annotations

# ============================================================================
# СЕКЦИЯ 11: SCALE MANAGER
# ============================================================================


class ScaleManager:
    """Менеджер масштаба (пиксели ↔ метры)."""

    def __init__(self, pixels_per_meter: float = 50.0) -> None:
        """Инициализация менеджера масштаба."""
        self.ppm = pixels_per_meter

    def px_to_m(self, px: float) -> float:
        """Конвертировать пиксели в метры."""
        return px / self.ppm

    def m_to_px(self, m: float) -> float:
        """Конвертировать метры в пиксели."""
        return m * self.ppm

    def area_px_to_m2(self, area_px: float) -> float:
        """Конвертировать площадь из пикселей в квадратные метры."""
        return area_px / (self.ppm**2)

    def area_m2_to_px(self, area_m2: float) -> float:
        """Конвертировать площадь из квадратных метров в пиксели."""
        return area_m2 * (self.ppm**2)

    # Alias for px_to_m (duplicate byte-for-byte).
    length_px_to_m = px_to_m

    def set_scale(self, ppm: float) -> None:
        """Установить новый масштаб."""
        self.ppm = ppm
