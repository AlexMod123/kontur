"""КОНТУР-ПРО: базовые типы стратегии экспорта.

Определяет ``ExportContext`` (данные проекта, передаваемые в форматтер) и
``ExportFormat`` — абстрактный базовый класс для одной стратегии экспорта
(JSON/HTML/TXT/Excel/PDF/DXF).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

    from kontur.models import Device, EngineeringResult, Room
    from kontur.scale import ScaleManager
    from kontur.twin import TwinModel

#: формат отображаемой даты/времени (для JSON/HTML/TXT)
DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
#: формат даты/времени для имени файла
FILE_TIME_FORMAT = "%Y%m%d_%H%M%S"


@dataclass(slots=True)
class ExportContext:
    """Данные проекта, необходимые любому из форматов экспорта.

    Единая метка времени (``timestamp``) хранится один раз, чтобы все
    форматы, сгенерированные в рамках одного вызова (см. ``export_all``),
    получили одинаковые дату/время и имя файла.
    """

    devices: list[Device]
    rooms: list[Room]
    result: EngineeringResult
    checks: list[dict] | None = None
    spec: list[dict] | None = None
    cable_journal: list[dict] | None = None
    scale_mgr: ScaleManager | None = None
    twin: TwinModel | None = None
    timestamp: time.struct_time = field(default_factory=time.localtime)

    @property
    def display_timestamp(self) -> str:
        """Дата/время для отображения в отчётах."""
        return time.strftime(DISPLAY_TIME_FORMAT, self.timestamp)

    @property
    def file_timestamp(self) -> str:
        """Дата/время для имени файла."""
        return time.strftime(FILE_TIME_FORMAT, self.timestamp)


class ExportFormat(ABC):
    """Абстрактная стратегия экспорта в конкретный формат."""

    #: короткое имя формата, используется как ключ реестра (например "json")
    name: ClassVar[str]
    #: расширение файла без точки (например "json")
    extension: ClassVar[str]

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Проверяет, установлена ли опциональная зависимость формата."""

    @staticmethod
    @abstractmethod
    def render(ctx: ExportContext) -> bytes | str:
        """Строит содержимое экспорта. Текстовые форматы возвращают ``str``,
        бинарные (Excel/PDF) — ``bytes``."""

    @classmethod
    def default_filename(cls, ctx: ExportContext) -> str:
        """Имя файла по умолчанию для данного формата и контекста."""
        return f"kontur_export_{ctx.file_timestamp}.{cls.extension}"

    @classmethod
    def write(cls, ctx: ExportContext, path: Path) -> Path:
        """Рендерит и сохраняет результат по указанному пути."""
        content = cls.render(ctx)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path
