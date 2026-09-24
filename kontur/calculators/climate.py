"""КОНТУР-ПРО: охлаждение, вентиляция и теплопотери (СП 50.13330)."""

from __future__ import annotations

from kontur.models import Room

# --- Охлаждение ---
COOLING_EQUIP_LOAD_FACTOR = 0.9  # доля мощности оборудования, переходящая в тепло
COOLING_WALL_HEAT_TRANSFER = 30  # удельный теплоприток через стены, Вт/(м²·°C) * 1e-3 масштаб
COOLING_WALL_SHADING_FACTOR = 0.8  # поправочный коэффициент на инсоляцию/затенение стен
COOLING_WINDOW_HEAT_TRANSFER = 200  # удельный теплоприток через окна, Вт/м² (приведённый)
COOLING_PER_PERSON_W = 100  # тепловыделение одного человека, Вт
COOLING_SAFETY_MARGIN = 1.15  # запас по мощности охлаждения

# --- Вентиляция ---
VENTILATION_AIR_HEAT_CAPACITY = 0.34  # объёмная теплоёмкость воздуха, Вт·ч/(м³·°C)
VENTILATION_DEFAULT_AIR_RATE = 3.0  # кратность воздухообмена по умолчанию, 1/ч

# --- Теплопотери (СП 50.13330) ---
HEAT_LOSS_SCALE_DIVISOR = 100  # масштабный коэффициент периметра помещения (см. Room.width/height)
HEAT_LOSS_R_WALLS = 3.0  # термическое сопротивление утеплённых стен, м²·°C/Вт
HEAT_LOSS_R_ROOF = 4.5  # термическое сопротивление кровли/перекрытия, м²·°C/Вт
HEAT_LOSS_R_WINDOWS = 0.6  # термическое сопротивление окон, м²·°C/Вт
HEAT_LOSS_WINDOW_AREA_SHARE = 0.2  # доля остекления в площади стен


class CoolingCalculator:
    """Расчёт охлаждения с учётом теплопритоков"""

    @staticmethod
    def calc(
        equip_power_w: float,
        room_area: float = 0,
        people_count: int = 0,
        window_area: float = 0,
        delta_t: float = 10,
    ) -> float:
        q_equip = equip_power_w * COOLING_EQUIP_LOAD_FACTOR
        q_walls = COOLING_WALL_HEAT_TRANSFER * room_area * delta_t / 1000 * COOLING_WALL_SHADING_FACTOR
        q_windows = COOLING_WINDOW_HEAT_TRANSFER * window_area / 1000
        q_people = COOLING_PER_PERSON_W * people_count
        total_kw = (q_equip + q_walls + q_windows + q_people) / 1000
        return round(total_kw * COOLING_SAFETY_MARGIN * 1000)


class VentilationCalculator:
    """Расчёт вентиляции по кратности воздухообмена"""

    @staticmethod
    def calc(
        heat_w: float,
        room_volume_m3: float = 0,
        delta_t: float = 10,
        air_rate: float = VENTILATION_DEFAULT_AIR_RATE,
    ) -> float:
        q_from_heat = heat_w / (VENTILATION_AIR_HEAT_CAPACITY * delta_t) if delta_t > 0 else 0
        q_from_rate = room_volume_m3 * air_rate
        return round(max(q_from_heat, q_from_rate))


class HeatLossCalculator:
    """Расчёт теплопотерь по СП 50.13330"""

    @staticmethod
    def calc(rooms: list[Room], outdoor_temp: float = -28, indoor_temp: float = 20) -> float:
        total_loss = 0.0
        delta_t = indoor_temp - outdoor_temp
        for room in rooms:
            # Ограждающие конструкции (упрощённо, масштаб см. Room.width/height)
            walls_area = 2 * (room.width + room.height) / HEAT_LOSS_SCALE_DIVISOR * room.height_m
            roof_area = room.area
            windows_area = walls_area * HEAT_LOSS_WINDOW_AREA_SHARE
            walls_net = walls_area - windows_area

            q_walls = walls_net * delta_t / HEAT_LOSS_R_WALLS
            q_windows = windows_area * delta_t / HEAT_LOSS_R_WINDOWS
            q_roof = roof_area * delta_t / HEAT_LOSS_R_ROOF
            total_loss += q_walls + q_windows + q_roof

        return round(total_loss)
