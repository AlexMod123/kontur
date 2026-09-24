"""КОНТУР-ПРО: модуль test_calculators (объединённые тесты)."""

from __future__ import annotations

import unittest

import pytest

from kontur.calculators import (
    AcousticCalculator,
    CableCalculator,
    CableJournal,
    CoolingCalculator,
    GroundCalculator,
    HeatLossCalculator,
    LANCalculator,
    LeakageCalculator,
    LightingCalculator,
    LightningProtection,
    ReactiveLossCalculator,
    SelectivityChecker,
    VentilationCalculator,
)
from kontur.config import AUTOMAT_STEPS
from kontur.models import CableTrace, Device, Room

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestCableCalculator(unittest.TestCase):
    def test_select_section(self):
        cable = CableCalculator.select_section(25)
        self.assertEqual(cable["section"], 2.5)

    def test_select_section_high(self):
        cable = CableCalculator.select_section(200)
        self.assertEqual(cable["section"], 70.0)

    def test_select_breaker(self):
        b = CableCalculator.select_breaker(20)
        self.assertIn(b, AUTOMAT_STEPS)
        self.assertGreaterEqual(b, 25)

    def test_voltage_drop_1phase(self):
        v = CableCalculator.voltage_drop(10, 30, 2.5)
        self.assertGreater(v, 0)
        self.assertLess(v, 10)

    def test_voltage_drop_3phase_cos_phi(self):
        v = CableCalculator.voltage_drop(30, 50, 6.0, voltage=380, phases=3, cos_phi=0.92)
        self.assertGreater(v, 0)
        self.assertLess(v, 10)

    def test_no_13_in_automat_steps(self):
        self.assertNotIn(13, AUTOMAT_STEPS)


class TestGroundCalculator(unittest.TestCase):
    def test_basic(self):
        r = GroundCalculator.calc()
        self.assertGreater(r["resistance"], 0)
        self.assertLessEqual(r["resistance"], 4.0)

    def test_rod_count(self):
        r = GroundCalculator.calc(rho_soil=500)
        self.assertGreater(r["rod_count"], 1)


class TestCoolingCalculator(unittest.TestCase):
    def test_basic(self):
        c = CoolingCalculator.calc(1000, 50, 2)
        self.assertGreater(c, 900)

    def test_no_equipment(self):
        c = CoolingCalculator.calc(0, 0, 0)
        self.assertGreaterEqual(c, 0)


class TestVentilationCalculator(unittest.TestCase):
    def test_basic(self):
        v = VentilationCalculator.calc(2000, 100, delta_t=10)
        self.assertGreater(v, 0)


class TestSelectivityChecker(unittest.TestCase):
    def test_ok(self):
        r = SelectivityChecker.check(63, [16, 20])
        self.assertTrue(r["ok"])

    def test_fail(self):
        r = SelectivityChecker.check(16, [16, 20])
        self.assertFalse(r["ok"])

    def test_curve_bc(self):
        self.assertTrue(SelectivityChecker.check_curve("C", "B", 40, 16))
        self.assertFalse(SelectivityChecker.check_curve("B", "C", 16, 40))


class TestLightingCalculator(unittest.TestCase):
    def test_office(self):
        r = LightingCalculator.calc(50, "office", 3.0)
        self.assertEqual(r["lux"], 500)
        self.assertGreater(r["lamps"], 0)

    def test_storage(self):
        r = LightingCalculator.calc(500, "storage")
        self.assertEqual(r["lux"], 200)


class TestLightningProtection(unittest.TestCase):
    def test_small_building(self):
        r = LightningProtection.assess(10, 10, 3)
        self.assertGreaterEqual(r["strikes_per_year"], 0)

    def test_large_building(self):
        r = LightningProtection.assess(100, 50, 20, region_thunderstorms=80)
        self.assertGreater(r["strikes_per_year"], 0)


class TestLeakageCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device("d1", "Test", 450, "it"), Device("d2", "Test2", 200, "network")]
        r = LeakageCalculator.calc(devs, [30, 50])
        self.assertGreater(r["current_ma"], 0)

    def test_uzo_selection(self):
        devs = [Device(f"d{i}", "Test", 450, "it") for i in range(80)]
        r = LeakageCalculator.calc(devs)
        self.assertGreater(r["uzo_ma"], 30)


