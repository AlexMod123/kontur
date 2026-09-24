
# ============================================================================
# СЕКЦИЯ 2: МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class Wall:
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    thickness: float = 0.2
    floor: int = 1

@dataclass
class Door:
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    rotation: float = 0.0
    floor: int = 1

@dataclass
class Annotation:
    x: float = 0.0
    y: float = 0.0
    text: str = ""
    floor: int = 1

@dataclass
class Device:
    id: str = ""
    name: str = ""
    category: str = "custom"
    type: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    floor: int = 1
    power_w: float = 0.0
    voltage: int = 220
    phase: str = "A"
    parent_panel: str = ""
    vendor: str = ""
    cost: float = 0.0
    cable_section: float = 0.0
    cable_length: float = 0.0
    vertical_length: float = 0.0
    breaker_rating: float = 0.0
    breaker_type: str = "C"
    designation: str = ""
    uzo_leakage: float = 0.0
    notes: str = ""
    status: str = "ok"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "category": self.category, "type": self.type,
                "x": self.x, "y": self.y, "z": self.z, "floor": self.floor,
                "power_w": self.power_w, "voltage": self.voltage, "phase": self.phase,
                "parent_panel": self.parent_panel, "vendor": self.vendor, "cost": self.cost,
                "cable_section": self.cable_section, "cable_length": self.cable_length,
                "vertical_length": self.vertical_length, "breaker_rating": self.breaker_rating,
                "breaker_type": self.breaker_type, "designation": self.designation,
                "uzo_leakage": self.uzo_leakage, "notes": self.notes, "status": self.status}

    @staticmethod
    def from_dict(d):
        dev = Device()
        for k, v in d.items():
            if hasattr(dev, k):
                setattr(dev, k, v)
        return dev

@dataclass
class Room:
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0
    floor: int = 1
    area: float = 0.0
    height: float = 3.5
    designation: str = ""

    def to_dict(self):
        return {"name": self.name, "x": self.x, "y": self.y, "w": self.w, "h": self.h,
                "floor": self.floor, "area": self.area, "height": self.height, "designation": self.designation}

    @staticmethod
    def from_dict(d):
        r = Room()
        for k, v in d.items():
            if hasattr(r, k):
                setattr(r, k, v)
        return r

@dataclass
class CableLine:
    id: str = ""
    src: str = ""
    dst: str = ""
    cable_type: str = "ВВГнг(А)-LS"
    section: float = 2.5
    cores: int = 3
    length: float = 0.0
    vertical_length: float = 0.0
    color: str = "#FF4444"
    status: str = "ok"
    label: str = ""
    path: list = field(default_factory=list)

    def to_dict(self):
        return {"id": self.id, "src": self.src, "dst": self.dst, "cable_type": self.cable_type,
                "section": self.section, "cores": self.cores, "length": self.length,
                "vertical_length": self.vertical_length, "color": self.color,
                "status": self.status, "label": self.label, "path": self.path}

    @staticmethod
    def from_dict(d):
        c = CableLine()
        for k, v in d.items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c

@dataclass
class EngineeringResult:
    """Единая структура результатов расчётов"""
    # Электрика
    total_power_w: float = 0.0
    design_power_w: float = 0.0
    total_current_a: float = 0.0
    phase_a_load: float = 0.0
    phase_b_load: float = 0.0
    phase_c_load: float = 0.0
    phase_imbalance: float = 0.0
    main_breaker: float = 0.0
    main_breaker_type: str = "C"
    main_cable_section: float = 0.0
    main_cable_name: str = ""
    voltage_drop: float = 0.0
    # Заземление
    ground_resistance: float = 0.0
    # ОВК
    cooling_load_w: float = 0.0
    # ИБП
    ups_power_w: float = 0.0
    ups_redundancy: str = "N"
    # Освещение
    lighting_lux: float = 0.0
    lighting_lamps: int = 0
    # КЗ
    short_circuit_3ph: float = 0.0
    short_circuit_1ph: float = 0.0
    short_circuit_impulse: float = 0.0
    # Молниезащита
    lightning_height: float = 0.0
    lightning_zone: str = "А"
    # Утечки
    total_leakage_ma: float = 0.0
    uzo_rating: float = 0.0
    uzo_leakage_ma: float = 0.0
    # Селективность
    selectivity_ok: bool = True
    selectivity_details: list = field(default_factory=list)
    # Реактивные потери
    reactive_loss_v: float = 0.0
    reactive_loss_pct: float = 0.0
    power_factor: float = 0.9
    # Теплопотери
    heat_loss_w: float = 0.0
    # Акустика
    noise_level_db: float = 0.0
    # Смета
    total_cost: float = 0.0
    # Проверки
    model_checks: list = field(default_factory=list)
    # Спецификация
    specification: list = field(default_factory=list)


