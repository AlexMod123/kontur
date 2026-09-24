"""КОНТУР-ПРО: экспорт в HTML."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from kontur.config import CATEGORIES, VERSION, VERSION_NAME
from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import register

if TYPE_CHECKING:
    from kontur.models import Device

#: цвета статусов проверок в отчёте
STATUS_COLORS = {"OK": "#10b981", "WARN": "#f59e0b", "FAIL": "#ef4444"}
DEFAULT_STATUS_COLOR = "#666"

_STYLE = """
body { font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }
h1 { color: #1a1a2e; } h2 { color: #06d6a0; border-bottom: 2px solid #06d6a0; padding-bottom: 5px; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; background: white; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #1a1a2e; color: white; } tr:nth-child(even) { background: #f8f9fa; }
.card { background: white; padding: 15px; border-radius: 8px; margin: 10px 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.rec { background: #fef3c7; padding: 8px; margin: 5px 0; border-left: 3px solid #f59e0b; border-radius: 4px; }
"""


def _render_checks_table(checks: list[dict] | None) -> str:
    """Строит блок с таблицей результатов проверок (может быть пустым)."""
    if not checks:
        return ""
    rows = []
    for c in checks:
        color = STATUS_COLORS.get(c["status"], DEFAULT_STATUS_COLOR)
        rows.append(
            f"<tr><td>{escape(str(c['name']))}</td>"
            f"<td style='color:{color};font-weight:bold'>{escape(str(c['status']))}</td>"
            f"<td>{escape(str(c['detail']))}</td></tr>"
        )
    return f"""
<h2>Проверки ({len(checks)})</h2>
<table><tr><th>Проверка</th><th>Статус</th><th>Детали</th></tr>{"".join(rows)}</table>"""


def _render_devices_rows(devices: list[Device]) -> str:
    """Строит строки таблицы оборудования."""
    rows = []
    for d in devices:
        category_name = CATEGORIES.get(d.category, {}).get("name", d.category)
        rows.append(
            f"<tr><td>{escape(d.name)}</td><td>{escape(str(category_name))}</td>"
            f"<td>{d.power_w} Вт</td><td>{escape(d.designation or '—')}</td></tr>"
        )
    return "".join(rows)


def _render_summary_table(ctx: ExportContext) -> str:
    """Строит сводную таблицу расчётных параметров."""
    r = ctx.result
    rows = [
        ("Установленная мощность", f"{r.installed_power_w / 1000:.2f} кВт"),
        ("Расчётная мощность", f"{r.demand_power_w / 1000:.2f} кВт"),
        ("Ток", f"{r.total_current_a:.1f} А"),
        ("cos φ", f"{r.cos_phi}"),
        ("Автомат", f"С{r.recommended_breaker}"),
        ("Кабель", r.recommended_cable),
        ("Падение напряжения", f"{r.voltage_drop_pct}%"),
        ("Заземление", f"{r.grounding_r} Ом [{r.grounding_status}]"),
        ("Охлаждение", f"{r.cooling_required_w / 1000:.1f} кВт"),
        ("ИБП", f"{r.ups_power_w / 1000:.1f} кВт"),
        ("Токи КЗ", f"I3ф={r.short_circuit_3ph}А, I1ф={r.short_circuit_1ph}А"),
        ("Утечки", f"{r.leakage_current_ma} мА (УЗО {r.leakage_uzo_ma} мА)"),
        ("Молниезащита", r.lightning_zone),
        ("ЛВС", f"{r.lan_ports} портов, {r.lan_cable_m:.0f} м"),
        ("PoE", f"{r.poe_required_w} Вт / {r.poe_budget_w} Вт"),
        ("Теплопотери", f"{r.heat_loss_w:.0f} Вт"),
        ("Смета", f"{r.cost_total:,.0f} ₽"),
    ]
    body = "".join(f"<tr><td>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"<table><tr><th>Параметр</th><th>Значение</th></tr>{body}</table>"


@register
class HtmlExportFormat(ExportFormat):
    """Экспорт отчёта в самодостаточную HTML-страницу."""

    name = "html"
    extension = "html"

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def render(ctx: ExportContext) -> str:
        checks_html = _render_checks_table(ctx.checks)
        devs_rows = _render_devices_rows(ctx.devices)
        summary_table = _render_summary_table(ctx)
        return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<title>КОНТУР-ПРО v{VERSION} — Отчёт</title>
<style>{_STYLE}</style></head><body>
<h1>КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»</h1>
<p>Дата: {ctx.display_timestamp}</p>
<div class="card"><h2>Сводка</h2>
{summary_table}</div>
{checks_html}
<div class="card"><h2>Оборудование ({len(ctx.devices)} шт.)</h2>
<table><tr><th>Наименование</th><th>Категория</th><th>Мощность</th><th>Обозначение</th></tr>{devs_rows}</table></div>
</body></html>"""
