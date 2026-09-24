
# ============================================================================
# СЕКЦИЯ 4: UGO PAINTER (УГО ПО ГОСТ 21.210-2014)
# ============================================================================

class UGOPainter:
    """Отрисовка УГО устройств по ГОСТ 21.210-2014, РД 78.36.002, РД 25.953"""

    @staticmethod
    def get_ugo_type(device_type: str) -> str:
        return UGO_TYPES.get(device_type, "custom")

    @staticmethod
    def draw_canvas(canvas_ctx, ugo_type: str, cx: float, cy: float, size: float = 40):
        """Отрисовка на canvas (упрощённый интерфейс для GUI)"""
        r = size / 2
        if ugo_type == "panel":
            canvas_ctx["rect"](cx - r, cy - r * 0.7, size, size * 0.7)
            canvas_ctx["text"](cx, cy, "Щ")
        elif ugo_type == "socket":
            canvas_ctx["arc"](cx, cy, r)
            canvas_ctx["line"](cx - r * 0.5, cy - r, cx - r * 0.5, cy - r * 1.4)
            canvas_ctx["line"](cx + r * 0.5, cy - r, cx + r * 0.5, cy - r * 1.4)
        elif ugo_type == "light":
            canvas_ctx["circle"](cx, cy, r * 0.7)
            canvas_ctx["line"](cx - r * 0.7, cy, cx + r * 0.7, cy)
            canvas_ctx["line"](cx, cy - r * 0.7, cx, cy + r * 0.7)
        elif ugo_type == "ups":
            canvas_ctx["rect"](cx - r, cy - r * 0.6, size, size * 0.6)
            canvas_ctx["line"](cx - r * 0.3, cy - r * 0.6, cx - r * 0.3, cy + r * 0.6)
            canvas_ctx["line"](cx + r * 0.3, cy - r * 0.6, cx + r * 0.3, cy + r * 0.6)
            canvas_ctx["text"](cx, cy, "+")
        elif ugo_type == "cam_dome":
            canvas_ctx["circle"](cx, cy, r * 0.6)
            canvas_ctx["arc_sector"](cx, cy, r * 1.2, -30, 30)
        elif ugo_type == "cam_cyl":
            canvas_ctx["circle"](cx - r * 0.3, cy, r * 0.3)
            canvas_ctx["line"](cx, cy, cx + r, cy)
        elif ugo_type == "nvr":
            canvas_ctx["rect"](cx - r, cy - r * 0.6, size, size * 0.6)
            canvas_ctx["text"](cx, cy, "NVR")
        elif ugo_type == "reader":
            canvas_ctx["rect"](cx - r * 0.6, cy - r * 0.8, r * 1.2, size * 0.8)
            canvas_ctx["text"](cx, cy, "R")
        elif ugo_type == "lock":
            canvas_ctx["rect"](cx - r, cy - r * 0.5, size, size * 0.5)
            canvas_ctx["text"](cx, cy, "Z")
        elif ugo_type == "turnstile":
            canvas_ctx["circle"](cx, cy, r * 0.8)
            canvas_ctx["line"](cx, cy - r * 0.8, cx, cy + r * 0.8)
        elif ugo_type == "smoke":
            canvas_ctx["circle"](cx, cy, r * 0.6)
            canvas_ctx["text"](cx, cy, "Д")
        elif ugo_type == "heat":
            canvas_ctx["circle"](cx, cy, r * 0.6)
            canvas_ctx["text"](cx, cy, "Т")
        elif ugo_type == "manual":
            canvas_ctx["rect"](cx - r * 0.5, cy - r * 0.7, r, size * 0.7)
            canvas_ctx["text"](cx, cy, "ИПР")
        elif ugo_type == "ppkpu":
            canvas_ctx["rect"](cx - r, cy - r * 0.6, size, size * 0.6)
            canvas_ctx["text"](cx, cy, "ППКПУ")
        elif ugo_type == "siren":
            canvas_ctx["polygon"]([(cx - r, cy - r * 0.4), (cx + r, cy - r * 0.4), (cx, cy + r * 0.6)])
        elif ugo_type == "beacon":
            canvas_ctx["rect"](cx - r * 0.7, cy - r * 0.5, r * 1.4, size * 0.5)
            canvas_ctx["text"](cx, cy, "ОС")
        elif ugo_type == "pc":
            canvas_ctx["rect"](cx - r, cy - r * 0.6, size, size * 0.6)
            canvas_ctx["text"](cx, cy, "ПК")
        elif ugo_type == "server":
            canvas_ctx["rect"](cx - r, cy - r * 0.6, size, size * 0.6)
            canvas_ctx["line"](cx - r * 0.8, cy, cx + r * 0.8, cy)
            canvas_ctx["text"](cx, cy + r * 0.3, "SRV")
        elif ugo_type == "rack":
            canvas_ctx["rect"](cx - r * 0.7, cy - r, r * 1.4, size)
            for i in range(5):
                y = cy - r + (i + 1) * size / 6
                canvas_ctx["line"](cx - r * 0.7, y, cx + r * 0.7, y)
        elif ugo_type == "switch":
            canvas_ctx["rect"](cx - r, cy - r * 0.3, size, size * 0.3)
            for i in range(8):
                x = cx - r + 2 + i * (size - 4) / 8
                canvas_ctx["line"](x, cy + r * 0.3, x, cy + r * 0.6)
        elif ugo_type == "router":
            canvas_ctx["circle"](cx, cy, r * 0.6)
            canvas_ctx["text"](cx, cy, "RT")
        elif ugo_type == "wifi":
            canvas_ctx["circle"](cx, cy, r * 0.3)
            canvas_ctx["arc"](cx, cy, r * 0.6, 200, 340)
            canvas_ctx["arc"](cx, cy, r * 0.9, 200, 340)
        elif ugo_type == "ac":
            canvas_ctx["rect"](cx - r, cy - r * 0.5, size, size * 0.5)
            canvas_ctx["text"](cx, cy, "AC")
        elif ugo_type == "patch":
            canvas_ctx["rect"](cx - r, cy - r * 0.3, size, size * 0.3)
            for i in range(12):
                x = cx - r + 2 + i * (size - 4) / 12
                canvas_ctx["line"](x, cy - r * 0.3, x, cy + r * 0.3)
        else:
            canvas_ctx["rect"](cx - r * 0.5, cy - r * 0.5, r, r)
            canvas_ctx["text"](cx, cy, "?")


