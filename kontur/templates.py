"""КОНТУР-ПРО: модуль templates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from kontur.config import PRICE_LIST, TEMPLATES
from kontur.designation import DesignationGenerator
from kontur.models import Device, Room

# ============================================================================
# СЕКЦИЯ 17: CLI
# ============================================================================

#: Начальные координаты (px) первой комнаты на плане; далее комнаты
#: раскладываются слева направо и переносятся на новую "строку" после X_WRAP.
INITIAL_OFFSET_PX = 100
X_WRAP_PX = 800
ROOM_GAP_PX = 50
ROW_MIN_HEIGHT_PX = 200

#: Масштаб перевода площади помещения (м²) в ширину/высоту плана (px).
ROOM_SIZE_SCALE = 15
ROOM_MAX_WIDTH_PX = 400


@dataclass(frozen=True)
class _RoomDeviceSpec:
    """Описание одного повторяющегося вида устройств внутри помещения.

    ``count`` определяет, сколько экземпляров создать по описанию комнаты
    (``room_def``), а ``pos`` — абсолютные координаты (x, y) для j-го
    (1-индексированного) экземпляра; принимает (x_off, y_off, w, h, j) и
    воспроизводит порядок операций оригинальных формул, чтобы избежать
    расхождений в последнем разряде float из-за иной ассоциативности "+"/"-".
    """

    name_tpl: str
    power_w: float
    category: str
    icon: str
    equip_type: str
    count: Callable[[dict], int]
    pos: Callable[[float, float, float, float, int], tuple[float, float]]


@dataclass(frozen=True)
class _StaticDeviceSpec:
    """Описание одиночного устройства с фиксированными координатами (серверная)."""

    name: str
    power_w: float
    category: str
    icon: str
    equip_type: str
    x: float
    y: float


#: Порядок и состав устройств, повторяемых в каждом помещении шаблона.
#: Порядок важен: он определяет последовательность id/designation устройств.
ROOM_DEVICE_SPECS: list[_RoomDeviceSpec] = [
    _RoomDeviceSpec(
        name_tpl="РМ {i:02d}.{j:02d}",
        power_w=450,
        category="it",
        icon="💻",
        equip_type="pc",
        count=lambda rd: rd.get("pc", 0),
        pos=lambda x_off, y_off, w, h, j: (
            x_off + 30 + (j - 1) % 4 * 40,
            y_off + 30 + (j - 1) // 4 * 40,
        ),
    ),
    _RoomDeviceSpec(
        name_tpl="IP-камера {i:02d}.{j:02d}",
        power_w=25,
        category="camera",
        icon="🎥",
        equip_type="camera_ip",
        count=lambda rd: rd.get("cameras", 0),
        pos=lambda x_off, y_off, w, h, j: (x_off + w - 30, y_off + 30 + (j - 1) * 40),
    ),
    _RoomDeviceSpec(
        name_tpl="Контроллер СКУД {i:02d}",
        power_w=50,
        category="skud",
        icon="🔑",
        equip_type="skud_ctrl",
        count=lambda rd: 1 if rd.get("skud") else 0,
        pos=lambda x_off, y_off, w, h, j: (x_off + w - 30, y_off + h - 30),
    ),
    _RoomDeviceSpec(
        name_tpl="Замок СКУД {i:02d}",
        power_w=15,
        category="skud",
        icon="🚪",
        equip_type="skud_lock",
        count=lambda rd: 1 if rd.get("skud") else 0,
        pos=lambda x_off, y_off, w, h, j: (x_off + w - 60, y_off + h - 30),
    ),
    _RoomDeviceSpec(
        name_tpl="Прибор ОПС {i:02d}",
        power_w=80,
        category="ops",
        icon="🔥",
        equip_type="ops_panel",
        count=lambda rd: 1 if rd.get("ops") else 0,
        pos=lambda x_off, y_off, w, h, j: (x_off + 30, y_off + h - 30),
    ),
    _RoomDeviceSpec(
        name_tpl="Датчик дымовой {i:02d}.{j:02d}",
        power_w=3,
        category="ops",
        icon="💨",
        equip_type="ops_smoke",
        count=lambda rd: 2 if rd.get("ops") else 0,
        pos=lambda x_off, y_off, w, h, j: (x_off + 60 + (j - 1) * 40, y_off + h - 60),
    ),
]

#: Оборудование серверной, добавляемое один раз, если tpl["server_room"] истинен.
SERVER_ROOM_SPECS: list[_StaticDeviceSpec] = [
    _StaticDeviceSpec("Серверная стойка 42U", 5000, "it", "🔲", "rack42u", 50, 50),
    _StaticDeviceSpec("Коммутатор 48p PoE+", 750, "network", "🔌", "switch", 50, 80),
    _StaticDeviceSpec("NVR видеосервер", 400, "camera", "💾", "nvr", 50, 110),
]


class _DeviceFactory:
    """Фабрика устройств: последовательные id, цены из прайс-листа, обозначения ГОСТ."""

    def __init__(self) -> None:
        self._idx = 0

    def _next_id(self) -> str:
        """Выдать очередной последовательный id вида dev_NNN."""
        self._idx += 1
        return f"dev_{self._idx:03d}"

    def _make(
        self,
        name: str,
        power_w: float,
        category: str,
        icon: str,
        equip_type: str,
        x: float,
        y: float,
        room_id: str | None = None,
    ) -> Device:
        """Создать одно устройство с ценой и позиционным обозначением."""
        dev = Device(
            id=self._next_id(),
            name=name,
            power_w=power_w,
            category=category,
            icon=icon,
            x=x,
            y=y,
            equip_type=equip_type,
            room_id=room_id,
            price=PRICE_LIST.get(equip_type, 0),
        )
        dev.designation = DesignationGenerator.generate(dev)
        return dev

    def build_room_devices(
        self,
        room_def: dict,
        i: int,
        rid: str,
        x_off: float,
        y_off: float,
        w: float,
        h: float,
    ) -> list[Device]:
        """Построить все устройства помещения по таблице ROOM_DEVICE_SPECS."""
        devices: list[Device] = []
        for spec in ROOM_DEVICE_SPECS:
            count = spec.count(room_def)
            for j in range(1, count + 1):
                x, y = spec.pos(x_off, y_off, w, h, j)
                devices.append(
                    self._make(
                        name=spec.name_tpl.format(i=i, j=j),
                        power_w=spec.power_w,
                        category=spec.category,
                        icon=spec.icon,
                        equip_type=spec.equip_type,
                        x=x,
                        y=y,
                        room_id=rid,
                    )
                )
        return devices

    def build_server_room_devices(self) -> list[Device]:
        """Построить фиксированный набор оборудования серверной."""
        return [
            self._make(s.name, s.power_w, s.category, s.icon, s.equip_type, s.x, s.y)
            for s in SERVER_ROOM_SPECS
        ]


def generate_template(template_name: str, tier: int = 1) -> tuple[list[Device], list[Room]]:
    """Сгенерировать устройства и помещения по шаблону из TEMPLATES.

    Неизвестное имя шаблона откатывается на "Офис". Параметр ``tier`` пока не
    влияет на состав устройств/помещений (зарезервирован для будущих правок),
    но сохранён в сигнатуре ради совместимости с вызывающим кодом.
    """
    tpl = TEMPLATES.get(template_name, TEMPLATES["Офис"])
    rooms: list[Room] = []
    devices: list[Device] = []

    DesignationGenerator.COUNTERS = {}  # сброс счётчиков

    factory = _DeviceFactory()
    x_off = INITIAL_OFFSET_PX
    y_off = INITIAL_OFFSET_PX

    room_defs = cast(list[dict], tpl["rooms"])
    for i, room_def in enumerate(room_defs, 1):
        rid = f"room_{i:02d}"
        w = min(room_def["area"] ** 0.5 * ROOM_SIZE_SCALE, ROOM_MAX_WIDTH_PX)
        h = room_def["area"] ** 0.5 * ROOM_SIZE_SCALE
        room = Room(
            id=rid,
            name=room_def["name"],
            area=room_def["area"],
            x=x_off,
            y=y_off,
            width=w,
            height=h,
            pc_count=room_def.get("pc", 0),
            camera_count=room_def.get("cameras", 0),
            has_skud=room_def.get("skud", False),
            has_ops=room_def.get("ops", False),
        )
        rooms.append(room)

        devices.extend(factory.build_room_devices(room_def, i, rid, x_off, y_off, w, h))

        x_off += w + ROOM_GAP_PX
        if x_off > X_WRAP_PX:
            x_off = INITIAL_OFFSET_PX
            y_off += max(h + ROOM_GAP_PX, ROW_MIN_HEIGHT_PX)

    if tpl.get("server_room"):
        devices.extend(factory.build_server_room_devices())

    return devices, rooms
