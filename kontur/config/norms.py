"""КОНТУР-ПРО: нормы электроснабжения (ПУЭ, СП, ГОСТ, IEEE)."""

from __future__ import annotations

from typing import Any, Final

# --- Напряжение и потери (ПУЭ 7) ---
VOLTAGE_DROP_MAX: Final = 5.0
VOLTAGE_DROP_WARN: Final = 3.0

# --- Асимметрия напряжения (ГОСТ 13109) ---
PHASE_IMBALANCE_MAX: Final = 15.0

# --- Заземление (ПУЭ 1.7) ---
GROUND_R_MAX: Final = 4.0
GROUND_R_WARN: Final = 10.0

# --- Коэффициент мощности (СП 256.1325800) ---
COS_PHI_DEFAULT: Final = 0.92

# --- Коэффициенты спроса по СП 256.1325800 ---
DEMAND_FACTORS = {
    "power": 0.7,
    "pc": 0.7,
    "server": 0.9,
    "network": 0.8,
    "camera": 0.95,
    "wifi": 0.6,
    "lighting": 0.6,
    "hvac": 0.8,
    "skud": 0.85,
    "ops": 0.9,
    "ups": 1.0,
    "custom": 0.7,
    "lan": 0.85,
    "phone": 0.7,
}

# --- Допустимые токи по ПУЭ (медный кабель, открыто) ---
# Однофазные линии: 3-жильный кабель (L, N, PE); нагружены 2 жилы —
# допустимые длительные токи по ПУЭ-7, табл. 1.3.6, графа «двухжильные» (прокладка в воздухе).
CABLE_TABLE: Final[list[dict[str, Any]]] = [
    {"section": 1.5, "max_current": 19, "name": "ВВГнг-LS 3x1.5"},
    {"section": 2.5, "max_current": 27, "name": "ВВГнг-LS 3x2.5"},
    {"section": 4.0, "max_current": 38, "name": "ВВГнг-LS 3x4"},
    {"section": 6.0, "max_current": 50, "name": "ВВГнг-LS 3x6"},
    {"section": 10.0, "max_current": 70, "name": "ВВГнг-LS 3x10"},
    {"section": 16.0, "max_current": 90, "name": "ВВГнг-LS 3x16"},
    {"section": 25.0, "max_current": 120, "name": "ВВГнг-LS 3x25"},
    {"section": 35.0, "max_current": 150, "name": "ВВГнг-LS 3x35"},
    {"section": 50.0, "max_current": 185, "name": "ВВГнг-LS 3x50"},
    {"section": 70.0, "max_current": 230, "name": "ВВГнг-LS 3x70"},
    {"section": 95.0, "max_current": 280, "name": "ВВГнг-LS 3x95"},
    {"section": 120.0, "max_current": 320, "name": "ВВГнг-LS 3x120"},
]

# Трёхфазные линии: 5-жильный кабель (L1, L2, L3, N, PE); нагружены 3 жилы —
# допустимые длительные токи по ПУЭ-7, табл. 1.3.6, графа «трёхжильные» (прокладка в воздухе).
CABLE_TABLE_3PH: Final[list[dict[str, Any]]] = [
    {"section": 1.5, "max_current": 19, "name": "ВВГнг-LS 5x1.5"},
    {"section": 2.5, "max_current": 25, "name": "ВВГнг-LS 5x2.5"},
    {"section": 4.0, "max_current": 35, "name": "ВВГнг-LS 5x4"},
    {"section": 6.0, "max_current": 42, "name": "ВВГнг-LS 5x6"},
    {"section": 10.0, "max_current": 55, "name": "ВВГнг-LS 5x10"},
    {"section": 16.0, "max_current": 75, "name": "ВВГнг-LS 5x16"},
    {"section": 25.0, "max_current": 95, "name": "ВВГнг-LS 5x25"},
    {"section": 35.0, "max_current": 120, "name": "ВВГнг-LS 5x35"},
    {"section": 50.0, "max_current": 145, "name": "ВВГнг-LS 5x50"},
    {"section": 70.0, "max_current": 180, "name": "ВВГнг-LS 5x70"},
    {"section": 95.0, "max_current": 220, "name": "ВВГнг-LS 5x95"},
    {"section": 120.0, "max_current": 260, "name": "ВВГнг-LS 5x120"},
]

# --- Номиналы автоматических выключателей (ПУЭ) ---
AUTOMAT_STEPS = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250]

# --- PoE-бюджеты (IEEE 802.3) ---
POE_BUDGETS = {
    "af": 15400,  # 15.4W per port
    "at": 30000,  # 30W per port (PoE+)
    "bt": 90000,  # 90W per port (PoE++)
}

# --- Удельное сопротивление грунтов (Ом·м) ---
SOIL_RESISTIVITY = {
    "black_earth": 50,
    "clay": 60,
    "loam": 100,
    "sand": 500,
    "rock": 5000,
    "default": 100,
}
