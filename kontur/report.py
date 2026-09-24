"""КОНТУР-ПРО: рендеринг текстового отчёта CLI.

Чистая функция ``render_report`` не имеет побочных эффектов (не печатает,
не пишет файлы) — это позволяет тестировать её отдельно от ``run_cli`` и
гарантировать байт-в-байт совпадение вывода с эталоном (``tests/golden``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kontur.config import VERSION, VERSION_NAME

if TYPE_CHECKING:
    from kontur.models import EngineeringResult

#: символ статуса проверки модели для текстового отчёта
_STATUS_SYMBOLS = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}


def render_report(template: str, tier: int, result: EngineeringResult, checks: list[dict]) -> str:
    """Формирует итоговый текстовый отчёт по расчёту.

    :param template: имя шаблона здания (как задано пользователем в CLI)
    :param tier: фактический tier-уровень использованного проекта
    :param result: результат расчёта :class:`EngineeringCore.calculate`
    :param checks: список проверок из :meth:`ModelChecker.run_all`
    :return: многострочный текст отчёта без завершающего перевода строки
    """
    ok_count = sum(1 for c in checks if c["status"] == "OK")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")

    lines = [
        "",
        f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»",
        f"Шаблон: {template}, Tier: {tier}",
        f"{'=' * 60}",
        f"Установленная мощность:  {result.installed_power_w / 1000:.2f} кВт",
        f"Расчётная мощность:      {result.demand_power_w / 1000:.2f} кВт",
        f"Ток нагрузки:             {result.total_current_a:.1f} А",
        f"cos φ:                   {result.cos_phi}",
        f"Перекос фаз:              {result.phase_imbalance_pct}%",
        f"Автомат:                  С{result.recommended_breaker}",
        f"Кабель:                   {result.recommended_cable}",
        f"Падение напряжения:       {result.voltage_drop_pct}%",
        f"Заземление:               {result.grounding_r} Ом [{result.grounding_status}]",
        f"Охлаждение:               {result.cooling_required_w / 1000:.1f} кВт",
        f"Вентиляция:               {result.ventilation_required_m3h:.0f} м³/ч",
        f"ИБП:                      {result.ups_power_w / 1000:.1f} кВт ({result.ups_autonomy_min} мин)",
        f"Токи КЗ:                  I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А",
        f"Ударный ток:              {result.short_circuit_iudar}А",
        f"Утечки:                   {result.leakage_current_ma} мА (УЗО {result.leakage_uzo_ma} мА)",
        f"Молниезащита:             {result.lightning_zone}",
        f"Освещение:                {result.lighting_lux} лк, ламп: {result.lighting_lamps}",
        f"ЛВС:                      {result.lan_ports} портов, {result.lan_cable_m:.0f} м",
        f"PoE-бюджет:               {result.poe_required_w} Вт / {result.poe_budget_w} Вт",
        f"Теплопотери:              {result.heat_loss_w:.0f} Вт",
        f"Уровень шума:             {result.noise_level_db:.1f} дБ",
        f"Смета:                    {result.cost_total:,.0f} ₽",
        f"{'=' * 60}",
        f"Проверок: {len(checks)} (OK: {ok_count}, WARN: {warn_count}, FAIL: {fail_count})",
    ]
    for c in checks:
        symbol = _STATUS_SYMBOLS.get(c["status"], "[?]")
        lines.append(f"  {symbol:8} {c['name']:<25} {c['detail']}")

    if result.recommendations:
        lines.append(f"{'=' * 60}")
        lines.append("РЕКОМЕНДАЦИИ:")
        for rec in result.recommendations:
            lines.append(f"  ⚠ {rec}")

    return "\n".join(lines)
