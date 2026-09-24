"""КОНТУР-ПРО: модуль test_core (объединённые тесты)."""

from __future__ import annotations

import math
import unittest
from dataclasses import asdict

import pytest

from kontur.config import CABLE_TABLE_3PH, TEMPLATES, TIER_CONFIG
from kontur.core import UPS_MODULE_POWER_W, EngineeringCore
from kontur.models import Device, EngineeringResult
from kontur.routing import AStarRouter
from kontur.templates import generate_template

TEMPLATE_NAMES = list(TEMPLATES.keys())


# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestEngineeringCore(unittest.TestCase):
    def test_office(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.installed_power_w, 0)
        self.assertGreater(result.demand_power_w, 0)
        self.assertGreater(result.total_current_a, 0)

    def test_cod_tier3(self):
        devices, rooms = generate_template("ЦОД", 3)
        core = EngineeringCore(devices, rooms, 3)
        result = core.calculate()
        self.assertGreater(result.ups_power_w, result.demand_power_w)

    def test_cos_phi_in_result(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.cos_phi, 0.9)

    def test_short_circuit_calculated(self):
        devices, rooms = generate_template("ЦОД", 3)
        core = EngineeringCore(devices, rooms, 3)
        result = core.calculate()
        self.assertGreater(result.short_circuit_3ph, 0)

    def test_lan_calculated(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.lan_ports, 0)

    def test_heat_loss(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.heat_loss_w, 0)


class TestTemplates(unittest.TestCase):
    def test_office(self):
        devices, rooms = generate_template("Офис", 1)
        self.assertGreater(len(devices), 0)
        self.assertGreater(len(rooms), 0)

    def test_cod(self):
        devices, _ = generate_template("ЦОД", 3)
        self.assertGreater(len(devices), 0)

    def test_school(self):
        devices, _ = generate_template("Школа", 1)
        self.assertGreater(len(devices), 0)

    def test_warehouse(self):
        devices, _ = generate_template("Склад", 2)
        self.assertGreater(len(devices), 0)


# ============================================================================
# EXTRA TESTS (from test_core_extra.py)
# ============================================================================


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_calculate_populates_every_pipeline_step(template_name: str, tier: int) -> None:
    """Для каждого шаблона/tier каждый шаг конвейера должен заполнить свои поля."""
    devices, rooms = generate_template(template_name, tier)
    core = EngineeringCore(devices, rooms, tier)
    result = core.calculate()

    assert result.installed_power_w > 0
    assert result.demand_power_w > 0
    assert result.active_power_w == result.demand_power_w
    assert result.reactive_power_var >= 0

    assert set(result.per_phase_current) == {"A", "B", "C"}
    assert result.total_current_a > 0

    assert result.recommended_breaker > 0
    assert result.recommended_cable
    assert result.cable_section > 0

    assert result.grounding_status in {"OK", "WARNING", "FAIL"}
    assert result.grounding_r > 0

    assert result.cooling_required_w >= 0
    assert result.ventilation_required_m3h >= 0

    assert result.ups_power_w > 0
    assert result.ups_battery_count >= 1
    assert result.ups_autonomy_min >= 0

    assert isinstance(result.selectivity_ok, bool)

    assert result.short_circuit_3ph > 0
    assert result.short_circuit_1ph > 0
    assert result.short_circuit_iudar > 0

    assert result.leakage_current_ma >= 0
    assert result.leakage_uzo_ma > 0

    assert result.lightning_zone != ""
    assert result.lightning_risk in {"Низкий", "Средний", "Высокий"}

    assert result.lighting_lux > 0
    assert result.lighting_lamps > 0

    assert result.lan_ports > 0
    assert result.lan_cable_m >= 0
    assert result.poe_budget_w >= 0

    assert result.heat_loss_w > 0

    assert result.noise_level_db > 0

    assert len(result.cable_traces) == len(devices)
    assert {t.device_id for t in result.cable_traces} == {d.id for d in devices}

    assert result.cost_total > 0

    assert isinstance(result.recommendations, list)

    assert result.device_count == len(devices)
    assert result.room_count == len(rooms)


def test_calculate_returns_fresh_result_each_time() -> None:
    """Повторный calculate() не должен переиспользовать/мутировать предыдущий результат."""
    devices, rooms = generate_template("Офис", 1)
    core = EngineeringCore(devices, rooms, 1)
    result1 = core.calculate()
    result2 = core.calculate()
    assert result1 is not result2
    assert asdict(result1) == asdict(result2)


