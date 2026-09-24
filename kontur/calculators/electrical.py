"""КОНТУР-ПРО: электрические калькуляторы (кабель, фазы, селективность, cos φ, утечки)."""

from __future__ import annotations

import math
from typing import Final, TypedDict, cast

from kontur.config import AUTOMAT_STEPS, CABLE_TABLE, CABLE_TABLE_3PH, COS_PHI_DEFAULT, DEMAND_FACTORS
from kontur.models import Device

# --- Электрофизические константы ---
COPPER_RESISTIVITY_OHM_MM2_PER_M = 0.0175  # удельное сопротивление меди, Ом·мм²/м
INDUCTIVE_REACTANCE_OHM_PER_M = 0.0001  # погонное индуктивное сопротивление кабеля, Ом/м
BREAKER_SAFETY_FACTOR = 1.25  # запас тока автомата над расчётным током (ПУЭ)
PHASE_VOLTAGE_V = 220  # фазное напряжение сети, В
SELECTIVITY_CURRENT_RATIO = 1.6  # минимальное отношение номиналов вводного/отходящего автоматов

# --- Балансировка фаз ---
# Инженерная практика: одиночные нагрузки такой мощности (стойки PDU, крупные ИБП и т.п.)
# подключаются сразу на три фазы, а не заводятся на одну.
THREE_PHASE_MIN_POWER_W: Final = 4000
PHASE_ORDER: Final = ("A", "B", "C")  # порядок фаз, используемый как детерминированный тай-брейк
MAX_BALANCE_IMPROVEMENT_ITERATIONS: Final = 50  # ограничение числа итераций локального улучшения

# --- Утечки тока (СП 256.1325800) ---
LEAKAGE_IT_MA = 0.35  # утечка на устройство: ИТ/силовое/ИБП, мА
LEAKAGE_HVAC_LIGHTING_MA = 0.15  # утечка на устройство: освещение/ОВК, мА
LEAKAGE_OTHER_MA = 0.1  # утечка на устройство: прочие категории, мА
LEAKAGE_PER_CABLE_METER_MA = 0.01  # утечка кабеля: 10 мкА/м
LEAKAGE_UZO_LOW_MA = 30  # порог УЗО 30 мА
LEAKAGE_UZO_MID_MA = 100  # порог УЗО 100 мА
LEAKAGE_UZO_HIGH_MA = 300  # порог УЗО 300 мА
LEAKAGE_LOW_THRESHOLD_MA = 25  # суммарная утечка, при которой достаточно УЗО 30 мА
LEAKAGE_MID_THRESHOLD_MA = 70  # суммарная утечка, при которой достаточно УЗО 100 мА


class CableSpec(TypedDict):
    """Форма записи таблицы допустимых токов (см. kontur.config.CABLE_TABLE и CABLE_TABLE_3PH)."""

    section: float
    max_current: float
    name: str


class SelectivityResult(TypedDict):
    ok: bool
    issues: list[str]


class ReactiveLossResult(TypedDict):
    reactive_var: float
    apparent_va: float
    tan_phi: float


class LeakageResult(TypedDict):
    current_ma: float
    uzo_ma: int


class CableCalculator:
    """Расчёт кабеля по ПУЭ с учётом cos φ"""

    @staticmethod
    def select_section(current_a: float, phases: int = 1) -> CableSpec:
        """Выбрать кабель по току: однофазный или трёхфазный."""
        if phases == 1:
            table = CABLE_TABLE
        elif phases == 3:
            table = CABLE_TABLE_3PH
        else:
            raise ValueError("phases must be 1 or 3")

        for cable in table:
            if cast(float, cable["max_current"]) >= current_a:
                return cast(CableSpec, cable)
        return cast(CableSpec, table[-1])

    @staticmethod
    def select_breaker(current_a: float) -> int:
        for a in AUTOMAT_STEPS:
            if a >= current_a * BREAKER_SAFETY_FACTOR:
                return a
        return AUTOMAT_STEPS[-1]

    @staticmethod
    def voltage_drop(
        current_a: float,
        length_m: float,
        section_mm2: float,
        voltage: float = 220,
        phases: int = 1,
        cos_phi: float = COS_PHI_DEFAULT,
    ) -> float:
        if section_mm2 <= 0:
            raise ValueError("section_mm2 must be positive")
        if voltage <= 0:
            raise ValueError("voltage must be positive")
        r_per_m = COPPER_RESISTIVITY_OHM_MM2_PER_M / section_mm2  # Ом/м (медь)
        x_per_m = INDUCTIVE_REACTANCE_OHM_PER_M  # Ом/м (индуктивное)
        if phases == 3:
            r = r_per_m * length_m
            x = x_per_m * length_m
            sin_phi = math.sqrt(max(0.0, 1 - cos_phi**2))
            delta_u = math.sqrt(3) * current_a * (r * cos_phi + x * sin_phi)
            return (delta_u * 100) / voltage
        else:
            r = 2 * r_per_m * length_m
            return (current_a * r * cos_phi * 100) / voltage


