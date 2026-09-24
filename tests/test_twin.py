"""КОНТУР-ПРО: модуль test_twin (объединённые тесты)."""

from __future__ import annotations

import unittest

from kontur.twin import DigitalTwin, TwinBuilder, TwinImporter, TwinNode

# ============================================================================
# LEGACY TESTS (from test_legacy.py)
# ============================================================================


class TestTwinBuilder(unittest.TestCase):
    def test_build_office(self):
        twin = TwinBuilder.build("Офис", 1)
        self.assertGreater(len(twin.nodes), 0)
        self.assertGreater(len(twin.edges), 0)

    def test_build_cod(self):
        twin = TwinBuilder.build("ЦОД", 3)
        stats = twin.get_stats()
        self.assertGreater(stats["nodes"], 0)

    def test_stats(self):
        twin = TwinBuilder.build("Склад")
        stats = twin.get_stats()
        self.assertIn("systems", stats)


class TestTwinImporter(unittest.TestCase):
    def test_parse_simple(self):
        json_text = (
            '{"nodes":[{"id":"n1","text":"Сервер","color":"1",'
            '"x":0,"y":0,"width":300,"height":100}],"edges":[],"groups":[]}'
        )
        twin = TwinImporter.parse(json_text)
        self.assertEqual(len(twin.nodes), 1)

    def test_detect_system(self):
        node = TwinNode("n1", "⚡ Автомат С16")
        self.assertEqual(node.system, "power")
        node2 = TwinNode("n2", "🎥 IP-камера")
        self.assertEqual(node2.system, "camera")


# ============================================================================
# EXTRA TESTS (from test_routing_twin_extra.py)
# ============================================================================


class TestTwinBuilderEdgeCases(unittest.TestCase):
    def test_unknown_template_falls_back_to_office(self):
        twin = TwinBuilder.build("НЕСУЩЕСТВУЮЩИЙ_ШАБЛОН")
        office_twin = TwinBuilder.build("Офис")
        self.assertEqual(twin.get_stats()["nodes"], office_twin.get_stats()["nodes"])

    def test_node_default_system_is_room(self):
        node = TwinNode("n1", "Просто текст без ключевых слов")
        self.assertEqual(node.system, "room")

    def test_add_edge_ignores_duplicate_id(self):
        twin = DigitalTwin()
        from kontur.twin import TwinEdge

        twin.add_edge(TwinEdge("e1", "a", "b"))
        twin.add_edge(TwinEdge("e1", "x", "y"))
        self.assertEqual(twin.edges["e1"].from_node, "a")


class TestTwinImporterEdgeCases(unittest.TestCase):
    def test_empty_canvas(self):
        twin = TwinImporter.parse('{"nodes": [], "edges": [], "groups": []}')
        stats = twin.get_stats()
        self.assertEqual(stats["nodes"], 0)
        self.assertEqual(stats["edges"], 0)
        self.assertEqual(stats["groups"], 0)

    def test_no_json_object_raises_value_error(self):
        with self.assertRaises(ValueError):
            TwinImporter.parse("это вообще не json")

    def test_malformed_json_is_repaired(self):
        raw = (
            '{"nodes":[{"id":"n1","text":"Comp"}],'
            '"edges":[{"id":"e1","fromNode":"n1","toNode":"n1"}],,,'
            '"groups":[{"id":"g1","label":"G1"}]}'
        )
        twin = TwinImporter.parse(raw)
        stats = twin.get_stats()
        self.assertEqual(stats["nodes"], 1)
        self.assertEqual(stats["edges"], 1)
        self.assertEqual(stats["groups"], 1)

    def test_node_without_id_is_skipped_not_fatal(self):
        raw = '{"nodes":[{"text":"без id"},{"id":"ok","text":"годный узел"}],"edges":[],"groups":[]}'
        twin = TwinImporter.parse(raw)
        self.assertEqual(list(twin.nodes), ["ok"])

    def test_duplicate_edge_id_keeps_first(self):
        raw = (
            '{"nodes":[],'
            '"edges":[{"id":"e1","fromNode":"a","toNode":"b"},'
            '{"id":"e1","fromNode":"c","toNode":"d"}],'
            '"groups":[]}'
        )
        twin = TwinImporter.parse(raw)
        self.assertEqual(len(twin.edges), 1)
        self.assertEqual(twin.edges["e1"].from_node, "a")
