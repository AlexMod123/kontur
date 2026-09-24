"""КОНТУР-ПРО: модуль multiproject."""

from __future__ import annotations

from typing import Any

from kontur.models import Device, EngineeringResult, Room

# ============================================================================
# СЕКЦИЯ 13: MULTI-PROJECT MANAGER
# ============================================================================


class MultiProjectManager:
    """Менеджер для управления несколькими проектами и их сравнения."""

    def __init__(self) -> None:
        """Инициализация менеджера проектов."""
        self.projects: dict[str, dict[str, Any]] = {}

    def add_project(
        self, name: str, devices: list[Device], rooms: list[Room], result: EngineeringResult
    ) -> None:
        """Добавить проект в менеджер.

        Args:
            name: Имя проекта.
            devices: Список устройств в проекте.
            rooms: Список помещений в проекте.
            result: Результат инженерного расчёта.
        """
        self.projects[name] = {
            "devices": devices,
            "rooms": rooms,
            "result": result,
        }

    def compare(self) -> list[dict[str, Any]]:
        """Получить сравнение всех проектов.

        Returns:
            Список с данными каждого проекта для сравнения.
        """
        comparison = []
        for name, proj in self.projects.items():
            r = proj["result"]
            comparison.append(
                {
                    "name": name,
                    "devices": len(proj["devices"]),
                    "rooms": len(proj["rooms"]),
                    "power_kw": round(r.installed_power_w / 1000, 1),
                    "demand_kw": round(r.demand_power_w / 1000, 1),
                    "breaker": r.recommended_breaker,
                    "cable": r.recommended_cable,
                    "cost": r.cost_total,
                    "cooling_kw": round(r.cooling_required_w / 1000, 1),
                }
            )
        return comparison