def test_router_factory_injection_is_used() -> None:
    """Кастомная фабрика роутера, переданная в конструктор, должна использоваться шагом трассировки."""
    calls = {"n": 0}

    def spy_router_factory() -> AStarRouter:
        calls["n"] += 1
        return AStarRouter()

    devices, rooms = generate_template("Офис", 1)
    core = EngineeringCore(devices, rooms, 1, router_factory=spy_router_factory)
    result = core.calculate()

    assert calls["n"] == 1
    assert len(result.cable_traces) == len(devices)


def test_constructor_stays_positional_compatible() -> None:
    """Старый способ вызова EngineeringCore(devices, rooms, tier, scale_mgr) должен работать."""
    from kontur.scale import ScaleManager

    devices, rooms = generate_template("Склад", 2)
    scale_mgr = ScaleManager()
    core = EngineeringCore(devices, rooms, 2, scale_mgr)
    result = core.calculate()
    assert isinstance(result, EngineeringResult)
    assert core.scale is scale_mgr


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
def test_generate_template_is_deterministic(template_name: str) -> None:
    """Два вызова generate_template с одинаковыми аргументами дают идентичный результат."""
    devices1, rooms1 = generate_template(template_name, 1)
    devices2, rooms2 = generate_template(template_name, 1)

    assert [asdict(d) for d in devices1] == [asdict(d) for d in devices2]
    assert [asdict(r) for r in rooms1] == [asdict(r) for r in rooms2]


def test_generate_template_unknown_falls_back_to_office() -> None:
    """Неизвестное имя шаблона должно откатываться на "Офис" (текущее поведение)."""
    devices_unknown, rooms_unknown = generate_template("НЕСУЩЕСТВУЮЩИЙ_ШАБЛОН", 1)
    devices_office, rooms_office = generate_template("Офис", 1)

    assert [asdict(d) for d in devices_unknown] == [asdict(d) for d in devices_office]
    assert [asdict(r) for r in rooms_unknown] == [asdict(r) for r in rooms_office]


def test_generate_template_tier_does_not_change_composition() -> None:
    """tier пока не влияет на состав устройств/помещений (сохранено ради совместимости)."""
    devices_t1, rooms_t1 = generate_template("ЦОД", 1)
    devices_t3, rooms_t3 = generate_template("ЦОД", 3)

    assert [asdict(d) for d in devices_t1] == [asdict(d) for d in devices_t3]
    assert [asdict(r) for r in rooms_t1] == [asdict(r) for r in rooms_t3]


# ============================================================================
# UPS SIZING TESTS (схема N/N+1/2N, батареи, автономия)
# ============================================================================


def _ups_load_device(power_w: float = 6070) -> Device:
    """Единственное устройство категории 'ups' (коэф. спроса 1.0), чтобы
    расчётная мощность (demand) точно равнялась power_w."""
    return Device(id="load", name="Нагрузка ИБП", power_w=power_w, category="ups")


@pytest.mark.parametrize(
    ("tier", "expected_modules"),
    [(1, 2), (2, 3), (3, 4)],
    ids=["tier1-N", "tier2-N+1", "tier3-2N"],
)
def test_ups_module_count_by_tier_scheme(tier: int, expected_modules: int) -> None:
    """Для demand=6070 Вт (2 модуля по 5 кВт нужно): N->2, N+1->3, 2N->4 модуля."""
    core = EngineeringCore([_ups_load_device()], [], tier)
    result = EngineeringResult()
    core._step_ups(result)
    assert result.ups_power_w == expected_modules * UPS_MODULE_POWER_W


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_ups_autonomy_meets_tier_target(tier: int) -> None:
    """Автономия АКБ, полученная округлением числа блоков вверх, не должна
    оказаться ниже целевой автономии яруса (иначе подбор АКБ некорректен)."""
    core = EngineeringCore([_ups_load_device()], [], tier)
    result = EngineeringResult()
    core._step_ups(result)
    target = TIER_CONFIG[tier]["ups_autonomy_target_min"]
    assert result.ups_autonomy_min >= target


def test_ups_battery_count_2n_is_double_n() -> None:
    """2N (Tier III) держит две независимые батарейные линии -> вдвое больше
    блоков АКБ, чем схема N (Tier I), при одинаковой нагрузке 6070 Вт."""
    device = _ups_load_device()
    result_n = EngineeringResult()
    EngineeringCore([device], [], 1)._step_ups(result_n)
    result_2n = EngineeringResult()
    EngineeringCore([device], [], 3)._step_ups(result_2n)
    assert result_2n.ups_battery_count == 2 * result_n.ups_battery_count


