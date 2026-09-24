"""КОНТУР-ПРО: модуль cli.

Точка входа командной строки: разбор аргументов (`build_parser`), выбор
источника проекта (шаблон / файл проекта / DXF), расчёт, вывод отчёта,
сохранение и экспорт. `main` возвращает код завершения процесса.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from kontur.calculators import CableJournal
from kontur.checker import ModelChecker
from kontur.config import VERSION
from kontur.core import EngineeringCore
from kontur.export import ExportContext, export_all
from kontur.persistence.dxf_import import DXFImporter
from kontur.persistence.project import ProjectManager
from kontur.report import render_report
from kontur.scale import ScaleManager
from kontur.specification import SpecificationBuilder
from kontur.templates import generate_template

if TYPE_CHECKING:
    from kontur.models import Device, Room

logger = logging.getLogger(__name__)

#: пакет, требуемый каждым необязательным форматом экспорта (для сообщения об отсутствии)
_EXPORT_REQUIRES = {"excel": "openpyxl", "pdf": "reportlab", "dxf": "ezdxf"}
#: порядок и подписи форматов в итоговой строке экспорта
_EXPORT_LABELS = [
    ("json", "JSON"),
    ("html", "HTML"),
    ("txt", "TXT"),
    ("excel", "Excel"),
    ("pdf", "PDF"),
    ("dxf", "DXF"),
]


class CliInputError(RuntimeError):
    """Ошибка входных данных CLI: отсутствующий/повреждённый файл проекта или DXF."""


def build_parser() -> argparse.ArgumentParser:
    """Строит единый argparse-парсер CLI КОНТУР-ПРО."""
    parser = argparse.ArgumentParser(description=f"КОНТУР-ПРО v{VERSION}")
    parser.add_argument("--cli", action="store_true", help="CLI режим")
    parser.add_argument("--gui", action="store_true", help="GUI режим (по умолчанию без аргументов)")
    parser.add_argument("--template", type=str, default="Офис", help="Шаблон здания")
    parser.add_argument("--tier", type=int, default=1, choices=[1, 2, 3], help="Tier уровень")
    parser.add_argument("--export", action="store_true", help="Экспорт отчёта")
    parser.add_argument("--test", action="store_true", help="Запуск тестов")
    parser.add_argument("--save", type=str, help="Сохранить проект в .kontur")
    parser.add_argument("--load", type=str, help="Загрузить проект из .kontur")
    parser.add_argument("--import", dest="import_file", type=str, help="Импорт DXF")
    parser.add_argument("--floor", type=int, default=1, help="Этаж")
    parser.add_argument("--outdoor", type=float, default=-28, help="Уличная температура для теплопотерь")
    parser.add_argument(
        "--output-dir", type=str, default=".", help="Каталог для экспортируемых файлов (по умолчанию текущий)"
    )
    return parser


def _resolve_project(ns: argparse.Namespace) -> tuple[list[Device], list[Room], int, float]:
    """Выбирает источник проекта: загрузка `.kontur`, импорт DXF или генерация шаблона.

    Печатает информационные сообщения об источнике (как раньше), поднимает
    :class:`CliInputError` при отсутствующем/повреждённом файле.
    """
    if ns.load:
        pm = ProjectManager()
        try:
            data = pm.load(ns.load)
        except (OSError, json.JSONDecodeError) as exc:
            raise CliInputError(f"не удалось загрузить проект «{ns.load}»: {exc}") from exc
        devices, rooms = data["devices"], data["rooms"]
        tier = data.get("tier", 1)
        scale = data.get("scale", 1.0)
        print(f"Проект загружен: {ns.load}")
        print(f"  Устройств: {len(devices)}, Помещений: {len(rooms)}")
        print(f"  Схема: {data.get('schema_version', '?')}")
        return devices, rooms, tier, scale

    if ns.import_file:
        result = DXFImporter.import_dxf(ns.import_file)
        if "error" in result:
            raise CliInputError(result["error"])
        devices = result.get("devices", [])
        rooms = result.get("rooms", [])
        walls = result.get("walls", [])
        print(f"DXF импортирован: {ns.import_file}")
        print(f"  Устройств: {len(devices)}, Стен: {len(walls)}")
        return devices, rooms, 1, 1.0

    devices, rooms = generate_template(ns.template, ns.tier)
    return devices, rooms, ns.tier, 1.0


def _print_export_summary(written: dict[str, Path | None]) -> None:
    """Печатает сводную строку по итогам экспорта (какие форматы удались)."""
    parts = []
    for key, label in _EXPORT_LABELS:
        if written.get(key) is not None:
            parts.append(f"{label} ✓")
        else:
            requirement = _EXPORT_REQUIRES.get(key)
            suffix = f" ({requirement})" if requirement else ""
            parts.append(f"{label} ✗{suffix}")
    print(f"\nЭкспорт: {', '.join(parts)}")


def run_cli(args: list[str]) -> int:
    """Выполняет один запуск CLI-конвейера: расчёт, отчёт, сохранение, экспорт.

    Оставлена для обратной совместимости (используется тестами и внешним кодом).
    Разбирает `args` собственным парсером и возвращает код завершения.
    """
    ns = build_parser().parse_args(args)
    return _run_cli(ns)


def _run_cli(ns: argparse.Namespace) -> int:
    """Основной конвейер CLI: источник проекта → расчёт → отчёт → сохранение → экспорт."""
    try:
        devices, rooms, tier, scale = _resolve_project(ns)
    except CliInputError as exc:
        print(f"Ошибка: {exc}")
        return 2

    scale_mgr = ScaleManager(50.0 * scale)
    core = EngineeringCore(devices, rooms, tier, scale_mgr)
    result = core.calculate()

    checker = ModelChecker()
    checks = checker.run_all(devices, rooms, result)

    print(render_report(ns.template, tier, result, checks))

    if ns.save:
        pm = ProjectManager()
        save_result = pm.save(ns.save, devices, rooms, tier=tier, scale=scale)
        print(f"\nПроект сохранён: {save_result['path']}")

    if ns.export:
        spec = SpecificationBuilder.build(devices, result)
        cable_journal = CableJournal.build(devices, result.cable_traces, scale_mgr)
        ctx = ExportContext(
            devices=devices,
            rooms=rooms,
            result=result,
            checks=checks,
            spec=spec,
            cable_journal=cast("list[dict]", cable_journal),
            scale_mgr=scale_mgr,
        )
        written = export_all(ctx, ns.output_dir)
        _print_export_summary(written)

    return 0


def run_tests() -> int:
    """Запускает все unit-тесты из каталога tests/ и возвращает код завершения."""
    import unittest

    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    suite = unittest.TestLoader().discover(str(tests_dir), top_level_dir=str(tests_dir.parent))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def _run_gui() -> int:
    """Запускает GUI, лениво импортируя kontur.gui (не тянет PyQt6 иначе)."""
    from kontur.gui import GuiUnavailableError, run_gui

    try:
        return run_gui()
    except GuiUnavailableError as exc:
        print(str(exc))
        print("Используйте CLI режим: python kontur_v18.py --cli --template Офис --tier 1")
        print("Или установите GUI-зависимости: pip install 'kontur-pro[gui]'")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI/GUI. `argv` — аргументы без имени программы (по умолчанию sys.argv[1:])."""
    raw_args = sys.argv[1:] if argv is None else list(argv)
    ns = build_parser().parse_args(raw_args)

    if ns.test:
        return run_tests()

    if ns.cli or ns.load or ns.import_file:
        return _run_cli(ns)

    if ns.gui or not raw_args:
        return _run_gui()

    return _run_cli(ns)
