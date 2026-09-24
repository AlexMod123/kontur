"""КОНТУР-ПРО: экспорт в JSON/HTML/TXT/Excel/PDF/DXF.

Пакет реализует паттерн «Стратегия»: каждый формат — отдельный класс
``ExportFormat`` в своём модуле, зарегистрированный в ``registry``.
Класс ``Exporter`` — фасад с оригинальными статическими методами
(``to_json``, ``to_html``, ...), сохранённый для обратной совместимости
с ``kontur.cli`` и ``kontur.gui``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

# импорт форматов регистрирует их в registry как побочный эффект
from kontur.export import (  # noqa: F401  (нужны только ради регистрации)
    dxf_export,
    excel_export,
    html_export,
    json_export,
    pdf_export,
    txt_export,
)
from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import all_formats, available_formats, get_exporter

if TYPE_CHECKING:
    from kontur.models import Device, EngineeringResult, Room
    from kontur.scale import ScaleManager
    from kontur.twin import TwinModel

__all__ = [
    "ExportContext",
    "ExportFormat",
    "Exporter",
    "all_formats",
    "available_formats",
    "export_all",
    "get_exporter",
]

logger = logging.getLogger(__name__)


def export_all(ctx: ExportContext, out_dir: str | Path) -> dict[str, Path | None]:
    """Экспортирует проект во все доступные форматы в ``out_dir``.

    Все форматы получают один и тот же ``ctx.timestamp``, поэтому имена
    файлов согласованы между собой (единая метка времени экспорта).
    Возвращает словарь {имя_формата: путь | None (если формат недоступен)}.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results: dict[str, Path | None] = {}
    for fmt in all_formats():
        if not fmt.is_available():
            logger.warning("Формат %s недоступен: отсутствует опциональная зависимость", fmt.name)
            results[fmt.name] = None
            continue
        target = out_path / fmt.default_filename(ctx)
        fmt.write(ctx, target)
        results[fmt.name] = target
    return results


class Exporter:
    """Фасад над стратегиями экспорта (обратная совместимость со старым API)."""

    @staticmethod
    def to_json(
        devices: list[Device],
        rooms: list[Room],
        result: EngineeringResult,
        twin: TwinModel | None = None,
    ) -> str:
        """Экспорт полного слепка проекта в JSON."""
        ctx = ExportContext(devices=devices, rooms=rooms, result=result, twin=twin)
        fmt = get_exporter("json")
        assert fmt is not None
        return fmt.render(ctx)  # type: ignore[return-value]

    @staticmethod
    def to_html(
        devices: list[Device],
        rooms: list[Room],
        result: EngineeringResult,
        checker_results: list[dict] | None = None,
    ) -> str:
        """Экспорт отчёта в HTML."""
        ctx = ExportContext(devices=devices, rooms=rooms, result=result, checks=checker_results)
        fmt = get_exporter("html")
        assert fmt is not None
        return fmt.render(ctx)  # type: ignore[return-value]

    @staticmethod
    def to_txt(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> str:
        """Экспорт отчёта в текстовый файл."""
        ctx = ExportContext(devices=devices, rooms=rooms, result=result)
        fmt = get_exporter("txt")
        assert fmt is not None
        return fmt.render(ctx)  # type: ignore[return-value]

    @staticmethod
    def to_excel(
        devices: list[Device],
        rooms: list[Room],
        result: EngineeringResult,
        checker_results: list[dict] | None = None,
        spec: list[dict] | None = None,
        cable_journal: list[dict] | None = None,
    ) -> str | None:
        """Экспорт отчёта в книгу Excel. ``None``, если openpyxl не установлен."""
        fmt = get_exporter("excel")
        assert fmt is not None
        if not fmt.is_available():
            return None
        ctx = ExportContext(
            devices=devices,
            rooms=rooms,
            result=result,
            checks=checker_results,
            spec=spec,
            cable_journal=cable_journal,
        )
        path = Path(fmt.default_filename(ctx))
        fmt.write(ctx, path)
        return str(path)

    @staticmethod
    def to_pdf(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> str | None:
        """Экспорт отчёта в PDF. ``None``, если reportlab не установлен."""
        fmt = get_exporter("pdf")
        assert fmt is not None
        if not fmt.is_available():
            return None
        ctx = ExportContext(devices=devices, rooms=rooms, result=result)
        path = Path(fmt.default_filename(ctx))
        fmt.write(ctx, path)
        return str(path)

    @staticmethod
    def to_dxf(
        devices: list[Device],
        rooms: list[Room],
        result: EngineeringResult,
        scale_manager: ScaleManager | None = None,
    ) -> str | None:
        """Экспорт плана в DXF. ``None``, если ezdxf не установлен."""
        fmt = get_exporter("dxf")
        assert fmt is not None
        if not fmt.is_available():
            return None
        ctx = ExportContext(devices=devices, rooms=rooms, result=result, scale_mgr=scale_manager)
        path = Path(fmt.default_filename(ctx))
        fmt.write(ctx, path)
        return str(path)
