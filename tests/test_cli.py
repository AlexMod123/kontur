"""КОНТУР-ПРО: модуль test_cli (объединённые тесты)."""

from __future__ import annotations

import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kontur.checker import ModelChecker
from kontur.cli import main
from kontur.core import EngineeringCore
from kontur.report import render_report
from kontur.templates import generate_template

GOLDEN_DIR = Path(__file__).parent / "golden"


def _run_main(args: list[str]) -> tuple[int, str]:
    """Запускает `main(args)`, перехватывая stdout. Возвращает (код, вывод)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


class TestMainExitCodes(unittest.TestCase):
    def test_bad_dxf_path_returns_2(self):
        code, out = _run_main(["--cli", "--import", "/no/such/path.dxf"])
        self.assertEqual(code, 2)
        self.assertIn("Ошибка", out)

    def test_missing_project_file_returns_2(self):
        code, out = _run_main(["--cli", "--load", "/no/such/project.kontur"])
        self.assertEqual(code, 2)
        self.assertIn("Ошибка", out)

    def test_template_report_returns_0(self):
        code, out = _run_main(["--cli", "--template", "Офис", "--tier", "1"])
        self.assertEqual(code, 0)
        self.assertIn("КОНТУР-ПРО", out)


class TestExportOutputDir(unittest.TestCase):
    def test_export_writes_files_with_shared_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = _run_main(
                ["--cli", "--template", "Офис", "--tier", "1", "--export", "--output-dir", tmp]
            )
            self.assertEqual(code, 0)
            files = sorted(Path(tmp).glob("kontur_export_*.*"))
            self.assertGreaterEqual(len(files), 3)

            timestamps = set()
            for f in files:
                m = re.match(r"kontur_export_(\d{8}_\d{6})\.", f.name)
                self.assertIsNotNone(m, f"неожиданное имя файла: {f.name}")
                timestamps.add(m.group(1))
            self.assertEqual(len(timestamps), 1, f"метки времени экспорта разошлись: {timestamps}")


class TestRenderReportGolden(unittest.TestCase):
    def test_matches_golden_office_tier1(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        checks = ModelChecker().run_all(devices, rooms, result)

        rendered = render_report("Офис", 1, result, checks)
        golden = (GOLDEN_DIR / "cli_Офис_tier1.txt").read_text(encoding="utf-8")
        self.assertEqual(rendered + "\n", golden)


class TestGuiUnavailable(unittest.TestCase):
    def test_no_pyqt6_returns_1_with_message(self):
        import kontur.gui as gui_module

        with mock.patch.object(gui_module, "QT_AVAILABLE", False):
            code, out = _run_main([])
        self.assertEqual(code, 1)
        self.assertIn("PyQt6", out)
        self.assertIn("--cli", out)
