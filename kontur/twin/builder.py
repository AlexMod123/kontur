"""КОНТУР-ПРО: построение цифрового двойника из шаблона здания."""

from __future__ import annotations

from typing import Any, cast

from kontur.config import TEMPLATES

from .model import DigitalTwin, TwinEdge, TwinGroup, TwinNode

# ============================================================================
# СЕКЦИЯ 6: ЦИФРОВОЙ ДВОЙНИК — ГЕНЕРАТОР ИЗ ШАБЛОНА
# ============================================================================

# --- Цветовые коды Twin-канвы (Obsidian Canvas) ---
COLOR_POWER = "1"
COLOR_SKUD = "2"
COLOR_PC = "3"
COLOR_NETWORK = "4"
COLOR_ROOM = "5"
COLOR_OPS = "6"

# --- Раскладка серверной (фиксированные координаты опорного узла) ---
_CORE_NODES: tuple[tuple[str, str, str, int, int, int, int], ...] = (
    ("SRV", "# 🎛️ ЦЕНТРАЛЬНАЯ СЕРВЕРНАЯ\nГлавный узел связи", COLOR_POWER, 1800, -900, 600, 130),
    (
        "CORE_RACK",
        "## 🔲 СЕРВЕРНАЯ СТОЙКА 42U\n**ИТ:** 17.35 кВт\n**Тепло:** 14.85 кВт",
        COLOR_POWER,
        1800,
        -1080,
        600,
        140,
    ),
    ("CORE_SWITCH", "### 🔌 SWITCH STACK\n48-port PoE+\nПортов: 45/48", COLOR_NETWORK, 1800, -1260, 420, 100),
    ("CORE_NVR", "### 📹 NVR ВИДЕОСЕРВЕР\nАрхив 64 ТБ RAID-6", COLOR_NETWORK, 1480, -1100, 280, 110),
    ("CORE_SKUD_SRV", "### 🔑 СЕРВЕР СКУД\nБаза: MS SQL", COLOR_SKUD, 2120, -1100, 280, 110),
    (
        "CORE_GRSH",
        "# ⚡ ЩИТ ЩРО\n**Автомат:** С83\n**Кабель:** ВВГнг-FRLS 5x25",
        COLOR_POWER,
        1800,
        -1440,
        420,
        110,
    ),
    (
        "CORE_OPS_PANEL",
        "### 🔥 ПАНЕЛЬ ОПС «Сигнал-20»\nПрибор приёмно-контрольный",
        COLOR_OPS,
        1480,
        -1280,
        280,
        110,
    ),
)

# --- Раскладка блока помещений (шаг сетки при обходе комнат шаблона) ---
ROOM_X_START = 600
ROOM_X_STEP = 1200
ROOM_X_WRAP_AT = 2400
ROOM_Y_WRAP_TO = 1800

ROOM_NODE_W, ROOM_NODE_H = 300, 110
PWR_NODE_W, PWR_NODE_H = 280, 90
PC_NODE_W, PC_NODE_H = 280, 65
CAM_NODE_W, CAM_NODE_H = 280, 80
SKUD_NODE_W, SKUD_NODE_H = 280, 110
OPS_NODE_W, OPS_NODE_H = 280, 120

PC_COLUMN_DX = 660
CAM_COLUMN_DX = 980
PWR_COLUMN_DX = 340

PC_ROW_PITCH = 75
CAM_ROW_PITCH = 90
CAM_ROW_START_DY = -40

GROUP_MARGIN = 30
GROUP_W, GROUP_H = 1400, 260

DEFAULT_SMOKE_DETECTORS = 2