def test_avg_cable_length_matches_manual_manhattan_distance() -> None:
    """_avg_cable_length должен быть средним Манхэттенским расстоянием до щита,
    переведённым в метры по масштабу (без двойного деления на масштаб)."""
    devices = [
        Device(id="d1", name="d1", power_w=100, category="power", x=125, y=25),
        Device(id="d2", name="d2", power_w=100, category="power", x=25, y=425),
    ]
    core = EngineeringCore(devices, [], 1)
    panel_x, panel_y = core.panel_pos
    expected = sum((abs(d.x - panel_x) + abs(d.y - panel_y)) / 50.0 for d in devices) / len(devices)
    assert expected == pytest.approx(5.0)
    assert core._avg_cable_length() == pytest.approx(expected)


# ============================================================================
# ТОК ВВОДА / КАБЕЛЬ / АВТОМАТ ТРЁХФАЗНОГО ВВОДА (регрессия: сумма фаз -> макс. фаза)
# ============================================================================


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_design_current_is_max_phase_over_cos_phi(template_name: str, tier: int) -> None:
    """Расчётный ток ввода = ток наиболее нагруженной фазы / cos φ, а не сумма фаз.

    Сумма трёх фазных токов завышает расчётный ток вводного автомата/кабеля
    примерно втрое для сбалансированной нагрузки — именно этот баг и правится.
    """
    devices, rooms = generate_template(template_name, tier)
    result = EngineeringCore(devices, rooms, tier).calculate()

    expected = round(max(result.per_phase_current.values()) / result.cos_phi, 1)
    assert result.total_current_a == expected

    phase_sum = sum(result.per_phase_current.values())
    if phase_sum > 0:
        assert result.total_current_a < phase_sum


def test_design_current_zero_when_no_load() -> None:
    """Без нагрузки расчётный ток ввода равен 0 (а не ZeroDivisionError/NaN)."""
    result = EngineeringResult()
    result.cos_phi = 0.92
    current = EngineeringCore([], [], 1)._design_current_a({"A": 0.0, "B": 0.0, "C": 0.0}, result.cos_phi)
    assert current == 0.0


def test_design_current_balanced_load_matches_line_current_formula() -> None:
    """Для сбалансированной 3-фазной нагрузки 3x2 кВт ток ввода ~= P/(sqrt(3)*380*cos phi).

    Три одинаковых однофазных нагрузки по 2 кВт (категория "power", cos φ по
    умолчанию) раскладываются жадной балансировкой по одной на фазу — нагрузка
    идеально сбалансирована, и формула "макс.фаза / cos φ" должна совпадать (с
    точностью до 220В/380В ~ 1/sqrt(3)) с классической формулой линейного тока.
    """
    devices = [
        Device(id="d1", name="Нагрузка 1", power_w=2000, category="power", x=100, y=100),
        Device(id="d2", name="Нагрузка 2", power_w=2000, category="power", x=200, y=100),
        Device(id="d3", name="Нагрузка 3", power_w=2000, category="power", x=300, y=100),
    ]
    result = EngineeringCore(devices, [], 1).calculate()

    # Нагрузка должна была лечь ровно по одному устройству на фазу.
    assert result.phase_imbalance_pct == 0.0

    demand_power_w = result.demand_power_w  # 3 * 2000 * 0.7 (коэфф. спроса "power")
    expected_line_current = demand_power_w / (math.sqrt(3) * 380 * result.cos_phi)
    # rel=0.02: двойное округление (фазный ток -> 0.1 А, итог -> 0.1 А) и разница
    # между 3*U_фазное=660В и sqrt(3)*380В=658.18В дают ~1% расхождение.
    assert result.total_current_a == pytest.approx(expected_line_current, rel=0.02)


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_recommended_cable_is_three_phase_5_core(template_name: str, tier: int) -> None:
    """Кабель ввода подбирается по 5-жильной трёхфазной таблице (ВВГнг-LS 5xS)."""
    devices, rooms = generate_template(template_name, tier)
    result = EngineeringCore(devices, rooms, tier).calculate()
    assert result.recommended_cable.startswith("ВВГнг-LS 5x")


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_breaker_rating_does_not_exceed_cable_ampacity(template_name: str, tier: int) -> None:
    """Координация автомат/кабель по ПУЭ 3.1.x: I_н.авт <= I_доп кабеля."""
    devices, rooms = generate_template(template_name, tier)
    result = EngineeringCore(devices, rooms, tier).calculate()
    row = next(c for c in CABLE_TABLE_3PH if c["name"] == result.recommended_cable)
    assert result.recommended_breaker <= row["max_current"]
