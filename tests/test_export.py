"""КОНТУР-ПРО: модуль test_export (объединённые тесты)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kontur.core import EngineeringCore
from kontur.export import ExportContext, Exporter, export_all
from kontur.export.registry import all_formats, available_formats, get_exporter
from kontur.templates import generate_template

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestExporter(unittest.TestCase):
    def test_json(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        json_str = Exporter.to_json(devices, rooms, result)
        self.assertIn("КОНТУР-ПРО", json_str)

    def test_html(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        html = Exporter.to_html(devices, rooms, result)
        self.assertIn("<html", html)

    def test_txt(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        txt = Exporter.to_txt(devices, rooms, result)
        self.assertIn("КОНТУР-ПРО", txt)


# ============================================================================
# EXTRA TESTS (from test_export_extra.py)
# ============================================================================


def _make_context() -> ExportContext:
    devices, rooms = generate_template("Офис", 1)
    core = EngineeringCore(devices, rooms, 1)
    result = core.calculate()
    return ExportContext(devices=devices, rooms=rooms, result=result)


class TestRegistry(unittest.TestCase):
    def test_lists_six_formats(self):
        formats = all_formats()
        names = {f.name for f in formats}
        self.assertEqual(len(formats), 6)
        self.assertEqual(names, {"json", "html", "txt", "excel", "pdf", "dxf"})

    def test_get_exporter_unknown_returns_none(self):
        self.assertIsNone(get_exporter("does-not-exist"))


class TestJsonExport(unittest.TestCase):
    def test_json_parses_and_has_expected_keys(self):
        ctx = _make_context()
        fmt = get_exporter("json")
        assert fmt is not None
        raw = fmt.render(ctx)
        data = json.loads(raw)
        for key in ("schema_version", "app", "version", "timestamp", "devices", "rooms", "result"):
            self.assertIn(key, data)
        self.assertEqual(data["app"], "КОНТУР-ПРО")

    def test_json_cable_traces_are_serialized_as_dicts_not_repr_strings(self):
        """Verify that cable_traces in result are dicts, not repr strings."""
        ctx = _make_context()
        fmt = get_exporter("json")
        assert fmt is not None
        raw = fmt.render(ctx)
        data = json.loads(raw)

        # Check result.cable_traces exists and is a list
        self.assertIn("cable_traces", data["result"])
        cable_traces = data["result"]["cable_traces"]
        self.assertIsInstance(cable_traces, list)

        # If there are cable traces, verify they are dicts with expected keys
        if cable_traces:
            for trace in cable_traces:
                self.assertIsInstance(trace, dict)
                for key in ("device_id", "path", "length_m", "system", "vertical_length"):
                    self.assertIn(key, trace)
                # Verify path is a list (tuples become lists in JSON)
                self.assertIsInstance(trace["path"], list)
                # Verify length_m is numeric
                self.assertIsInstance(trace["length_m"], (int, float))

    def test_json_no_repr_strings_in_output(self):
        """Verify no field in JSON is a Python repr string of a dataclass."""
        ctx = _make_context()
        fmt = get_exporter("json")
        assert fmt is not None
        raw = fmt.render(ctx)
        data = json.loads(raw)

        def walk_json(obj):
            """Walk JSON object tree and yield all string values."""
            if isinstance(obj, dict):
                for v in obj.values():
                    yield from walk_json(v)
            elif isinstance(obj, list):
                for item in obj:
                    yield from walk_json(item)
            elif isinstance(obj, str):
                yield obj

        # Check no string starts with class name repr patterns
        for value in walk_json(data):
            self.assertFalse(value.startswith("CableTrace("), f"Found CableTrace repr string: {value[:50]}")
            self.assertFalse(value.startswith("Device("), f"Found Device repr string: {value[:50]}")
            self.assertFalse(value.startswith("Room("), f"Found Room repr string: {value[:50]}")


class TestHtmlExport(unittest.TestCase):
    def test_html_escapes_script_tag(self):
        ctx = _make_context()
        ctx.devices[0].name = "<script>alert(1)</script>"
        fmt = get_exporter("html")
        assert fmt is not None
        html = fmt.render(ctx)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestExporterFacade(unittest.TestCase):
    """Проверка, что старый API Exporter.to_* не изменил поведения."""

    def test_to_json_to_html_to_txt(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertIn("КОНТУР-ПРО", Exporter.to_json(devices, rooms, result))
        self.assertIn("<html", Exporter.to_html(devices, rooms, result))
        self.assertIn("КОНТУР-ПРО", Exporter.to_txt(devices, rooms, result))


class TestExportAll(unittest.TestCase):
    def test_export_all_writes_all_available_formats_with_shared_timestamp(self):
        ctx = _make_context()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            results = export_all(ctx, out_dir)

            self.assertEqual(set(results), {"json", "html", "txt", "excel", "pdf", "dxf"})

            for name in ("json", "html", "txt"):
                path = results[name]
                assert path is not None
                self.assertTrue(path.exists())

            for name in ("excel", "pdf", "dxf"):
                fmt = get_exporter(name)
                assert fmt is not None
                if fmt.is_available():
                    path = results[name]
                    assert path is not None
                    self.assertTrue(path.exists())

            stamp = ctx.file_timestamp
            for path in results.values():
                if path is not None:
                    self.assertIn(stamp, path.name)

    def test_unavailable_format_is_skipped(self):
        ctx = _make_context()
        excel_fmt = get_exporter("excel")
        assert excel_fmt is not None
        original_is_available = excel_fmt.is_available
        excel_fmt.is_available = staticmethod(lambda: False)  # type: ignore[method-assign]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                results = export_all(ctx, Path(tmp))
                self.assertIsNone(results["excel"])
                self.assertNotIn(excel_fmt, available_formats())
        finally:
            excel_fmt.is_available = original_is_available  # type: ignore[method-assign]
