"""КОНТУР-ПРО: модуль specification."""

from __future__ import annotations

from typing import Any, ClassVar

from kontur.config import CATEGORIES
from kontur.models import Device, EngineeringResult

# ============================================================================
# СЕКЦИЯ 8: VENDOR DATABASE + SPECIFICATION BUILDER
# ============================================================================


class VendorDatabase:
    """База данных вендоров оборудования (регистр)."""

    VENDORS: ClassVar[dict[str, dict[str, Any]]] = {
        "siemens": {
            "name": "Siemens",
            "country": "Германия",
            "products": ["switch", "breaker", "ups", "shelf"],
        },
        "schneider": {
            "name": "Schneider Electric",
            "country": "Франция",
            "products": ["breaker", "ups", "shelf", "outlet"],
        },
        "abb": {"name": "ABB", "country": "Швейцария", "products": ["breaker", "ups", "shelf", "motor"]},
        "hikvision": {
            "name": "Hikvision",
            "country": "Китай",
            "products": ["camera_ip", "camera_ptz", "nvr"],
        },
        "cisco": {"name": "Cisco", "country": "США", "products": ["switch", "router", "patch_panel"]},
        "rubezh": {
            "name": "Рубеж",
            "country": "Россия",
            "products": ["ops_panel", "ops_smoke", "ops_heat", "ops_manual", "ops_siren"],
        },
    }

    @staticmethod
    def get_vendor(equip_type: str) -> str | None:
        """Получить вендора для типа оборудования.

        Args:
            equip_type: Тип оборудования.

        Returns:
            Имя вендора или None если не найдено.
        """
        for _vid, vdata in VendorDatabase.VENDORS.items():
            if equip_type in vdata["products"]:
                return vdata["name"]
        return None

    @staticmethod
    def list_all() -> dict[str, dict[str, Any]]:
        """Получить всех вендоров.

        Returns:
            Словарь всех вендоров.
        """
        return VendorDatabase.VENDORS


class SpecificationBuilder:
    """Построитель спецификации оборудования по ГОСТ 21.110."""

    @staticmethod
    def build(devices: list[Device], result: EngineeringResult | None = None) -> list[dict[str, Any]]:
        """Построить спецификацию оборудования.

        Args:
            devices: Список устройств для спецификации.
            result: Опциональный результат инженерного расчёта (не используется).

        Returns:
            Список строк спецификации с заголовками категорий и устройствами.
        """
        spec: list[dict[str, Any]] = []
        groups: dict[str, list[Device]] = {}
        for dev in devices:
            cat = dev.category
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(dev)

        pos = 1
        for cat_name, devs in sorted(groups.items()):
            cat_info = CATEGORIES.get(cat_name, {"name": cat_name})
            spec.append(
                {
                    "pos": pos,
                    "designation": "",
                    "name": f"== {cat_info.get('name', cat_name)} ==",
                    "type": "",
                    "vendor": "",
                    "unit": "",
                    "qty": "",
                    "note": "",
                }
            )
            pos += 1

            for dev in devs:
                vendor = VendorDatabase.get_vendor(dev.equip_type) or "—"
                unit = "шт."
                qty = 1
                note = ""
                if dev.equip_type == "cable_tray":
                    unit = "м"
                    qty = 0
                    note = "Трасса СКС"
                elif dev.equip_type in ("breaker",):
                    unit = "шт."
                    qty = 1

                spec.append(
                    {
                        "pos": pos,
                        "designation": dev.designation or dev.name,
                        "name": dev.name,
                        "type": dev.equip_type,
                        "vendor": vendor,
                        "unit": unit,
                        "qty": qty,
                        "note": note,
                    }
                )
                pos += 1

        return spec
