
# ============================================================================
# СЕКЦИЯ 11: MODEL CHECKER (35+ ПРОВЕРОК)
# ============================================================================

class ModelChecker:
    """Проверка модели на соответствие нормам: 35+ проверок с цветовой подсветкой"""

    def __init__(self):
        self.checks: List[Dict] = []

    def run_all(self, devices: List[Device], rooms: List[Room],
                result: EngineeringResult) -> List[Dict]:
        self.checks = []
        self._check_power(devices, result)
        self._check_phases(devices, result)
        self._check_voltage_drop(devices, result)
        self._check_cable_sections(devices)
        self._check_grounding(result)
        self._check_cooling(result)
        self._check_ups(devices, result)
        self._check_lighting(devices, rooms, result)
        self._check_short_circuit(result)
        self._check_leakage(devices, result)
        self._check_selectivity(devices, result)
        self._check_lightning(rooms, result)
        self._check_poe(devices)
        self._check_redundancy(result)
        self._check_fire_detectors(devices, rooms)
        self._check_cost(result)
        self._check_heat_loss(result)
        self._check_noise(devices, rooms)
        return self.checks

    def _add(self, name: str, status: str, detail: str = ""):
        colors = {"ok": "#34d399", "warn": "#fbbf24", "fail": "#f87171"}
        self.checks.append({
            "name": name,
            "status": status,
            "color": colors.get(status, "#a0a0b0"),
            "detail": detail,
        })

    def _check_power(self, devices, result):
        if result.total_power_w > 0:
            self._add("Установленная мощность", "ok",
                       f"{result.total_power_w/1000:.1f} кВт")
        else:
            self._add("Установленная мощность", "warn", "Нет оборудования")

    def _check_phases(self, devices, result):
        imb = result.phase_imbalance
        if imb <= PHASE_IMBALANCE_MAX:
            self._add("Перекос фаз", "ok", f"{imb:.1f}% (норма до {PHASE_IMBALANCE_MAX:.0f}%)")
        else:
            self._add("Перекос фаз", "fail", f"{imb:.1f}% > {PHASE_IMBALANCE_MAX:.0f}%")

    def _check_voltage_drop(self, devices, result):
        if result.voltage_drop <= VOLTAGE_DROP_MAX:
            self._add("Падение напряжения", "ok", f"{result.voltage_drop:.2f}% (норма до {VOLTAGE_DROP_MAX:.0f}%)")
        elif result.voltage_drop <= VOLTAGE_DROP_WARN:
            self._add("Падение напряжения", "warn", f"{result.voltage_drop:.2f}% (рекоменд. до {VOLTAGE_DROP_WARN:.0f}%)")
        else:
            self._add("Падение напряжения", "fail", f"{result.voltage_drop:.2f}% > {VOLTAGE_DROP_MAX:.0f}%")

    def _check_cable_sections(self, devices):
        for d in devices:
            if d.power_w > 0 and d.cable_section > 0:
                current = d.power_w / d.voltage if d.voltage > 0 else 0
                ampacity = CABLE_AMPACITY.get(d.cable_section, 0)
                if ampacity >= current:
                    self._add(f"Сечение {d.name}", "ok",
                               f"{d.cable_section:g} мм² ({current:.1f} А)")
                else:
                    self._add(f"Сечение {d.name}", "fail",
                               f"{d.cable_section:g} мм² < {current:.1f} А")

    def _check_grounding(self, result):
        if result.ground_resistance <= GROUND_R_MAX:
            self._add("Заземление", "ok", f"{result.ground_resistance:.2f} Ом (норма до {GROUND_R_MAX:.0f})")
        elif result.ground_resistance <= GROUND_R_WARN:
            self._add("Заземление", "warn", f"{result.ground_resistance:.2f} Ом")
        else:
            self._add("Заземление", "fail", f"{result.ground_resistance:.2f} Ом > {GROUND_R_WARN:.0f}")

    def _check_cooling(self, result):
        if result.cooling_load_w > 0:
            self._add("Охлаждение", "ok", f"{result.cooling_load_w/1000:.1f} кВт")
        else:
            self._add("Охлаждение", "warn", "Не рассчитано")

    def _check_ups(self, devices, result):
        if result.ups_power_w > 0:
            self._add("ИБП", "ok", f"{result.ups_power_w/1000:.1f} кВт ({result.ups_redundancy})")
        else:
            crit = sum(d.power_w for d in devices if d.category in ("it", "network", "lan"))
            if crit > 0:
                self._add("ИБП", "warn", "Нет ИБП для критичной нагрузки")
            else:
                self._add("ИБП", "ok", "Не требуется")

    def _check_lighting(self, devices, rooms, result):
        if result.lighting_lux > 0:
            min_lux = LIGHTING_NORMS.get("office", 300)
            if result.lighting_lux >= min_lux:
                self._add("Освещённость", "ok", f"{result.lighting_lux:.0f} лк")
            else:
                self._add("Освещённость", "warn", f"{result.lighting_lux:.0f} лк < {min_lux}")
        else:
            self._add("Освещённость", "warn", "Не рассчитано")

    def _check_short_circuit(self, result):
        if result.short_circuit_3ph > 0:
            self._add("Ток КЗ 3ф", "ok", f"{result.short_circuit_3ph:.0f} А")
        else:
            self._add("Ток КЗ 3ф", "warn", "Не рассчитано")

    def _check_leakage(self, devices, result):
        if result.total_leakage_ma > 0:
            if result.uzo_leakage_ma >= 30:
                self._add("УЗО", "ok", f"УЗО {result.uzo_leakage_ma:.0f} мА")
            else:
                self._add("УЗО", "warn", f"УЗО {result.uzo_leakage_ma:.0f} мА < 30 мА")
        else:
            self._add("УЗО", "ok", "Нет утечек")

    def _check_selectivity(self, devices, result):
        if result.selectivity_ok:
            self._add("Селективность", "ok", "Все автоматы корректны")
        else:
            self._add("Селективность", "fail", "Есть проблемы с селективностью")

    def _check_lightning(self, rooms, result):
        if result.lightning_height > 0:
            self._add("Молниезащита", "ok",
                       f"h={result.lightning_height:.1f} м (зона {result.lightning_zone})")
        else:
            self._add("Молниезащита", "warn", "Не рассчитано")

    def _check_poe(self, devices):
        poe_count = sum(1 for d in devices if d.category == "camera" or d.type == "wifi")
        if poe_count > 0:
            poe_power = poe_count * 15
            if poe_power <= POE_BUDGET_W:
                self._add("PoE-бюджет", "ok", f"{poe_power} Вт / {POE_BUDGET_W} Вт")
            else:
                self._add("PoE-бюджет", "fail", f"{poe_power} Вт > {POE_BUDGET_W} Вт")

    def _check_redundancy(self, result):
        if result.ups_redundancy in ("N+1", "2N"):
            self._add("Резервирование", "ok", f"{result.ups_redundancy}")
        elif result.ups_redundancy == "N":
            self._add("Резервирование", "warn", "Нет резервирования")

    def _check_fire_detectors(self, devices, rooms):
        smoke_count = sum(1 for d in devices if d.type == "ops_smoke")
        total_area = sum(r.area for r in rooms if r.area > 0)
        if total_area > 0 and smoke_count > 0:
            area_per_detector = total_area / smoke_count
            if area_per_detector <= 85:
                self._add("Дымовые извещатели", "ok",
                           f"{smoke_count} шт, {area_per_detector:.0f} м²/шт (норма до 85)")
            else:
                self._add("Дымовые извещатели", "fail",
                           f"{area_per_detector:.0f} м²/шт > 85 м²")
        else:
            self._add("Дымовые извещатели", "warn", "Недостаточно данных")

    def _check_cost(self, result):
        if result.total_cost > 0:
            self._add("Смета", "ok", f"{result.total_cost:,.0f} ₽")
        else:
            self._add("Смета", "warn", "Не рассчитана")

    def _check_heat_loss(self, result):
        if result.heat_loss_w > 0:
            self._add("Теплопотери", "ok", f"{result.heat_loss_w/1000:.1f} кВт")
        else:
            self._add("Теплопотери", "warn", "Не рассчитано")

    def _check_noise(self, devices, rooms):
        total_area = sum(r.area for r in rooms if r.area > 0) or 50.0
        noise = AcousticCalculator.calc(devices, total_area)
        if noise <= 60:
            self._add("Уровень шума", "ok", f"{noise:.1f} дБ (норма до 60)")
        elif noise <= 80:
            self._add("Уровень шума", "warn", f"{noise:.1f} дБ")
        else:
            self._add("Уровень шума", "fail", f"{noise:.1f} дБ > 80")


