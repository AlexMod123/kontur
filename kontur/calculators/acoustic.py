"""КОНТУР-ПРО: расчёт уровня шума по СНиП 23-03."""

from __future__ import annotations

import math

from kontur.models import Device

# --- Уровень звуковой мощности источников, дБ ---
NOISE_SOURCES_DB = {
    "server": 65,
    "rack42u": 70,
    "precise_ac": 68,
    "ac_unit": 55,
    "switch": 45,
    "ups": 50,
    "nvr": 48,
    "router": 40,
}
DEFAULT_DEVICE_NOISE_DB = 35  # уровень шума для неучтённых типов оборудования
BACKGROUND_NOISE_DB = 30  # фоновый шум помещения при отсутствии источников
ROOM_ABSORPTION_COEFF = 0.15  # коэффициент звукопоглощения помещения
ROOM_ABSORPTION_VOLUME_EXPONENT = 0.66  # показатель степени объёма в формуле поглощения


class AcousticCalculator:
    """Расчёт уровня шума по СНиП 23-03"""

    @staticmethod
    def calc(devices: list[Device], room_volume_m3: float = 100) -> float:
        if room_volume_m3 < 0:
            raise ValueError("room_volume_m3 must not be negative")
        # Уровень звуковой мощности источников
        total_power = 0.0
        for dev in devices:
            dev_noise = NOISE_SOURCES_DB.get(dev.equip_type, DEFAULT_DEVICE_NOISE_DB)
            total_power += 10 ** (dev_noise / 10)

        if total_power == 0:
            return BACKGROUND_NOISE_DB

        # Снижение с расстоянием (упрощённо)
        l_w = 10 * math.log10(total_power)
        # Поправка на объём помещения
        room_absorption = ROOM_ABSORPTION_COEFF * room_volume_m3**ROOM_ABSORPTION_VOLUME_EXPONENT
        l_p = l_w - 10 * math.log10(max(room_absorption, 1))
        return round(l_p, 1)
