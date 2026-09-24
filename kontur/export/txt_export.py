"""КОНТУР-ПРО: экспорт в текстовый отчёт (TXT)."""

from __future__ import annotations

from kontur.config import VERSION, VERSION_NAME
from kontur.export.base import ExportContext, ExportFormat
from kontur.export.registry import register
from kontur.models import EngineeringResult

#: ширина разделительной линии в TXT-отчёте
SEPARATOR_WIDTH = 60
SEPARATOR = "=" * SEPARATOR_WIDTH


def _render_summary_lines(r: EngineeringResult) -> list[str]:
    """Строит строки сводки расчётных параметров."""
    return [
        f"Установленная мощность: {r.installed_power_w / 1000:.2f} кВт",
        f"Расчётная мощность:     {r.demand_power_w / 1000:.2f} кВт",
        f"Ток нагрузки:           {r.total_current_a:.1f} А",
        f"cos φ:                  {r.cos_phi}",
        f"Перекос фаз:             {r.phase_imbalance_pct}%",
        f"Автомат:                С{r.recommended_breaker}",
        f"Кабель:                 {r.recommended_cable}",
        f"Падение напряжения:     {r.voltage_drop_pct}%",
        f"Заземление:             {r.grounding_r} Ом [{r.grounding_status}]",
        f"Охлаждение:             {r.cooling_required_w / 1000:.1f} кВт",
        f"Вентиляция:             {r.ventilation_required_m3h:.0f} м³/ч",
        f"ИБП:                    {r.ups_power_w / 1000:.1f} кВт ({r.ups_autonomy_min} мин)",
        f"Токи КЗ:                I3ф={r.short_circuit_3ph}А, I1ф={r.short_circuit_1ph}А",
        f"Ударный ток:            {r.short_circuit_iudar}А",
        f"Утечки:                 {r.leakage_current_ma} мА (УЗО {r.leakage_uzo_ma} мА)",
        f"Молниезащита:           {r.lightning_zone}",
        f"ЛВС:                    {r.lan_ports} портов, {r.lan_cable_m:.0f} м",
        f"PoE-бюджет:             {r.poe_required_w} Вт / {r.poe_budget_w} Вт",
        f"Теплопотери:            {r.heat_loss_w:.0f} Вт",
        f"Уровень шума:           {r.noise_level_db:.1f} дБ",
        f"Смета:                  {r.cost_total:,.0f} ₽",
    ]


def _render_devices_lines(devices: list) -> list[str]:
    """Строит строки перечня оборудования."""
    return [f"  {d.designation or '—':<12} {d.name:<40} {d.power_w:>6.0f} Вт" for d in devices]


@register
class TxtExportFormat(ExportFormat):
    """Экспорт отчёта в простой текстовый файл."""

    name = "txt"
    extension = "txt"

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def render(ctx: ExportContext) -> str:
        lines = [
            f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»",
            f"Дата: {ctx.display_timestamp}",
            SEPARATOR,
            "СВОДКА",
            SEPARATOR,
            *_render_summary_lines(ctx.result),
            SEPARATOR,
            f"ОБОРУДОВАНИЕ ({len(ctx.devices)} шт.)",
            SEPARATOR,
            *_render_devices_lines(ctx.devices),
            SEPARATOR,
        ]
        if ctx.result.recommendations:
            lines.append("РЕКОМЕНДАЦИИ:")
            lines.extend(f"  ⚠ {rec}" for rec in ctx.result.recommendations)
        return "\n".join(lines)