class TestReactiveLoss(unittest.TestCase):
    def test_basic(self):
        r = ReactiveLossCalculator.calc(1000, 0.85)
        self.assertGreater(r["reactive_var"], 0)
        self.assertGreater(r["apparent_va"], 1000)

    def test_unity(self):
        r = ReactiveLossCalculator.calc(1000, 1.0)
        self.assertEqual(r["reactive_var"], 0)


class TestHeatLoss(unittest.TestCase):
    def test_basic(self):
        rooms = [Room("r1", "Test", 50, width=200, height=150, height_m=3.0)]
        loss = HeatLossCalculator.calc(rooms, outdoor_temp=-28)
        self.assertGreater(loss, 0)


class TestAcousticCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device("d1", "Server", 500, "it", equip_type="server")]
        noise = AcousticCalculator.calc(devs, 200)
        self.assertGreater(noise, 30)

    def test_silent(self):
        devs = [Device("d1", "Outlet", 500, "power", equip_type="outlet")]
        noise = AcousticCalculator.calc(devs, 200)
        self.assertGreater(noise, 0)


class TestLANCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device(f"d{i}", "PC", 450, "it", equip_type="pc") for i in range(10)]
        devs.append(Device("cam1", "Camera", 25, "camera", equip_type="camera_ip"))
        r = LANCalculator.calc(devs)
        self.assertGreater(r["total_ports"], 0)
        self.assertGreater(r["cable_m"], 0)

    def test_poe(self):
        devs = [Device(f"c{i}", "Cam", 25, "camera", equip_type="camera_ip") for i in range(10)]
        r = LANCalculator.calc(devs)
        self.assertGreater(r["poe_required_w"], 0)
        self.assertGreater(r["poe_budget_w"], 0)


class TestCableJournal(unittest.TestCase):
    def test_build(self):
        from kontur.core import EngineeringCore
        from kontur.templates import generate_template

        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        journal = CableJournal.build(devices, result.cable_traces)
        self.assertGreater(len(journal), 0)


# ============================================================================
# EXTRA TESTS (from test_calculators_extra.py)
# ============================================================================

DEVICES_LEAKAGE = [
    Device(id="1", name="PC1", power_w=300, category="it"),
    Device(id="2", name="Light1", power_w=100, category="lighting"),
    Device(id="3", name="Misc1", power_w=50, category="other"),
]

DEVICES_NOISE = [
    Device(id="1", name="Srv1", power_w=500, category="it", equip_type="server"),
    Device(id="2", name="Sw1", power_w=50, category="network", equip_type="switch"),
]

DEVICES_LAN = [
    Device(id="1", name="PC1", power_w=300, category="it"),
    Device(id="2", name="Cam1", power_w=10, category="camera"),
    Device(id="3", name="AP1", power_w=15, category="network", equip_type="wifi"),
    Device(id="4", name="Srv1", power_w=500, category="it", equip_type="server"),
]


