"""КОНТУР-ПРО: модуль twin — цифровой двойник здания.

Пакет собран из трёх ответственностей:
- ``model``    — графовая модель (TwinNode/TwinEdge/TwinGroup/DigitalTwin);
- ``builder``  — построение двойника из шаблона (TwinBuilder);
- ``importer`` — разбор Obsidian Canvas / Figma JSON (TwinImporter).

Все имена, которые раньше жили в ``kontur/twin.py``, реэкспортируются
здесь, чтобы существующие импорты (``from kontur.twin import ...``)
продолжали работать без изменений.
"""

from __future__ import annotations

from .builder import TwinBuilder
from .importer import TwinImporter
from .model import DigitalTwin, TwinEdge, TwinGroup, TwinModel, TwinNode

__all__ = [
    "DigitalTwin",
    "TwinBuilder",
    "TwinEdge",
    "TwinGroup",
    "TwinImporter",
    "TwinModel",
    "TwinNode",
]
