"""КОНТУР-ПРО: экспорт в DXF (опциональная зависимость ezdxf)."""

from __future__ import annotations

import importlib.util
import io

from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import register

#: версия формата DXF, в которую экспортируется чертёж
DXF_DOC_VERSION = "R2010"
#: радиус окружности условного обозначения устройства, мм
DEVICE_MARKER_RADIUS = 15
#: высота текста подписи помещения, мм
ROOM_LABEL_HEIGHT = 10
#: высота текста подписи устройства, мм
DEVICE_LABEL_HEIGHT = 8


@register
class DxfExportFormat(ExportFormat):
    """Экспорт плана помещений и устройств в DXF. Требует ezdxf."""

    name = "dxf"
    extension = "dxf"

    @staticmethod
    def is_available() -> bool:
        return importlib.util.find_spec("ezdxf") is not None

    @staticmethod
    def render(ctx: ExportContext) -> str:
        import ezdxf

        doc = ezdxf.new(DXF_DOC_VERSION)
        msp = doc.modelspace()

        for room in ctx.rooms:
            x, y, w, h = room.x, room.y, room.width, room.height
            msp.add_lwpolyline(
                [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], dxfattribs={"layer": "ROOMS"}
            )
            msp.add_text(
                room.name,
                dxfattribs={"insert": (x + w / 2, y + h / 2), "height": ROOM_LABEL_HEIGHT, "layer": "TEXT"},
            )

        for d in ctx.devices:
            r = DEVICE_MARKER_RADIUS
            msp.add_circle((d.x, d.y), r, dxfattribs={"layer": d.category.upper()})
            msp.add_text(
                d.designation or d.name,
                dxfattribs={
                    "insert": (d.x, d.y - r - 5),
                    "height": DEVICE_LABEL_HEIGHT,
                    "layer": "DEVICE_LABELS",
                },
            )

        buffer = io.StringIO()
        doc.write(buffer, fmt="asc")
        return buffer.getvalue()
