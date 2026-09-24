"""КОНТУР-ПРО: импорт цифрового двойника из Obsidian Canvas / Figma JSON."""

from __future__ import annotations

import json
import logging
from typing import Any

from .model import (
    DEFAULT_EDGE_FROM_SIDE,
    DEFAULT_EDGE_TO_SIDE,
    DEFAULT_GROUP_HEIGHT,
    DEFAULT_GROUP_WIDTH,
    DEFAULT_NODE_COLOR,
    DEFAULT_NODE_HEIGHT,
    DEFAULT_NODE_WIDTH,
    DigitalTwin,
    TwinEdge,
    TwinGroup,
    TwinNode,
)

# ============================================================================
# СЕКЦИЯ 6: ЦИФРОВОЙ ДВОЙНИК — ИМПОРТ JSON
# ============================================================================

logger = logging.getLogger(__name__)


class TwinImporter:
    """Импорт Twin JSON из Obsidian Canvas / Figma."""

    @staticmethod
    def parse(text: str) -> DigitalTwin:
        """Разобрать текст файла канвы (.canvas/.json) в DigitalTwin.

        Некорректные отдельные узлы/группы (без обязательного поля id)
        пропускаются с предупреждением в лог, а не роняют весь импорт.
        """
        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start == -1 or json_end == -1:
            raise ValueError("JSON не найден в файле")

        raw = text[json_start : json_end + 1]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Некорректный JSON, попытка восстановления структуры")
            data = TwinImporter._repair_json(raw)

        twin = DigitalTwin()
        seen_edge_ids: set[str] = set()

        for node in data.get("nodes", []):
            try:
                twin.add_node(
                    TwinNode(
                        node["id"],
                        node.get("text", ""),
                        node.get("color", DEFAULT_NODE_COLOR),
                        node.get("x", 0),
                        node.get("y", 0),
                        node.get("width", DEFAULT_NODE_WIDTH),
                        node.get("height", DEFAULT_NODE_HEIGHT),
                    )
                )
            except KeyError as exc:
                logger.warning("Пропущен узел без обязательного поля %s: %r", exc, node)

        for edge in data.get("edges", []):
            eid = edge.get("id", f"e_{edge.get('fromNode', '')}_{edge.get('toNode', '')}")
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            twin.add_edge(
                TwinEdge(
                    eid,
                    edge.get("fromNode", ""),
                    edge.get("toNode", ""),
                    edge.get("fromSide", DEFAULT_EDGE_FROM_SIDE),
                    edge.get("toSide", DEFAULT_EDGE_TO_SIDE),
                )
            )

        for group in data.get("groups", []):
            try:
                twin.add_group(
                    TwinGroup(
                        group["id"],
                        group.get("label", ""),
                        group.get("x", 0),
                        group.get("y", 0),
                        group.get("width", DEFAULT_GROUP_WIDTH),
                        group.get("height", DEFAULT_GROUP_HEIGHT),
                    )
                )
            except KeyError as exc:
                logger.warning("Пропущена группа без обязательного поля %s: %r", exc, group)

        return twin

    @staticmethod
    def _repair_json(raw: str) -> dict[str, Any]:
        """Попытаться восстановить чуть повреждённый JSON (обрубленный/задвоенный хвост).

        Используется, когда прямой json.loads не смог разобрать текст целиком,
        например если экспорт из внешнего редактора обрезал массив groups.
        """
        edges_start = raw.find('"edges"')
        if edges_start == -1:
            return json.loads(raw)  # type: ignore[no-any-return]

        first_array_start = raw.find("[", edges_start)
        depth = 0
        first_array_end = -1
        for i in range(first_array_start, len(raw)):
            if raw[i] == "[":
                depth += 1
            elif raw[i] == "]":
                depth -= 1
            if depth == 0:
                first_array_end = i
                break

        if first_array_end == -1:
            return json.loads(raw)  # type: ignore[no-any-return]

        after_first = raw[first_array_end + 1 :]
        groups_start = after_first.find('"groups"')
        if groups_start != -1:
            cleaned = raw[: first_array_end + 1]
            cleaned += "," + after_first[groups_start:]
            cleaned = cleaned.rstrip()
            if not cleaned.endswith("}"):
                cleaned += "}"
            try:
                return json.loads(cleaned)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                logger.warning("Восстановление JSON не удалось, используем исходный текст")

        return json.loads(raw)  # type: ignore[no-any-return]