# ============================================================================
# СЕКЦИЯ 3: КАЛЬКУЛЯТОРЫ
# ============================================================================

class CableCalculator:
    """Подбор сечений кабеля по ПУЭ"""

    @staticmethod
    def select_section(current_a: float, material: str = "cu") -> Tuple[float, str]:
        """Подбор сечения по допустимому току"""
        for row in CABLE_TABLE:
            if row["max_current"] >= current_a:
                return row["section"], row["name"]
        return 240.0, "ВВГнг(А)-LS 3x240"

    @staticmethod
    def select_breaker(current_a: float) -> float:
        """Подбор номинала автомата"""
        for rating in AUTOMAT_STEPS:
            if rating >= current_a:
                return float(rating)
        return 250.0

    @staticmethod
    def voltage_drop_v(power_w: float, length_m: float, section_mm2: float,
                       voltage: int = 220, cos_phi: float = 0.9, phases: int = 1) -> float:
        """Падение напряжения в вольтах с учётом cos ф и количества фаз"""
        if section_mm2 <= 0 or length_m <= 0:
            return 0.0
        current = power_w / (voltage * cos_phi * math.sqrt(phases)) if phases > 1 else power_w / (voltage * cos_phi)
        # Активная составляющая
        r = CU_RESISTIVITY * length_m / section_mm2
        drop_active = current * r
        # Реактивная составляющая
        x = CABLE_REACTANCE.get(section_mm2, 0.08) * length_m / 1000
        sin_phi = math.sqrt(1 - cos_phi**2)
        drop_reactive = current * x * sin_phi
        drop = drop_active * cos_phi + drop_reactive * sin_phi
        if phases == 3:
            drop = drop * math.sqrt(3)
        return drop

    @staticmethod
    def voltage_drop_pct(power_w: float, length_m: float, section_mm2: float,
                          voltage: int = 220, cos_phi: float = 0.9, phases: int = 1) -> float:
        """Падение напряжения в процентах"""
        if voltage <= 0:
            return 0.0
        drop_v = CableCalculator.voltage_drop_v(power_w, length_m, section_mm2, voltage, cos_phi, phases)
        return (drop_v / voltage) * 100.0


class PhaseBalancer:
    """Жадная балансировка фаз (сортировка по убыванию мощности)"""

    @staticmethod
    def balance(devices: List[Device]) -> Dict[str, List[Device]]:
        """Распределение устройств по фазам A/B/C жадным алгоритмом"""
        phases = {"A": [], "B": [], "C": []}
        loads = {"A": 0.0, "B": 0.0, "C": 0.0}

        # Только 220В устройства балансируются; 380В — на все фазы
        single_phase = [d for d in devices if d.voltage == 220 and d.power_w > 0]
        single_phase.sort(key=lambda d: d.power_w, reverse=True)

        for dev in single_phase:
            min_phase = min(loads, key=lambda k: loads[k])
            phases[min_phase].append(dev)
            loads[min_phase] += dev.power_w
            dev.phase = min_phase

        # 380В устройства — на фазу A (условно)
        for dev in devices:
            if dev.voltage == 380 and dev.power_w > 0:
                dev.phase = "ABC"

        return phases

    @staticmethod
    def imbalance(devices: List[Device]) -> float:
        """Расчёт перекоса фаз в процентах"""
        loads = {"A": 0.0, "B": 0.0, "C": 0.0}
        for d in devices:
            if d.voltage == 220 and d.power_w > 0:
                if d.phase in loads:
                    loads[d.phase] += d.power_w
            elif d.voltage == 380 and d.power_w > 0:
                # Распределяем поровну
                for ph in loads:
                    loads[ph] += d.power_w / 3.0
        avg = sum(loads.values()) / 3.0
        if avg <= 0:
            return 0.0
        max_dev = max(abs(loads[ph] - avg) for ph in loads)
        return (max_dev / avg) * 100.0


