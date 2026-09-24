"""КОНТУР-ПРО: модуль persistence.dxf_import."""

from __future__ import annotations

import logging
import math
import os
from typing import Any

from kontur.config import PRICE_LIST
from kontur.models import Annotation, Device, Door, Wall

# ============================================================================
# СЕКЦИЯ 10: DXF IMPORTER
# ============================================================================

logger = logging.getLogger(__name__)

#: Длина линии (в единицах DXF), начиная с которой LINE считается стеной,
#: а не дверью.
WALL_MIN_LENGTH = 50

#: Значок по умолчанию для устройств, распознанных из блоков DXF.
DEFAULT_DEVICE_ICON = "📦"

#: Сопоставление подстроки в имени блока (INSERT) с параметрами устройства:
#: (equip_type, name, power_w, category).
BLOCK_NAME_TO_DEVICE: dict[str, tuple[str, str, float, str]] = {
    "SERVER": ("server", "Сервер 1U", 500, "it"),
    "RACK": ("rack42u", "Стойка 42U", 5000, "it"),
    "SWITCH": ("switch", "Коммутатор 48p PoE+", 750, "network"),
    "ROUTER": ("router", "Маршрутизатор", 200, "network"),
    "CAM": ("camera_ip", "IP-камера PoE", 25, "camera"),
    "PTZ": ("camera_ptz", "PTZ-камера PoE+", 60, "camera"),
    "NVR": ("nvr", "NVR видеосервер", 400, "camera"),
    "UPS": ("ups", "ИБП онлайн", 0, "power"),
    "AC": ("ac_unit", "Кондиционер", 2000, "hvac"),
    "BREAKER": ("breaker", "Автомат", 0, "power"),
    "SHELF": ("shelf", "Щит этажный", 0, "power"),
    "SMOKE": ("ops_smoke", "Датчик дымовой", 3, "ops"),
    "PANEL": ("ops_panel", "Прибор ОПС", 80, "ops"),
    "LOCK": ("skud_lock", "Замок электромагнитный", 15, "skud"),
}


class DXFImporter:
    """Импорт DXF из AutoCAD/nanoCAD через ezdxf"""

    @staticmethod
    def import_dxf(filepath: str | os.PathLike[str]) -> dict[str, Any]:
        try:
            import ezdxf
        except ImportError:
            return {"error": "ezdxf не установлен. Установите: pip install ezdxf"}

        try:
            doc = ezdxf.readfile(str(filepath))
        except ezdxf.DXFError as e:
            logger.warning("Некорректная структура DXF %s: %s", filepath, e)
            return {"error": f"Ошибка чтения DXF: {e}"}
        except OSError as e:
            logger.warning("Не удалось прочитать DXF %s: %s", filepath, e)
            return {"error": f"Ошибка чтения DXF: {e}"}

        msp = doc.modelspace()

        walls: list[Wall] = []
        doors: list[Door] = []
        annotations: list[Annotation] = []
        devices: list[Device] = []
        rooms: list[Any] = []

        for entity in msp:
            etype = entity.dxftype()

            if etype == "LINE":
                x1, y1 = entity.dxf.start.x, entity.dxf.start.y
                x2, y2 = entity.dxf.end.x, entity.dxf.end.y
                length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                if length > WALL_MIN_LENGTH:
                    walls.append(Wall(x1, y1, x2, y2))
                else:
                    # Короткие линии могут быть дверями
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    doors.append(Door(mx, my, width=length))

            elif etype == "ARC":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                doors.append(Door(cx, cy, width=r * 2))

            elif etype == "TEXT":
                annotations.append(Annotation(entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.text))

            elif etype == "INSERT":
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                block_name = entity.dxf.name.upper()
                dev = DXFImporter._map_block_to_device(block_name, x, y)
                if dev:
                    devices.append(dev)

        return {
            "walls": walls,
            "doors": doors,
            "annotations": annotations,
            "devices": devices,
            "rooms": rooms,
        }

    @staticmethod
    def _map_block_to_device(block_name: str, x: float, y: float) -> Device | None:
        name_upper = block_name.upper()
        for key, (equip_type, name, power, cat) in BLOCK_NAME_TO_DEVICE.items():
            if key in name_upper:
                dev_id = f"dxf_{equip_type}_{int(x)}_{int(y)}"
                return Device(
                    id=dev_id,
                    name=name,
                    power_w=power,
                    category=cat,
                    icon=DEFAULT_DEVICE_ICON,
                    x=x,
                    y=y,
                    equip_type=equip_type,
                    price=PRICE_LIST.get(equip_type, 0),
                )
        return None
