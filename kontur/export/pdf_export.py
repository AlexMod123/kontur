"""КОНТУР-ПРО: экспорт в PDF (опциональная зависимость reportlab)."""

from __future__ import annotations

import importlib.util
import io
from typing import TYPE_CHECKING

from kontur.config import VERSION, VERSION_NAME
from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import register

if TYPE_CHECKING:
    from kontur.models import EngineeringResult

#: основной тёмный цвет заголовков таблиц (шапка «Сводка»)
HEADER_COLOR_DARK = "#1a1a2e"
#: акцентный цвет заголовка таблицы оборудования
HEADER_COLOR_ACCENT = "#06d6a0"


def _summary_table_data(r: EngineeringResult) -> list[list[str]]:
    """Строки таблицы сводных параметров для PDF."""
    return [
        ["Параметр", "Значение"],
        ["Мощность (уст.)", f"{r.installed_power_w / 1000:.2f} кВт"],
        ["Мощность (расч.)", f"{r.demand_power_w / 1000:.2f} кВт"],
        ["Ток", f"{r.total_current_a:.1f} А"],
        ["Автомат", f"С{r.recommended_breaker}"],
        ["Кабель", r.recommended_cable],
        ["Падение U", f"{r.voltage_drop_pct}%"],
        ["Заземление", f"{r.grounding_r} Ом"],
        ["Охлаждение", f"{r.cooling_required_w / 1000:.1f} кВт"],
        ["ИБП", f"{r.ups_power_w / 1000:.1f} кВт"],
        ["Смета", f"{r.cost_total:,.0f} ₽"],
    ]


@register
class PdfExportFormat(ExportFormat):
    """Экспорт отчёта в PDF (сводка + перечень оборудования). Требует reportlab."""

    name = "pdf"
    extension = "pdf"

    @staticmethod
    def is_available() -> bool:
        return importlib.util.find_spec("reportlab") is not None

    @staticmethod
    def render(ctx: ExportContext) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»", styles["Title"]), Spacer(1, 12)]

        summary_table = Table(_summary_table_data(ctx.result))
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(HEADER_COLOR_DARK)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 20))

        dev_data = [["Обозначение", "Наименование", "Мощность, Вт"]]
        dev_data.extend([d.designation or "—", d.name, str(d.power_w)] for d in ctx.devices)
        devices_table = Table(dev_data)
        devices_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(HEADER_COLOR_ACCENT)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(devices_table)

        doc.build(story)
        return buffer.getvalue()