class SelectivityChecker:
    """Проверка селективности автоматов (B/C/D)"""

    @staticmethod
    def check(main_breaker: int, sub_breakers: list[int]) -> SelectivityResult:
        issues: list[str] = []
        for i, sb in enumerate(sub_breakers):
            idx_main = (
                AUTOMAT_STEPS.index(main_breaker) if main_breaker in AUTOMAT_STEPS else len(AUTOMAT_STEPS) - 1
            )
            idx_sub = AUTOMAT_STEPS.index(sb) if sb in AUTOMAT_STEPS else 0
            if idx_main - idx_sub < 1:
                issues.append(f"Автомат №{i + 1} ({sb}А) не селективен с вводным ({main_breaker}А)")
        return {"ok": len(issues) == 0, "issues": issues}

    @staticmethod
    def check_curve(main_curve: str, sub_curve: str, main_breaker: int, sub_breaker: int) -> bool:
        """Проверка селективности по характеристике B/C/D"""
        curve_order = {"B": 1, "C": 2, "D": 3}
        if curve_order.get(main_curve, 2) < curve_order.get(sub_curve, 2):
            return False
        return not main_breaker < sub_breaker * SELECTIVITY_CURRENT_RATIO


class LeakageCalculator:
    """Расчёт утечек тока и подбор УЗО по СП 256"""

    @staticmethod
    def calc(devices: list[Device], cable_lengths: list[float] | None = None) -> LeakageResult:
        device_leakage = 0.0
        for dev in devices:
            cat = dev.category
            if cat in ("it", "power", "ups"):
                device_leakage += LEAKAGE_IT_MA
            elif cat in ("lighting", "hvac"):
                device_leakage += LEAKAGE_HVAC_LIGHTING_MA
            else:
                device_leakage += LEAKAGE_OTHER_MA

        cable_leakage = 0.0
        if cable_lengths:
            for length in cable_lengths:
                cable_leakage += length * LEAKAGE_PER_CABLE_METER_MA

        total = device_leakage + cable_leakage
        if total <= LEAKAGE_LOW_THRESHOLD_MA:
            uzo = LEAKAGE_UZO_LOW_MA
        elif total <= LEAKAGE_MID_THRESHOLD_MA:
            uzo = LEAKAGE_UZO_MID_MA
        else:
            uzo = LEAKAGE_UZO_HIGH_MA

        return {"current_ma": round(total, 2), "uzo_ma": uzo}


class ReactiveLossCalculator:
    """Расчёт реактивных потерь (X/R, cos φ)"""

    @staticmethod
    def calc(active_power_w: float, cos_phi: float = COS_PHI_DEFAULT) -> ReactiveLossResult:
        if cos_phi >= 1.0:
            return {"reactive_var": 0, "apparent_va": active_power_w, "tan_phi": 0}
        if cos_phi <= 0:
            raise ValueError("cos_phi must be in (0, 1]")
        sin_phi = math.sqrt(1 - cos_phi**2)
        tan_phi = sin_phi / cos_phi
        reactive_var = active_power_w * tan_phi
        apparent_va = active_power_w / cos_phi
        return {
            "reactive_var": round(reactive_var, 1),
            "apparent_va": round(apparent_va, 1),
            "tan_phi": round(tan_phi, 3),
        }


