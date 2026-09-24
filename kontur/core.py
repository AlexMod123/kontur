"""КОНТУР-ПРО: модуль core."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import cast

from kontur.calculators import (
    AcousticCalculator,
    CableCalculator,
    CoolingCalculator,
    GroundCalculator,
    HeatLossCalculator,
    LANCalculator,
    LeakageCalculator,
    LightingCalculator,
    LightningProtection,
    PhaseBalancer,
    ReactiveLossCalculator,
    SelectivityChecker,
    ShortCircuitCalculator,
    VentilationCalculator,
)
from kontur.config import (
    CATEGORIES,
    COS_PHI_DEFAULT,
    DEMAND_FACTORS,
    GROUND_R_MAX,
    GROUND_R_WARN,
    PHASE_IMBALANCE_MAX,
    PRICE_LIST,
    TIER_CONFIG,
    VOLTAGE_DROP_MAX,
    VOLTAGE_DROP_WARN,
)
from kontur.models import CableTrace, Device, EngineeringResult, Room
from kontur.routing import AStarRouter
from kontur.scale import ScaleManager

# ============================================================================
# СЕКЦИЯ 16: ИНЖЕНЕРНОЕ ЯДРО (полный расчёт v18)
# ============================================================================

#: Позиция электрощита по умолчанию (px), от которой считаются длины трасс.
DEFAULT_PANEL_POS: tuple[int, int] = (25, 25)

#: Параметры сети для расчёта падения напряжения (3-фазная сеть 380 В).
THREE_PHASE_VOLTAGE_V = 380
PHASE_COUNT_THREE = 3

#: Мощность одного силового модуля ИБП (Вт), по которой считается их количество.
UPS_MODULE_POWER_W = 5000
#: Ёмкость одного батарейного блока АКБ (Вт·ч): 12 В x 100 А·ч.
UPS_BATTERY_BLOCK_WH = 1200
#: КПД инвертора ИБП при разряде АКБ (проектное допущение).
UPS_INVERTER_EFFICIENCY = 0.9
#: Доля номинальной ёмкости АКБ, реально доступная при 10-15-минутном разряде
#: (проектное допущение — при коротких/интенсивных разрядах отдаваемая
#: ёмкость АКБ меньше номинальной, заявленной при 10/20-часовом разряде).
UPS_BATTERY_USABLE_FRACTION = 0.8

#: Число вводных потребителей, по которым проверяется селективность автоматов.
SELECTIVITY_SAMPLE_SIZE = 10
SINGLE_PHASE_VOLTAGE_V = 220

#: Порог тока утечки (мА), после которого выдаётся рекомендация по УЗО.
LEAKAGE_WARNING_MA = 25

#: Масштаб перевода суммарной площади/периметра в условные единицы (СО-153).
LIGHTNING_GEOMETRY_SCALE = 10
DEFAULT_ROOM_HEIGHT_M = 3.0

#: Объём помещения по умолчанию (м3), если помещения не заданы (для акустики).
DEFAULT_ROOM_VOLUME_M3 = 100.0

#: Запас на подъём/спуск кабельной трассы от устройства до потолка/лотка (м).
VERTICAL_RISE_MARGIN_M = 1.0

DEFAULT_AVG_CABLE_LENGTH_M = 50.0

RouterFactory = Callable[[], AStarRouter]


class EngineeringCore:
    """Полный инженерный расчёт: конвейер из ~15 инженерных калькуляторов."""

    def __init__(
        self,
        devices: list[Device],
        rooms: list[Room],
        tier: int = 1,
        scale_manager: ScaleManager | None = None,
        router_factory: RouterFactory = AStarRouter,
    ) -> None:
        """Инициализация ядра расчёта.

        Args:
            devices: Список устройств проекта.
            rooms: Список помещений проекта.
            tier: Уровень отказоустойчивости (1..3, влияет на резерв ИБП).
            scale_manager: Менеджер масштаба px<->м (по умолчанию новый ScaleManager).
            router_factory: Фабрика роутера трассировки кабеля (по умолчанию AStarRouter).
        """
        self.devices = devices
        self.rooms = rooms
        self.tier = tier
        self.scale = scale_manager or ScaleManager()
        self.router_factory = router_factory
        self.panel_pos = DEFAULT_PANEL_POS

        # Конвейер шагов расчёта. Каждый шаг читает self.devices/self.rooms и
        # уже заполненные поля result, дополняя result своей частью данных.
        self._steps: list[Callable[[EngineeringResult], None]] = [
            self._step_power_demand,
            self._step_phases,
            self._step_cable_and_breaker,
            self._step_grounding,
            self._step_climate,
            self._step_ups,
            self._step_selectivity,
            self._step_short_circuit,
            self._step_leakage,
            self._step_lightning,
            self._step_lighting,
            self._step_lan,
            self._step_heat_loss,
            self._step_acoustics,
            self._step_routing,
            self._step_cost,
            self._step_recommendations,
        ]

    def calculate(self) -> EngineeringResult:
        """Выполнить полный расчёт и вернуть заполненный EngineeringResult."""
        result = EngineeringResult()
        result.device_count = len(self.devices)
        result.room_count = len(self.rooms)
        result.cos_phi = COS_PHI_DEFAULT

        for step in self._steps:
            step(result)

        return result

    # -- вспомогательные (чистые) функции ----------------------------------

    def _demand_power_w(self) -> float:
        """Расчётная мощность с учётом коэффициентов спроса по категориям (не округлена)."""
        return sum(d.power_w * DEMAND_FACTORS.get(d.category, 0.7) for d in self.devices)

    def _avg_cable_length(self) -> float:
        """Средняя длина кабеля от щита до устройств (м), с учётом масштаба."""
        lengths = []
        for dev in self.devices:
            dx = abs(dev.x - self.panel_pos[0])
            dy = abs(dev.y - self.panel_pos[1])
            lengths.append(self.scale.px_to_m(dx + dy))
        return sum(lengths) / len(lengths) if lengths else DEFAULT_AVG_CABLE_LENGTH_M

    def _leakage_cable_lengths(self) -> list[float]:
        """Длины кабелей от щита до каждого устройства (м) для расчёта утечек."""
        return [
            self.scale.px_to_m(abs(d.x - self.panel_pos[0]) + abs(d.y - self.panel_pos[1]))
            for d in self.devices
        ]

    def _room_type(self) -> str:
        """Определить тип помещения (для норм освещённости) по названиям комнат."""
        if any("склад" in r.name.lower() or "зон" in r.name.lower() for r in self.rooms):
            return "storage"
        if any("сервер" in r.name.lower() or "машин" in r.name.lower() for r in self.rooms):
            return "server"
        return "office"

    # -- шаги конвейера -------------------------------------------------

    def _step_power_demand(self, result: EngineeringResult) -> None:
        """Установленная/расчётная мощность и реактивная мощность."""
        installed = sum(d.power_w for d in self.devices)
        demand = self._demand_power_w()
        result.installed_power_w = round(installed, 1)
        result.demand_power_w = round(demand, 1)
        result.active_power_w = round(demand, 1)

        reactive = ReactiveLossCalculator.calc(demand, result.cos_phi)
        result.reactive_power_var = reactive["reactive_var"]

    @staticmethod
    def _design_current_a(phases: dict[str, float], cos_phi: float) -> float:
        """Расчётный ток трёхфазного ввода, А.

        Здание запитано трёхфазно (380/220 В) — расчётным током ввода (по которому
        подбираются вводной автомат и кабель) является ток НАИБОЛЕЕ нагруженной фазы,
        а не сумма токов трёх фаз (сумма его завышает примерно в 3 раза и не имеет
        физического смысла для трёхфазной сети). PhaseBalancer.balance() возвращает
        активные токи по фазам (I = P*k/U_фазное, без учёта cos φ), поэтому
        расчётный (полный) ток получается делением на cos φ. Для идеально
        сбалансированной нагрузки это эквивалентно классической формуле линейного
        тока I = P / (√3 * U_лин * cos φ).
        """
        if not phases:
            return 0.0
        max_phase = max(phases.values())
        if max_phase <= 0:
            return 0.0
        return round(max_phase / cos_phi, 1)

    def _step_phases(self, result: EngineeringResult) -> None:
        """Ток и распределение нагрузки по фазам (жадная балансировка)."""
        phases = PhaseBalancer.balance(self.devices)
        result.per_phase_current = phases
        result.phase_imbalance_pct = PhaseBalancer.imbalance_pct(phases)
        result.total_current_a = self._design_current_a(phases, result.cos_phi)

    def _step_cable_and_breaker(self, result: EngineeringResult) -> None:
        """Вводной автомат, сечение кабеля и падение напряжения."""
        result.recommended_breaker = CableCalculator.select_breaker(result.total_current_a)
        cable = CableCalculator.select_section(result.total_current_a, phases=PHASE_COUNT_THREE)

        # Координация автомат/кабель (ПУЭ 3.1.x): номинал автомата не должен
        # превышать длительно допустимый ток кабеля (I_н.авт <= I_доп). Автомат
        # выбирается с запасом от расчётного тока (BREAKER_SAFETY_FACTOR) и на
        # границах шкалы номиналов может "перепрыгнуть" сечение, подобранное по
        # тому же расчётному току напрямую — в этом случае поднимаем сечение
        # кабеля до первой строки таблицы, выдерживающей ток автомата.
        if result.recommended_breaker > cable["max_current"]:
            cable = CableCalculator.select_section(result.recommended_breaker, phases=PHASE_COUNT_THREE)

        result.recommended_cable = cable["name"]
        result.cable_section = cable["section"]

        avg_length = self._avg_cable_length()
        result.voltage_drop_pct = round(
            CableCalculator.voltage_drop(
                result.total_current_a,
                avg_length,
                result.cable_section,
                voltage=THREE_PHASE_VOLTAGE_V,
                phases=PHASE_COUNT_THREE,
                cos_phi=result.cos_phi,
            ),
            2,
        )

    def _step_grounding(self, result: EngineeringResult) -> None:
        """Сопротивление заземления и его статус."""
        ground = GroundCalculator.calc()
        result.grounding_r = ground["resistance"]
        if result.grounding_r <= GROUND_R_MAX:
            result.grounding_status = "OK"
        elif result.grounding_r <= GROUND_R_WARN:
            result.grounding_status = "WARNING"
        else:
            result.grounding_status = "FAIL"

    def _step_climate(self, result: EngineeringResult) -> None:
        """Требуемое охлаждение и вентиляция."""
        demand = self._demand_power_w()
        people = sum(1 for d in self.devices if d.category == "it")
        room_area = sum(r.area for r in self.rooms)
        result.cooling_required_w = CoolingCalculator.calc(demand, room_area, people)

        room_volume = sum(r.area * r.height_m for r in self.rooms)
        result.ventilation_required_m3h = VentilationCalculator.calc(result.cooling_required_w, room_volume)

    def _step_ups(self, result: EngineeringResult) -> None:
        """Подбор ИБП (мощность, число АКБ, автономия) по уровню Tier.

        Схема резервирования (TIER_CONFIG["ups_scheme"]) определяет:
        - число установленных силовых модулей ИБП относительно расчётного
          минимума (N — без резерва, N+1 — один резервный модуль, 2N — полное
          дублирование мощности);
        - число независимых батарейных линий (N/N+1 — общая батарея, 2N —
          две независимые линии, каждая рассчитана на полную автономию).
        """
        demand = self._demand_power_w()
        tier_cfg = TIER_CONFIG.get(self.tier, TIER_CONFIG[1])
        scheme = cast(str, tier_cfg["ups_scheme"])
        autonomy_target_min = cast(float, tier_cfg["ups_autonomy_target_min"])

        modules_needed = max(1, math.ceil(demand / UPS_MODULE_POWER_W))
        if scheme == "N+1":
            installed_modules = modules_needed + 1
        elif scheme == "2N":
            installed_modules = modules_needed * 2
        else:
            installed_modules = modules_needed
        result.ups_power_w = installed_modules * UPS_MODULE_POWER_W

        battery_lines = 2 if scheme == "2N" else 1
        usable_wh_per_wh = UPS_INVERTER_EFFICIENCY * UPS_BATTERY_USABLE_FRACTION
        required_energy_wh = demand * autonomy_target_min / 60 / usable_wh_per_wh if demand > 0 else 0.0
        blocks_per_line = max(1, math.ceil(required_energy_wh / UPS_BATTERY_BLOCK_WH))
        result.ups_battery_count = blocks_per_line * battery_lines
        result.ups_autonomy_min = (
            round(blocks_per_line * UPS_BATTERY_BLOCK_WH * usable_wh_per_wh / demand * 60, 1)
            if demand > 0
            else 0
        )

    def _step_selectivity(self, result: EngineeringResult) -> None:
        """Проверка селективности вводного и групповых автоматов."""
        sub_breakers = [
            CableCalculator.select_breaker(
                d.power_w * DEMAND_FACTORS.get(d.category, 0.7) / SINGLE_PHASE_VOLTAGE_V
            )
            for d in self.devices[:SELECTIVITY_SAMPLE_SIZE]
            if d.power_w > 0
        ]
        sel = SelectivityChecker.check(result.recommended_breaker, sub_breakers)
        result.selectivity_ok = sel["ok"]

    def _step_short_circuit(self, result: EngineeringResult) -> None:
        """Токи короткого замыкания (3-фазный, 1-фазный, ударный)."""
        avg_length = self._avg_cable_length()
        result.short_circuit_3ph = ShortCircuitCalculator.calc_3phase(avg_length, result.cable_section)
        result.short_circuit_1ph = ShortCircuitCalculator.calc_1phase(avg_length, result.cable_section)
        result.short_circuit_iudar = ShortCircuitCalculator.calc_iudar(result.short_circuit_3ph)

    def _step_leakage(self, result: EngineeringResult) -> None:
        """Суммарный ток утечки и рекомендуемое УЗО."""
        cable_lengths = self._leakage_cable_lengths()
        leakage = LeakageCalculator.calc(self.devices, cable_lengths)
        result.leakage_current_ma = leakage["current_ma"]
        result.leakage_uzo_ma = leakage["uzo_ma"]

    def _step_lightning(self, result: EngineeringResult) -> None:
        """Зона и риск молниезащиты по геометрии здания."""
        total_area = sum(r.area for r in self.rooms)
        total_w = sum(r.width for r in self.rooms)
        max_height = max((r.height_m for r in self.rooms), default=DEFAULT_ROOM_HEIGHT_M)
        lightning = LightningProtection.assess(
            total_area / LIGHTNING_GEOMETRY_SCALE, total_w / LIGHTNING_GEOMETRY_SCALE, max_height
        )
        result.lightning_zone = lightning["zone"]
        result.lightning_risk = lightning["risk"]

    def _step_lighting(self, result: EngineeringResult) -> None:
        """Нормируемая освещённость и число светильников."""
        if not self.rooms:
            return
        room_type = self._room_type()
        light = LightingCalculator.calc(self.rooms[0].area, room_type, self.rooms[0].height_m)
        result.lighting_lux = light["lux"]
        result.lighting_lamps = sum(
            LightingCalculator.calc(r.area, room_type, r.height_m)["lamps"] for r in self.rooms
        )

    def _step_lan(self, result: EngineeringResult) -> None:
        """ЛВС/СКС — порты, длина кабеля, бюджет PoE."""
        lan = LANCalculator.calc(self.devices, self.scale)
        result.lan_ports = lan["total_ports"]
        result.lan_cable_m = lan["cable_m"]
        result.poe_required_w = lan["poe_required_w"]
        result.poe_budget_w = lan["poe_budget_w"]

    def _step_heat_loss(self, result: EngineeringResult) -> None:
        """Теплопотери здания."""
        result.heat_loss_w = HeatLossCalculator.calc(self.rooms)

    def _step_acoustics(self, result: EngineeringResult) -> None:
        """Уровень шума от оборудования."""
        room_vol = sum(r.area * r.height_m for r in self.rooms) if self.rooms else DEFAULT_ROOM_VOLUME_M3
        result.noise_level_db = AcousticCalculator.calc(self.devices, room_vol)

    def _step_routing(self, result: EngineeringResult) -> None:
        """Трассировка кабеля от щита к устройствам (A*)."""
        router = self.router_factory()
        for room in self.rooms:
            router.add_wall(room.x, room.y, room.x + room.width, room.y)
            router.add_wall(room.x, room.y + room.height, room.x + room.width, room.y + room.height)

        for dev in self.devices:
            path = router.find_path(self.panel_pos, (dev.x, dev.y))
            trace = CableTrace(
                device_id=dev.id,
                path=path,
                system=cast(str, CATEGORIES.get(dev.category, {}).get("trace_key", "power")).replace(
                    "trace_", ""
                ),
            )
            trace.length_m = self.scale.px_to_m(
                sum(
                    math.sqrt((path[i + 1][0] - path[i][0]) ** 2 + (path[i + 1][1] - path[i][1]) ** 2)
                    for i in range(len(path) - 1)
                )
            )
            trace.vertical_length = dev.z + VERTICAL_RISE_MARGIN_M  # подъём от пола + спуск к устройству
            result.cable_traces.append(trace)

    def _step_cost(self, result: EngineeringResult) -> None:
        """Смета — суммарная стоимость оборудования."""
        result.cost_total = self._calc_cost()

    def _step_recommendations(self, result: EngineeringResult) -> None:
        """Итоговые рекомендации по результатам всех расчётов."""
        result.recommendations = self._generate_recommendations(result)

    # -- финальные агрегаторы, использующие уже заполненный result --------

    def _generate_recommendations(self, r: EngineeringResult) -> list[str]:
        """Сформировать список текстовых рекомендаций по итогам расчёта."""
        recs = []
        if r.voltage_drop_pct > VOLTAGE_DROP_MAX:
            recs.append(
                f"Падение напряжения {r.voltage_drop_pct}% > {VOLTAGE_DROP_MAX}%. Увеличьте сечение кабеля."
            )
        elif r.voltage_drop_pct > VOLTAGE_DROP_WARN:
            recs.append(
                f"Падение напряжения {r.voltage_drop_pct}% — выше рекомендуемого {VOLTAGE_DROP_WARN}%."
            )
        if r.phase_imbalance_pct > PHASE_IMBALANCE_MAX:
            recs.append(
                f"Перекос фаз {r.phase_imbalance_pct}% > {PHASE_IMBALANCE_MAX}%. Перераспределите нагрузку."
            )
        if r.grounding_status == "FAIL":
            recs.append(
                f"Сопротивление заземления {r.grounding_r} Ом > {GROUND_R_WARN} Ом. Добавьте электроды."
            )
        if not r.selectivity_ok:
            recs.append("Нарушена селективность автоматов. Увеличьте номинал вводного автомата.")
        if r.cooling_required_w > 0:
            recs.append(f"Требуется охлаждение: {r.cooling_required_w / 1000:.1f} кВт.")
        if r.ups_power_w > 0:
            tier_cfg = TIER_CONFIG.get(self.tier, TIER_CONFIG[1])
            scheme = cast(str, tier_cfg["ups_scheme"])
            autonomy_target_min = cast(float, tier_cfg["ups_autonomy_target_min"])
            recs.append(
                f"ИБП: {r.ups_power_w / 1000:.1f} кВт (схема {scheme}), автономия {r.ups_autonomy_min} мин."
            )
            # По построению (см. _step_ups) автономия всегда >= целевой, но
            # проверка оставлена на случай ручного изменения result.
            if r.ups_autonomy_min < autonomy_target_min:
                recs.append(
                    f"Автономия ИБП {r.ups_autonomy_min} мин ниже целевой "
                    f"{autonomy_target_min} мин для схемы {scheme}. Добавьте АКБ."
                )
        if r.poe_required_w > r.poe_budget_w and r.poe_budget_w > 0:
            recs.append(
                f"PoE-бюджет недостаточен: {r.poe_required_w} Вт > {r.poe_budget_w} Вт. "
                "Добавьте PoE-коммутатор."
            )
        if r.heat_loss_w > 0:
            recs.append(f"Теплопотери здания: {r.heat_loss_w:.0f} Вт.")
        if r.leakage_current_ma > LEAKAGE_WARNING_MA:
            recs.append(f"Утечки {r.leakage_current_ma} мА — установите УЗО {r.leakage_uzo_ma} мА.")
        return recs

    def _calc_cost(self) -> float:
        """Посчитать суммарную стоимость оборудования по прайс-листу."""
        total = 0.0
        for dev in self.devices:
            price = dev.price or cast(float, PRICE_LIST.get(dev.equip_type, 0))
            total += price
        return round(total)
