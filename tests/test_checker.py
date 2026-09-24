"""КОНТУР-ПРО: модуль test_checker (объединённые тесты)."""

from __future__ import annotations

import unittest

from kontur.checker import DEFAULT_RULES, CheckResult, ModelChecker
from kontur.core import EngineeringCore
from kontur.models import CheckStatus, Device, EngineeringResult, Room
from kontur.templates import generate_template

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestModelChecker(unittest.TestCase):
    def test_run_all(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        checker = ModelChecker()
        checks = checker.run_all(devices, rooms, result)
        self.assertGreater(len(checks), 10)

    def test_statuses(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        checker = ModelChecker()
        checks = checker.run_all(devices, rooms, result)
        for c in checks:
            self.assertIn(c["status"], ["OK", "WARN", "FAIL"])


# ============================================================================
# EXTRA TESTS (from test_checker_extra.py)
# ============================================================================


class TestCheckStatus(unittest.TestCase):
    """CheckStatus должен оставаться взаимозаменяемым с обычными строками."""

    def test_values_match_legacy_strings(self) -> None:
        """Значения enum совпадают со строками, которые исторически ожидают потребители."""
        self.assertEqual(CheckStatus.OK, "OK")
        self.assertEqual(CheckStatus.WARN, "WARN")
        self.assertEqual(CheckStatus.FAIL, "FAIL")

    def test_str_and_format_give_plain_value(self) -> None:
        """str()/f-строка от CheckStatus не должны содержать имя класса enum."""
        self.assertEqual(str(CheckStatus.OK), "OK")
        self.assertEqual(f"{CheckStatus.WARN}", "WARN")


class TestModelCheckerRuleOrdering(unittest.TestCase):
    """Порядок и количество правил не должны меняться при рефакторинге."""

    def _build_result(self) -> EngineeringResult:
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.demand_power_w = 700
        return result

    def test_run_all_preserves_rule_order(self) -> None:
        """run_all выполняет правила в порядке DEFAULT_RULES и не переупорядочивает их."""
        devices: list[Device] = []
        rooms: list[Room] = []
        result = self._build_result()

        checker = ModelChecker()
        checks = checker.run_all(devices, rooms, result)

        self.assertEqual(len(checks), len(DEFAULT_RULES))
        expected_names = [rule(devices, rooms, result).name for rule in DEFAULT_RULES]
        actual_names = [c["name"] for c in checks]
        self.assertEqual(actual_names, expected_names)

    def test_run_all_returns_same_list_object_as_self_checks(self) -> None:
        """Атрибут self.checks остаётся синхронизирован с возвращаемым списком."""
        checker = ModelChecker()
        result = self._build_result()
        checks = checker.run_all([], [], result)
        self.assertIs(checks, checker.checks)

    def test_custom_rules_are_respected_and_do_not_affect_default(self) -> None:
        """Можно передать собственный список правил, не затрагивая DEFAULT_RULES."""

        def _only_rule(devices, rooms, result) -> CheckResult:
            return CheckResult("Тест", CheckStatus.OK, "ok")

        checker = ModelChecker(rules=[_only_rule])
        checks = checker.run_all([], [], self._build_result())

        self.assertEqual(checks, [{"name": "Тест", "status": "OK", "detail": "ok"}])
        self.assertEqual(len(DEFAULT_RULES), 14)


class TestModelCheckerStatuses(unittest.TestCase):
    """Синтетические случаи, порождающие WARN и FAIL, для проверки статусов."""

    def test_synthetic_case_produces_fail_and_warn(self) -> None:
        """Модель без мощности и с превышенным перекосом фаз даёт FAIL, а нерассчитанные
        разделы (охлаждение, ИБП, освещение и т. п.) дают WARN."""
        result = EngineeringResult()
        result.installed_power_w = 0
        result.phase_imbalance_pct = 50.0
        result.voltage_drop_pct = 1.0
        result.grounding_status = "OK"
        result.grounding_r = 2.0
        result.cooling_required_w = 0
        result.ups_power_w = 0
        result.selectivity_ok = True
        result.lighting_lux = 0
        result.short_circuit_3ph = 0
        result.leakage_current_ma = 0
        result.lightning_zone = ""
        result.poe_required_w = 0
        result.lan_ports = 0

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        by_name = {c["name"]: c for c in checks}

        self.assertEqual(by_name["Мощность"]["status"], "FAIL")
        self.assertEqual(by_name["Перекос фаз"]["status"], "FAIL")
        self.assertEqual(by_name["Охлаждение"]["status"], "WARN")
        self.assertEqual(by_name["ИБП"]["status"], "WARN")
        self.assertEqual(by_name["Освещение"]["status"], "WARN")
        self.assertEqual(by_name["Токи КЗ"]["status"], "WARN")
        self.assertEqual(by_name["Утечки"]["status"], "WARN")
        self.assertEqual(by_name["Молниезащита"]["status"], "WARN")
        self.assertEqual(by_name["ЛВС/СКС"]["status"], "WARN")

        statuses = {c["status"] for c in checks}
        self.assertTrue(statuses.issubset({"OK", "WARN", "FAIL"}))

    def test_grounding_warning_status_maps_to_warn(self) -> None:
        """Промежуточный result.grounding_status == 'WARNING' даёт CheckStatus.WARN."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.grounding_status = "WARNING"
        result.grounding_r = 7.0

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        grounding = next(c for c in checks if c["name"] == "Заземление")
        self.assertEqual(grounding["status"], "WARN")

    def test_grounding_other_status_maps_to_fail(self) -> None:
        """Любой иной result.grounding_status (например 'FAIL') даёт CheckStatus.FAIL."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.grounding_status = "FAIL"
        result.grounding_r = 12.0

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        grounding = next(c for c in checks if c["name"] == "Заземление")
        self.assertEqual(grounding["status"], "FAIL")


class TestCheckCable(unittest.TestCase):
    """ "Сечение кабеля": реальная проверка координации автомат/кабель (ПУЭ 3.1.x)."""

    def test_fails_when_breaker_exceeds_cable_ampacity(self) -> None:
        """Автомат крупнее допустимого тока кабеля -> FAIL (нарушена координация)."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.total_current_a = 30.0
        result.recommended_breaker = 125
        result.recommended_cable = "ВВГнг-LS 5x2.5"  # I_доп = 25 А
        result.cable_section = 2.5

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        cable = next(c for c in checks if c["name"] == "Сечение кабеля")
        self.assertEqual(cable["status"], "FAIL")

    def test_fails_when_design_current_exceeds_cable_ampacity(self) -> None:
        """Расчётный ток превышает I_доп кабеля -> FAIL, даже если автомат "проходит"."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.total_current_a = 40.0
        result.recommended_breaker = 20
        result.recommended_cable = "ВВГнг-LS 5x2.5"  # I_доп = 25 А
        result.cable_section = 2.5

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        cable = next(c for c in checks if c["name"] == "Сечение кабеля")
        self.assertEqual(cable["status"], "FAIL")

    def test_ok_when_breaker_and_current_within_ampacity(self) -> None:
        """Автомат и расчётный ток в пределах I_доп кабеля -> OK, формат detail сохранён."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.total_current_a = 20.0
        result.recommended_breaker = 25
        result.recommended_cable = "ВВГнг-LS 5x2.5"  # I_доп = 25 А
        result.cable_section = 2.5

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        cable = next(c for c in checks if c["name"] == "Сечение кабеля")
        self.assertEqual(cable["status"], "OK")
        self.assertEqual(cable["detail"], "ВВГнг-LS 5x2.5, 2.5 мм²")

    def test_fails_when_cable_name_unknown(self) -> None:
        """Имя кабеля отсутствует в CABLE_TABLE_3PH -> FAIL, а не молчаливый OK."""
        result = EngineeringResult()
        result.installed_power_w = 1000
        result.total_current_a = 10.0
        result.recommended_breaker = 16
        result.recommended_cable = "НЕСУЩЕСТВУЮЩИЙ КАБЕЛЬ"
        result.cable_section = 2.5

        checker = ModelChecker()
        checks = checker.run_all([], [], result)
        cable = next(c for c in checks if c["name"] == "Сечение кабеля")
        self.assertEqual(cable["status"], "FAIL")
