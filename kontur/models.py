"""КОНТУР-ПРО: модуль models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from enum import StrEnum
from typing import Any

from kontur.config import COS_PHI_DEFAULT

# ============================================================================
# СЕКЦИЯ 2: МОДЕЛИ ДАННЫХ
# ============================================================================


class CheckStatus(StrEnum):
    """Статус проверки модели (используется ModelChecker).

    Значения совпадают со строками, исторически возвращаемыми в словарях
    проверок, поэтому сравнение ``status == "OK"`` продолжает работать.
    """

    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


class _DictSerializableMixin:
    """Аддитивные помощники сериализации для моделей-датаклассов."""

    def to_dict(self) -> dict[str, Any]:
        """Представить модель в виде словаря (для JSON/сохранения)."""
        return asdict(self)  # type: ignore[call-overload]

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Создать модель из словаря, игнорируя незнакомые ключи."""
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Device(_DictSerializableMixin):
    """Инженерное устройство (нагрузка) на плане этажа.

    Единицы: power_w — Вт, voltage — В, price — ₽, x/y/z — м.
    """

    id: str
    name: str
    power_w: float
    category: str
    icon: str = "📦"
    x: float = 100
    y: float = 100
    z: float = 1.0  # высота установки (м)
    floor: int = 1
    voltage: float = 220
    equip_type: str = ""
    custom: bool = False
    room_id: str | None = None
    price: float = 0
    designation: str = ""  # позиционное обозначение (ГОСТ 2.710)


@dataclass
class Room(_DictSerializableMixin):
    """Помещение на плане этажа.

    Единицы: area/width/height — м² / м / м, height_m — м (высота потолка).
    """

    id: str
    name: str
    area: float
    x: float = 50
    y: float = 50
    width: float = 200
    height: float = 150
    floor: int = 1
    pc_count: int = 0
    camera_count: int = 0
    has_skud: bool = False
    has_ops: bool = False
    custom: bool = False
    height_m: float = 3.0  # высота потолка


@dataclass
class Wall(_DictSerializableMixin):
    """Отрезок стены на плане этажа (координаты в метрах)."""

    x1: float
    y1: float
    x2: float
    y2: float
    floor: int = 1


@dataclass
class Door(_DictSerializableMixin):
    """Дверной проём. Единицы: x/y — м, width — мм, angle — градусы."""

    x: float
    y: float
    width: float = 90
    angle: float = 0
    floor: int = 1


@dataclass
class Annotation(_DictSerializableMixin):
    """Текстовая аннотация на плане этажа (координаты в метрах)."""

    x: float
    y: float
    text: str = ""
    floor: int = 1


@dataclass
class CableTrace(_DictSerializableMixin):
    """Трасса прокладки кабеля к устройству.

    Единицы: length_m/vertical_length — м.
    """

    device_id: str
    path: list[tuple[float, float]] = field(default_factory=list)
    length_m: float = 0.0
    system: str = "power"
    vertical_length: float = 0.0  # вертикальная длина (подъём/спуск)


@dataclass
class EngineeringResult(_DictSerializableMixin):
    """Сводный результат инженерного расчёта проекта.

    Единицы: мощности — Вт, токи — А, напряжение — В, кабели — мм²,
    сопротивление заземления — Ом, вентиляция — м³/ч, освещённость — лк,
    шум — дБ, деньги — ₽.
    """

    installed_power_w: float = 0
    demand_power_w: float = 0
    # расчётный ток ввода (наиболее нагруженная фаза с учётом cos φ), А
    total_current_a: float = 0
    per_phase_current: dict[str, float] = field(default_factory=lambda: {"A": 0, "B": 0, "C": 0})
    phase_imbalance_pct: float = 0
    recommended_breaker: int = 16
    recommended_cable: str = "ВВГнг-LS 5x2.5"
    cable_section: float = 2.5
    voltage_drop_pct: float = 0
    grounding_r: float = 0
    grounding_status: str = "OK"
    cooling_required_w: float = 0
    ventilation_required_m3h: float = 0
    ups_power_w: float = 0
    ups_autonomy_min: float = 0
    ups_battery_count: int = 0
    selectivity_ok: bool = True
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cost_total: float = 0
    device_count: int = 0
    room_count: int = 0
    cable_traces: list[CableTrace] = field(default_factory=list)
    cos_phi: float = COS_PHI_DEFAULT
    reactive_power_var: float = 0
    active_power_w: float = 0
    short_circuit_3ph: float = 0
    short_circuit_1ph: float = 0
    short_circuit_iudar: float = 0
    lightning_risk: str = ""
    lightning_zone: str = ""
    leakage_current_ma: float = 0
    leakage_uzo_ma: int = 30
    lighting_lux: float = 0
    lighting_lamps: int = 0
    heat_loss_w: float = 0
    noise_level_db: float = 0
    lan_ports: int = 0
    lan_cable_m: float = 0
    poe_budget_w: float = 0
    poe_required_w: float = 0
