"""КОНТУР-ПРО: графовая модель цифрового двойника здания."""

from __future__ import annotations

from dataclasses import dataclass, field

# ============================================================================
# СЕКЦИЯ 6: ЦИФРОВОЙ ДВОЙНИК (ГРАФОВАЯ МОДЕЛЬ)
# ============================================================================

#: Значения по умолчанию для узла Twin-канвы.
DEFAULT_NODE_COLOR = "5"
DEFAULT_NODE_WIDTH = 300
DEFAULT_NODE_HEIGHT = 100

#: Значения по умолчанию для связи (ребра) Twin-канвы.
DEFAULT_EDGE_FROM_SIDE = "bottom"
DEFAULT_EDGE_TO_SIDE = "top"

#: Значения по умолчанию для группы (рамки) Twin-канвы.
DEFAULT_GROUP_WIDTH = 500
DEFAULT_GROUP_HEIGHT = 200

#: Инженерная система узла, определяемая по ключевым словам в тексте.
#: Порядок важен: первое совпавшее правило побеждает.
SYSTEM_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("power", ("щит", "автомат", "электр", "кабель", "ввг", "⚡")),
    ("network", ("switch", "коммутатор", "маршрутиз", "wifi", "wi-fi", "сет", "utp", "🌐", "📡")),
    ("camera", ("nvr", "камер", "видео", "poе", "poe", "🎥", "📹")),
    ("skud", ("скуд", "замок", "контроллер", "доступ", "🔑", "🚪")),
    ("ops", ("опс", "пожар", "дым", "охранн", "датчик", "шс", "🔥")),
    ("hvac", ("кондицион", "охлажд", "тепло", "вентиляц", "❄️")),
    ("lan", ("lan", "скс", "патч", "лоток")),
    ("phone", ("телефон", "phone", "📞")),
)
#: Система по умолчанию, если ни одно ключевое слово не найдено.
DEFAULT_SYSTEM = "room"


def detect_system(text: str) -> str:
    """Определить инженерную систему узла по ключевым словам в тексте."""
    lowered = text.lower()
    for system, keywords in SYSTEM_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return system
    return DEFAULT_SYSTEM


@dataclass
class TwinNode:
    """Узел Twin-канвы (устройство, щит, помещение и т.п.)."""

    id: str
    text: str
    color: str = DEFAULT_NODE_COLOR
    x: int = 0
    y: int = 0
    width: int = DEFAULT_NODE_WIDTH
    height: int = DEFAULT_NODE_HEIGHT
    system: str = field(init=False, default=DEFAULT_SYSTEM)

    def __post_init__(self) -> None:
        self.system = detect_system(self.text)


@dataclass
class TwinEdge:
    """Связь между двумя узлами Twin-канвы."""

    id: str
    from_node: str
    to_node: str
    from_side: str = DEFAULT_EDGE_FROM_SIDE
    to_side: str = DEFAULT_EDGE_TO_SIDE


@dataclass
class TwinGroup:
    """Группа (визуальная рамка), объединяющая несколько узлов."""

    id: str
    label: str
    x: int = 0
    y: int = 0
    width: int = DEFAULT_GROUP_WIDTH
    height: int = DEFAULT_GROUP_HEIGHT


class DigitalTwin:
    """Графовая модель здания: узлы, связи и группы Twin-канвы."""

    def __init__(self) -> None:
        self.nodes: dict[str, TwinNode] = {}
        self.edges: dict[str, TwinEdge] = {}
        self.groups: dict[str, TwinGroup] = {}

    def add_node(self, node: TwinNode) -> None:
        """Добавить или заменить узел по его id (O(1))."""
        self.nodes[node.id] = node

    def add_edge(self, edge: TwinEdge) -> None:
        """Добавить связь, если id ещё не занят (O(1))."""
        if edge.id not in self.edges:
            self.edges[edge.id] = edge

    def add_group(self, group: TwinGroup) -> None:
        """Добавить или заменить группу по её id (O(1))."""
        self.groups[group.id] = group

    def get_stats(self) -> dict:
        """Сводная статистика по двойнику: число узлов/связей/групп и разбивка по системам."""
        systems: dict[str, int] = {}
        for node in self.nodes.values():
            systems[node.system] = systems.get(node.system, 0) + 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "groups": len(self.groups),
            "systems": systems,
        }


#: Псевдоним для совместимости с потребителями, ожидающими имя TwinModel
#: (например, аннотации типов в модуле экспорта).
TwinModel = DigitalTwin
