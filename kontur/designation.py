"""КОНТУР-ПРО: модуль designation."""

from __future__ import annotations

from typing import Any, ClassVar

from kontur.models import Device

# ============================================================================
# СЕКЦИЯ 7: UGO PAINTER + DESIGNATION GENERATOR
# ============================================================================


class UGOPainter:
    """Условные графические обозначения по ГОСТ 21.614."""

    UGO_SHAPES: ClassVar[dict[str, str]] = {
        "breaker": "rect_rounded",
        "shelf": "rect",
        "outlet": "circle_rect",
        "server": "rect_servers",
        "rack42u": "rect_rack",
        "switch": "rect_ports",
        "router": "router_shape",
        "wifi": "antenna",
        "camera_ip": "camera_shape",
        "camera_ptz": "camera_ptz",
        "nvr": "rect_monitor",
        "skud_ctrl": "key_shape",
        "skud_lock": "lock_shape",
        "ops_panel": "panel_shape",
        "ops_smoke": "circle_dot",
        "ac_unit": "ac_shape",
        "ups": "battery_shape",
        "lighting_panel": "lamp_shape",
        "patch_panel": "rect_ports",
        "ip_phone": "phone_shape",
    }

    @staticmethod
    def get_ugo(equip_type: str) -> str:
        """Получить вид УГО по типу оборудования.

        Args:
            equip_type: Тип оборудования.

        Returns:
            Вид УГО или "rect" по умолчанию.
        """
        return UGOPainter.UGO_SHAPES.get(equip_type, "rect")

    @staticmethod
    def draw_shape(
        canvas: Any, x: int, y: int, equip_type: str, size: int = 30, color: str = "#06d6a0"
    ) -> None:
        """Отрисовка УГО на canvas (Tkinter или PyQt).

        Args:
            canvas: Объект canvas (Tkinter или PyQt).
            x: Координата X.
            y: Координата Y.
            equip_type: Тип оборудования.
            size: Размер УГО в пикселях.
            color: Цвет УГО.
        """
        shape = UGOPainter.get_ugo(equip_type)
        if hasattr(canvas, "create_oval"):
            if shape == "rect_rounded" or shape == "rect":
                canvas.create_rectangle(x, y, x + size, y + size, outline=color, width=2)
            elif shape == "circle_dot":
                r = size // 2
                canvas.create_oval(x, y, x + size, y + size, outline=color, width=2)
                canvas.create_oval(x + r - 3, y + r - 3, x + r + 3, y + r + 3, fill=color)
            elif shape == "antenna":
                canvas.create_oval(x, y, x + size, y + size, outline=color, width=2)
                canvas.create_line(x + size // 2, y, x + size // 2, y - 10, fill=color, width=2)
            else:
                canvas.create_rectangle(x, y, x + size, y + size, outline=color, width=2)


class DesignationGenerator:
    """Генератор позиционных обозначений по ГОСТ 2.710-81.

    COUNTERS — глобальный счётчик обозначений (можно сбрасывать извне).
    """

    # Счётчик обозначений по типам: регистр, может быть сброшен извне.
    COUNTERS: ClassVar[dict[str, int]] = {}

    @classmethod
    def reset(cls) -> None:
        """Сбросить счётчики обозначений.

        Для использования вместо прямого обнуления COUNTERS.
        """
        cls.COUNTERS.clear()

    @staticmethod
    def generate(device: Device) -> str:
        """Сгенерировать позиционное обозначение для устройства.

        Args:
            device: Устройство для обозначения.

        Returns:
            Позиционное обозначение (например, "QF1", "A2").
        """
        cat = device.category
        prefix_map = {
            "power": "Q",
            "it": "A",
            "network": "A",
            "camera": "A",
            "skud": "A",
            "ops": "A",
            "hvac": "A",
            "lighting": "E",
            "lan": "A",
            "phone": "A",
            "custom": "A",
        }
        prefix = prefix_map.get(cat, "A")

        # Специальные обозначения по типам оборудования
        type_map = {
            "breaker": "QF",
            "shelf": "S",
            "outlet": "XS",
            "server": "A",
            "rack42u": "A",
            "switch": "A",
            "ups": "G",
            "ac_unit": "E",
            "precise_ac": "E",
            "lighting_panel": "E",
            "skud_lock": "YA",
            "ops_panel": "A",
            "ops_smoke": "B",
            "ops_heat": "B",
            "ops_manual": "SB",
            "ops_siren": "HA",
            "camera_ip": "A",
            "camera_ptz": "A",
            "nvr": "A",
            "skud_ctrl": "A",
            "skud_reader": "A",
            "skud_turnstile": "A",
            "patch_panel": "A",
            "ip_phone": "A",
            "intercom": "A",
            "cable_tray": "A",
        }
        symbol = type_map.get(device.equip_type, prefix)

        key = symbol
        DesignationGenerator.COUNTERS[key] = DesignationGenerator.COUNTERS.get(key, 0) + 1
        return f"{symbol}{DesignationGenerator.COUNTERS[key]}"
