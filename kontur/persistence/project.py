"""КОНТУР-ПРО: модуль persistence.project."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import shutil
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar

from kontur.config import SCHEMA_VERSION, VERSION
from kontur.models import Annotation, Device, Door, Room, Wall
from kontur.persistence._atomic import atomic_write_json

# ============================================================================
# СЕКЦИЯ 9: PROJECT MANAGER (.kontur JSON)
# ============================================================================

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

#: Значение схемы, используемое, когда файл не содержит "schema_version" вовсе.
_DEFAULT_SCHEMA_VERSION = "1.0"


def _version_tuple(version: str) -> tuple[int, ...]:
    """Преобразует строку версии ('1.0') в кортеж для сравнения."""
    parts = []
    for chunk in version.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _migrate_devices_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Миграция 1.0 -> 2.0: добавляет z/price/designation к устройствам."""
    for d in data.get("devices", []):
        d.setdefault("z", 1.0)
        d.setdefault("price", 0)
        d.setdefault("designation", "")
    return data


def _migrate_rooms_v5(data: dict[str, Any]) -> dict[str, Any]:
    """Миграция 2.0 -> 5.0: добавляет высоту потолка к помещениям."""
    for r in data.get("rooms", []):
        r.setdefault("height_m", 3.0)
    return data


#: Явная упорядоченная цепочка миграций схемы (Chain of Responsibility),
#: зарегистрированная как (целевая_версия, функция_миграции). Миграции
#: применяются по порядку, начиная с той, чья целевая версия выше текущей
#: версии данных.
SCHEMA_MIGRATIONS: tuple[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]], ...] = (
    ("2.0", _migrate_devices_v2),
    ("5.0", _migrate_rooms_v5),
)


def _construct(
    cls: type[_T],
    required: Sequence[str],
    default_overrides: Mapping[str, Any],
    data: Mapping[str, Any],
) -> _T:
    """Строит dataclass ``cls`` из словаря ``data``.

    * ``required`` — поля, обязательные к наличию в ``data`` (как и раньше,
      их отсутствие приводит к KeyError).
    * ``default_overrides`` — значения по умолчанию для полей, у которых нет
      default в самом dataclass (например power_w, category, area).
    * Прочие известные поля берутся из dataclass-default, если в ``data`` их
      нет; неизвестные ключи ``data`` игнорируются (прямая совместимость).
    """
    kwargs: dict[str, Any] = {name: data[name] for name in required}
    for f in dataclasses.fields(cls):  # type: ignore[arg-type]
        if f.name in required:
            continue
        if f.name in data:
            kwargs[f.name] = data[f.name]
        elif f.name in default_overrides:
            kwargs[f.name] = default_overrides[f.name]
        elif f.default is not dataclasses.MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            kwargs[f.name] = f.default_factory()
        else:
            raise KeyError(f.name)
    return cls(**kwargs)  # type: ignore[call-arg]


def _device_from_dict(d: Mapping[str, Any]) -> Device:
    return _construct(Device, ("id", "name"), {"power_w": 0, "category": "custom"}, d)


def _room_from_dict(r: Mapping[str, Any]) -> Room:
    return _construct(Room, ("id", "name"), {"area": 0}, r)


def _wall_from_dict(w: Mapping[str, Any]) -> Wall:
    return _construct(Wall, ("x1", "y1", "x2", "y2"), {}, w)


def _door_from_dict(d: Mapping[str, Any]) -> Door:
    return _construct(Door, ("x", "y"), {}, d)


def _annotation_from_dict(a: Mapping[str, Any]) -> Annotation:
    return _construct(Annotation, ("x", "y"), {}, a)


def _to_dict(obj: Any) -> dict[str, Any]:
    """Централизованная сериализация dataclass'ов Device/Room/Wall/Door/Annotation."""
    return dataclasses.asdict(obj)


class ProjectManager:
    """Сохранение/загрузка проектов в .kontur (JSON)"""

    def __init__(self) -> None:
        self.current_project: Path | None = None
        self.autosave_interval = 300  # секунд
        self.backup_dir = ".backups"

    def save(
        self,
        filepath: str | os.PathLike[str],
        devices: list[Device],
        rooms: list[Room],
        walls: list[Wall] | None = None,
        doors: list[Door] | None = None,
        annotations: list[Annotation] | None = None,
        tier: int = 1,
        scale: float = 1.0,
    ) -> dict[str, Any]:
        path = Path(filepath)
        data = {
            "schema_version": SCHEMA_VERSION,
            "app": "КОНТУР-ПРО",
            "version": VERSION,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tier": tier,
            "scale": scale,
            "devices": [_to_dict(d) for d in devices],
            "rooms": [_to_dict(r) for r in rooms],
            "walls": [_to_dict(w) for w in (walls or [])],
            "doors": [_to_dict(d) for d in (doors or [])],
            "annotations": [_to_dict(a) for a in (annotations or [])],
        }

        path.parent.mkdir(parents=True, exist_ok=True)

        # Резервная копия
        if path.exists():
            self._backup(path)

        atomic_write_json(path, data, ensure_ascii=False, indent=2)

        self.current_project = path
        return {"ok": True, "path": str(path), "devices": len(devices), "rooms": len(rooms)}

    def _backup(self, path: Path) -> None:
        backup_dir = path.parent / self.backup_dir
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_name = path.name.replace(".kontur", f"_backup_{time.strftime('%Y%m%d_%H%M%S')}.kontur")
            shutil.copy2(path, backup_dir / backup_name)
        except OSError:
            logger.warning("Не удалось создать резервную копию %s", path, exc_info=True)

    def load(self, filepath: str | os.PathLike[str]) -> dict[str, Any]:
        path = Path(filepath)
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Миграция схемы
        data = self._migrate(data)

        devices = [_device_from_dict(d) for d in data.get("devices", [])]
        rooms = [_room_from_dict(r) for r in data.get("rooms", [])]
        walls = [_wall_from_dict(w) for w in data.get("walls", [])]
        doors = [_door_from_dict(d) for d in data.get("doors", [])]
        annotations = [_annotation_from_dict(a) for a in data.get("annotations", [])]

        self.current_project = path
        return {
            "devices": devices,
            "rooms": rooms,
            "walls": walls,
            "doors": doors,
            "annotations": annotations,
            "tier": data.get("tier", 1),
            "scale": data.get("scale", 1.0),
            "schema_version": data.get("schema_version", _DEFAULT_SCHEMA_VERSION),
        }

    def _migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Применяет явную упорядоченную цепочку миграций (см. SCHEMA_MIGRATIONS)."""
        version = data.get("schema_version", _DEFAULT_SCHEMA_VERSION)
        current = _version_tuple(version)
        for target_version, step in SCHEMA_MIGRATIONS:
            if current < _version_tuple(target_version):
                data = step(data)
        data["schema_version"] = SCHEMA_VERSION
        return data
