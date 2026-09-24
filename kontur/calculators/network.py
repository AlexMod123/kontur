"""КОНТУР-ПРО: расчёт ЛВС/СКС (ГОСТ Р 53246)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, TypedDict

from kontur.models import Device

if TYPE_CHECKING:
    from kontur.scale import ScaleManager

# --- Порты ---
RESERVE_PORTS = 4  # резервные порты коммутации
SERVER_PORTS_PER_DEVICE = 2  # число портов на сервер/стойку (резервирование)

# --- Кабель СКС ---
AVG_CABLE_LENGTH_M = 45  # средняя длина кабеля СКС (типовое значение)
PATCH_PANEL_PORTS = 24  # ёмкость патч-панели, портов

# --- PoE ---
POE_PLUS_WATTS_PER_PORT = 30  # бюджет PoE+ на порт, Вт (IEEE 802.3at)
SWITCH_POE_BUDGET_W = 740  # бюджет типового 48-портового PoE+ коммутатора, Вт


class LANResult(TypedDict):
    total_ports: int
    user_ports: int
    camera_ports: int
    phone_ports: int
    server_ports: int
    patch_panels: int
    cable_m: float
    poe_ports: int
    poe_required_w: int
    poe_budget_w: int


class LANCalculator:
    """Расчёт ЛВС/СКС (ГОСТ Р 53246)"""

    @staticmethod
    def calc(devices: list[Device], scale_manager: ScaleManager | None = None) -> LANResult:
        cameras = [d for d in devices if d.category == "camera"]

        # Порты
        user_ports = sum(1 for d in devices if d.category == "it")
        camera_ports = len(cameras)
        phone_ports = sum(1 for d in devices if d.category == "phone")
        ap_ports = sum(1 for d in devices if d.equip_type == "wifi")
        total_ports = user_ports + camera_ports + phone_ports + ap_ports + RESERVE_PORTS

        # Серверные порты
        server_ports = sum(SERVER_PORTS_PER_DEVICE for d in devices if d.equip_type in ("server", "rack42u"))
        total_ports += server_ports

        # Длина кабеля (упрощённо: средняя длина × количество)
        total_cable = total_ports * AVG_CABLE_LENGTH_M

        # Количество патч-панелей 24p
        patch_panels = math.ceil(total_ports / PATCH_PANEL_PORTS)

        # PoE-бюджет
        poe_ports = camera_ports + ap_ports
        poe_required = poe_ports * POE_PLUS_WATTS_PER_PORT
        poe_budget = SWITCH_POE_BUDGET_W if poe_ports > 0 else 0

        return {
            "total_ports": total_ports,
            "user_ports": user_ports,
            "camera_ports": camera_ports,
            "phone_ports": phone_ports,
            "server_ports": server_ports,
            "patch_panels": patch_panels,
            "cable_m": round(total_cable, 1),
            "poe_ports": poe_ports,
            "poe_required_w": poe_required,
            "poe_budget_w": poe_budget,
        }
