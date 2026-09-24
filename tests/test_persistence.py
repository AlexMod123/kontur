"""КОНТУР-ПРО: модуль test_persistence (объединённые тесты)."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from kontur.config import SCHEMA_VERSION
from kontur.models import Annotation, Device, Door, Room, Wall
from kontur.persistence.catalog import ExternalCatalog
from kontur.persistence.dxf_import import DXFImporter
from kontur.persistence.project import ProjectManager
from kontur.templates import generate_template

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestProjectManager(unittest.TestCase):
    def test_save_load(self):
        devices, rooms = generate_template("Офис", 1)
        pm = ProjectManager()
        filepath = "test_project.kontur"
        save_result = pm.save(filepath, devices, rooms, tier=1)
        self.assertTrue(save_result["ok"])
        loaded = pm.load(filepath)
        self.assertEqual(len(loaded["devices"]), len(devices))
        self.assertEqual(len(loaded["rooms"]), len(rooms))
        with contextlib.suppress(Exception):
            os.remove(filepath)

    def test_migration(self):
        old_data = {
            "schema_version": "1.0",
            "devices": [{"id": "d1", "name": "Test", "power_w": 100, "category": "it"}],
            "rooms": [{"id": "r1", "name": "Room", "area": 50}],
        }
        pm = ProjectManager()
        migrated = pm._migrate(old_data)
        self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
        self.assertEqual(migrated["devices"][0]["z"], 1.0)
        self.assertEqual(migrated["rooms"][0]["height_m"], 3.0)


class TestExternalCatalog(unittest.TestCase):
    def test_default_items(self):
        path = os.path.join(tempfile.gettempdir(), "test_catalog.json")
        if os.path.exists(path):
            os.remove(path)
        cat = ExternalCatalog(path)
        self.assertGreater(len(cat.items), 20)
        os.remove(path)

    def test_find(self):
        path = os.path.join(tempfile.gettempdir(), "test_catalog2.json")
        if os.path.exists(path):
            os.remove(path)
        cat = ExternalCatalog(path)
        results = cat.find("сервер")
        self.assertGreater(len(results), 0)
        os.remove(path)


# ============================================================================
# EXTRA TESTS (from test_persistence_extra.py)
# ============================================================================


class TestProjectManagerRoundtrip(unittest.TestCase):
    def test_save_load_roundtrip(self):
        devices = [
            Device(id="d1", name="Сервер", power_w=500, category="it", x=10, y=20, price=1000),
        ]
        rooms = [Room(id="r1", name="Серверная", area=25, width=300, height=200)]
        walls = [Wall(0, 0, 100, 0)]
        doors = [Door(50, 0, width=90)]
        annotations = [Annotation(5, 5, text="Примечание")]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "проект.kontur"
            pm = ProjectManager()
            save_result = pm.save(
                path, devices, rooms, walls=walls, doors=doors, annotations=annotations, tier=2, scale=1.5
            )
            self.assertTrue(save_result["ok"])
            self.assertEqual(save_result["path"], str(path))
            self.assertTrue(path.exists())

            loaded = pm.load(path)
            self.assertEqual(len(loaded["devices"]), 1)
            self.assertEqual(loaded["devices"][0].id, "d1")
            self.assertEqual(loaded["devices"][0].price, 1000)
            self.assertEqual(len(loaded["rooms"]), 1)
            self.assertEqual(loaded["rooms"][0].name, "Серверная")
            self.assertEqual(len(loaded["walls"]), 1)
            self.assertEqual(len(loaded["doors"]), 1)
            self.assertEqual(len(loaded["annotations"]), 1)
            self.assertEqual(loaded["tier"], 2)
            self.assertEqual(loaded["scale"], 1.5)
            self.assertEqual(loaded["schema_version"], SCHEMA_VERSION)

    def test_save_accepts_str_path(self):
        devices = [Device(id="d1", name="X", power_w=10, category="it")]
        rooms = [Room(id="r1", name="Room", area=10)]
        with tempfile.TemporaryDirectory() as tmp:
            path_str = os.path.join(tmp, "sub", "project.kontur")
            pm = ProjectManager()
            result = pm.save(path_str, devices, rooms)
            self.assertTrue(os.path.exists(path_str))
            loaded = pm.load(path_str)
            self.assertEqual(len(loaded["devices"]), 1)
            self.assertEqual(result["path"], path_str)

    def test_atomic_write_leaves_no_temp_files(self):
        devices = [Device(id="d1", name="X", power_w=10, category="it")]
        rooms = [Room(id="r1", name="Room", area=10)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.kontur"
            pm = ProjectManager()
            pm.save(path, devices, rooms)
            pm.save(path, devices, rooms)
            entries = os.listdir(tmp)
            leftover_tmp = [e for e in entries if ".tmp" in e or e.startswith(".project.kontur.")]
            self.assertEqual(leftover_tmp, [], f"обнаружены временные файлы: {entries}")

    def test_load_missing_file_raises(self):
        pm = ProjectManager()
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist.kontur"
            with self.assertRaises(FileNotFoundError):
                pm.load(missing)

    def test_load_migrates_old_schema(self):
        old_data = {
            "schema_version": "1.0",
            "devices": [{"id": "d1", "name": "Test", "power_w": 100, "category": "it"}],
            "rooms": [{"id": "r1", "name": "Room", "area": 50}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.kontur"
            path.write_text(json.dumps(old_data), encoding="utf-8")

            pm = ProjectManager()
            loaded = pm.load(path)
            self.assertEqual(loaded["schema_version"], SCHEMA_VERSION)
            self.assertEqual(loaded["devices"][0].z, 1.0)
            self.assertEqual(loaded["devices"][0].price, 0)
            self.assertEqual(loaded["rooms"][0].height_m, 3.0)

    def test_migrate_registry_matches_legacy_behavior(self):
        old_data = {
            "schema_version": "1.0",
            "devices": [{"id": "d1", "name": "Test", "power_w": 100, "category": "it"}],
            "rooms": [{"id": "r1", "name": "Room", "area": 50}],
        }
        pm = ProjectManager()
        migrated = pm._migrate(old_data)
        self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
        self.assertEqual(migrated["devices"][0]["z"], 1.0)
        self.assertEqual(migrated["rooms"][0]["height_m"], 3.0)

    def test_load_ignores_unknown_keys(self):
        """Прямая совместимость: неизвестные ключи в файле не должны ломать загрузку."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "devices": [
                {
                    "id": "d1",
                    "name": "Test",
                    "power_w": 100,
                    "category": "it",
                    "future_field": "from a newer version",
                }
            ],
            "rooms": [{"id": "r1", "name": "Room", "area": 50, "future_field": 123}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forward.kontur"
            path.write_text(json.dumps(data), encoding="utf-8")
            pm = ProjectManager()
            loaded = pm.load(path)
            self.assertEqual(loaded["devices"][0].id, "d1")
            self.assertEqual(loaded["rooms"][0].id, "r1")


class TestDXFImporterExtra(unittest.TestCase):
    def test_import_missing_file(self):
        result = DXFImporter.import_dxf("/no/such/file.dxf")
        self.assertIn("error", result)

    def test_import_garbage_file_returns_error(self):
        """Не-DXF файл (мусорные байты) не должен приводить к необработанному
        исключению: import_dxf обязан вернуть {"error": ...}, как и раньше."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "garbage.dxf"
            path.write_bytes(os.urandom(256))

            result = DXFImporter.import_dxf(path)
            self.assertIn("error", result)

    def test_import_small_dxf(self):
        ezdxf = self._require_ezdxf()
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0), (100, 0))
        doc.blocks.new(name="SERVER_RACK")
        msp.add_blockref("SERVER_RACK", insert=(10, 10))
        msp.add_text("Примечание", dxfattribs={"insert": (5, 5)})

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drawing.dxf"
            doc.saveas(path)

            result = DXFImporter.import_dxf(path)
            self.assertNotIn("error", result)
            self.assertEqual(len(result["walls"]), 1)
            self.assertEqual(len(result["devices"]), 1)
            self.assertEqual(result["devices"][0].equip_type, "server")
            self.assertEqual(len(result["annotations"]), 1)

    @staticmethod
    def _require_ezdxf():
        try:
            import ezdxf
        except ImportError as err:
            raise unittest.SkipTest("ezdxf не установлен") from err
        return ezdxf


class TestExternalCatalogExtra(unittest.TestCase):
    def test_csv_import_with_bad_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            cat = ExternalCatalog(catalog_path)
            before = len(cat.items)

            csv_path = Path(tmp) / "price.csv"
            csv_path.write_text(
                "id;name;power_w;category;price\n"
                "srv1;Сервер;500;it;10000\n"
                "bad_row;Без мощности;not_a_number;it;5000\n"
                "too_short;Мало колонок\n"
                "cam1;Камера;25;camera;2500\n",
                encoding="utf-8",
            )

            imported = cat.import_csv(csv_path)
            self.assertEqual(imported, 2)
            self.assertEqual(len(cat.items), before + 2)

            ids = {i["id"] for i in cat.items}
            self.assertIn("srv1", ids)
            self.assertIn("cam1", ids)
            self.assertNotIn("bad_row", ids)
            self.assertNotIn("too_short", ids)

    def test_csv_import_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat = ExternalCatalog(Path(tmp) / "catalog.json")
            result = cat.import_csv(Path(tmp) / "does_not_exist.csv")
            self.assertEqual(result, -1)
