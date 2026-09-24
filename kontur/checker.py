"""КОНТУР-ПРО: модуль checker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from kontur.config import (
    CABLE_TABLE_3PH,
    GROUND_R_MAX,
    GROUND_R_WARN,
    PHASE_IMBALANCE_MAX,
    VOLTAGE_DROP_MAX,
    VOLTAGE_DROP_WARN,
)
from kontur.models import CheckStatus, Device, EngineeringResult, Room

# ============================================================================
# СЕКЦИЯ 4: MODEL CHECKER
# ============================================================================

#: Делитель для перевода Вт в кВт при выводе детализации проверок.
WATTS_PER_KW: Final = 1000

#: Статус result.grounding_status (не CheckStatus!), выставляемый калькулятором
#: заземления (kontur.calculators) при промежуточном (не критичном) отклонении.
GROUNDING_STATUS_WARNING: Final = "WARNING"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Результат одной проверки модели на соответствие нормам."""

    name: str
    status: CheckStatus
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Представить результат в виде словаря {name, status, detail}.

        Это исторический формат, потребляемый CLI/GUI/экспортом — статус
        сериализуется как обычная строка ("OK"/"WARN"/"FAIL").
        """
        return {"name": self.name, "status": str(self.status), "detail": self.detail}


#: Сигнатура правила проверки: (устройства, помещения, расчёт) -> результат.
CheckRule = Callable[[list[Device], list[Room], EngineeringResult], CheckResult]


def _check_power(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.installed_power_w == 0:
        return CheckResult("Мощность", CheckStatus.FAIL, "Нет устройств с энергопотреблением")
    return CheckResult(
        "Мощность",
        CheckStatus.OK,
        f"Установлена: {result.installed_power_w / WATTS_PER_KW:.1f} кВт, "
        f"расчётная: {result.demand_power_w / WATTS_PER_KW:.1f} кВт",
    )


def _check_phases(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.phase_imbalance_pct <= PHASE_IMBALANCE_MAX:
        return CheckResult(
            "Перекос фаз", CheckStatus.OK, f"{result.phase_imbalance_pct}% (норма ≤{PHASE_IMBALANCE_MAX}%)"
        )
    return CheckResult(
        "Перекос фаз", CheckStatus.FAIL, f"{result.phase_imbalance_pct}% > {PHASE_IMBALANCE_MAX}%"
    )


def _check_cable(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    """Кабель по расчётному току и координация с автоматом (I_доп >= Iрасч, I_н.авт <= I_доп)."""
    row = next((c for c in CABLE_TABLE_3PH if c["name"] == result.recommended_cable), None)
    if row is None:
        return CheckResult(
            "Сечение кабеля", CheckStatus.FAIL, f"Кабель {result.recommended_cable!r} не найден в таблице"
        )
    ampacity = row["max_current"]
    if ampacity >= result.total_current_a and result.recommended_breaker <= ampacity:
        return CheckResult(
            "Сечение кабеля", CheckStatus.OK, f"{result.recommended_cable}, {result.cable_section} мм²"
        )
    return CheckResult(
        "Сечение кабеля",
        CheckStatus.FAIL,
        f"{result.recommended_cable} (I_доп={ampacity} А) не подходит: "
        f"Iрасч={result.total_current_a} А, автомат {result.recommended_breaker} А",
    )


def _check_voltage_drop(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.voltage_drop_pct <= VOLTAGE_DROP_WARN:
        return CheckResult(
            "Падение напряжения",
            CheckStatus.OK,
            f"{result.voltage_drop_pct}% (норма ≤{VOLTAGE_DROP_MAX}%)",
        )
    if result.voltage_drop_pct <= VOLTAGE_DROP_MAX:
        return CheckResult(
            "Падение напряжения",
            CheckStatus.WARN,
            f"{result.voltage_drop_pct}% — выше рекоменд. {VOLTAGE_DROP_WARN}%",
        )
    return CheckResult(
        "Падение напряжения", CheckStatus.FAIL, f"{result.voltage_drop_pct}% > {VOLTAGE_DROP_MAX}%"
    )


def _check_grounding(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.grounding_status == "OK":
        return CheckResult(
            "Заземление", CheckStatus.OK, f"R = {result.grounding_r} Ом (норма ≤{GROUND_R_MAX} Ом)"
        )
    if result.grounding_status == GROUNDING_STATUS_WARNING:
        return CheckResult(
            "Заземление", CheckStatus.WARN, f"R = {result.grounding_r} Ом (реком. ≤{GROUND_R_WARN} Ом)"
        )
    return CheckResult("Заземление", CheckStatus.FAIL, f"R = {result.grounding_r} Ом > {GROUND_R_WARN} Ом")


def _check_cooling(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.cooling_required_w > 0:
        return CheckResult(
            "Охлаждение", CheckStatus.OK, f"Требуется {result.cooling_required_w / WATTS_PER_KW:.1f} кВт"
        )
    return CheckResult("Охлаждение", CheckStatus.WARN, "Расчёт не выполнен")


def _check_ups(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.ups_power_w > 0:
        return CheckResult(
            "ИБП",
            CheckStatus.OK,
            f"{result.ups_power_w / WATTS_PER_KW:.1f} кВт, автономия {result.ups_autonomy_min} мин",
        )
    return CheckResult("ИБП", CheckStatus.WARN, "Не рассчитан")


def _check_selectivity(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.selectivity_ok:
        return CheckResult("Селективность", CheckStatus.OK, "Автоматы селективны")
    return CheckResult("Селективность", CheckStatus.FAIL, "Нарушена селективность")


def _check_lighting(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.lighting_lux > 0:
        return CheckResult(
            "Освещение", CheckStatus.OK, f"{result.lighting_lux} лк, ламп: {result.lighting_lamps}"
        )
    return CheckResult("Освещение", CheckStatus.WARN, "Не рассчитано")


def _check_short_circuit(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.short_circuit_3ph > 0:
        return CheckResult(
            "Токи КЗ",
            CheckStatus.OK,
            f"I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А, "
            f"Iуд={result.short_circuit_iudar}А",
        )
    return CheckResult("Токи КЗ", CheckStatus.WARN, "Не рассчитаны")


def _check_leakage(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.leakage_current_ma > 0:
        return CheckResult(
            "Утечки", CheckStatus.OK, f"Iут={result.leakage_current_ma} мА, УЗО {result.leakage_uzo_ma} мА"
        )
    return CheckResult("Утечки", CheckStatus.WARN, "Не рассчитаны")


def _check_lightning(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.lightning_zone:
        return CheckResult(
            "Молниезащита", CheckStatus.OK, f"{result.lightning_zone} ({result.lightning_risk})"
        )
    return CheckResult("Молниезащита", CheckStatus.WARN, "Не рассчитана")


def _check_poe(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.poe_required_w > 0:
        if result.poe_budget_w >= result.poe_required_w:
            return CheckResult(
                "PoE-бюджет", CheckStatus.OK, f"{result.poe_required_w} Вт / {result.poe_budget_w} Вт"
            )
        return CheckResult(
            "PoE-бюджет", CheckStatus.FAIL, f"{result.poe_required_w} Вт > {result.poe_budget_w} Вт"
        )
    return CheckResult("PoE-бюджет", CheckStatus.OK, "PoE-устройства не требуются")


def _check_lan(devices: list[Device], rooms: list[Room], result: EngineeringResult) -> CheckResult:
    if result.lan_ports > 0:
        return CheckResult(
            "ЛВС/СКС", CheckStatus.OK, f"{result.lan_ports} портов, {result.lan_cable_m:.0f} м кабеля"
        )
    return CheckResult("ЛВС/СКС", CheckStatus.WARN, "Не рассчитана")


#: Реестр правил проверки в порядке исполнения (важен для CLI golden-вывода).
DEFAULT_RULES: Final[list[CheckRule]] = [
    _check_power,
    _check_phases,
    _check_cable,
    _check_voltage_drop,
    _check_grounding,
    _check_cooling,
    _check_ups,
    _check_selectivity,
    _check_lighting,
    _check_short_circuit,
    _check_leakage,
    _check_lightning,
    _check_poe,
    _check_lan,
]


class ModelChecker:
    """Проверка модели на соответствие нормам (35+ проверок).

    Правила регистрируются как обычные функции ``CheckRule`` в
    ``self.rules`` (по умолчанию — ``DEFAULT_RULES``) и выполняются по
    порядку в :meth:`run_all`. Порядок и тексты результатов сохранены для
    совместимости с golden-тестами CLI.
    """

    def __init__(self, rules: list[CheckRule] | None = None) -> None:
        self.rules: list[CheckRule] = list(rules) if rules is not None else list(DEFAULT_RULES)
        self.checks: list[dict[str, str]] = []

    def run_all(self, devices: list[Device], rooms: list[Room], result: EngineeringResult) -> list[dict]:
        """Выполнить все зарегистрированные правила и вернуть список проверок.

        Возвращает список словарей ``{"name", "status", "detail"}`` в том же
        порядке, что и правила — формат и порядок неизменны исторически.
        """
        self.checks = [rule(devices, rooms, result).to_dict() for rule in self.rules]
        return self.checks
