"""КОНТУР-ПРО: модуль test_undo_scale_multiproject (объединённые тесты)."""

from __future__ import annotations

import unittest

from kontur.core import EngineeringCore
from kontur.models import Device, EngineeringResult, Room
from kontur.multiproject import MultiProjectManager
from kontur.scale import ScaleManager
from kontur.templates import generate_template
from kontur.undo import UndoManager

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestUndoManager(unittest.TestCase):
    def test_undo_redo(self):
        mgr = UndoManager()
        mgr.push({"state": 1})
        mgr.push({"state": 2})
        mgr.push({"state": 3})
        self.assertTrue(mgr.can_undo())
        state = mgr.undo()
        self.assertEqual(state["state"], 2)
        state = mgr.redo()
        self.assertEqual(state["state"], 3)


class TestScaleManager(unittest.TestCase):
    def test_px_to_m(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.px_to_m(100), 2.0)

    def test_m_to_px(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.m_to_px(2.0), 100)

    def test_area(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.area_px_to_m2(2500), 1.0)


class TestMultiProject(unittest.TestCase):
    def test_compare(self):
        mp = MultiProjectManager()
        d1, r1 = generate_template("Офис", 1)
        core1 = EngineeringCore(d1, r1, 1)
        res1 = core1.calculate()
        mp.add_project("Офис", d1, r1, res1)

        d2, r2 = generate_template("ЦОД", 3)
        core2 = EngineeringCore(d2, r2, 3)
        res2 = core2.calculate()
        mp.add_project("ЦОД", d2, r2, res2)

        comp = mp.compare()
        self.assertEqual(len(comp), 2)


# ============================================================================
# EXTRA TESTS (from test_small_modules.py)
# ============================================================================


class TestUndoManagerBehavior(unittest.TestCase):
    """Тесты для UndoManager с ограниченной историей."""

    def test_bounded_history(self) -> None:
        """Проверить, что история ограничена max_steps."""
        mgr = UndoManager(max_steps=3)
        mgr.push({"step": 1})
        mgr.push({"step": 2})
        mgr.push({"step": 3})
        mgr.push({"step": 4})

        self.assertEqual(len(mgr.stack), 3)

    def test_undo_clears_redo(self) -> None:
        """Проверить, что новый push очищает стек повторов."""
        mgr = UndoManager()
        mgr.push({"step": 1})
        mgr.push({"step": 2})
        mgr.push({"step": 3})

        mgr.undo()
        self.assertTrue(mgr.can_redo())

        mgr.push({"step": 4})
        self.assertFalse(mgr.can_redo())

    def test_deepcopy_isolation(self) -> None:
        """Проверить, что состояния изолированы через deepcopy."""
        mgr = UndoManager()
        state1 = {"data": {"value": 1}}
        mgr.push(state1)
        state1["data"]["value"] = 999

        mgr.push({"data": {"value": 2}})
        restored = mgr.undo()

        self.assertEqual(restored["data"]["value"], 1)


class TestScaleManagerConversions(unittest.TestCase):
    """Тесты для ScaleManager с различными масштабами."""

    def test_custom_scale(self) -> None:
        """Проверить работу со стандартным и пользовательским масштабом."""
        sm = ScaleManager(100.0)
        self.assertEqual(sm.px_to_m(100), 1.0)
        self.assertEqual(sm.m_to_px(1.0), 100)

    def test_area_conversions(self) -> None:
        """Проверить конвертацию площадей."""
        sm = ScaleManager(10.0)
        self.assertEqual(sm.area_m2_to_px(1.0), 100.0)
        self.assertEqual(sm.area_px_to_m2(100.0), 1.0)

    def test_set_scale_changes_ratio(self) -> None:
        """Проверить изменение масштаба."""
        sm = ScaleManager(50.0)
        self.assertEqual(sm.px_to_m(100), 2.0)

        sm.set_scale(100.0)
        self.assertEqual(sm.px_to_m(100), 1.0)


class TestMultiProjectManagerTypes(unittest.TestCase):
    """Тесты для MultiProjectManager с правильной типизацией."""

    def test_add_and_compare(self) -> None:
        """Проверить добавление и сравнение проектов."""
        mpm = MultiProjectManager()

        devices1 = [Device("d1", "Device1", 0, "power", equip_type="breaker")]
        devices2 = [Device("d2", "Device2", 0, "power", equip_type="breaker")]
        rooms1 = [Room("r1", "Room1", 50, 3.0)]
        rooms2 = [Room("r2", "Room2", 100, 3.0)]

        result1 = EngineeringResult(
            installed_power_w=1000,
            demand_power_w=500,
            recommended_breaker="16A",
            recommended_cable="1.5mm2",
            cost_total=1000,
            cooling_required_w=2000,
        )
        result2 = EngineeringResult(
            installed_power_w=2000,
            demand_power_w=1000,
            recommended_breaker="32A",
            recommended_cable="2.5mm2",
            cost_total=2000,
            cooling_required_w=4000,
        )

        mpm.add_project("proj1", devices1, rooms1, result1)
        mpm.add_project("proj2", devices2, rooms2, result2)

        comparison = mpm.compare()
        self.assertEqual(len(comparison), 2)
        self.assertEqual(comparison[0]["name"], "proj1")
        self.assertEqual(comparison[1]["power_kw"], 2.0)