class ShortCircuitCalculator:
    """Расчёт токов КЗ по ГОСТ 28249-93"""

    @staticmethod
    def calc_3phase(uf: float = 380, rk: float = 0.05, xk: float = 0.01,
                     zk: float = 0.0) -> float:
        """Трёхфазный ток КЗ"""
        if zk > 0:
            z = zk
        else:
            z = math.sqrt(rk**2 + xk**2)
        if z <= 0:
            return 0.0
        return uf / (math.sqrt(3) * z)

    @staticmethod
    def calc_1phase(uf: float = 220, r0: float = 0.1, x0: float = 0.02,
                     r1: float = 0.05, x1: float = 0.01) -> float:
        """Однофазный ток КЗ"""
        z1 = math.sqrt(r1**2 + x1**2)
        z0 = math.sqrt(r0**2 + x0**2)
        z_total = math.sqrt((r1 + r0)**2 + (x1 + x0)**2)
        if z_total <= 0:
            return 0.0
        return uf / z_total

    @staticmethod
    def impulse_current(i_k3: float, kud: float = 1.5) -> float:
        """Ударный ток КЗ"""
        return i_k3 * math.sqrt(2) * kud

    @staticmethod
    def check_breaker(i_k: float, breaker_rating: float) -> bool:
        """Проверка отключающей способности автомата"""
        return i_k > breaker_rating * 10  # Отключающая способность > 10x номинала


class LightningProtection:
    """Расчёт молниезащиты по СО 153-34.21.122-2003"""

    @staticmethod
    def calc_height(building_h: float, building_w: float, building_l: float,
                    zone: str = "А") -> Tuple[float, str]:
        """Расчёт высоты молниеотвода"""
        # Радиус защиты на уровне крыши
        r_needed = max(building_w, building_l) / 2.0
        if zone == "А":
            h = building_h + r_needed / 1.5
        else:
            h = building_h + r_needed / 2.0
        # Минимум 5 м от края
        h = max(h, building_h + 5)
        return h, zone

    @staticmethod
    def zone_type(importance: int = 1) -> str:
        """Определение зоны защиты"""
        if importance <= 1:
            return "А"
        return "Б"


class LeakageCalculator:
    """Расчёт токов утечки и подбор УЗО по СП 256.1325800"""

    @staticmethod
    def calc_leakage(devices: List[Device]) -> float:
        """Суммарный ток утечки в мА"""
        total = 0.0
        for d in devices:
            if d.power_w > 0:
                # 0.4 мА на 1 А тока нагрузки
                current = d.power_w / d.voltage if d.voltage > 0 else 0
                total += current * 0.4
            # 0.1 мА на метр кабеля
            if d.cable_length > 0:
                total += d.cable_length * 0.1
        return total

    @staticmethod
    def select_uzo(leakage_ma: float) -> Tuple[float, float]:
        """Подбор УЗО: (номинальный ток, дифференциальный ток)"""
        # Дифференциальный ток: 3x от расчётной утечки, минимум 30 мА
        diff = max(leakage_ma * 3, 30.0)
        # Номинальный ток УЗО
        return 25.0, diff


class LightingCalculator:
    """Расчёт освещённости по СП 52.13330.2016 (метод коэффициента использования)"""

    @staticmethod
    def calc(room: Room, target_lux: float = 300, lamp_flux: float = 4000,
             utilization_factor: float = 0.6, maintenance_factor: float = 0.8) -> Tuple[int, float]:
        """Расчёт количества светильников и фактической освещённости"""
        if room.area <= 0:
            room.area = room.w * room.h / 10000.0  # w,h в см -> м²
        if room.area <= 0:
            return 0, 0.0
        n = math.ceil((target_lux * room.area) / (lamp_flux * utilization_factor * maintenance_factor))
        if n <= 0:
            n = 1
        actual_lux = (n * lamp_flux * utilization_factor * maintenance_factor) / room.area
        return n, actual_lux


class CableJournal:
    """Кабельный журнал по ГОСТ 21.613-2014"""

    @staticmethod
    def generate(devices: List[Device], cables: List[CableLine]) -> List[Dict]:
        """Формирование кабельного журнала"""
        journal = []
        for cable in cables:
            src_dev = next((d for d in devices if d.id == cable.src), None)
            dst_dev = next((d for d in devices if d.id == cable.dst), None)
            entry = {
                "pos": cable.id,
                "start": src_dev.name if src_dev else cable.src,
                "end": dst_dev.name if dst_dev else cable.dst,
                "cable": f"{cable.cable_type} 3x{cable.section:g}",
                "length": round(cable.length + cable.vertical_length, 1),
                "section": cable.section,
            }
            journal.append(entry)
        return journal