# ============================================================================
# СЕКЦИЯ 5: DESIGNATION GENERATOR (ГОСТ 2.710-81)
# ============================================================================

class DesignationGenerator:
    """Генератор позиционных обозначений по ГОСТ 2.710-81"""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)

    def generate(self, device_type: str, floor: int = 1) -> str:
        prefix = DESIGNATION_PREFIX.get(device_type, "X")
        self.counters[prefix] += 1
        return f"{prefix}-{floor}.{self.counters[prefix]:02d}"

    def reset(self):
        self.counters.clear()

    def generate_all(self, devices: List[Device]) -> None:
        """Присвоение обозначений всем устройствам"""
        self.reset()
        for dev in devices:
            dev.designation = self.generate(dev.type, dev.floor)


# ============================================================================
# СЕКЦИЯ 6: A* ROUTER (8 НАПРАВЛЕНИЙ, CLOSED_SET, HEAPQ)
# ============================================================================

class AStarRouter:
    """A* с 8 направлениями, closed_set и приоритетной очередью (heapq)"""

    DIRECTIONS = [
        (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414),
    ]

    def __init__(self, width: int = 200, height: int = 150, grid_size: int = 10):
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.obstacles: Set[Tuple[int, int]] = set()
        self.walls: List[Wall] = []

    def add_wall(self, wall: Wall):
        self.walls.append(wall)
        x1, y1 = int(wall.x1 / self.grid_size), int(wall.y1 / self.grid_size)
        x2, y2 = int(wall.x2 / self.grid_size), int(wall.y2 / self.grid_size)
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for i in range(steps + 1):
            t = i / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            self.obstacles.add((x, y))

    def heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return (dx + dy) + (1.414 - 2) * min(dx, dy)  # Octile distance

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        sx, sy = int(start[0] / self.grid_size), int(start[1] / self.grid_size)
        gx, gy = int(goal[0] / self.grid_size), int(goal[1] / self.grid_size)

        if gx < 0 or gx >= self.width or gy < 0 or gy >= self.height:
            return []

        open_heap = [(0, sx, sy)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {(sx, sy): 0}
        closed_set: Set[Tuple[int, int]] = set()

        while open_heap:
            _, cx, cy = heapq.heappop(open_heap)
            if (cx, cy) == (gx, gy):
                path = [(gx * self.grid_size, gy * self.grid_size)]
                while (cx, cy) in came_from:
                    cx, cy = came_from[(cx, cy)]
                    path.append((cx * self.grid_size, cy * self.grid_size))
                path.reverse()
                path[0] = (start[0], start[1])
                path[-1] = (goal[0], goal[1])
                return path

            if (cx, cy) in closed_set:
                continue
            closed_set.add((cx, cy))

            for dx, dy, cost in self.DIRECTIONS:
                nx, ny = cx + dx, cy + dy
                if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
                    continue
                if (nx, ny) in closed_set:
                    continue
                if (nx, ny) in self.obstacles:
                    continue

                tentative_g = g_score[(cx, cy)] + cost
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = tentative_g
                    f = tentative_g + self.heuristic(nx, ny, gx, gy)
                    heapq.heappush(open_heap, (f, nx, ny))
                    came_from[(nx, ny)] = (cx, cy)

        return []

    def path_length(self, path: List[Tuple[float, float]]) -> float:
        if len(path) < 2:
            return 0.0
        total = 0.0
        for i in range(1, len(path)):
            dx = path[i][0] - path[i-1][0]
            dy = path[i][1] - path[i-1][1]
            total += math.hypot(dx, dy)
        return total


# ============================================================================
# СЕКЦИЯ 7: DIGITAL TWIN (ГРАФОВАЯ МОДЕЛЬ)
# ============================================================================

@dataclass
class TwinNode:
    id: str
    node_type: str  # device, panel, room
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    floor: int = 1
    attributes: dict = field(default_factory=dict)

@dataclass
class TwinEdge:
    src: str
    dst: str
    edge_type: str = "power"  # power, data, control
    cable: str = ""
    length: float = 0.0

class DigitalTwin:
    """Цифровой двойник здания: графовая модель"""

    def __init__(self):
        self.nodes: Dict[str, TwinNode] = {}
        self.edges: List[TwinEdge] = []
        self.adjacency: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, node: TwinNode):
        self.nodes[node.id] = node

    def add_edge(self, edge: TwinEdge):
        self.edges.append(edge)
        self.adjacency[edge.src].append(edge.dst)
        self.adjacency[edge.dst].append(edge.src)

    def build_from_project(self, devices: List[Device], rooms: List[Room],
                           cables: List[CableLine]):
        for d in devices:
            self.add_node(TwinNode(id=d.id, node_type="device",
                                   name=d.name, x=d.x, y=d.y, floor=d.floor,
                                   attributes={"category": d.category, "power_w": d.power_w,
                                               "voltage": d.voltage, "designation": d.designation}))
        for r in rooms:
            self.add_node(TwinNode(id=f"room_{r.name}", node_type="room",
                                   name=r.name, x=r.x + r.w/2, y=r.y + r.h/2, floor=r.floor,
                                   attributes={"area": r.area, "height": r.height}))
        for c in cables:
            self.add_edge(TwinEdge(src=c.src, dst=c.dst, edge_type="power",
                                   cable=c.cable_type, length=c.length))

    def get_devices_by_category(self, category: str) -> List[TwinNode]:
        return [n for n in self.nodes.values()
                if n.attributes.get("category") == category]

    def get_total_power(self) -> float:
        return sum(n.attributes.get("power_w", 0) for n in self.nodes.values())

    def to_dict(self) -> dict:
        return {
            "nodes": {k: {"id": v.id, "type": v.node_type, "name": v.name,
                          "x": v.x, "y": v.y, "floor": v.floor,
                          "attributes": v.attributes}
                      for k, v in self.nodes.items()},
            "edges": [{"src": e.src, "dst": e.dst, "type": e.edge_type,
                       "cable": e.cable, "length": e.length} for e in self.edges],
        }

    @staticmethod
    def from_dict(d: dict) -> "DigitalTwin":
        twin = DigitalTwin()
        for k, v in d.get("nodes", {}).items():
            twin.add_node(TwinNode(id=v["id"], node_type=v["type"], name=v["name"],
                                   x=v["x"], y=v["y"], floor=v.get("floor", 1),
                                   attributes=v.get("attributes", {})))
        for e in d.get("edges", []):
            twin.add_edge(TwinEdge(src=e["src"], dst=e["dst"], edge_type=e.get("type", "power"),
                                   cable=e.get("cable", ""), length=e.get("length", 0)))
        return twin


