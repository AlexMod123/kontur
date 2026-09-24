"""КОНТУР-ПРО: экспорт в JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from kontur.config import SCHEMA_VERSION, VERSION
from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import register


@register
class JsonExportFormat(ExportFormat):
    """Экспорт полного слепка проекта в JSON (схема ``SCHEMA_VERSION``)."""

    name = "json"
    extension = "json"

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def render(ctx: ExportContext) -> str:
        data: dict = {
            "schema_version": SCHEMA_VERSION,
            "app": "КОНТУР-ПРО",
            "version": VERSION,
            "timestamp": ctx.display_timestamp,
            "devices": [asdict(d) for d in ctx.devices],
            "rooms": [asdict(r) for r in ctx.rooms],
            "result": asdict(ctx.result),
        }
        if ctx.twin:
            data["twin"] = {
                "nodes": {k: {"text": v.text, "system": v.system} for k, v in ctx.twin.nodes.items()},
                "edges": len(ctx.twin.edges),
                "groups": len(ctx.twin.groups),
            }
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