class ExtendedSelectivity:
    """Расширенная проверка селективности B/C/D по ГОСТ IEC 60898-1-2020"""

    @staticmethod
    def check(devices: List[Device]) -> Tuple[bool, List[Dict]]:
        """Проверка селективности автоматов"""
        results = []
        all_ok = True
        for d in devices:
            if d.breaker_rating > 0:
                # Проверка: номинал автомата должен быть >= тока нагрузки
                load_current = d.power_w / d.voltage if d.voltage > 0 else 0
                btype = d.breaker_type if d.breaker_type in ("B", "C", "D") else "C"
                # Характеристика срабатывания
                if btype == "B":
                    min_trip = 3 * d.breaker_rating
                    max_trip = 5 * d.breaker_rating
                elif btype == "C":
                    min_trip = 5 * d.breaker_rating
                    max_trip = 10 * d.breaker_rating
                else:  # D
                    min_trip = 10 * d.breaker_rating
                    max_trip = 20 * d.breaker_rating

                ok = load_current <= d.breaker_rating
                if not ok:
                    all_ok = False
                results.append({
                    "device": d.name,
                    "breaker": f"{btype}{int(d.breaker_rating)}",
                    "load_current": round(load_current, 1),
                    "trip_range": f"{min_trip:g}-{max_trip:g} А",
                    "ok": ok,
                })
        return all_ok, results


class ReactiveLossCalculator:
    """Потери с реактивным сопротивлением (X/R, cos ф)"""

    @staticmethod
    def calc(power_w: float, length_m: float, section_mm2: float,
             cos_phi: float = 0.9, voltage: int = 220) -> Tuple[float, float, float]:
        """Расчёт потерь: (потери_В, потери_%, cos_ф_фактический)"""
        if section_mm2 <= 0 or length_m <= 0 or voltage <= 0:
            return 0.0, 0.0, cos_phi
        current = power_w / (voltage * cos_phi)
        r = CU_RESISTIVITY * length_m / section_mm2
        x = CABLE_REACTANCE.get(section_mm2, 0.08) * length_m / 1000
        sin_phi = math.sqrt(1 - cos_phi**2)
        loss_v = current * (r * cos_phi + x * sin_phi)
        loss_pct = (loss_v / voltage) * 100
        return loss_v, loss_pct, cos_phi


class GroundingCalculator:
    """Расчёт заземления по ПУЭ"""

    @staticmethod
    def calc(vertical_rods: int = 3, rod_length: float = 3.0,
             soil_resistivity: float = 100.0, rod_diameter: float = 0.016) -> float:
        """Расчёт сопротивления заземляющего устройства"""
        if vertical_rods <= 0:
            return float('inf')
        # Сопротивление одиночного стержня
        r_single = (soil_resistivity / (2 * math.pi * rod_length)) * \
                   math.log(2 * rod_length / (0.5 * rod_diameter))
        # Коэффициент использования (упрощённо)
        if vertical_rods == 1:
            return r_single
        util_factor = 1.0 / (1.0 + 0.3 * (vertical_rods - 1))
        return r_single * util_factor / vertical_rods


class CoolingCalculator:
    """Расчёт охлаждения"""

    @staticmethod
    def calc(devices: List[Device], tier: int = 1, area_m2: float = 0) -> float:
        """Требуемая мощность охлаждения в Вт"""
        it_power = sum(d.power_w for d in devices if d.category in ("it", "network", "lan"))
        other_power = sum(d.power_w for d in devices if d.category not in ("it", "network", "lan", "lighting"))
        # ИТ-оборудование: 100% в тепло
        # Прочее: 80% в тепло
        heat_load = it_power + other_power * 0.8
        # Добавляем теплопритоки от помещения (упрощённо: 50 Вт/м²)
        if area_m2 > 0:
            heat_load += area_m2 * 50
        # Коэффициент резервирования по Tier
        redundancy = {"N": 1.0, "N+1": 1.5, "2N": 2.0}
        tier_cfg = TIER_CONFIG.get(tier, TIER_CONFIG[1])
        factor = redundancy.get(tier_cfg["cooling_redundancy"], 1.0)
        return heat_load * factor


