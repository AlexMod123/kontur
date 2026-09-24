"""КОНТУР-ПРО: модуль test_designation_spec (объединённые тесты)."""

from __future__ import annotations

import unittest

from kontur.designation import DesignationGenerator, UGOPainter
from kontur.models import Device
from kontur.specification import SpecificationBuilder, VendorDatabase
from kontur.templates import generate_template

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestDesignationGenerator(unittest.TestCase):
    def test_breaker(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "Автомат", 0, "power", equip_type="breaker")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "QF1")

    def test_ups(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "ИБП", 0, "power", equip_type="ups")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "G1")

    def test_smoke(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "Датчик", 3, "ops", equip_type="ops_smoke")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "B1")


class TestVendorDatabase(unittest.TestCase):
    def test_get_vendor(self):
        self.assertIsNotNone(VendorDatabase.get_vendor("camera_ip"))
        self.assertIsNotNone(VendorDatabase.get_vendor("breaker"))

    def test_list_all(self):
        vendors = VendorDatabase.list_all()
        self.assertGreaterEqual(len(vendors), 6)


class TestSpecificationBuilder(unittest.TestCase):
    def test_build(self):
        devices, _ = generate_template("Офис", 1)
        spec = SpecificationBuilder.build(devices)
        self.assertGreater(len(spec), 0)


# ============================================================================
# EXTRA TESTS (from test_small_modules.py)
# ============================================================================


class TestDesignationGeneratorReset(unittest.TestCase):
    """Тесты для DesignationGenerator с новым методом reset()."""

    def setUp(self) -> None:
        """Очистить счётчики перед каждым тестом."""
        DesignationGenerator.COUNTERS.clear()

    def test_reset_method(self) -> None:
        """Проверить работу нового метода reset()."""
        dev = Device("d1", "Test", 0, "power", equip_type="breaker")
        DesignationGenerator.generate(dev)
        self.assertEqual(len(DesignationGenerator.COUNTERS), 1)

        DesignationGenerator.reset()
        self.assertEqual(len(DesignationGenerator.COUNTERS), 0)

    def test_reset_method_vs_direct_assignment(self) -> None:
        """Проверить, что оба способа сброса работают одинаково."""
        dev = Device("d1", "Test", 0, "power", equip_type="breaker")
        DesignationGenerator.generate(dev)

        DesignationGenerator.reset()
        self.assertEqual(len(DesignationGenerator.COUNTERS), 0)

        DesignationGenerator.generate(dev)
        DesignationGenerator.COUNTERS = {}
        self.assertEqual(len(DesignationGenerator.COUNTERS), 0)

    def test_multiple_types_counters(self) -> None:
        """Проверить счёт для разных типов обозначений."""
        dev_breaker = Device("d1", "Breaker", 0, "power", equip_type="breaker")
        dev_ups = Device("d2", "UPS", 0, "power", equip_type="ups")

        d1 = DesignationGenerator.generate(dev_breaker)
        d2 = DesignationGenerator.generate(dev_breaker)
        d3 = DesignationGenerator.generate(dev_ups)

        self.assertEqual(d1, "QF1")
        self.assertEqual(d2, "QF2")
        self.assertEqual(d3, "G1")


class TestUGOPainterStaticRegistry(unittest.TestCase):
    """Тесты для UGOPainter с неизменяемым регистром."""

    def test_ugo_shapes_is_registry(self) -> None:
        """Проверить, что UGO_SHAPES является классовым регистром."""
        shapes = UGOPainter.UGO_SHAPES.copy()
        shapes["test"] = "test_shape"

        self.assertNotIn("test", UGOPainter.UGO_SHAPES)

    def test_get_ugo_fallback(self) -> None:
        """Проверить fallback для неизвестных типов."""
        self.assertEqual(UGOPainter.get_ugo("breaker"), "rect_rounded")
        self.assertEqual(UGOPainter.get_ugo("unknown_type"), "rect")


class TestVendorDatabaseRegistry(unittest.TestCase):
    """Тесты для VendorDatabase с неизменяемым регистром."""

    def test_vendors_is_registry(self) -> None:
        """Проверить, что VENDORS является классовым регистром."""
        vendors = VendorDatabase.list_all()
        self.assertGreaterEqual(len(vendors), 6)

    def test_get_vendor_by_equipment(self) -> None:
        """Проверить получение вендора по типу оборудования."""
        siemens = VendorDatabase.get_vendor("switch")
        self.assertEqual(siemens, "Siemens")

        hikvision = VendorDatabase.get_vendor("camera_ip")
        self.assertEqual(hikvision, "Hikvision")

    def test_get_vendor_unknown(self) -> None:
        """Проверить None для неизвестного оборудования."""
        result = VendorDatabase.get_vendor("unknown_equipment")
        self.assertIsNone(result)


class TestSpecificationBuilderTypes(unittest.TestCase):
    """Тесты для SpecificationBuilder с правильной типизацией."""

    def test_build_with_optional_result(self) -> None:
        """Проверить, что result является опциональным параметром."""
        devices = [
            Device("d1", "Breaker", 0, "power", equip_type="breaker"),
            Device("d2", "Switch", 1, "network", equip_type="switch"),
        ]

        spec = SpecificationBuilder.build(devices)
        self.assertGreater(len(spec), 0)

        spec2 = SpecificationBuilder.build(devices, result=None)
        self.assertEqual(len(spec), len(spec2))

    def test_specification_structure(self) -> None:
        """Проверить структуру элементов спецификации."""
        devices = [Device("d1", "Device", 0, "power", equip_type="breaker")]

        spec = SpecificationBuilder.build(devices)
        self.assertGreater(len(spec), 0)

        for item in spec:
            self.assertIn("pos", item)
            self.assertIn("name", item)
            self.assertIn("vendor", item)
            self.assertIn("unit", item)
            self.assertIn("qty", item)