# ============================================================================
# СЕКЦИЯ 12: PROJECT MANAGER (.kontur JSON)
# ============================================================================

class ProjectManager:
    """Сохранение и загрузка проектов в формате .kontur (JSON)"""

    def __init__(self):
        self.project_name: str = "Новый проект"
        self.project_data: Dict = {}
        self.autosave_interval: int = 300  # секунд
        self.backup_count: int = 3

    def save(self, filepath: str, devices: List[Device], rooms: List[Room],
             cables: List[CableLine], walls: List[Wall], doors: List[Door],
             annotations: List[Annotation], twin: DigitalTwin,
             scale_manager=None) -> bool:
        """Сохранение проекта"""
        data = {
            "schema_version": SCHEMA_VERSION,
            "version": VERSION,
            "name": self.project_name,
            "saved": datetime.now().isoformat(),
            "devices": [d.to_dict() for d in devices],
            "rooms": [r.to_dict() for r in rooms],
            "cables": [c.to_dict() for c in cables],
            "walls": [{"x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
                       "thickness": w.thickness, "floor": w.floor} for w in walls],
            "doors": [{"x": d.x, "y": d.y, "width": d.width, "rotation": d.rotation,
                       "floor": d.floor} for d in doors],
            "annotations": [{"x": a.x, "y": a.y, "text": a.text, "floor": a.floor}
                            for a in annotations],
            "twin": twin.to_dict(),
        }
        if scale_manager:
            data["scale"] = {"px_per_m": scale_manager.px_per_m}
        self.project_data = data
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, OSError):
            return False

    def load(self, filepath: str) -> Optional[Dict]:
        """Загрузка проекта с миграцией схемы"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

        # Миграция схемы
        old_ver = data.get("schema_version", "1.0")
        if old_ver != SCHEMA_VERSION:
            data = self._migrate(data, old_ver)
        self.project_data = data
        self.project_name = data.get("name", "Загруженный проект")
        return data

    def _migrate(self, data: Dict, old_ver: str) -> Dict:
        """Миграция схемы между версиями"""
        data["schema_version"] = SCHEMA_VERSION
        if "z" not in str(data.get("devices", [])):
            for d in data.get("devices", []):
                if "z" not in d:
                    d["z"] = 0.0
        if "vertical_length" not in str(data.get("devices", [])):
            for d in data.get("devices", []):
                if "vertical_length" not in d:
                    d["vertical_length"] = 0.0
        return data

    @staticmethod
    def restore(data: Dict) -> Tuple[List[Device], List[Room], List[CableLine],
                                      List[Wall], List[Door], List[Annotation], DigitalTwin]:
        """Восстановление объектов из загруженных данных"""
        devices = [Device.from_dict(d) for d in data.get("devices", [])]
        rooms = [Room.from_dict(r) for r in data.get("rooms", [])]
        cables = [CableLine.from_dict(c) for c in data.get("cables", [])]
        walls = [Wall(x1=w["x1"], y1=w["y1"], x2=w["x2"], y2=w["y2"],
                      thickness=w.get("thickness", 0.2), floor=w.get("floor", 1))
                 for w in data.get("walls", [])]
        doors = [Door(x=d["x"], y=d["y"], width=d.get("width", 1.0),
                     rotation=d.get("rotation", 0), floor=d.get("floor", 1))
                for d in data.get("doors", [])]
        annotations = [Annotation(x=a["x"], y=a["y"], text=a.get("text", ""),
                                  floor=a.get("floor", 1))
                       for a in data.get("annotations", [])]
        twin = DigitalTwin.from_dict(data.get("twin", {"nodes": {}, "edges": []}))
        return devices, rooms, cables, walls, doors, annotations, twin


# ============================================================================
# СЕКЦИЯ 13: DXF IMPORTER
# ============================================================================

class DXFImporter:
    """Импорт DXF из AutoCAD/nanoCAD через ezdxf"""

    @staticmethod
    def import_dxf(filepath: str) -> Tuple[List[Wall], List[Door],
                                            List[Device], List[Room], List[Annotation]]:
        """Импорт DXF файла"""
        walls = []
        doors = []
        devices = []
        rooms = []
        annotations = []

        try:
            import ezdxf
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()

            for entity in msp:
                etype = entity.dxftype()

                if etype == "LINE":
                    walls.append(Wall(
                        x1=float(entity.dxf.start.x), y1=float(entity.dxf.start.y),
                        x2=float(entity.dxf.end.x), y2=float(entity.dxf.end.y),
                        thickness=0.2
                    ))

                elif etype == "ARC":
                    doors.append(Door(
                        x=float(entity.dxf.center.x),
                        y=float(entity.dxf.center.y),
                        width=float(entity.dxf.radius) * 2
                    ))

                elif etype == "CIRCLE":
                    devices.append(Device(
                        id=f"dxf_{len(devices)}",
                        name=f"DXF_{len(devices)}",
                        x=float(entity.dxf.center.x),
                        y=float(entity.dxf.center.y)
                    ))

                elif etype == "LWPOLYLINE":
                    pts = entity.get_points()
                    if len(pts) >= 2:
                        cx = sum(p[0] for p in pts) / len(pts)
                        cy = sum(p[1] for p in pts) / len(pts)
                        w = max(p[0] for p in pts) - min(p[0] for p in pts)
                        h = max(p[1] for p in pts) - min(p[1] for p in pts)
                        rooms.append(Room(name=f"DXF_{len(rooms)}", x=min(p[0] for p in pts),
                                         y=min(p[1] for p in pts), w=w, h=h))

                elif etype == "TEXT":
                    annotations.append(Annotation(
                        x=float(entity.dxf.insert.x),
                        y=float(entity.dxf.insert.y),
                        text=entity.dxf.text or ""
                    ))

                elif etype == "INSERT":
                    block_name = entity.dxf.name.upper()
                    x = float(entity.dxf.insert.x)
                    y = float(entity.dxf.insert.y)
                    mapped = False
                    for eq_id, eq in EQUIPMENT_BY_ID.items():
                        if eq_id.upper() in block_name or eq["name"].upper() in block_name:
                            devices.append(Device(
                                id=f"dxf_{len(devices)}", name=eq["name"], type=eq_id,
                                category=eq["category"], x=x, y=y,
                                power_w=eq["power_w"], voltage=eq["voltage"]
                            ))
                            mapped = True
                            break
                    if not mapped:
                        if "LOCK" in block_name or "ДВЕРЬ" in block_name:
                            doors.append(Door(x=x, y=y))

        except ImportError:
            pass
        except Exception:
            pass

        return walls, doors, devices, rooms, annotations


# ============================================================================
# СЕКЦИЯ 14: SCALE MANAGER (ПИКСЕЛЬ-МЕТР)
# ============================================================================

class ScaleManager:
    """Управление масштабом пиксель-метр"""

    def __init__(self, px_per_m: float = 50.0):
        self.px_per_m = px_per_m

    def px_to_m(self, px: float) -> float:
        return px / self.px_per_m

    def m_to_px(self, m: float) -> float:
        return m * self.px_per_m

    def area_m2(self, w_px: float, h_px: float) -> float:
        return (w_px / self.px_per_m) * (h_px / self.px_per_m)

    def length_m(self, px: float) -> float:
        return px / self.px_per_m

    def cable_length_m(self, path: List[Tuple[float, float]]) -> float:
        if len(path) < 2:
            return 0.0
        total_px = 0.0
        for i in range(1, len(path)):
            dx = path[i][0] - path[i-1][0]
            dy = path[i][1] - path[i-1][1]
            total_px += math.hypot(dx, dy)
        return total_px / self.px_per_m

    def set_scale(self, px_per_m: float):
        self.px_per_m = max(1.0, px_per_m)


# ============================================================================
# СЕКЦИЯ 15: EXTERNAL CATALOG
# ============================================================================

class ExternalCatalog:
    """Внешний каталог оборудования (catalog.json)"""

    def __init__(self, filepath: str = "catalog.json"):
        self.filepath = filepath
        self.items: List[Dict] = []

    def load(self) -> bool:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.items = json.load(f)
            return True
        except (IOError, json.JSONDecodeError):
            return False

    def save(self) -> bool:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, OSError):
            return False

    def add(self, item: Dict) -> bool:
        self.items.append(item)
        return self.save()

    def search(self, query: str) -> List[Dict]:
        q = query.lower()
        return [i for i in self.items if q in i.get("name", "").lower() or q in i.get("id", "").lower()]

    def import_csv(self, filepath: str) -> int:
        """Импорт прайс-листа из CSV"""
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.items.append({
                        "id": row.get("id", f"ext_{count}"),
                        "name": row.get("name", ""),
                        "price": float(row.get("price", 0)),
                        "category": row.get("category", "custom"),
                        "power_w": float(row.get("power_w", 0)),
                        "voltage": int(row.get("voltage", 220)),
                    })
                    count += 1
        except (IOError, csv.Error, ValueError):
            pass
        return count


# ============================================================================
# СЕКЦИЯ 16: MULTI PROJECT MANAGER
# ============================================================================

class MultiProjectManager:
    """Управление несколькими проектами, сравнение по метрикам"""

    def __init__(self):
        self.projects: Dict[str, Dict] = {}

    def add_project(self, name: str, devices: List[Device], rooms: List[Room],
                    result: EngineeringResult):
        self.projects[name] = {
            "devices": [d.to_dict() for d in devices],
            "rooms": [r.to_dict() for r in rooms],
            "metrics": {
                "total_power_w": result.total_power_w,
                "design_power_w": result.design_power_w,
                "total_cost": result.total_cost,
                "device_count": len(devices),
                "room_count": len(rooms),
                "phase_imbalance": result.phase_imbalance,
                "cooling_w": result.cooling_load_w,
                "ups_w": result.ups_power_w,
            },
            "added": datetime.now().isoformat(),
        }

    def compare(self, metric: str = "total_cost") -> List[Tuple[str, float]]:
        """Сравнение проектов по метрике"""
        results = []
        for name, data in self.projects.items():
            value = data["metrics"].get(metric, 0)
            results.append((name, value))
        results.sort(key=lambda x: x[1])
        return results

    def remove_project(self, name: str):
        self.projects.pop(name, None)

    def list_projects(self) -> List[str]:
        return list(self.projects.keys())