class UPSCalculator:
    """Расчёт ИБП"""

    @staticmethod
    def calc(devices: List[Device], tier: int = 1) -> Tuple[float, str]:
        """Требуемая мощность ИБП: (Вт, схема резервирования)"""
        critical_power = sum(d.power_w for d in devices if d.category in ("it", "network", "lan", "camera", "ops", "skud"))
        tier_cfg = TIER_CONFIG.get(tier, TIER_CONFIG[1])
        redundancy = tier_cfg["ups_redundancy"]
        factor = {"N": 1.0, "N+1": 1.5, "2N": 2.0}.get(redundancy, 1.0)
        if not tier_cfg["ups"]:
            return 0.0, "N"
        return critical_power * factor, redundancy


class LANCalculator:
    """Расчёт ЛВС/СКС"""

    @staticmethod
    def calc(devices: List[Device], area_m2: float = 0) -> Dict:
        """Расчёт параметров ЛВС"""
        # Подсчёт портов
        pc_count = sum(1 for d in devices if d.category == "it")
        cam_count = sum(1 for d in devices if d.category == "camera")
        ap_count = sum(1 for d in devices if d.type == "wifi")
        phone_count = sum(1 for d in devices if d.category == "phone")
        # Точки доступа Wi-Fi: 1 на 100 м²
        ap_needed = max(ap_count, math.ceil(area_m2 / 100)) if area_m2 > 0 else ap_count
        # Количество портов коммутатора
        total_ports = pc_count + cam_count + ap_needed + phone_count
        switch_count = math.ceil(total_ports / 48) if total_ports > 0 else 0
        # Длина кабеля СКС (упрощённо: средняя длина 30м на порт)
        cable_length = total_ports * 30
        # PoE бюджет
        poe_devices = cam_count + ap_needed
        poe_power = poe_devices * 15  # 15 Вт на устройство PoE
        poe_ok = poe_power <= POE_BUDGET_W
        return {
            "total_ports": total_ports,
            "switch_count": switch_count,
            "cable_length_m": cable_length,
            "poe_power_w": poe_power,
            "poe_ok": poe_ok,
            "ap_count": ap_needed,
        }


class HeatLossCalculator:
    """Теплопотери по СП 50.13330"""

    @staticmethod
    def calc(rooms: List[Room], outdoor_temp: float = -28.0,
             indoor_temp: float = 22.0, wall_r: float = 3.0,
             window_r: float = 0.6, window_ratio: float = 0.15) -> float:
        """Расчёт теплопотерь здания"""
        total_loss = 0.0
        delta_t = indoor_temp - outdoor_temp
        for room in rooms:
            if room.area <= 0:
                room.area = room.w * room.h / 10000.0
            # Площадь стен (периметр * высота)
            perimeter = 2 * (room.w / 100.0 + room.h / 100.0)  # м
            wall_area = perimeter * room.height
            window_area = wall_area * window_ratio
            solid_wall_area = wall_area - window_area
            # Теплопотери через стены и окна
            q_walls = solid_wall_area * delta_t / wall_r
            q_windows = window_area * delta_t / window_r
            # Вентиляция (0.5 воздухообмена)
            volume = room.area * room.height
            q_vent = 0.5 * volume * 0.33 * delta_t
            total_loss += q_walls + q_windows + q_vent
        return total_loss


class AcousticCalculator:
    """Расчёт уровня шума по СНиП 23-03"""

    @staticmethod
    def calc(devices: List[Device], room_area: float = 50.0) -> float:
        """Расчёт уровня шума от оборудования"""
        # Базовые уровни шума по типам (дБ)
        noise_levels = {
            "server": 55, "rack42u": 60, "ac_5kw": 45, "ac_15kw": 55,
            "switch_l3": 40, "switch_l2": 35, "ups_30": 50, "ups_10": 45,
            "nvr": 35, "turnstile": 50,
        }
        total_power = 0.0
        for d in devices:
            level = noise_levels.get(d.type, 30)
            # Преобразование дБ в мощность звука (10^(L/10))
            total_power += 10 ** (level / 10)
        if total_power <= 0:
            return 30.0
        total_db = 10 * math.log10(total_power)
        # Корректировка на площадь
        if room_area > 0:
            total_db -= 10 * math.log10(max(room_area / 50.0, 0.1))
        return round(total_db, 1)
