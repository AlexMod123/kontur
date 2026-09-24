"""КОНТУР-ПРО: реестр форматов экспорта."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kontur.export.base import ExportFormat

_REGISTRY: dict[str, type[ExportFormat]] = {}


def register(fmt: type[ExportFormat]) -> type[ExportFormat]:
    """Регистрирует класс формата экспорта под его ``name``. Используется как декоратор."""
    _REGISTRY[fmt.name] = fmt
    return fmt


def get_exporter(name: str) -> type[ExportFormat] | None:
    """Возвращает класс формата экспорта по имени, либо ``None``, если не найден."""
    return _REGISTRY.get(name)


def all_formats() -> list[type[ExportFormat]]:
    """Все зарегистрированные форматы, независимо от доступности библиотек."""
    return list(_REGISTRY.values())


def available_formats() -> list[type[ExportFormat]]:
    """Зарегистрированные форматы, чьи опциональные зависимости установлены."""
    return [fmt for fmt in _REGISTRY.values() if fmt.is_available()]
