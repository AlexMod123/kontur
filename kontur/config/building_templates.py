"""КОНТУР-ПРО: шаблоны зданий и классификация Tier."""

from __future__ import annotations

from typing import Any, Final

# --- Шаблоны зданий ---
TEMPLATES: Final[dict[str, dict[str, Any]]] = {
    "Офис": {
        "rooms": [
            {"name": "Офис администрации", "area": 48, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Опенспейс", "area": 220, "pc": 4, "cameras": 2, "skud": True, "ops": True},
            {"name": "Бухгалтерия", "area": 54, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Пост охраны", "area": 48, "pc": 3, "cameras": 4, "skud": False, "ops": True},
            {"name": "Архив", "area": 45, "pc": 0, "cameras": 2, "skud": True, "ops": True},
            {"name": "Кофепоинт", "area": 30, "pc": 0, "cameras": 1, "skud": False, "ops": True},
        ],
        "server_room": True,
        "floor_area": 445,
    },
    "Склад": {
        "rooms": [
            {"name": "Зона хранения А", "area": 500, "pc": 1, "cameras": 4, "skud": True, "ops": True},
            {"name": "Зона хранения Б", "area": 500, "pc": 1, "cameras": 4, "skud": True, "ops": True},
            {"name": "Зона разгрузки", "area": 200, "pc": 2, "cameras": 3, "skud": True, "ops": True},
            {"name": "Контора", "area": 60, "pc": 4, "cameras": 2, "skud": True, "ops": True},
            {"name": "Кабинет нач. склада", "area": 25, "pc": 1, "cameras": 1, "skud": True, "ops": True},
        ],
        "server_room": True,
        "floor_area": 1285,
    },
    "ЦОД": {
        "rooms": [
            {"name": "Машинный зал 1", "area": 200, "pc": 0, "cameras": 4, "skud": True, "ops": True},
            {"name": "Машинный зал 2", "area": 200, "pc": 0, "cameras": 4, "skud": True, "ops": True},
            {"name": "КОды (входная зона)", "area": 50, "pc": 2, "cameras": 3, "skud": True, "ops": True},
            {"name": "Электрощитовая", "area": 40, "pc": 0, "cameras": 2, "skud": True, "ops": True},
            {
                "name": "Аварийный дизельгенератор",
                "area": 80,
                "pc": 0,
                "cameras": 2,
                "skud": False,
                "ops": True,
            },
        ],
        "server_room": True,
        "floor_area": 570,
    },
    "Школа": {
        "rooms": [
            {"name": "Директорская", "area": 30, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Учительская", "area": 40, "pc": 6, "cameras": 1, "skud": True, "ops": True},
            {"name": "Кабинет информатики 1", "area": 60, "pc": 15, "cameras": 2, "skud": False, "ops": True},
            {"name": "Кабинет информатики 2", "area": 60, "pc": 15, "cameras": 2, "skud": False, "ops": True},
            {"name": "Актовый зал", "area": 200, "pc": 1, "cameras": 4, "skud": False, "ops": True},
            {"name": "Столовая", "area": 150, "pc": 2, "cameras": 3, "skud": False, "ops": True},
            {"name": "Гардероб", "area": 80, "pc": 0, "cameras": 2, "skud": True, "ops": True},
        ],
        "server_room": True,
        "floor_area": 620,
    },
}

# --- Tier-уровни ---
# ups_scheme: топология резервирования ИБП ("N" / "N+1" / "2N"), определяет
# число установленных модулей ИБП и число независимых батарейных линий.
# ups_autonomy_target_min: целевая автономия ИБП при полной нагрузке (мин) —
# проектное допущение (не норма), используется для подбора числа АКБ.
# ups_redundancy/cooling_redundancy сохранены ради обратной совместимости
# (используются/могут использоваться внешним кодом, не участвуют в подборе
# ИБП по схеме N/N+1/2N — см. kontur.core.EngineeringCore._step_ups).
TIER_CONFIG: Final[dict[int, dict[str, Any]]] = {
    1: {
        "name": "Tier I",
        "ups_redundancy": 1,
        "cooling_redundancy": 1,
        "ups_scheme": "N",
        "ups_autonomy_target_min": 10,
        "desc": "Базовый, без резервирования",
    },
    2: {
        "name": "Tier II",
        "ups_redundancy": 2,
        "cooling_redundancy": 2,
        "ups_scheme": "N+1",
        "ups_autonomy_target_min": 15,
        "desc": "N+1 резервирование",
    },
    3: {
        "name": "Tier III",
        "ups_redundancy": 2,
        "cooling_redundancy": 2,
        "ups_scheme": "2N",
        "ups_autonomy_target_min": 15,
        "desc": "Конкурентное обслуживание, 2N",
    },
}
