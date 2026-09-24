"""КОНТУР-ПРО: пакет калькуляторов (15 инженерных калькуляторов по доменам).

Публичный интерфейс сохраняет плоскую структуру исходного модуля
``kontur.calculators`` — все классы по-прежнему импортируются как
``from kontur.calculators import <Class>``. Внутреннее разбиение по файлам
организовано по инженерному домену:

- ``electrical``    — кабель, фазы, селективность, реактивные потери, утечки
- ``short_circuit`` — токи короткого замыкания (ГОСТ 28249)
- ``grounding``      — заземление и молниезащита (СО 153)
- ``climate``        — охлаждение, вентиляция, теплопотери (СП 50.13330)
- ``lighting``       — освещённость (СП 52.13330)
- ``acoustic``       — уровень шума (СНиП 23-03)
- ``network``        — ЛВС/СКС (ГОСТ Р 53246)
- ``journal``        — кабельный журнал (ГОСТ 21.613)
"""

from __future__ import annotations

from kontur.calculators.acoustic import AcousticCalculator
from kontur.calculators.climate import CoolingCalculator, HeatLossCalculator, VentilationCalculator
from kontur.calculators.electrical import (
    CableCalculator,
    LeakageCalculator,
    PhaseBalancer,
    ReactiveLossCalculator,
    SelectivityChecker,
)
from kontur.calculators.grounding import GroundCalculator, LightningProtection
from kontur.calculators.journal import CableJournal
from kontur.calculators.lighting import LightingCalculator
from kontur.calculators.network import LANCalculator
from kontur.calculators.short_circuit import DEFAULT_SOURCE, ShortCircuitCalculator, SourceImpedance

__all__ = [
    "DEFAULT_SOURCE",
    "AcousticCalculator",
    "CableCalculator",
    "CableJournal",
    "CoolingCalculator",
    "GroundCalculator",
    "HeatLossCalculator",
    "LANCalculator",
    "LeakageCalculator",
    "LightingCalculator",
    "LightningProtection",
    "PhaseBalancer",
    "ReactiveLossCalculator",
    "SelectivityChecker",
    "ShortCircuitCalculator",
    "SourceImpedance",
    "VentilationCalculator",
]