class TestElectricalReference:
    def test_select_section_reference(self):
        assert CableCalculator.select_section(25) == {
            "section": 2.5,
            "max_current": 27,
            "name": "ВВГнг-LS 3x2.5",
        }

    def test_select_section_above_table_falls_back_to_last(self):
        assert CableCalculator.select_section(200) == {
            "section": 70.0,
            "max_current": 230,
            "name": "ВВГнг-LS 3x70",
        }

    def test_select_section_3phase_40a(self):
        assert CableCalculator.select_section(40, phases=3) == {
            "section": 6.0,
            "max_current": 42,
            "name": "ВВГнг-LS 5x6",
        }

    def test_select_section_3phase_25a(self):
        assert CableCalculator.select_section(25, phases=3) == {
            "section": 2.5,
            "max_current": 25,
            "name": "ВВГнг-LS 5x2.5",
        }

    def test_select_section_3phase_26a(self):
        assert CableCalculator.select_section(26, phases=3) == {
            "section": 4.0,
            "max_current": 35,
            "name": "ВВГнг-LS 5x4",
        }

    def test_select_section_3phase_above_table_falls_back_to_last(self):
        assert CableCalculator.select_section(300, phases=3) == {
            "section": 120.0,
            "max_current": 260,
            "name": "ВВГнг-LS 5x120",
        }

    def test_select_breaker_reference(self):
        assert CableCalculator.select_breaker(20) == 25

    def test_voltage_drop_1phase_reference(self):
        assert CableCalculator.voltage_drop(10, 30, 2.5) == pytest.approx(1.7563636363636366)

    def test_voltage_drop_3phase_reference(self):
        v = CableCalculator.voltage_drop(30, 50, 6.0, voltage=380, phases=3, cos_phi=0.92)
        assert v == pytest.approx(1.861402072883051)

    def test_selectivity_ok_reference(self):
        assert SelectivityChecker.check(63, [16, 20]) == {"ok": True, "issues": []}

    def test_selectivity_bad_reference(self):
        result = SelectivityChecker.check(16, [16, 20])
        assert result["ok"] is False
        assert len(result["issues"]) == 2

    def test_selectivity_curve_reference(self):
        assert SelectivityChecker.check_curve("C", "B", 40, 16) is True
        assert SelectivityChecker.check_curve("B", "C", 16, 40) is False

    def test_leakage_reference(self):
        assert LeakageCalculator.calc(DEVICES_LEAKAGE, [30, 50]) == {"current_ma": 1.4, "uzo_ma": 30}
        assert LeakageCalculator.calc(DEVICES_LEAKAGE) == {"current_ma": 0.6, "uzo_ma": 30}

    def test_reactive_loss_reference(self):
        r = ReactiveLossCalculator.calc(1000, 0.85)
        assert r == {"reactive_var": 619.7, "apparent_va": 1176.5, "tan_phi": 0.62}
        assert ReactiveLossCalculator.calc(1000, 1.0) == {
            "reactive_var": 0,
            "apparent_va": 1000,
            "tan_phi": 0,
        }


class TestElectricalGuards:
    def test_voltage_drop_rejects_zero_section(self):
        with pytest.raises(ValueError):
            CableCalculator.voltage_drop(10, 30, 0)

    def test_voltage_drop_rejects_zero_voltage(self):
        with pytest.raises(ValueError):
            CableCalculator.voltage_drop(10, 30, 2.5, voltage=0)

    def test_reactive_loss_rejects_zero_cos_phi(self):
        with pytest.raises(ValueError):
            ReactiveLossCalculator.calc(1000, 0)

    def test_select_section_handles_zero_current(self):
        assert CableCalculator.select_section(0)["name"] == "ВВГнг-LS 3x1.5"

    def test_select_section_rejects_invalid_phases(self):
        with pytest.raises(ValueError):
            CableCalculator.select_section(25, phases=2)


class TestGroundingReference:
    def test_ground_default_reference(self):
        assert GroundCalculator.calc() == {"resistance": 3.79, "rod_count": 9, "single_resistance": 32.57}

    def test_ground_high_resistivity_reference(self):
        r = GroundCalculator.calc(rho_soil=500)
        assert r == {"resistance": 3.98, "rod_count": 43, "single_resistance": 162.86}

    def test_lightning_low_risk_reference(self):
        r = LightningProtection.assess(10, 10, 3)
        assert r == {
            "strikes_per_year": 0.03,
            "zone": "Не требуется (N < 1)",
            "risk": "Низкий",
            "building_area": 714.5,
        }

    def test_lightning_medium_risk_reference(self):
        r = LightningProtection.assess(100, 50, 20, region_thunderstorms=80)
        assert r == {
            "strikes_per_year": 2.74,
            "zone": "Зона Б (III категория)",
            "risk": "Средний",
            "building_area": 34309.7,
        }

    def test_lightning_zero_size_building(self):
        r = LightningProtection.assess(0, 0, 0)
        assert r == {
            "strikes_per_year": 0.0,
            "zone": "Не требуется (N < 1)",
            "risk": "Низкий",
            "building_area": 0.0,
        }


class TestGroundingGuards:
    def test_ground_rejects_zero_rod_length(self):
        with pytest.raises(ValueError):
            GroundCalculator.calc(length_rod=0)

    def test_ground_rejects_zero_rod_diameter(self):
        with pytest.raises(ValueError):
            GroundCalculator.calc(diameter_rod=0)


