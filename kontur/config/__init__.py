"""КОНТУР-ПРО: модуль config."""

from __future__ import annotations

from kontur.config.building_templates import TEMPLATES, TIER_CONFIG
from kontur.config.equipment import CATEGORIES, EQUIPMENT_LIBRARY, PRICE_LIST
from kontur.config.norms import (
    AUTOMAT_STEPS,
    CABLE_TABLE,
    CABLE_TABLE_3PH,
    COS_PHI_DEFAULT,
    DEMAND_FACTORS,
    GROUND_R_MAX,
    GROUND_R_WARN,
    PHASE_IMBALANCE_MAX,
    POE_BUDGETS,
    SOIL_RESISTIVITY,
    VOLTAGE_DROP_MAX,
    VOLTAGE_DROP_WARN,
)
from kontur.config.themes import THEME_DARK, THEME_LIGHT
from kontur.config.version import SCHEMA_VERSION, VERSION, VERSION_NAME

__all__ = [
    "AUTOMAT_STEPS",
    "CABLE_TABLE",
    "CABLE_TABLE_3PH",
    "CATEGORIES",
    "COS_PHI_DEFAULT",
    "DEMAND_FACTORS",
    "EQUIPMENT_LIBRARY",
    "GROUND_R_MAX",
    "GROUND_R_WARN",
    "PHASE_IMBALANCE_MAX",
    "POE_BUDGETS",
    "PRICE_LIST",
    "SCHEMA_VERSION",
    "SOIL_RESISTIVITY",
    "TEMPLATES",
    "THEME_DARK",
    "THEME_LIGHT",
    "TIER_CONFIG",
    "VERSION",
    "VERSION_NAME",
    "VOLTAGE_DROP_MAX",
    "VOLTAGE_DROP_WARN",
]