class TwinBuilder:
    """Генератор цифрового двойника из шаблона."""

    @staticmethod
    def build(template_name: str, tier: int = 1) -> DigitalTwin:
        """Построить DigitalTwin по имени шаблона здания (см. kontur.config.TEMPLATES)."""
        tpl = TEMPLATES.get(template_name, TEMPLATES["Офис"])
        twin = DigitalTwin()

        for nid, text, color, x, y, w, h in _CORE_NODES:
            twin.add_node(TwinNode(nid, text, color, x, y, w, h))

        rooms = cast("list[dict[str, Any]]", tpl.get("rooms", []))
        x_offset = ROOM_X_START
        y_offset = 0
        for i, room in enumerate(rooms, 1):
            rid = f"ROOM_{i:02d}"
            text = f"### 🏢 {room['name'].upper()}\n**Площадь:** ~{room['area']} м²"
            twin.add_node(TwinNode(rid, text, COLOR_ROOM, x_offset, y_offset, ROOM_NODE_W, ROOM_NODE_H))

            pwr_id = f"{rid}_pwr"
            twin.add_node(
                TwinNode(
                    pwr_id,
                    f"⚡ **АВТОМАТ С16 (№{i:02d})**\n*Кабель:* ВВГнг-LS 3x2.5",
                    COLOR_POWER,
                    x_offset + PWR_COLUMN_DX,
                    y_offset,
                    PWR_NODE_W,
                    PWR_NODE_H,
                )
            )
            twin.add_edge(TwinEdge(f"e_pwr_{rid}", rid, pwr_id, "right", "left"))
            twin.add_edge(TwinEdge(f"e_grsh_{rid}", "CORE_GRSH", rid, "bottom", "top"))

            for j in range(1, room.get("pc", 0) + 1):
                pc_id = f"{rid}_pc_{j}"
                twin.add_node(
                    TwinNode(
                        pc_id,
                        f"💻 РМ {j}\n*Хост:* PC-{i:02d}{j:02d}\n*Линия:* UTP Cat.5e",
                        COLOR_PC,
                        x_offset + PC_COLUMN_DX,
                        y_offset - PC_ROW_PITCH + (j - 1) * PC_ROW_PITCH,
                        PC_NODE_W,
                        PC_NODE_H,
                    )
                )
                twin.add_edge(TwinEdge(f"e_{rid}_pc_{j}", rid, pc_id, "right", "left"))

            for j in range(1, room.get("cameras", 0) + 1):
                cam_id = f"{rid}_cam_{j}"
                twin.add_node(
                    TwinNode(
                        cam_id,
                        f"🎥 IP-КАМЕРА №{j}\n*Поток:* H.265+ / 2 Мп\n*Питание:* PoE",
                        COLOR_NETWORK,
                        x_offset + CAM_COLUMN_DX,
                        y_offset + CAM_ROW_START_DY + (j - 1) * CAM_ROW_PITCH,
                        CAM_NODE_W,
                        CAM_NODE_H,
                    )
                )
                twin.add_edge(TwinEdge(f"e_nvr_{rid}_{j}", "CORE_NVR", cam_id, "bottom", "top"))

            if room.get("skud"):
                skud_id = f"{rid}_skud"
                twin.add_node(
                    TwinNode(
                        skud_id,
                        "🔑 **МОДУЛЬ СКУД**\n*Контроллер:* IP-Class\n*Замок:* Электромагнит 300кг",
                        COLOR_SKUD,
                        x_offset + PC_COLUMN_DX,
                        y_offset,
                        SKUD_NODE_W,
                        SKUD_NODE_H,
                    )
                )
                twin.add_edge(TwinEdge(f"e_skud_{rid}", "CORE_SKUD_SRV", skud_id, "bottom", "top"))

            if room.get("ops"):
                ops_id = f"{rid}_ops"
                smoke = room.get("smoke", DEFAULT_SMOKE_DETECTORS)
                twin.add_node(
                    TwinNode(
                        ops_id,
                        f"🔥 **БЛОК ОПС**\n*Дымовые ДПИ х{smoke} шт.*\n*Шлейф:* ШС №{i:02d}",
                        COLOR_OPS,
                        x_offset + CAM_COLUMN_DX,
                        y_offset,
                        OPS_NODE_W,
                        OPS_NODE_H,
                    )
                )
                twin.add_edge(TwinEdge(f"e_ops_box_{rid}", rid, ops_id, "right", "left"))

            twin.add_group(
                TwinGroup(
                    f"g_{rid}",
                    f"🏢 {room['name'].upper()}",
                    x_offset - GROUP_MARGIN,
                    y_offset - GROUP_MARGIN,
                    GROUP_W,
                    GROUP_H,
                )
            )
            twin.add_edge(TwinEdge(f"e_sw_{rid}", "CORE_SWITCH", rid, "bottom", "top"))
            twin.add_edge(TwinEdge(f"e_ops_{rid}", "CORE_OPS_PANEL", rid, "bottom", "top"))

            x_offset += ROOM_X_STEP
            if x_offset > ROOM_X_WRAP_AT:
                x_offset = ROOM_X_START
                y_offset = ROOM_Y_WRAP_TO

        return twin