class PhaseBalancer:
    """Балансировка фаз: LPT-эвристика по расчётному току + локальное улучшение.

    Крупные нагрузки (``power_w >= THREE_PHASE_MIN_POWER_W``) считаются подключёнными
    сразу на три фазы (см. константу) и распределяются поровну между A/B/C — они не
    участвуют в однофазном распределении и не двигаются локальным улучшением.

    Остальные (однофазные) устройства сортируются по убыванию расчётного тока
    (``power_w * DEMAND_FACTORS[category] / PHASE_VOLTAGE_V``, а не по сырой мощности —
    иначе низкоприоритетная, но "тяжёлая" по факту спроса нагрузка может быть
    ошибочно поставлена в конец очереди) и жадно раскладываются по методу LPT
    (Longest Processing Time — на наименее загруженную фазу). После жадного прохода
    выполняется локальное улучшение: пока это строго уменьшает (max - min),
    устройство переносится с самой загруженной фазы на самую разгруженную, либо
    происходит обмен парой устройств между ними. Алгоритм детерминирован: сортировки
    устойчивы, тай-брейки — по порядку фаз A/B/C и по порядку устройств в исходном списке.
    """

    @staticmethod
    def _current_a(dev: Device) -> float:
        """Расчётный ток устройства при однофазном подключении, А."""
        factor = DEMAND_FACTORS.get(dev.category, 0.7)
        return dev.power_w * factor / PHASE_VOLTAGE_V

    @staticmethod
    def _distribute(devices: list[Device]) -> tuple[dict[str, list[Device]], list[Device]]:
        """Разложить устройства на однофазные "корзины" A/B/C и список трёхфазных."""
        single = [d for d in devices if 0 < d.power_w < THREE_PHASE_MIN_POWER_W]
        three_phase = [d for d in devices if d.power_w >= THREE_PHASE_MIN_POWER_W]

        # Устойчивая сортировка сохраняет исходный порядок устройств при равенстве
        # токов — это и даёт детерминированный тай-брейк "по порядку устройств".
        sorted_single = sorted(single, key=PhaseBalancer._current_a, reverse=True)

        loads: dict[str, float] = {p: 0.0 for p in PHASE_ORDER}
        buckets: dict[str, list[Device]] = {p: [] for p in PHASE_ORDER}
        for dev in sorted_single:
            target = min(PHASE_ORDER, key=lambda p: loads[p])
            buckets[target].append(dev)
            loads[target] += PhaseBalancer._current_a(dev)

        PhaseBalancer._improve(buckets, loads)
        return buckets, three_phase

    @staticmethod
    def _improve(buckets: dict[str, list[Device]], loads: dict[str, float]) -> None:
        """Локальный поиск: перенос/обмен устройством между самой загруженной и самой
        разгруженной фазой, если это строго уменьшает (max - min). Останавливается,
        когда улучшений больше нет, либо по достижении лимита итераций.
        """
        for _ in range(MAX_BALANCE_IMPROVEMENT_ITERATIONS):
            max_p = max(PHASE_ORDER, key=lambda p: loads[p])
            min_p = min(PHASE_ORDER, key=lambda p: loads[p])
            if max_p == min_p:
                break
            other = next(p for p in PHASE_ORDER if p not in (max_p, min_p))
            current_diff = loads[max_p] - loads[min_p]
            if current_diff <= 1e-9:
                break

            best_diff = current_diff
            best_action: tuple[str, int, int] | None = None

            # Перенос одного устройства с max_p на min_p.
            for i, dev in enumerate(buckets[max_p]):
                c = PhaseBalancer._current_a(dev)
                new_max = loads[max_p] - c
                new_min = loads[min_p] + c
                diff = max(new_max, new_min, loads[other]) - min(new_max, new_min, loads[other])
                if diff < best_diff - 1e-9:
                    best_diff = diff
                    best_action = ("move", i, -1)

            # Обмен парой устройств между max_p и min_p.
            for i, dev_max in enumerate(buckets[max_p]):
                c_max = PhaseBalancer._current_a(dev_max)
                for j, dev_min in enumerate(buckets[min_p]):
                    c_min = PhaseBalancer._current_a(dev_min)
                    new_max = loads[max_p] - c_max + c_min
                    new_min = loads[min_p] - c_min + c_max
                    diff = max(new_max, new_min, loads[other]) - min(new_max, new_min, loads[other])
                    if diff < best_diff - 1e-9:
                        best_diff = diff
                        best_action = ("swap", i, j)

            if best_action is None:
                break

            kind, i, j = best_action
            if kind == "move":
                dev = buckets[max_p].pop(i)
                c = PhaseBalancer._current_a(dev)
                loads[max_p] -= c
                loads[min_p] += c
                buckets[min_p].append(dev)
            else:
                dev_max = buckets[max_p][i]
                dev_min = buckets[min_p][j]
                c_max = PhaseBalancer._current_a(dev_max)
                c_min = PhaseBalancer._current_a(dev_min)
                buckets[max_p][i], buckets[min_p][j] = dev_min, dev_max
                loads[max_p] += c_min - c_max
                loads[min_p] += c_max - c_min

    @staticmethod
    def assign(devices: list[Device]) -> dict[str, list[str]]:
        """Распределить устройства по фазам, вернув id устройств на A/B/C.

        Трёхфазные устройства (см. THREE_PHASE_MIN_POWER_W) перечислены под ключом
        "ABC" — они подключены сразу на все три фазы и не привязаны к одной из них.
        """
        buckets, three_phase = PhaseBalancer._distribute(devices)
        result: dict[str, list[str]] = {p: [d.id for d in buckets[p]] for p in PHASE_ORDER}
        result["ABC"] = [d.id for d in three_phase]
        return result

    @staticmethod
    def balance(devices: list[Device]) -> dict[str, float]:
        buckets, three_phase = PhaseBalancer._distribute(devices)
        phases: dict[str, float] = {p: 0.0 for p in PHASE_ORDER}
        for p in PHASE_ORDER:
            for dev in buckets[p]:
                phases[p] += PhaseBalancer._current_a(dev)
        # Трёхфазная нагрузка делится поровну между фазами: в той же модели тока
        # (I = P*k/U_phase, без учёта cos φ), симметричный ток на фазу — P*k/(3*U_phase).
        for dev in three_phase:
            share = PhaseBalancer._current_a(dev) / 3
            for p in PHASE_ORDER:
                phases[p] += share
        return {k: round(v, 1) for k, v in phases.items()}

    @staticmethod
    def imbalance_pct(phases: dict[str, float]) -> float:
        vals = list(phases.values())
        if not vals or all(v == 0 for v in vals):
            return 0.0
        max_v = max(vals)
        min_v = min(vals)
        return round((max_v - min_v) / max_v * 100, 1)
