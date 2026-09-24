"""КОНТУР-ПРО: модуль test_routing (объединённые тесты)."""

from __future__ import annotations

import itertools
import math
import unittest

from kontur.routing import AStarRouter

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestAStar(unittest.TestCase):
    def test_simple_path(self):
        router = AStarRouter(100, 80, 10)
        path = router.find_path((10, 10), (50, 50))
        self.assertGreater(len(path), 1)

    def test_8_directions(self):
        router = AStarRouter(100, 100, 10)
        path = router.find_path((10, 10), (40, 40))
        self.assertGreater(len(path), 1)

    def test_wall_avoidance(self):
        router = AStarRouter(100, 80, 10)
        router.add_wall(30, 0, 30, 80)
        path = router.find_path((10, 40), (50, 40))
        self.assertGreater(len(path), 2)

    def test_same_point(self):
        router = AStarRouter()
        path = router.find_path((50, 50), (50, 50))
        self.assertEqual(len(path), 2)


# ============================================================================
# EXTRA TESTS (from test_routing_twin_extra.py)
# ============================================================================


class TestAStarEdgeCases(unittest.TestCase):
    def test_start_equals_goal(self):
        router = AStarRouter()
        path = router.find_path((42, 42), (42, 42))
        self.assertEqual(path, [(42, 42), (42, 42)])

    def test_start_equals_goal_same_cell_different_pixel(self):
        router = AStarRouter(50, 50, 10)
        path = router.find_path((21, 21), (24, 24))
        self.assertEqual(path, [(21, 21), (24, 24)])

    def test_unreachable_goal_returns_fallback_straight_line(self):
        router = AStarRouter(10, 10, 10)
        goal_cell = (5, 5)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                router.walls.add((goal_cell[0] + dx, goal_cell[1] + dy))

        path = router.find_path((0, 0), (55, 55))
        self.assertEqual(path, [(0, 0), (55, 55)])

    def test_diagonal_path_uses_diagonal_moves(self):
        router = AStarRouter(20, 20, 10)
        path = router.find_path((0, 0), (50, 50))

        cell_steps = path[1:-1]
        for (x1, y1), (x2, y2) in itertools.pairwise(cell_steps):
            self.assertEqual(abs(x2 - x1), 10)
            self.assertEqual(abs(y2 - y1), 10)

        total_length = sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))
        direct_distance = math.dist((0, 0), (50, 50))
        self.assertAlmostEqual(total_length, direct_distance, delta=1.0)

    def test_obstacle_avoidance_detours_around_wall(self):
        router = AStarRouter(20, 20, 10)
        router.add_wall(50, 20, 50, 80)

        path = router.find_path((0, 50), (100, 50))

        self.assertTrue(any(y != 50 for _x, y in path))
        self.assertEqual(path[0], (0, 50))
        self.assertEqual(path[-1], (100, 50))

    def test_wall_cells_are_never_stepped_on(self):
        router = AStarRouter(20, 20, 10)
        router.add_wall(50, 20, 50, 80)
        path = router.find_path((0, 50), (100, 50))

        for x, y in path:
            cell = (x // router.cell, y // router.cell)
            self.assertNotIn(cell, router.walls)
