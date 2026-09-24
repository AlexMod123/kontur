"""КОНТУР-ПРО: кабельный журнал по ГОСТ 21.613."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from kontur.calculators.electrical import PHASE_VOLTAGE_V, CableCalculator
from kontur.config import DEMAND_FACTORS
from kontur.models import CableTrace, Device

if TYPE_CHECKING:
    from kontur.scale import ScaleManager

DEFAULT_PANEL_DESIGNATION = "ЩРО"  # обозначение вводного щита по умолчанию


class CableJournalEntry(TypedDict):
    num: int
    designation: str
    start: str
    end: str
    cable: str
    section: float
    length_m: float
    current_a: float
    system: str


class CableJournal:
    """Кабельный журнал по ГОСТ 21.613"""

    @staticmethod
    def build(
        devices: list[Device], traces: list[CableTrace], scale_manager: ScaleManager | None = None
    ) -> list[CableJournalEntry]:
        journal: list[CableJournalEntry] = []
        for i, dev in enumerate(devices, 1):
            trace = next((t for t in traces if t.device_id == dev.id), None)
            length = trace.length_m + trace.vertical_length if trace else 0
            current = dev.power_w * DEMAND_FACTORS.get(dev.category, 0.7) / PHASE_VOLTAGE_V
            cable = CableCalculator.select_section(current)
            journal.append(
                {
                    "num": i,
                    "designation": dev.designation or dev.name,
                    "start": DEFAULT_PANEL_DESIGNATION,
                    "end": dev.name,
                    "cable": cable["name"],
                    "section": cable["section"],
                    "length_m": round(length, 1),
                    "current_a": round(current, 1),
                    "system": dev.category,
                }
            )
        return journal