# ============================================================================
# СЕКЦИЯ 8: TWIN IMPORTER (OBSIDIAN CANVAS + FIGMA)
# ============================================================================

class TwinImporter:
    """Импорт цифрового двойника из Obsidian Canvas / Figma"""

    @staticmethod
    def import_obsidian_canvas(json_data: str) -> Tuple[List[Device], List[Room]]:
        """Импорт из Obsidian Canvas JSON"""
        devices = []
        rooms = []
        try:
            data = json.loads(json_data)
            for node in data.get("nodes", []):
                if node.get("type") == "text":
                    text = node.get("text", "")
                    x = node.get("x", 0)
                    y = node.get("y", 0)
                    w = node.get("width", 100)
                    h = node.get("height", 100)
                    # Парсинг типа устройства из текста
                    parts = text.strip().split("|")
                    if len(parts) >= 2:
                        dtype = parts[0].strip().lower()
                        name = parts[1].strip()
                        if dtype in EQUIPMENT_BY_ID:
                            eq = EQUIPMENT_BY_ID[dtype]
                            dev = Device(id=f"imp_{len(devices)}", name=name, type=dtype,
                                         category=eq["category"], x=float(x), y=float(y),
                                         power_w=eq["power_w"], voltage=eq["voltage"])
                            devices.append(dev)
                    else:
                        rooms.append(Room(name=text[:20], x=float(x), y=float(y),
                                          w=float(w), h=float(h)))
        except (json.JSONDecodeError, KeyError) as e:
            pass
        return devices, rooms

    @staticmethod
    def import_figma(json_data: str) -> Tuple[List[Device], List[Room]]:
        """Импорт из Figma JSON (упрощённый)"""
        devices = []
        rooms = []
        try:
            data = json.loads(json_data)
            for node in data.get("nodes", {}).values():
                doc = node.get("document", {})
                if doc.get("type") == "FRAME":
                    rooms.append(Room(name=doc.get("name", "Room"),
                                      x=doc.get("x", 0), y=doc.get("y", 0),
                                      w=doc.get("width", 100), h=doc.get("height", 100)))
                elif doc.get("type") == "RECTANGLE":
                    name = doc.get("name", "").lower()
                    for eq_id, eq in EQUIPMENT_BY_ID.items():
                        if eq_id in name or eq["name"].lower() in name:
                            devices.append(Device(id=f"fig_{len(devices)}",
                                                  name=eq["name"], type=eq_id,
                                                  category=eq["category"],
                                                  x=doc.get("x", 0), y=doc.get("y", 0),
                                                  power_w=eq["power_w"], voltage=eq["voltage"]))
                            break
        except (json.JSONDecodeError, KeyError):
            pass
        return devices, rooms


