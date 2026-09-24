"""КОНТУР-ПРО: модуль routing."""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Iterator

# ============================================================================
# СЕКЦИЯ 5: A* АЛГОРИТМ ТРАССИРОВКИ (8 направлений + heapq + closed_set)
# ============================================================================

#: Координаты ячейки сетки (целочисленные индексы, не пиксели).
Point = tuple[int, int]

#: Позиция в реальных единицах (пиксели/мм), как принимает публичный API.
Position = tuple[float, float]

#: Стоимость шага по диагонали (~sqrt(2), намеренно неточное значение —
#: используется и в стоимости хода, и в эвристике, поэтому эвристика
#: остаётся допустимой и согласованной).
DIAGONAL_COST = 1.414
#: Стоимость шага по прямой.
STRAIGHT_COST = 1.0

#: 8 направлений хода: сначала прямые, затем диагонали.
DIRECTIONS_8: tuple[Point, ...] = (
    (0, 1),
    (1, 0),
    (0, -1),
    (-1, 0),  # прямые
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),  # диагонали
)


class AStarRouter:
    """A* для трассировки кабеля с 8 направлениями и обходом стен."""

    DIRECTIONS_8 = DIRECTIONS_8

    def __init__(self, grid_w: int = 200, grid_h: int = 150, cell: int = 10) -> None:
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell = cell
        self.walls: set[Point] = set()

    def add_wall(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Добавить прямоугольную стену (в реальных координатах) в сетку."""
        cx1, cy1 = self._to_cell(x1, y1)
        cx2, cy2 = self._to_cell(x2, y2)
        for cx in range(min(cx1, cx2), max(cx1, cx2) + 1):
            for cy in range(min(cy1, cy2), max(cy1, cy2) + 1):
                self.walls.add((cx, cy))

    def find_path(self, start: Position, end: Position) -> list[Position]:
        """Найти путь A* между двумя точками.

        Контракт возврата не меняется: при start == end (в пересчёте на
        ячейку) возвращается [start, end]; если путь не найден — тоже
        [start, end] (прямая линия как запасной вариант).
        """
        start_cell = self._to_cell(*start)
        end_cell = self._to_cell(*end)

        if start_cell == end_cell:
            return [start, end]

        came_from = self._search(start_cell, end_cell)
        if came_from is None:
            return [start, end]  # fallback: прямая линия

        return self._reconstruct(came_from, end_cell, start, end)

    def _to_cell(self, x: float, y: float) -> Point:
        return int(x / self.cell), int(y / self.cell)

    def _in_bounds(self, cell: Point) -> bool:
        x, y = cell
        return 0 <= x < self.grid_w and 0 <= y < self.grid_h

    def _neighbours(self, cell: Point, closed_set: Iterable[Point]) -> Iterator[tuple[Point, float]]:
        """Сгенерировать проходимых соседей ячейки со стоимостью хода до них."""
        cx, cy = cell
        for dx, dy in DIRECTIONS_8:
            neighbour = (cx + dx, cy + dy)
            if neighbour in self.walls or neighbour in closed_set:
                continue
            if not self._in_bounds(neighbour):
                continue
            step_cost = DIAGONAL_COST if (dx != 0 and dy != 0) else STRAIGHT_COST
            yield neighbour, step_cost

    def _search(self, start_cell: Point, end_cell: Point) -> dict[Point, Point] | None:
        """Выполнить поиск A* по сетке ячеек. Возвращает came_from или None, если путь не найден."""
        # heapq: (f_score, counter, cell) — counter разрешает коллизии f_score без сравнения кортежей ячеек
        counter = 0
        open_set: list[tuple[float, int, Point]] = [(0.0, counter, start_cell)]
        came_from: dict[Point, Point] = {}
        g_score: dict[Point, float] = {start_cell: 0.0}
        closed_set: set[Point] = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current == end_cell:
                return came_from

            if current in closed_set:
                continue
            closed_set.add(current)

            for neighbour, step_cost in self._neighbours(current, closed_set):
                tentative = g_score[current] + step_cost
                if neighbour not in g_score or tentative < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative
                    f_score = tentative + self._heuristic(neighbour, end_cell)
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbour))

        return None

    @staticmethod
    def _heuristic(cell: Point, goal: Point) -> float:
        """Октайл-расстояние (допустимая эвристика для 8-направленного хода)."""
        dx = abs(cell[0] - goal[0])
        dy = abs(cell[1] - goal[1])
        return (dx + dy) + (DIAGONAL_COST - 2) * min(dx, dy)

    def _reconstruct(
        self,
        came_from: dict[Point, Point],
        end_cell: Point,
        start_pos: Position,
        end_pos: Position,
    ) -> list[Position]:
        """Восстановить путь из came_from и подставить исходные начальную/конечную точки."""
        path_cells = [end_cell]
        current = end_cell
        while current in came_from:
            current = came_from[current]
            path_cells.append(current)
        path_cells.reverse()

        path: list[Position] = [start_pos]
        for cx, cy in path_cells:
            path.append((cx * self.cell, cy * self.cell))
        path.append(end_pos)
        return path