class TestClimateReference:
    def test_cooling_reference(self):
        assert CoolingCalculator.calc(1000, 50, 2) == 1279

    def test_cooling_all_zero(self):
        assert CoolingCalculator.calc(0, 0, 0) == 0

    def test_ventilation_reference(self):
        assert VentilationCalculator.calc(2000, 100, delta_t=10) == 588

    def test_ventilation_zero_delta_t_falls_back_to_air_rate(self):
        assert VentilationCalculator.calc(2000, 100, delta_t=0) == 300

    def test_heat_loss_reference(self):
        rooms = [Room(id="r1", name="Room1", area=50, width=800, height=600, height_m=3.0)]
        assert HeatLossCalculator.calc(rooms, outdoor_temp=-28) == 2953


class TestLightingReference:
    def test_lighting_office_reference(self):
        r = LightingCalculator.calc(50, "office", 3.0)
        assert r == {"lux": 500, "lamps": 21, "utilization": 0.5}

    def test_lighting_storage_reference(self):
        r = LightingCalculator.calc(500, "storage")
        assert r == {"lux": 200, "lamps": 84, "utilization": 0.5}


class TestLightingGuards:
    def test_lighting_rejects_zero_lamp_flux(self):
        with pytest.raises(ValueError):
            LightingCalculator.calc(50, "office", 3.0, lamp_flux=0)

    def test_lighting_rejects_zero_maintenance_factor(self):
        with pytest.raises(ValueError):
            LightingCalculator.calc(50, "office", 3.0, maintenance_factor=0)


class TestAcousticReference:
    def test_acoustic_reference(self):
        assert AcousticCalculator.calc(DEVICES_NOISE, 200) == 58.1

    def test_acoustic_empty_devices_is_background(self):
        assert AcousticCalculator.calc([], 100) == 30


class TestAcousticGuards:
    def test_acoustic_rejects_negative_room_volume(self):
        with pytest.raises(ValueError):
            AcousticCalculator.calc(DEVICES_NOISE, -10)


class TestNetworkReference:
    def test_lan_reference(self):
        r = LANCalculator.calc(DEVICES_LAN)
        assert r == {
            "total_ports": 10,
            "user_ports": 2,
            "camera_ports": 1,
            "phone_ports": 0,
            "server_ports": 2,
            "patch_panels": 1,
            "cable_m": 450,
            "poe_ports": 2,
            "poe_required_w": 60,
            "poe_budget_w": 740,
        }

    def test_lan_empty_devices_reserve_only(self):
        r = LANCalculator.calc([])
        assert r == {
            "total_ports": 4,
            "user_ports": 0,
            "camera_ports": 0,
            "phone_ports": 0,
            "server_ports": 0,
            "patch_panels": 1,
            "cable_m": 180,
            "poe_ports": 0,
            "poe_required_w": 0,
            "poe_budget_w": 0,
        }


class TestCableJournalReference:
    def test_journal_reference(self):
        traces = [CableTrace(device_id="1", length_m=10, vertical_length=2)]
        journal = CableJournal.build(DEVICES_LAN, traces)
        assert journal == [
            {
                "num": 1,
                "designation": "PC1",
                "start": "ЩРО",
                "end": "PC1",
                "cable": "ВВГнг-LS 3x1.5",
                "section": 1.5,
                "length_m": 12,
                "current_a": 1.0,
                "system": "it",
            },
            {
                "num": 2,
                "designation": "Cam1",
                "start": "ЩРО",
                "end": "Cam1",
                "cable": "ВВГнг-LS 3x1.5",
                "section": 1.5,
                "length_m": 0,
                "current_a": 0.0,
                "system": "camera",
            },
            {
                "num": 3,
                "designation": "AP1",
                "start": "ЩРО",
                "end": "AP1",
                "cable": "ВВГнг-LS 3x1.5",
                "section": 1.5,
                "length_m": 0,
                "current_a": 0.1,
                "system": "network",
            },
            {
                "num": 4,
                "designation": "Srv1",
                "start": "ЩРО",
                "end": "Srv1",
                "cable": "ВВГнг-LS 3x1.5",
                "section": 1.5,
                "length_m": 0,
                "current_a": 1.6,
                "system": "it",
            },
        ]


def test_calculators_public_api_matches_all():
    import kontur.calculators as calculators_pkg

    for name in calculators_pkg.__all__:
        assert hasattr(calculators_pkg, name), f"{name} missing from kontur.calculators"