# ============================================================================
# СЕКЦИЯ 9: VENDOR DATABASE
# ============================================================================

class VendorDatabase:
    """База данных вендоров"""

    @staticmethod
    def get_vendor(name: str) -> Dict:
        return VENDORS.get(name, {"country": "Неизвестно", "cert": "—", "warranty": 0})

    @staticmethod
    def recommend(category: str, budget: str = "medium") -> List[str]:
        """Рекомендация вендоров по категории и бюджету"""
        if budget == "low":
            return ["IEK", "КЭАЗ"]
        elif budget == "high":
            return ["ABB", "Schneider", "Legrand"]
        return ["КЭАЗ", "Systeme_Electric", "ABB"]

    @staticmethod
    def all_vendors() -> List[str]:
        return list(VENDORS.keys())


# ============================================================================
# СЕКЦИЯ 10: SPECIFICATION BUILDER (ГОСТ 21.110)
# ============================================================================

class SpecificationBuilder:
    """Формирование спецификации оборудования по ГОСТ 21.110"""

    @staticmethod
    def build(devices: List[Device]) -> List[Dict]:
        """Формирование спецификации"""
        spec: Dict[str, Dict] = {}
        for d in devices:
            key = d.type if d.type else d.name
            if key in spec:
                spec[key]["qty"] += 1
            else:
                eq = EQUIPMENT_BY_ID.get(d.type, {})
                spec[key] = {
                    "pos": len(spec) + 1,
                    "name": d.name if d.name else eq.get("name", d.type),
                    "type": d.type,
                    "vendor": d.vendor,
                    "unit": "шт",
                    "qty": 1,
                    "price": eq.get("price", d.cost),
                    "total": eq.get("price", d.cost),
                    "category": d.category,
                }
        result = list(spec.values())
        for i, item in enumerate(result):
            item["pos"] = i + 1
            item["total"] = item["qty"] * item["price"]
        return result

    @staticmethod
    def total_cost(devices: List[Device]) -> float:
        spec = SpecificationBuilder.build(devices)
        return sum(item["total"] for item in spec)