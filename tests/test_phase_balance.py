"""Тесты балансировки фаз (PhaseBalancer)."""

from __future__ import annotations

import unittest

from kontur.calculators import PhaseBalancer
from kontur.calculators.electrical import PHASE_VOLTAGE_V, THREE_PHASE_MIN_POWER_W
from kontur.config import DEMAND_FACTORS, PHASE_IMBALANCE_MAX, TEMPLATES
from kontur.models import Device
from kontur.templates import generate_template
from tests.test_calculators import DEVICES_LEAKAGE


class TestPhaseBalancer(unittest.TestCase):
    def test_balanced(self):
        devs = [Device(f"d{i}", "Test", 100, "it") for i in range(9)]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertLess(imbalance, 5)

    def test_one_large(self):
        devs = [Device("d1", "Big", 5000, "it"), Device("d2", "Small", 100, "it")]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertLess(imbalance, 100)

    def test_greedy_better_than_round_robin(self):
        devs = [
            Device("d1", "A", 3000, "it"),
            Device("d2", "B", 3000, "it"),
            Device("d3", "C", 2000, "it"),
            Device("d4", "D", 2000, "it"),
            Device("d5", "E", 1000, "it"),
            Device("d6", "F", 1000, "it"),
        ]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertLess(imbalance, 20)

    def test_three_phase_device_splits_equally(self):
        # power_w >= THREE_PHASE_MIN_POWER_W => подключение сразу на три фазы,
        # ток делится строго поровну: I = P*k/(3*U_phase).
        dev = Device("d1", "Rack", 6000, "server")
        self.assertGreaterEqual(dev.power_w, THREE_PHASE_MIN_POWER_W)
        phases = PhaseBalancer.balance([dev])
        expected_per_phase = round(6000 * DEMAND_FACTORS["server"] / PHASE_VOLTAGE_V / 3, 1)
        self.assertEqual(phases, {"A": expected_per_phase, "B": expected_per_phase, "C": expected_per_phase})
        self.assertEqual(PhaseBalancer.imbalance_pct(phases), 0.0)

        assignment = PhaseBalancer.assign([dev])
        self.assertEqual(assignment["ABC"], ["d1"])
        self.assertEqual(assignment["A"], [])
        self.assertEqual(assignment["B"], [])
        self.assertEqual(assignment["C"], [])

    def test_zero_phase_imbalance_is_100_percent(self):
        # Раньше нулевые фазы отфильтровывались из расчёта, и это давало 0% вместо 100%.
        phases = {"A": 10.0, "B": 0.0, "C": 0.0}
        self.assertEqual(PhaseBalancer.imbalance_pct(phases), 100.0)

    def test_all_zero_imbalance_is_zero(self):
        self.assertEqual(PhaseBalancer.imbalance_pct({"A": 0.0, "B": 0.0, "C": 0.0}), 0)

    def test_lpt_plus_improvement_beats_naive(self):
        # Крафченный случай: currents (при cos-независимой модели тока I=P*k/U,
        # категория "ups" => k=1.0, значит ток в А численно равен power_w/220)
        # равны [2, 3, 5, 2, 6, 9]. Один жадный LPT-проход (сортировка по убыванию
        # и раскладка на наименее загруженную фазу) даёт {A:9, B:10, C:8} — diff=2,
        # imbalance=20%. Локальное улучшение (перенос/обмен между самой загруженной
        # и самой разгруженной фазой) находит идеальный баланс {9, 9, 9} — 0%.
        currents = [2, 3, 5, 2, 6, 9]
        devs = [Device(f"d{i}", f"D{i}", c * PHASE_VOLTAGE_V, "ups") for i, c in enumerate(currents)]

        # Наивный алгоритм "как было": сортировка по мощности, без локального улучшения.
        naive_phases = {"A": 0.0, "B": 0.0, "C": 0.0}
        for dev in sorted(devs, key=lambda d: d.power_w, reverse=True):
            phase = min(naive_phases, key=lambda p: naive_phases[p])
            naive_phases[phase] += dev.power_w * DEMAND_FACTORS["ups"] / PHASE_VOLTAGE_V
        naive_imbalance = PhaseBalancer.imbalance_pct(naive_phases)
        self.assertEqual(naive_imbalance, 20.0)

        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertEqual(phases, {"A": 9.0, "B": 9.0, "C": 9.0})
        self.assertEqual(imbalance, 0.0)
        self.assertLess(imbalance, naive_imbalance)

    def test_deterministic(self):
        devs = [
            Device("d1", "A", 1500, "it"),
            Device("d2", "B", 1500, "hvac"),
            Device("d3", "C", 800, "lighting"),
            Device("d4", "D", 800, "lighting"),
            Device("d5", "E", 6000, "server"),
            Device("d6", "F", 300, "other"),
        ]
        first = PhaseBalancer.balance(devs)
        for _ in range(10):
            self.assertEqual(PhaseBalancer.balance(devs), first)

        first_assign = PhaseBalancer.assign(devs)
        for _ in range(10):
            self.assertEqual(PhaseBalancer.assign(devs), first_assign)


class TestPhaseBalancerReference:
    def test_phase_balance_reference(self):
        # Проверено вручную: для DEVICES_LEAKAGE (PC1=300W it, Light1=100W lighting,
        # Misc1=50W other) сортировка по убыванию расчётного тока (0.955, 0.273, 0.159 А)
        # даёт тот же порядок, что и сортировка по мощности (нет трёхфазных устройств,
        # улучшение не находит выигрыша при одном устройстве на фазу) — значения не
        # изменились по сравнению со старым алгоритмом.
        phases = PhaseBalancer.balance(DEVICES_LEAKAGE)
        assert phases == {"A": 1.0, "B": 0.3, "C": 0.2}
        # Все три фазы ненулевые, поэтому фикс imbalance_pct (учёт нулевых фаз) тоже
        # не меняет результат для этого набора: 80.0 остаётся верным.
        assert PhaseBalancer.imbalance_pct(phases) == 80.0

    def test_phase_imbalance_empty_is_zero(self):
        assert PhaseBalancer.imbalance_pct({"A": 0.0, "B": 0.0, "C": 0.0}) == 0


class TestPhaseBalanceTemplates(unittest.TestCase):
    """Балансировка фаз на реальных шаблонах (kontur.templates.generate_template).

    ЦОД содержит серверную стойку 5000 Вт в помещении суммарной нагрузкой ~8 кВт:
    при однофазном подключении такой стойки дисбаланс близок к 63%% (см. баг №1
    в задаче). После фикса (стойка >= THREE_PHASE_MIN_POWER_W подключается на три
    фазы поровну, плюс LPT по току и локальное улучшение) дисбаланс должен быть
    существенно ниже нормы PHASE_IMBALANCE_MAX=15%.
    """

    def test_template_imbalances(self):
        report = []
        for name in TEMPLATES:
            devices, _rooms = generate_template(name, tier=1)
            phases = PhaseBalancer.balance(devices)
            imbalance = PhaseBalancer.imbalance_pct(phases)
            report.append((name, phases, imbalance))

        print("\nБалансировка фаз по шаблонам (tier=1):")
        for name, phases, imbalance in report:
            print(f"  {name}: phases={phases} imbalance={imbalance}%")

        zcod_imbalance = next(imbalance for name, _phases, imbalance in report if name == "ЦОД")
        self.assertLess(zcod_imbalance, 63.5)
        # После фикса ЦОД должен укладываться в норму ГОСТ 13109 (PHASE_IMBALANCE_MAX).
        self.assertLessEqual(zcod_imbalance, PHASE_IMBALANCE_MAX)
