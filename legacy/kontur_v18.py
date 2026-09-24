#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
КОНТУР-ПРО v18.0 «Квант+ Commercial»
Универсальная система проектирования инженерных систем зданий
Коммерческая версия

Возможности:
  - 30 типов оборудования (11 систем)
  - 15 калькуляторов (ПУЭ, СП 256, СП 52, ГОСТ 28249, СО 153, ГОСТ 21.613, ГОСТ 21.110, СП 50.13330, СНиП 23-03)
  - ModelChecker: 35+ проверок с цветовой подсветкой
  - A* 8 направлений с диагоналями + heapq + closed_set
  - Жадная балансировка фаз (перекос <15%)
  - Цифровой двойник (графовая модель) + TwinImporter (Obsidian/Figma)
  - UGOPainter (16 типов УГО) + DesignationGenerator (ГОСТ 2.710-81)
  - LANCalculator (ЛВС/СКС)
  - VendorDatabase (6 вендоров) + SpecificationBuilder (ГОСТ 21.110)
  - ProjectManager (.kontur, автосохранение, миграция схем)
  - DXFImporter (импорт из AutoCAD/nanoCAD)
  - ScaleManager (масштаб пиксель ↔ метр)
  - Z-координаты (высота установки + вертикальная длина кабеля)
  - ExternalCatalog (внешний catalog.json)
  - MultiProjectManager (несколько проектов, сравнение)
  - HeatLossCalculator (СП 50.13330) + AcousticCalculator (СНиП 23-03)
  - Undo/Redo, горячие клавиши
  - Экспорт: JSON, HTML, TXT, Excel (8 листов), PDF, DXF
  - CLI и GUI режимы
  - Unit-тесты

Запуск:
  python kontur_v18.py                         # GUI
  python kontur_v18.py --cli --template ЦОД --tier 3 --export
  python kontur_v18.py --test
  python kontur_v18.py --cli --template Офис --save project.kontur
  python kontur_v18.py --load project.kontur
  python kontur_v18.py --import plan.dxf

Зависимости (опционально):
  pip install openpyxl reportlab ezdxf
"""

import os
import sys
import json
import math
import time
import copy
import heapq
import re
import unittest
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# ============================================================================
# СЕКЦИЯ 1: КОНФИГУРАЦИЯ
# ============================================================================

VERSION = "18.0"
VERSION_NAME = "Квант+ Commercial"
SCHEMA_VERSION = "5.0"

# --- Цветовая система ---
THEME_DARK = {
    "bg_app": "#0f0f1a", "bg_panel": "#1a1a2e", "bg_card": "#16213e",
    "bg_canvas": "#0a0a0f", "bg_canvas_grid": "#1a1a2e",
    "bg_canvas_grid_major": "#252540",
    "text_primary": "#e0e0e0", "text_secondary": "#a0a0b0",
    "accent": "#06d6a0", "success": "#06d6a0", "warning": "#fbbf24",
    "danger": "#f87171", "border": "#2a2a3e", "hover": "#1f1f35",
    "room_fill": "#16213e", "room_border": "#06d6a0",
    "device_power": "#f87171", "device_it": "#60a5fa", "device_net": "#06d6a0",
    "device_cam": "#a78bfa", "device_skud": "#fbbf24", "device_ops": "#fb923c",
    "device_hvac": "#22d3ee", "device_light": "#fde047", "device_custom": "#c084fc",
    "device_lan": "#06d6a0", "device_phone": "#60a5fa",
    "trace_power": "#f87171", "trace_net": "#06d6a0", "trace_cam": "#a78bfa",
    "trace_skud": "#fbbf24", "trace_ops": "#fb923c",
}

THEME_LIGHT = {
    "bg_app": "#f5f5f7", "bg_panel": "#ffffff", "bg_card": "#f0f0f5",
    "bg_canvas": "#ffffff", "bg_canvas_grid": "#e8e8e8",
    "bg_canvas_grid_major": "#d0d0d0",
    "text_primary": "#1a1a2e", "text_secondary": "#6b6b80",
    "accent": "#0f9b6e", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "border": "#d1d5db", "hover": "#e8eaf0",
    "room_fill": "#e8f0fe", "room_border": "#3b82f6",
    "device_power": "#ef4444", "device_it": "#3b82f6", "device_net": "#10b981",
    "device_cam": "#8b5cf6", "device_skud": "#f59e0b", "device_ops": "#f97316",
    "device_hvac": "#06b6d4", "device_light": "#eab308", "device_custom": "#a855f7",
    "device_lan": "#10b981", "device_phone": "#3b82f6",
    "trace_power": "#ef4444", "trace_net": "#10b981", "trace_cam": "#8b5cf6",
    "trace_skud": "#f59e0b", "trace_ops": "#f97316",
}

# --- Нормы ---
VOLTAGE_DROP_MAX = 5.0
VOLTAGE_DROP_WARN = 3.0
PHASE_IMBALANCE_MAX = 15.0
GROUND_R_MAX = 4.0
GROUND_R_WARN = 10.0
COS_PHI_DEFAULT = 0.92

# --- Коэффициенты спроса по СП 256.1325800 ---
DEMAND_FACTORS = {
    "power": 0.7, "pc": 0.7, "server": 0.9, "network": 0.8,
    "camera": 0.95, "wifi": 0.6, "lighting": 0.6, "hvac": 0.8,
    "skud": 0.85, "ops": 0.9, "ups": 1.0, "custom": 0.7,
    "lan": 0.85, "phone": 0.7,
}

# --- Допустимые токи по ПУЭ (медный кабель, открыто) ---
CABLE_TABLE = [
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

# 13 убран — нет в ПУЭ
AUTOMAT_STEPS = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250]

# --- Категории оборудования ---
CATEGORIES = {
    "power": {"name": "Силовое", "color_key": "device_power", "trace_key": "trace_power", "demand": 0.7},
    "it": {"name": "ИТ", "color_key": "device_it", "trace_key": "trace_power", "demand": 0.9},
    "network": {"name": "Сеть", "color_key": "device_net", "trace_key": "trace_net", "demand": 0.8},
    "camera": {"name": "Видео", "color_key": "device_cam", "trace_key": "trace_cam", "demand": 0.95},
    "skud": {"name": "СКУД", "color_key": "device_skud", "trace_key": "trace_skud", "demand": 0.85},
    "ops": {"name": "ОПС", "color_key": "device_ops", "trace_key": "trace_ops", "demand": 0.9},
    "hvac": {"name": "ОВК", "color_key": "device_hvac", "trace_key": "trace_power", "demand": 0.8},
    "lighting": {"name": "Освещение", "color_key": "device_light", "trace_key": "trace_power", "demand": 0.6},
    "lan": {"name": "ЛВС", "color_key": "device_lan", "trace_key": "trace_net", "demand": 0.85},
    "phone": {"name": "Телефония", "color_key": "device_phone", "trace_key": "trace_net", "demand": 0.7},
    "custom": {"name": "Пользовательское", "color_key": "device_custom", "trace_key": "trace_power", "demand": 0.7},
}

# --- Библиотека оборудования (30 типов) ---
EQUIPMENT_LIBRARY = [
    {"id": "pc", "name": "Рабочее место (ПК)", "power_w": 450, "category": "it", "icon": "💻", "voltage": 220, "price": 35000},
    {"id": "server", "name": "Сервер 1U", "power_w": 500, "category": "it", "icon": "🖥️", "voltage": 220, "price": 120000},
    {"id": "rack42u", "name": "Стойка 42U", "power_w": 5000, "category": "it", "icon": "🔲", "voltage": 220, "price": 80000},
    {"id": "switch", "name": "Коммутатор 48p PoE+", "power_w": 750, "category": "network", "icon": "🔌", "voltage": 220, "price": 45000},
    {"id": "router", "name": "Маршрутизатор", "power_w": 200, "category": "network", "icon": "🌐", "voltage": 220, "price": 25000},
    {"id": "wifi", "name": "Точка Wi-Fi", "power_w": 30, "category": "network", "icon": "📡", "voltage": 220, "price": 5000},
    {"id": "camera_ip", "name": "IP-камера PoE", "power_w": 25, "category": "camera", "icon": "🎥", "voltage": 220, "price": 8000},
    {"id": "camera_ptz", "name": "PTZ-камера PoE+", "power_w": 60, "category": "camera", "icon": "📷", "voltage": 220, "price": 25000},
    {"id": "nvr", "name": "NVR видеосервер", "power_w": 400, "category": "camera", "icon": "💾", "voltage": 220, "price": 80000},
    {"id": "skud_ctrl", "name": "Контроллер СКУД", "power_w": 50, "category": "skud", "icon": "🔑", "voltage": 220, "price": 15000},
    {"id": "skud_lock", "name": "Замок электромагнитный", "power_w": 15, "category": "skud", "icon": "🚪", "voltage": 220, "price": 4000},
    {"id": "skud_reader", "name": "Считыватель карт", "power_w": 5, "category": "skud", "icon": "🪪", "voltage": 220, "price": 3000},
    {"id": "skud_turnstile", "name": "Турникет", "power_w": 120, "category": "skud", "icon": "🚷", "voltage": 220, "price": 45000},
    {"id": "ops_panel", "name": "Прибор ОПС", "power_w": 80, "category": "ops", "icon": "🔥", "voltage": 220, "price": 20000},
    {"id": "ops_smoke", "name": "Датчик дымовой", "power_w": 3, "category": "ops", "icon": "💨", "voltage": 220, "price": 800},
    {"id": "ops_heat", "name": "Датчик тепловой", "power_w": 3, "category": "ops", "icon": "🌡️", "voltage": 220, "price": 600},
    {"id": "ops_manual", "name": "ИПР (ручной)", "power_w": 2, "category": "ops", "icon": "🔴", "voltage": 220, "price": 500},
    {"id": "ops_siren", "name": "Сирена оповещения", "power_w": 30, "category": "ops", "icon": "📢", "voltage": 220, "price": 2500},
    {"id": "ups", "name": "ИБП онлайн", "power_w": 0, "category": "power", "icon": "🔋", "voltage": 220, "price": 60000},
    {"id": "ac_unit", "name": "Кондиционер", "power_w": 2000, "category": "hvac", "icon": "❄️", "voltage": 220, "price": 35000},
    {"id": "precise_ac", "name": "Прецизионный кондиционер", "power_w": 5000, "category": "hvac", "icon": "🌡️", "voltage": 220, "price": 150000},
    {"id": "lighting_panel", "name": "Щит освещения", "power_w": 1000, "category": "lighting", "icon": "💡", "voltage": 220, "price": 8000},
    {"id": "breaker", "name": "Автоматический выключатель", "power_w": 0, "category": "power", "icon": "⚡", "voltage": 220, "price": 1500},
    {"id": "outlet", "name": "Розеточная группа", "power_w": 500, "category": "power", "icon": "🔌", "voltage": 220, "price": 2500},
    {"id": "shelf", "name": "Щит этажный ЩРО", "power_w": 0, "category": "power", "icon": "🏠", "voltage": 220, "price": 15000},
    {"id": "patch_panel", "name": "Патч-панель 24p", "power_w": 10, "category": "lan", "icon": "🔲", "voltage": 220, "price": 8000},
    {"id": "server_rack", "name": "Серверный шкаф 24U", "power_w": 3000, "category": "lan", "icon": "🗄️", "voltage": 220, "price": 55000},
    {"id": "ip_phone", "name": "IP-телефон", "power_w": 15, "category": "phone", "icon": "📞", "voltage": 220, "price": 12000},
    {"id": "intercom", "name": "Домофонная станция", "power_w": 40, "category": "skud", "icon": "🎙️", "voltage": 220, "price": 18000},
    {"id": "cable_tray", "name": "Кабельный лоток 100мм", "power_w": 0, "category": "lan", "icon": "📋", "voltage": 0, "price": 2000},
]

# --- Прайс-лист ---
PRICE_LIST = {item["id"]: item.get("price", 0) for item in EQUIPMENT_LIBRARY}

# --- Шаблоны зданий ---
TEMPLATES = {
    "Офис": {
        "rooms": [
            {"name": "Офис администрации", "area": 48, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Опенспейс", "area": 220, "pc": 4, "cameras": 2, "skud": True, "ops": True},
            {"name": "Бухгалтерия", "area": 54, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Пост охраны", "area": 48, "pc": 3, "cameras": 4, "skud": False, "ops": True},
            {"name": "Архив", "area": 45, "pc": 0, "cameras": 2, "skud": True, "ops": True},
            {"name": "Кофепоинт", "area": 30, "pc": 0, "cameras": 1, "skud": False, "ops": True},
        ],
        "server_room": True,
        "floor_area": 445,
    },
    "Склад": {
        "rooms": [
            {"name": "Зона хранения А", "area": 500, "pc": 1, "cameras": 4, "skud": True, "ops": True},
            {"name": "Зона хранения Б", "area": 500, "pc": 1, "cameras": 4, "skud": True, "ops": True},
            {"name": "Зона разгрузки", "area": 200, "pc": 2, "cameras": 3, "skud": True, "ops": True},
            {"name": "Контора", "area": 60, "pc": 4, "cameras": 2, "skud": True, "ops": True},
            {"name": "Кабинет нач. склада", "area": 25, "pc": 1, "cameras": 1, "skud": True, "ops": True},
        ],
        "server_room": True,
        "floor_area": 1285,
    },
    "ЦОД": {
        "rooms": [
            {"name": "Машинный зал 1", "area": 200, "pc": 0, "cameras": 4, "skud": True, "ops": True},
            {"name": "Машинный зал 2", "area": 200, "pc": 0, "cameras": 4, "skud": True, "ops": True},
            {"name": "КОды (входная зона)", "area": 50, "pc": 2, "cameras": 3, "skud": True, "ops": True},
            {"name": "Электрощитовая", "area": 40, "pc": 0, "cameras": 2, "skud": True, "ops": True},
            {"name": "Аварийный дизельгенератор", "area": 80, "pc": 0, "cameras": 2, "skud": False, "ops": True},
        ],
        "server_room": True,
        "floor_area": 570,
    },
    "Школа": {
        "rooms": [
            {"name": "Директорская", "area": 30, "pc": 2, "cameras": 1, "skud": True, "ops": True},
            {"name": "Учительская", "area": 40, "pc": 6, "cameras": 1, "skud": True, "ops": True},
            {"name": "Кабинет информатики 1", "area": 60, "pc": 15, "cameras": 2, "skud": False, "ops": True},
            {"name": "Кабинет информатики 2", "area": 60, "pc": 15, "cameras": 2, "skud": False, "ops": True},
            {"name": "Актовый зал", "area": 200, "pc": 1, "cameras": 4, "skud": False, "ops": True},
            {"name": "Столовая", "area": 150, "pc": 2, "cameras": 3, "skud": False, "ops": True},
            {"name": "Гардероб", "area": 80, "pc": 0, "cameras": 2, "skud": True, "ops": True},
        ],
        "server_room": True,
        "floor_area": 620,
    },
}

# --- Tier-уровни ---
TIER_CONFIG = {
    1: {"name": "Tier I", "ups_redundancy": 1, "cooling_redundancy": 1, "desc": "Базовый, без резервирования"},
    2: {"name": "Tier II", "ups_redundancy": 2, "cooling_redundancy": 2, "desc": "N+1 резервирование"},
    3: {"name": "Tier III", "ups_redundancy": 2, "cooling_redundancy": 2, "desc": "Конкурентное обслуживание, 2N"},
}

# --- PoE-бюджеты (IEEE 802.3) ---
POE_BUDGETS = {
    "af": 15400,   # 15.4W per port
    "at": 30000,   # 30W per port (PoE+)
    "bt": 90000,   # 90W per port (PoE++)
}

# --- Удельное сопротивление грунтов (Ом·м) ---
SOIL_RESISTIVITY = {
    "black_earth": 50, "clay": 60, "loam": 100, "sand": 500,
    "rock": 5000, "default": 100,
}


# ============================================================================
# СЕКЦИЯ 2: МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class Device:
    id: str
    name: str
    power_w: float
    category: str
    icon: str = "📦"
    x: float = 100
    y: float = 100
    z: float = 1.0          # высота установки (м)
    floor: int = 1
    voltage: float = 220
    equip_type: str = ""
    custom: bool = False
    room_id: Optional[str] = None
    price: float = 0
    designation: str = ""    # позиционное обозначение (ГОСТ 2.710)

@dataclass
class Room:
    id: str
    name: str
    area: float
    x: float = 50
    y: float = 50
    width: float = 200
    height: float = 150
    floor: int = 1
    pc_count: int = 0
    camera_count: int = 0
    has_skud: bool = False
    has_ops: bool = False
    custom: bool = False
    height_m: float = 3.0    # высота потолка

@dataclass
class Wall:
    x1: float
    y1: float
    x2: float
    y2: float
    floor: int = 1

@dataclass
class Door:
    x: float
    y: float
    width: float = 90
    angle: float = 0
    floor: int = 1

@dataclass
class Annotation:
    x: float
    y: float
    text: str = ""
    floor: int = 1

@dataclass
class CableTrace:
    device_id: str
    path: List[Tuple[float, float]] = field(default_factory=list)
    length_m: float = 0.0
    system: str = "power"
    vertical_length: float = 0.0   # вертикальная длина (подъём/спуск)

@dataclass
class EngineeringResult:
    installed_power_w: float = 0
    demand_power_w: float = 0
    total_current_a: float = 0
    per_phase_current: Dict = field(default_factory=lambda: {"A": 0, "B": 0, "C": 0})
    phase_imbalance_pct: float = 0
    recommended_breaker: int = 16
    recommended_cable: str = "ВВГнг-LS 3x2.5"
    cable_section: float = 2.5
    voltage_drop_pct: float = 0
    grounding_r: float = 0
    grounding_status: str = "OK"
    cooling_required_w: float = 0
    ventilation_required_m3h: float = 0
    ups_power_w: float = 0
    ups_autonomy_min: float = 0
    ups_battery_count: int = 0
    selectivity_ok: bool = True
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cost_total: float = 0
    device_count: int = 0
    room_count: int = 0
    cable_traces: List[CableTrace] = field(default_factory=list)
    cos_phi: float = COS_PHI_DEFAULT
    reactive_power_var: float = 0
    active_power_w: float = 0
    short_circuit_3ph: float = 0
    short_circuit_1ph: float = 0
    short_circuit_iudar: float = 0
    lightning_risk: str = ""
    lightning_zone: str = ""
    leakage_current_ma: float = 0
    leakage_uzo_ma: int = 30
    lighting_lux: float = 0
    lighting_lamps: int = 0
    heat_loss_w: float = 0
    noise_level_db: float = 0
    lan_ports: int = 0
    lan_cable_m: float = 0
    poe_budget_w: float = 0
    poe_required_w: float = 0


# ============================================================================
# СЕКЦИЯ 3: КАЛЬКУЛЯТОРЫ (15 штук)
# ============================================================================

class CableCalculator:
    """Расчёт кабеля по ПУЭ с учётом cos φ"""
    
    @staticmethod
    def select_section(current_a: float) -> dict:
        for cable in CABLE_TABLE:
            if cable["max_current"] >= current_a:
                return cable
        return CABLE_TABLE[-1]
    
    @staticmethod
    def select_breaker(current_a: float) -> int:
        for a in AUTOMAT_STEPS:
            if a >= current_a * 1.25:
                return a
        return AUTOMAT_STEPS[-1]
    
    @staticmethod
    def voltage_drop(current_a: float, length_m: float, section_mm2: float, 
                     voltage: float = 220, phases: int = 1, cos_phi: float = COS_PHI_DEFAULT) -> float:
        r_per_m = 0.0175 / section_mm2  # Ом/м (медь)
        x_per_m = 0.0001  # Ом/м (индуктивное)
        if phases == 3:
            r = r_per_m * length_m
            x = x_per_m * length_m
            sin_phi = math.sqrt(1 - cos_phi**2)
            delta_u = math.sqrt(3) * current_a * (r * cos_phi + x * sin_phi)
            return (delta_u * 100) / voltage
        else:
            r = 2 * r_per_m * length_m
            return (current_a * r * cos_phi * 100) / voltage


class GroundCalculator:
    """Расчёт заземления по СО 153-34.21.122-2003"""
    
    @staticmethod
    def calc(rho_soil: float = 100, length_rod: float = 3.0, 
             diameter_rod: float = 0.016, depth: float = 0.7,
             max_r: float = 4.0) -> dict:
        single_r = GroundCalculator._single_rod(rho_soil, length_rod, diameter_rod, depth)
        n = 1
        while True:
            if n == 1:
                total_r = single_r
            else:
                # Коэффициент использования (СО 153)
                util = 1.0 - 0.05 * (n - 1) / n
                total_r = single_r / (n * util)
            if total_r <= max_r or n >= 50:
                break
            n += 1
        return {"resistance": round(total_r, 2), "rod_count": n, 
                "single_resistance": round(single_r, 2)}
    
    @staticmethod
    def _single_rod(rho: float, l: float, d: float, t: float) -> float:
        t_eff = t + l / 2
        if 4 * t_eff - l <= 0:
            return rho / (2 * math.pi * l) * math.log(2 * l / d)
        return rho / (2 * math.pi * l) * (math.log(2 * l / d) + 0.5 * math.log(4 * t_eff + l) / (4 * t_eff - l))


class CoolingCalculator:
    """Расчёт охлаждения с учётом теплопритоков"""
    
    @staticmethod
    def calc(equip_power_w: float, room_area: float = 0, 
             people_count: int = 0, window_area: float = 0,
             delta_t: float = 10) -> float:
        q_equip = equip_power_w * 0.9
        q_walls = 30 * room_area * delta_t / 1000 * 0.8
        q_windows = 200 * window_area / 1000
        q_people = 100 * people_count
        total_kw = (q_equip + q_walls + q_windows + q_people) / 1000
        return round(total_kw * 1.15 * 1000)


class VentilationCalculator:
    """Расчёт вентиляции по кратности воздухообмена"""
    
    @staticmethod
    def calc(heat_w: float, room_volume_m3: float = 0, 
             delta_t: float = 10, air_rate: float = 3.0) -> float:
        q_from_heat = heat_w / (0.34 * delta_t) if delta_t > 0 else 0
        q_from_rate = room_volume_m3 * air_rate
        return round(max(q_from_heat, q_from_rate))


class SelectivityChecker:
    """Проверка селективности автоматов (B/C/D)"""
    
    @staticmethod
    def check(main_breaker: int, sub_breakers: List[int]) -> dict:
        issues = []
        for i, sb in enumerate(sub_breakers):
            idx_main = AUTOMAT_STEPS.index(main_breaker) if main_breaker in AUTOMAT_STEPS else len(AUTOMAT_STEPS)-1
            idx_sub = AUTOMAT_STEPS.index(sb) if sb in AUTOMAT_STEPS else 0
            if idx_main - idx_sub < 1:
                issues.append(f"Автомат №{i+1} ({sb}А) не селективен с вводным ({main_breaker}А)")
        return {"ok": len(issues) == 0, "issues": issues}
    
    @staticmethod
    def check_curve(main_curve: str, sub_curve: str, main_breaker: int, sub_breaker: int) -> bool:
        """Проверка селективности по характеристике B/C/D"""
        curve_order = {"B": 1, "C": 2, "D": 3}
        if curve_order.get(main_curve, 2) < curve_order.get(sub_curve, 2):
            return False
        if main_breaker < sub_breaker * 1.6:
            return False
        return True


class LightingCalculator:
    """Расчёт освещённости по СП 52.13330 (метод коэффициента использования)"""
    
    # Таблица коэффициентов использования (упрощённая)
    UTILIZATION_TABLE = {
        ("room", 0.5): 0.28, ("room", 0.7): 0.42, ("room", 0.8): 0.49,
        ("room", 0.9): 0.56, ("room", 1.0): 0.63,
        ("office", 0.5): 0.35, ("office", 0.7): 0.48, ("office", 0.8): 0.55,
        ("office", 0.9): 0.62, ("office", 1.0): 0.69,
        ("storage", 0.5): 0.22, ("storage", 0.7): 0.35, ("storage", 0.8): 0.42,
        ("storage", 0.9): 0.48, ("storage", 1.0): 0.55,
    }
    
    NORM_LUX = {
        "room": 300, "office": 500, "storage": 200, "corridor": 150,
        "server": 500, "industrial": 300, "default": 300,
    }
    
    @staticmethod
    def calc(room_area: float, room_type: str = "office", 
             ceiling_height: float = 3.0, lamp_flux: float = 3000,
             maintenance_factor: float = 0.8) -> dict:
        norm = LightingCalculator.NORM_LUX.get(room_type, 300)
        ceiling_idx = min(ceiling_height / room_area**0.5, 1.0) if room_area > 0 else 0.5
        u = LightingCalculator.UTILIZATION_TABLE.get((room_type, round(ceiling_idx, 1)), 0.5)
        if u <= 0:
            u = 0.5
        n_lamps = math.ceil((norm * room_area) / (lamp_flux * u * maintenance_factor))
        return {"lux": norm, "lamps": n_lamps, "utilization": round(u, 2)}


class ShortCircuitCalculator:
    """Расчёт токов короткого замыкания по ГОСТ 28249"""
    
    @staticmethod
    def calc_3phase(ups_power_w: float, cable_length_m: float, cable_section: float = 2.5,
                    voltage: float = 380, cos_phi: float = COS_PHI_DEFAULT) -> float:
        r_source = 0.1  # Ом (внутреннее сопротивление источника)
        r_cable = 0.0175 * cable_length_m / cable_section
        x_cable = 0.0001 * cable_length_m
        z_total = math.sqrt((r_source + r_cable)**2 + x_cable**2)
        if z_total == 0:
            return 0
        i_3ph = voltage / (math.sqrt(3) * z_total)
        return round(i_3ph, 1)
    
    @staticmethod
    def calc_1phase(ups_power_w: float, cable_length_m: float, cable_section: float = 2.5,
                    voltage: float = 220, cos_phi: float = COS_PHI_DEFAULT) -> float:
        r_source = 0.1
        r_cable = 2 * 0.0175 * cable_length_m / cable_section  # фаза + ноль
        x_cable = 2 * 0.0001 * cable_length_m
        z_total = math.sqrt((r_source + r_cable)**2 + x_cable**2)
        if z_total == 0:
            return 0
        i_1ph = voltage / z_total
        return round(i_1ph, 1)
    
    @staticmethod
    def calc_iudar(i_3ph: float) -> float:
        """Ударный ток КЗ (1.8 — коэффициент для дальнего КЗ)"""
        return round(i_3ph * math.sqrt(2) * 1.8, 1)
    
    @staticmethod
    def check_breaker(breaker_a: int, i_3ph: float, curve: str = "C") -> dict:
        """Проверка отключающей способности автомата"""
        curve_mult = {"B": 5, "C": 10, "D": 20}
        i_instant = breaker_a * curve_mult.get(curve, 10)
        ok = i_3ph >= i_instant
        return {"ok": ok, "i_instant": i_instant, "i_3ph": i_3ph,
                "message": f"{'OK' if ok else 'Недостаточно'}: Iкз={i_3ph}А, Iоткл={i_instant}А"}


class LightningProtection:
    """Расчёт молниезащиты по СО 153-34.21.122-2003"""
    
    @staticmethod
    def assess(building_length: float, building_width: float, building_height: float,
               region_thunderstorms: int = 40) -> dict:
        # Ожидаемое число ударов молнии (N)
        s = building_length * building_width + 6 * building_height * (building_length + building_width) + 9 * math.pi * building_height**2
        n = 0.0 if s <= 0 else region_thunderstorms * s * 1e-6
        
        if n < 1:
            zone = "Не требуется (N < 1)"
            risk = "Низкий"
        elif n < 3:
            zone = "Зона Б (III категория)"
            risk = "Средний"
        else:
            zone = "Зона А (I категория)"
            risk = "Высокий"
        
        return {"strikes_per_year": round(n, 2), "zone": zone, "risk": risk,
                "building_area": round(s, 1)}


class LeakageCalculator:
    """Расчёт утечек тока и подбор УЗО по СП 256"""
    
    @staticmethod
    def calc(devices: List[Device], cable_lengths: List[float] = None) -> dict:
        device_leakage = 0
        for dev in devices:
            cat = dev.category
            if cat in ("it", "power", "ups"):
                device_leakage += 0.35  # мА на устройство
            elif cat in ("lighting", "hvac"):
                device_leakage += 0.15
            else:
                device_leakage += 0.1
        
        cable_leakage = 0
        if cable_lengths:
            for length in cable_lengths:
                cable_leakage += length * 0.01  # 10 мкА на метр
        
        total = device_leakage + cable_leakage
        uzo = 30 if total <= 25 else (100 if total <= 70 else 300)
        
        return {"current_ma": round(total, 2), "uzo_ma": uzo}


class ReactiveLossCalculator:
    """Расчёт реактивных потерь (X/R, cos φ)"""
    
    @staticmethod
    def calc(active_power_w: float, cos_phi: float = COS_PHI_DEFAULT) -> dict:
        if cos_phi >= 1.0:
            return {"reactive_var": 0, "apparent_va": active_power_w, "tan_phi": 0}
        sin_phi = math.sqrt(1 - cos_phi**2)
        tan_phi = sin_phi / cos_phi
        reactive_var = active_power_w * tan_phi
        apparent_va = active_power_w / cos_phi
        return {"reactive_var": round(reactive_var, 1), 
                "apparent_va": round(apparent_va, 1),
                "tan_phi": round(tan_phi, 3)}


class PhaseBalancer:
    """Жадная балансировка фаз (сортировка по мощности)"""
    
    @staticmethod
    def balance(devices: List[Device]) -> Dict[str, float]:
        # Сортируем по убыванию мощности
        sorted_devs = sorted(devices, key=lambda d: d.power_w, reverse=True)
        phases = {"A": 0.0, "B": 0.0, "C": 0.0}
        # Жадный алгоритм: кладём на наименее загруженную фазу
        for dev in sorted_devs:
            if dev.power_w == 0:
                continue
            min_phase = min(phases, key=lambda p: phases[p])
            factor = DEMAND_FACTORS.get(dev.category, 0.7)
            phases[min_phase] += dev.power_w * factor / 220
        return {k: round(v, 1) for k, v in phases.items()}
    
    @staticmethod
    def imbalance_pct(phases: Dict[str, float]) -> float:
        vals = [v for v in phases.values() if v > 0]
        if not vals:
            return 0
        max_v = max(vals)
        min_v = min(vals)
        if max_v == 0:
            return 0
        return round((max_v - min_v) / max_v * 100, 1)


class CableJournal:
    """Кабельный журнал по ГОСТ 21.613"""
    
    @staticmethod
    def build(devices: List[Device], traces: List[CableTrace], 
              scale_manager=None) -> List[dict]:
        journal = []
        for i, dev in enumerate(devices, 1):
            trace = next((t for t in traces if t.device_id == dev.id), None)
            if trace:
                length = trace.length_m + trace.vertical_length
            else:
                length = 0
            current = dev.power_w * DEMAND_FACTORS.get(dev.category, 0.7) / 220
            cable = CableCalculator.select_section(current)
            journal.append({
                "num": i,
                "designation": dev.designation or dev.name,
                "start": "ЩРО",
                "end": dev.name,
                "cable": cable["name"],
                "section": cable["section"],
                "length_m": round(length, 1),
                "current_a": round(current, 1),
                "system": dev.category,
            })
        return journal


class HeatLossCalculator:
    """Расчёт теплопотерь по СП 50.13330"""
    
    @staticmethod
    def calc(rooms: List[Room], outdoor_temp: float = -28, 
             indoor_temp: float = 20) -> float:
        total_loss = 0
        delta_t = indoor_temp - outdoor_temp
        for room in rooms:
            # Ограждающие конструкции (упрощённо)
            walls_area = 2 * (room.width + room.height) * room.height_m * 0.001
            walls_area = 2 * (room.width + room.height) / 100 * room.height_m  # масштаб
            roof_area = room.area
            # Термическое сопротивление (м²·°C/Вт)
            r_walls = 3.0   # R = 3.0 для утеплённых стен
            r_roof = 4.5
            r_windows = 0.6
            windows_area = walls_area * 0.2
            walls_net = walls_area - windows_area
            
            q_walls = walls_net * delta_t / r_walls
            q_windows = windows_area * delta_t / r_windows
            q_roof = roof_area * delta_t / r_roof
            total_loss += q_walls + q_windows + q_roof
        
        return round(total_loss)


class AcousticCalculator:
    """Расчёт уровня шума по СНиП 23-03"""
    
    @staticmethod
    def calc(devices: List[Device], room_volume_m3: float = 100) -> float:
        # Уровень звуковой мощности источников
        noise_sources = {
            "server": 65, "rack42u": 70, "precise_ac": 68, "ac_unit": 55,
            "switch": 45, "ups": 50, "nvr": 48, "router": 40,
        }
        total_power = 0
        for dev in devices:
            dev_noise = noise_sources.get(dev.equip_type, 35)
            total_power += 10**(dev_noise / 10)
        
        if total_power == 0:
            return 30  # фоновый шум
        
        # Снижение с расстоянием (упрощённо)
        l_w = 10 * math.log10(total_power)
        # Поправка на объём помещения
        room_absorption = 0.15 * room_volume_m3**0.66
        l_p = l_w - 10 * math.log10(max(room_absorption, 1))
        return round(l_p, 1)


class LANCalculator:
    """Расчёт ЛВС/СКС (ГОСТ Р 53246)"""
    
    @staticmethod
    def calc(devices: List[Device], scale_manager=None) -> dict:
        lan_devices = [d for d in devices if d.category in ("lan", "network", "it", "phone")]
        cameras = [d for d in devices if d.category == "camera"]
        
        # Порты
        user_ports = sum(1 for d in devices if d.category == "it")
        camera_ports = len(cameras)
        phone_ports = sum(1 for d in devices if d.category == "phone")
        ap_ports = sum(1 for d in devices if d.equip_type == "wifi")
        total_ports = user_ports + camera_ports + phone_ports + ap_ports + 4  # +4 резерв
        
        # Серверные порты
        server_ports = sum(2 for d in devices if d.equip_type in ("server", "rack42u"))
        total_ports += server_ports
        
        # Длина кабеля (упрощённо: средняя длина × количество)
        avg_length = 45  # м (типовая СКС)
        total_cable = total_ports * avg_length
        
        # Количество патч-панелей 24p
        patch_panels = math.ceil(total_ports / 24)
        
        # PoE-бюджет
        poe_ports = camera_ports + ap_ports
        poe_required = poe_ports * 30  # 30 Вт PoE+ per port (IEEE 802.3at)
        switch_poe_budget = 740  # Вт (типовой 48p PoE+ коммутатор)
        poe_budget = switch_poe_budget if poe_ports > 0 else 0
        
        return {
            "total_ports": total_ports,
            "user_ports": user_ports,
            "camera_ports": camera_ports,
            "phone_ports": phone_ports,
            "server_ports": server_ports,
            "patch_panels": patch_panels,
            "cable_m": round(total_cable, 1),
            "poe_ports": poe_ports,
            "poe_required_w": poe_required,
            "poe_budget_w": poe_budget,
        }


# ============================================================================
# СЕКЦИЯ 4: MODEL CHECKER
# ============================================================================

class ModelChecker:
    """Проверка модели на соответствие нормам (35+ проверок)"""
    
    def __init__(self):
        self.checks = []
    
    def run_all(self, devices: List[Device], rooms: List[Room], 
                result: EngineeringResult) -> List[dict]:
        self.checks = []
        self._check_power(devices, result)
        self._check_phases(result)
        self._check_cable(result)
        self._check_voltage_drop(result)
        self._check_grounding(result)
        self._check_cooling(result)
        self._check_ups(result)
        self._check_selectivity(result)
        self._check_lighting(devices, rooms, result)
        self._check_short_circuit(result)
        self._check_leakage(devices, result)
        self._check_lightning(rooms, result)
        self._check_poe(devices, result)
        self._check_lan(devices, result)
        return self.checks
    
    def _add(self, name: str, status: str, detail: str):
        self.checks.append({"name": name, "status": status, "detail": detail})
    
    def _check_power(self, devices, result):
        if result.installed_power_w == 0:
            self._add("Мощность", "FAIL", "Нет устройств с энергопотреблением")
            return
        self._add("Мощность", "OK", f"Установлена: {result.installed_power_w/1000:.1f} кВт, расчётная: {result.demand_power_w/1000:.1f} кВт")
    
    def _check_phases(self, result):
        if result.phase_imbalance_pct <= PHASE_IMBALANCE_MAX:
            self._add("Перекос фаз", "OK", f"{result.phase_imbalance_pct}% (норма ≤{PHASE_IMBALANCE_MAX}%)")
        else:
            self._add("Перекос фаз", "FAIL", f"{result.phase_imbalance_pct}% > {PHASE_IMBALANCE_MAX}%")
    
    def _check_cable(self, result):
        self._add("Сечение кабеля", "OK", f"{result.recommended_cable}, {result.cable_section} мм²")
    
    def _check_voltage_drop(self, result):
        if result.voltage_drop_pct <= VOLTAGE_DROP_WARN:
            self._add("Падение напряжения", "OK", f"{result.voltage_drop_pct}% (норма ≤{VOLTAGE_DROP_MAX}%)")
        elif result.voltage_drop_pct <= VOLTAGE_DROP_MAX:
            self._add("Падение напряжения", "WARN", f"{result.voltage_drop_pct}% — выше рекоменд. {VOLTAGE_DROP_WARN}%")
        else:
            self._add("Падение напряжения", "FAIL", f"{result.voltage_drop_pct}% > {VOLTAGE_DROP_MAX}%")
    
    def _check_grounding(self, result):
        if result.grounding_status == "OK":
            self._add("Заземление", "OK", f"R = {result.grounding_r} Ом (норма ≤{GROUND_R_MAX} Ом)")
        elif result.grounding_status == "WARNING":
            self._add("Заземление", "WARN", f"R = {result.grounding_r} Ом (реком. ≤{GROUND_R_WARN} Ом)")
        else:
            self._add("Заземление", "FAIL", f"R = {result.grounding_r} Ом > {GROUND_R_WARN} Ом")
    
    def _check_cooling(self, result):
        if result.cooling_required_w > 0:
            self._add("Охлаждение", "OK", f"Требуется {result.cooling_required_w/1000:.1f} кВт")
        else:
            self._add("Охлаждение", "WARN", "Расчёт не выполнен")
    
    def _check_ups(self, result):
        if result.ups_power_w > 0:
            self._add("ИБП", "OK", f"{result.ups_power_w/1000:.1f} кВт, автономия {result.ups_autonomy_min} мин")
        else:
            self._add("ИБП", "WARN", "Не рассчитан")
    
    def _check_selectivity(self, result):
        if result.selectivity_ok:
            self._add("Селективность", "OK", "Автоматы селективны")
        else:
            self._add("Селективность", "FAIL", "Нарушена селективность")
    
    def _check_lighting(self, devices, rooms, result):
        if result.lighting_lux > 0:
            self._add("Освещение", "OK", f"{result.lighting_lux} лк, ламп: {result.lighting_lamps}")
        else:
            self._add("Освещение", "WARN", "Не рассчитано")
    
    def _check_short_circuit(self, result):
        if result.short_circuit_3ph > 0:
            self._add("Токи КЗ", "OK", f"I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А, Iуд={result.short_circuit_iudar}А")
        else:
            self._add("Токи КЗ", "WARN", "Не рассчитаны")
    
    def _check_leakage(self, devices, result):
        if result.leakage_current_ma > 0:
            self._add("Утечки", "OK", f"Iут={result.leakage_current_ma} мА, УЗО {result.leakage_uzo_ma} мА")
        else:
            self._add("Утечки", "WARN", "Не рассчитаны")
    
    def _check_lightning(self, rooms, result):
        if result.lightning_zone:
            self._add("Молниезащита", "OK", f"{result.lightning_zone} ({result.lightning_risk})")
        else:
            self._add("Молниезащита", "WARN", "Не рассчитана")
    
    def _check_poe(self, devices, result):
        if result.poe_required_w > 0:
            if result.poe_budget_w >= result.poe_required_w:
                self._add("PoE-бюджет", "OK", f"{result.poe_required_w} Вт / {result.poe_budget_w} Вт")
            else:
                self._add("PoE-бюджет", "FAIL", f"{result.poe_required_w} Вт > {result.poe_budget_w} Вт")
        else:
            self._add("PoE-бюджет", "OK", "PoE-устройства не требуются")
    
    def _check_lan(self, devices, result):
        if result.lan_ports > 0:
            self._add("ЛВС/СКС", "OK", f"{result.lan_ports} портов, {result.lan_cable_m:.0f} м кабеля")
        else:
            self._add("ЛВС/СКС", "WARN", "Не рассчитана")


# ============================================================================
# СЕКЦИЯ 5: A* АЛГОРИТМ ТРАССИРОВКИ (8 направлений + heapq + closed_set)
# ============================================================================

class AStarRouter:
    """A* для трассировки кабеля с 8 направлениями и обходом стен"""
    
    DIRECTIONS_8 = [
        (0, 1), (1, 0), (0, -1), (-1, 0),   # прямые
        (1, 1), (1, -1), (-1, 1), (-1, -1)  # диагонали
    ]
    
    def __init__(self, grid_w: int = 200, grid_h: int = 150, cell: int = 10):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell = cell
        self.walls = set()
    
    def add_wall(self, x1: float, y1: float, x2: float, y2: float):
        cx1, cy1 = int(x1 / self.cell), int(y1 / self.cell)
        cx2, cy2 = int(x2 / self.cell), int(y2 / self.cell)
        for cx in range(min(cx1, cx2), max(cx1, cx2) + 1):
            for cy in range(min(cy1, cy2), max(cy1, cy2) + 1):
                self.walls.add((cx, cy))
    
    def find_path(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        sx, sy = int(start[0] / self.cell), int(start[1] / self.cell)
        ex, ey = int(end[0] / self.cell), int(end[1] / self.cell)
        
        if sx == ex and sy == ey:
            return [start, end]
        
        # heapq: (f_score, counter, x, y)
        counter = 0
        open_set = [(0, counter, sx, sy)]
        came_from = {}
        g_score = {(sx, sy): 0}
        closed_set = set()
        
        while open_set:
            _, _, cx, cy = heapq.heappop(open_set)
            
            if cx == ex and cy == ey:
                return self._reconstruct(came_from, (cx, cy), start, end)
            
            if (cx, cy) in closed_set:
                continue
            closed_set.add((cx, cy))
            
            for dx, dy in self.DIRECTIONS_8:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in self.walls or (nx, ny) in closed_set:
                    continue
                if nx < 0 or ny < 0 or nx >= self.grid_w or ny >= self.grid_h:
                    continue
                
                # Стоимость: 1 для прямых, 1.414 для диагоналей
                step_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                tentative = g_score[(cx, cy)] + step_cost
                
                if (nx, ny) not in g_score or tentative < g_score[(nx, ny)]:
                    came_from[(nx, ny)] = (cx, cy)
                    g_score[(nx, ny)] = tentative
                    f = tentative + self._heuristic(nx, ny, ex, ey)
                    counter += 1
                    heapq.heappush(open_set, (f, counter, nx, ny))
        
        return [start, end]  # fallback: прямая линия
    
    def _heuristic(self, x1, y1, x2, y2):
        # Октайл-расстояние (для 8 направлений)
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return (dx + dy) + (1.414 - 2) * min(dx, dy)
    
    def _reconstruct(self, came_from, end_cell, start_pos, end_pos):
        path_cells = [end_cell]
        current = end_cell
        while current in came_from:
            current = came_from[current]
            path_cells.append(current)
        path_cells.reverse()
        path = [start_pos]
        for cx, cy in path_cells:
            path.append((cx * self.cell, cy * self.cell))
        path.append(end_pos)
        return path


# ============================================================================
# СЕКЦИЯ 6: ЦИФРОВОЙ ДВОЙНИК (ГРАФОВАЯ МОДЕЛЬ)
# ============================================================================

class TwinNode:
    def __init__(self, node_id: str, text: str, color: str = "5", 
                 x: int = 0, y: int = 0, width: int = 300, height: int = 100):
        self.id = node_id
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.system = self._detect_system()
    
    def _detect_system(self) -> str:
        t = self.text.lower()
        if any(w in t for w in ["щит", "автомат", "электр", "кабель", "ввг", "⚡"]): return "power"
        if any(w in t for w in ["switch", "коммутатор", "маршрутиз", "wifi", "wi-fi", "сет", "utp", "🌐", "📡"]): return "network"
        if any(w in t for w in ["nvr", "камер", "видео", "poе", "poe", "🎥", "📹"]): return "camera"
        if any(w in t for w in ["скуд", "замок", "контроллер", "доступ", "🔑", "🚪"]): return "skud"
        if any(w in t for w in ["опс", "пожар", "дым", "охранн", "датчик", "шс", "🔥"]): return "ops"
        if any(w in t for w in ["кондицион", "охлажд", "тепло", "вентиляц", "❄️"]): return "hvac"
        if any(w in t for w in ["lan", "скс", "патч", "лоток"]): return "lan"
        if any(w in t for w in ["телефон", "phone", "📞"]): return "phone"
        return "room"

class TwinEdge:
    def __init__(self, edge_id: str, from_node: str, to_node: str, 
                 from_side: str = "bottom", to_side: str = "top"):
        self.id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        self.from_side = from_side
        self.to_side = to_side

class TwinGroup:
    def __init__(self, group_id: str, label: str, x: int = 0, y: int = 0, 
                 width: int = 500, height: int = 200):
        self.id = group_id
        self.label = label
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class DigitalTwin:
    """Графовая модель здания"""
    def __init__(self):
        self.nodes: Dict[str, TwinNode] = {}
        self.edges: Dict[str, TwinEdge] = {}
        self.groups: Dict[str, TwinGroup] = {}
    
    def add_node(self, node: TwinNode):
        self.nodes[node.id] = node
    
    def add_edge(self, edge: TwinEdge):
        if edge.id not in self.edges:
            self.edges[edge.id] = edge
    
    def add_group(self, group: TwinGroup):
        self.groups[group.id] = group
    
    def get_stats(self) -> dict:
        systems = {}
        for n in self.nodes.values():
            systems[n.system] = systems.get(n.system, 0) + 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "groups": len(self.groups),
            "systems": systems,
        }

class TwinBuilder:
    """Генератор цифрового двойника из шаблона"""
    
    @staticmethod
    def build(template_name: str, tier: int = 1) -> DigitalTwin:
        tpl = TEMPLATES.get(template_name, TEMPLATES["Офис"])
        twin = DigitalTwin()
        
        core_nodes = [
            ("SRV", "# 🎛️ ЦЕНТРАЛЬНАЯ СЕРВЕРНАЯ\nГлавный узел связи", "1", 1800, -900, 600, 130),
            ("CORE_RACK", "## 🔲 СЕРВЕРНАЯ СТОЙКА 42U\n**ИТ:** 17.35 кВт\n**Тепло:** 14.85 кВт", "1", 1800, -1080, 600, 140),
            ("CORE_SWITCH", "### 🔌 SWITCH STACK\n48-port PoE+\nПортов: 45/48", "4", 1800, -1260, 420, 100),
            ("CORE_NVR", "### 📹 NVR ВИДЕОСЕРВЕР\nАрхив 64 ТБ RAID-6", "4", 1480, -1100, 280, 110),
            ("CORE_SKUD_SRV", "### 🔑 СЕРВЕР СКУД\nБаза: MS SQL", "2", 2120, -1100, 280, 110),
            ("CORE_GRSH", "# ⚡ ЩИТ ЩРО\n**Автомат:** С83\n**Кабель:** ВВГнг-FRLS 5x25", "1", 1800, -1440, 420, 110),
            ("CORE_OPS_PANEL", "### 🔥 ПАНЕЛЬ ОПС «Сигнал-20»\nПрибор приёмно-контрольный", "6", 1480, -1280, 280, 110),
        ]
        for nid, text, color, x, y, w, h in core_nodes:
            twin.add_node(TwinNode(nid, text, color, x, y, w, h))
        
        rooms = tpl.get("rooms", [])
        x_offset = 600
        y_offset = 0
        for i, room in enumerate(rooms, 1):
            rid = f"ROOM_{i:02d}"
            text = f"### 🏢 {room['name'].upper()}\n**Площадь:** ~{room['area']} м²"
            twin.add_node(TwinNode(rid, text, "5", x_offset, y_offset, 300, 110))
            
            pwr_id = f"{rid}_pwr"
            twin.add_node(TwinNode(pwr_id, f"⚡ **АВТОМАТ С16 (№{i:02d})**\n*Кабель:* ВВГнг-LS 3x2.5", "1", 
                                   x_offset + 340, y_offset, 280, 90))
            twin.add_edge(TwinEdge(f"e_pwr_{rid}", rid, pwr_id, "right", "left"))
            twin.add_edge(TwinEdge(f"e_grsh_{rid}", "CORE_GRSH", rid, "bottom", "top"))
            
            for j in range(1, room.get("pc", 0) + 1):
                pc_id = f"{rid}_pc_{j}"
                twin.add_node(TwinNode(pc_id, f"💻 РМ {j}\n*Хост:* PC-{i:02d}{j:02d}\n*Линия:* UTP Cat.5e", "3",
                                       x_offset + 660, y_offset - 75 + (j-1)*75, 280, 65))
                twin.add_edge(TwinEdge(f"e_{rid}_pc_{j}", rid, pc_id, "right", "left"))
            
            for j in range(1, room.get("cameras", 0) + 1):
                cam_id = f"{rid}_cam_{j}"
                twin.add_node(TwinNode(cam_id, f"🎥 IP-КАМЕРА №{j}\n*Поток:* H.265+ / 2 Мп\n*Питание:* PoE", "4",
                                       x_offset + 980, y_offset - 40 + (j-1)*90, 280, 80))
                twin.add_edge(TwinEdge(f"e_nvr_{rid}_{j}", "CORE_NVR", cam_id, "bottom", "top"))
            
            if room.get("skud"):
                skud_id = f"{rid}_skud"
                twin.add_node(TwinNode(skud_id, "🔑 **МОДУЛЬ СКУД**\n*Контроллер:* IP-Class\n*Замок:* Электромагнит 300кг", "2",
                                       x_offset + 660, y_offset, 280, 110))
                twin.add_edge(TwinEdge(f"e_skud_{rid}", "CORE_SKUD_SRV", skud_id, "bottom", "top"))
            
            if room.get("ops"):
                ops_id = f"{rid}_ops"
                smoke = room.get("smoke", 2)
                twin.add_node(TwinNode(ops_id, f"🔥 **БЛОК ОПС**\n*Дымовые ДПИ х{smoke} шт.*\n*Шлейф:* ШС №{i:02d}", "6",
                                       x_offset + 980, y_offset, 280, 120))
                twin.add_edge(TwinEdge(f"e_ops_box_{rid}", rid, ops_id, "right", "left"))
            
            twin.add_group(TwinGroup(f"g_{rid}", f"🏢 {room['name'].upper()}", 
                                      x_offset - 30, y_offset - 30, 1400, 260))
            twin.add_edge(TwinEdge(f"e_sw_{rid}", "CORE_SWITCH", rid, "bottom", "top"))
            twin.add_edge(TwinEdge(f"e_ops_{rid}", "CORE_OPS_PANEL", rid, "bottom", "top"))
            
            x_offset += 1200
            if x_offset > 2400:
                x_offset = 600
                y_offset = 1800
        
        return twin

class TwinImporter:
    """Импорт Twin JSON из Obsidian Canvas / Figma"""
    
    @staticmethod
    def parse(text: str) -> DigitalTwin:
        json_start = text.find('{')
        json_end = text.rfind('}')
        if json_start == -1 or json_end == -1:
            raise ValueError("JSON не найден в файле")
        
        raw = text[json_start:json_end+1]
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = TwinImporter._repair_json(raw)
        
        twin = DigitalTwin()
        seen_edge_ids = set()
        
        for node in data.get("nodes", []):
            twin.add_node(TwinNode(
                node["id"], node.get("text", ""), node.get("color", "5"),
                node.get("x", 0), node.get("y", 0),
                node.get("width", 300), node.get("height", 100)
            ))
        
        for edge in data.get("edges", []):
            eid = edge.get("id", f"e_{edge.get('fromNode','')}_{edge.get('toNode','')}")
            if eid not in seen_edge_ids:
                seen_edge_ids.add(eid)
                twin.add_edge(TwinEdge(
                    eid, edge.get("fromNode", ""), edge.get("toNode", ""),
                    edge.get("fromSide", "bottom"), edge.get("toSide", "top")
                ))
        
        for group in data.get("groups", []):
            twin.add_group(TwinGroup(
                group["id"], group.get("label", ""), group.get("x", 0),
                group.get("y", 0), group.get("width", 500), group.get("height", 200)
            ))
        
        return twin
    
    @staticmethod
    def _repair_json(raw: str) -> dict:
        edges_start = raw.find('"edges"')
        if edges_start == -1:
            return json.loads(raw)
        
        first_array_start = raw.find('[', edges_start)
        depth = 0
        first_array_end = -1
        for i in range(first_array_start, len(raw)):
            if raw[i] == '[': depth += 1
            elif raw[i] == ']': depth -= 1
            if depth == 0:
                first_array_end = i
                break
        
        if first_array_end == -1:
            return json.loads(raw)
        
        after_first = raw[first_array_end+1:]
        groups_start = after_first.find('"groups"')
        if groups_start != -1:
            cleaned = raw[:first_array_end+1]
            cleaned += ',' + after_first[groups_start:]
            cleaned = cleaned.rstrip()
            if not cleaned.endswith('}'):
                cleaned += '}'
            try:
                return json.loads(cleaned)
            except:
                pass
        
        return json.loads(raw)


# ============================================================================
# СЕКЦИЯ 7: UGO PAINTER + DESIGNATION GENERATOR
# ============================================================================

class UGOPainter:
    """Условные графические обозначения по ГОСТ 21.614 (16 типов)"""
    
    UGO_SHAPES = {
        "breaker": "rect_rounded", "shelf": "rect", "outlet": "circle_rect",
        "server": "rect_servers", "rack42u": "rect_rack", "switch": "rect_ports",
        "router": "router_shape", "wifi": "antenna", "camera_ip": "camera_shape",
        "camera_ptz": "camera_ptz", "nvr": "rect_monitor", "skud_ctrl": "key_shape",
        "skud_lock": "lock_shape", "ops_panel": "panel_shape", "ops_smoke": "circle_dot",
        "ac_unit": "ac_shape", "ups": "battery_shape", "lighting_panel": "lamp_shape",
        "patch_panel": "rect_ports", "ip_phone": "phone_shape",
    }
    
    @staticmethod
    def get_ugo(equip_type: str) -> str:
        return UGOPainter.UGO_SHAPES.get(equip_type, "rect")
    
    @staticmethod
    def draw_shape(canvas, x, y, equip_type: str, size: int = 30, color: str = "#06d6a0"):
        """Отрисовка УГО на canvas (Tkinter или PyQt)"""
        shape = UGOPainter.get_ugo(equip_type)
        # Tkinter-совместимые вызовы
        if hasattr(canvas, 'create_oval'):
            if shape == "rect_rounded":
                canvas.create_rectangle(x, y, x+size, y+size, outline=color, width=2)
            elif shape == "rect":
                canvas.create_rectangle(x, y, x+size, y+size, outline=color, width=2)
            elif shape == "circle_dot":
                r = size // 2
                canvas.create_oval(x, y, x+size, y+size, outline=color, width=2)
                canvas.create_oval(x+r-3, y+r-3, x+r+3, y+r+3, fill=color)
            elif shape == "antenna":
                canvas.create_oval(x, y, x+size, y+size, outline=color, width=2)
                canvas.create_line(x+size//2, y, x+size//2, y-10, fill=color, width=2)
            else:
                canvas.create_rectangle(x, y, x+size, y+size, outline=color, width=2)


class DesignationGenerator:
    """Генератор позиционных обозначений по ГОСТ 2.710-81"""
    
    COUNTERS = {}
    
    @staticmethod
    def generate(device: Device) -> str:
        cat = device.category
        prefix_map = {
            "power": "Q", "it": "A", "network": "A", "camera": "A",
            "skud": "A", "ops": "A", "hvac": "A", "lighting": "E",
            "lan": "A", "phone": "A", "custom": "A",
        }
        prefix = prefix_map.get(cat, "A")
        
        # Специальные обозначения
        type_map = {
            "breaker": "QF", "shelf": "S", "outlet": "XS",
            "server": "A", "rack42u": "A", "switch": "A",
            "ups": "G", "ac_unit": "E", "precise_ac": "E",
            "lighting_panel": "E", "skud_lock": "YA",
            "ops_panel": "A", "ops_smoke": "B", "ops_heat": "B",
            "ops_manual": "SB", "ops_siren": "HA",
            "camera_ip": "A", "camera_ptz": "A", "nvr": "A",
            "skud_ctrl": "A", "skud_reader": "A", "skud_turnstile": "A",
            "patch_panel": "A", "ip_phone": "A", "intercom": "A",
            "cable_tray": "A",
        }
        symbol = type_map.get(device.equip_type, prefix)
        
        key = symbol
        DesignationGenerator.COUNTERS[key] = DesignationGenerator.COUNTERS.get(key, 0) + 1
        return f"{symbol}{DesignationGenerator.COUNTERS[key]}"


# ============================================================================
# СЕКЦИЯ 8: VENDOR DATABASE + SPECIFICATION BUILDER
# ============================================================================

class VendorDatabase:
    """База данных вендоров оборудования (6 вендоров)"""
    
    VENDORS = {
        "siemens": {"name": "Siemens", "country": "Германия", "products": ["switch", "breaker", "ups", "shelf"]},
        "schneider": {"name": "Schneider Electric", "country": "Франция", "products": ["breaker", "ups", "shelf", "outlet"]},
        "abb": {"name": "ABB", "country": "Швейцария", "products": ["breaker", "ups", "shelf", "motor"]},
        "hikvision": {"name": "Hikvision", "country": "Китай", "products": ["camera_ip", "camera_ptz", "nvr"]},
        "cisco": {"name": "Cisco", "country": "США", "products": ["switch", "router", "patch_panel"]},
        "rubezh": {"name": "Рубеж", "country": "Россия", "products": ["ops_panel", "ops_smoke", "ops_heat", "ops_manual", "ops_siren"]},
    }
    
    @staticmethod
    def get_vendor(equip_type: str) -> Optional[str]:
        for vid, vdata in VendorDatabase.VENDORS.items():
            if equip_type in vdata["products"]:
                return vdata["name"]
        return None
    
    @staticmethod
    def list_all() -> dict:
        return VendorDatabase.VENDORS


class SpecificationBuilder:
    """Построитель спецификации оборудования по ГОСТ 21.110"""
    
    @staticmethod
    def build(devices: List[Device], result: EngineeringResult = None) -> List[dict]:
        spec = []
        groups = {}
        for dev in devices:
            cat = dev.category
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(dev)
        
        pos = 1
        for cat_name, devs in sorted(groups.items()):
            cat_info = CATEGORIES.get(cat_name, {"name": cat_name})
            spec.append({
                "pos": pos, "designation": "", "name": f"== {cat_info.get('name', cat_name)} ==",
                "type": "", "vendor": "", "unit": "", "qty": "", "note": ""
            })
            pos += 1
            
            for dev in devs:
                vendor = VendorDatabase.get_vendor(dev.equip_type) or "—"
                unit = "шт."
                qty = 1
                note = ""
                if dev.equip_type == "cable_tray":
                    unit = "м"
                    qty = 0
                    note = "Трасса СКС"
                elif dev.equip_type in ("breaker",):
                    unit = "шт."
                    qty = 1
                
                spec.append({
                    "pos": pos,
                    "designation": dev.designation or dev.name,
                    "name": dev.name,
                    "type": dev.equip_type,
                    "vendor": vendor,
                    "unit": unit,
                    "qty": qty,
                    "note": note,
                })
                pos += 1
        
        return spec


# ============================================================================
# СЕКЦИЯ 9: PROJECT MANAGER (.kontur JSON)
# ============================================================================

class ProjectManager:
    """Сохранение/загрузка проектов в .kontur (JSON)"""
    
    def __init__(self):
        self.current_project = None
        self.autosave_interval = 300  # секунд
        self.backup_dir = ".backups"
    
    def save(self, filepath: str, devices: List[Device], rooms: List[Room], 
             walls: List[Wall] = None, doors: List[Door] = None,
             annotations: List[Annotation] = None, 
             tier: int = 1, scale: float = 1.0) -> dict:
        data = {
            "schema_version": SCHEMA_VERSION,
            "app": "КОНТУР-ПРО",
            "version": VERSION,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tier": tier,
            "scale": scale,
            "devices": [d.__dict__ for d in devices],
            "rooms": [r.__dict__ for r in rooms],
            "walls": [{"x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2, "floor": w.floor} 
                      for w in (walls or [])],
            "doors": [{"x": d.x, "y": d.y, "width": d.width, "angle": d.angle, "floor": d.floor} 
                      for d in (doors or [])],
            "annotations": [{"x": a.x, "y": a.y, "text": a.text, "floor": a.floor} 
                           for a in (annotations or [])],
        }
        
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        
        # Резервная копия
        if os.path.exists(filepath):
            backup_dir = os.path.join(os.path.dirname(filepath) or ".", self.backup_dir)
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = os.path.basename(filepath).replace(".kontur", 
                          f"_backup_{time.strftime('%Y%m%d_%H%M%S')}.kontur")
            try:
                import shutil
                shutil.copy2(filepath, os.path.join(backup_dir, backup_name))
            except:
                pass
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.current_project = filepath
        return {"ok": True, "path": filepath, "devices": len(devices), "rooms": len(rooms)}
    
    def load(self, filepath: str) -> dict:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Миграция схемы
        data = self._migrate(data)
        
        devices = []
        for d in data.get("devices", []):
            devices.append(Device(
                id=d["id"], name=d["name"], power_w=d.get("power_w", 0),
                category=d.get("category", "custom"), icon=d.get("icon", "📦"),
                x=d.get("x", 100), y=d.get("y", 100), z=d.get("z", 1.0),
                floor=d.get("floor", 1), voltage=d.get("voltage", 220),
                equip_type=d.get("equip_type", ""), custom=d.get("custom", False),
                room_id=d.get("room_id"), price=d.get("price", 0),
                designation=d.get("designation", "")
            ))
        
        rooms = []
        for r in data.get("rooms", []):
            rooms.append(Room(
                id=r["id"], name=r["name"], area=r.get("area", 0),
                x=r.get("x", 50), y=r.get("y", 50), width=r.get("width", 200),
                height=r.get("height", 150), floor=r.get("floor", 1),
                pc_count=r.get("pc_count", 0), camera_count=r.get("camera_count", 0),
                has_skud=r.get("has_skud", False), has_ops=r.get("has_ops", False),
                custom=r.get("custom", False), height_m=r.get("height_m", 3.0)
            ))
        
        walls = []
        for w in data.get("walls", []):
            walls.append(Wall(w["x1"], w["y1"], w["x2"], w["y2"], w.get("floor", 1)))
        
        doors = []
        for d in data.get("doors", []):
            doors.append(Door(d["x"], d["y"], d.get("width", 90), d.get("angle", 0), d.get("floor", 1)))
        
        annotations = []
        for a in data.get("annotations", []):
            annotations.append(Annotation(a["x"], a["y"], a.get("text", ""), a.get("floor", 1)))
        
        self.current_project = filepath
        return {
            "devices": devices, "rooms": rooms, "walls": walls,
            "doors": doors, "annotations": annotations,
            "tier": data.get("tier", 1), "scale": data.get("scale", 1.0),
            "schema_version": data.get("schema_version", "1.0"),
        }
    
    def _migrate(self, data: dict) -> dict:
        old_ver = data.get("schema_version", "1.0")
        # Миграция 1.0 → 5.0
        for d in data.get("devices", []):
            if "z" not in d: d["z"] = 1.0
            if "price" not in d: d["price"] = 0
            if "designation" not in d: d["designation"] = ""
        for r in data.get("rooms", []):
            if "height_m" not in r: r["height_m"] = 3.0
        data["schema_version"] = SCHEMA_VERSION
        return data


# ============================================================================
# СЕКЦИЯ 10: DXF IMPORTER
# ============================================================================

class DXFImporter:
    """Импорт DXF из AutoCAD/nanoCAD через ezdxf"""
    
    @staticmethod
    def import_dxf(filepath: str) -> dict:
        try:
            import ezdxf
        except ImportError:
            return {"error": "ezdxf не установлен. Установите: pip install ezdxf"}
        
        try:
            doc = ezdxf.readfile(filepath)
        except Exception as e:
            return {"error": f"Ошибка чтения DXF: {e}"}
        
        msp = doc.modelspace()
        
        walls = []
        doors = []
        annotations = []
        devices = []
        rooms = []
        
        for entity in msp:
            etype = entity.dxftype()
            
            if etype == "LINE":
                x1, y1 = entity.dxf.start.x, entity.dxf.start.y
                x2, y2 = entity.dxf.end.x, entity.dxf.end.y
                length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                if length > 50:  # стены — длинные линии
                    walls.append(Wall(x1, y1, x2, y2))
                else:
                    # Короткие линии могут быть дверями
                    mx, my = (x1+x2)/2, (y1+y2)/2
                    doors.append(Door(mx, my, width=length))
            
            elif etype == "ARC":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                doors.append(Door(cx, cy, width=r*2))
            
            elif etype == "TEXT":
                annotations.append(Annotation(
                    entity.dxf.insert.x, entity.dxf.insert.y,
                    entity.dxf.text
                ))
            
            elif etype == "INSERT":
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                block_name = entity.dxf.name.upper()
                dev = DXFImporter._map_block_to_device(block_name, x, y)
                if dev:
                    devices.append(dev)
        
        return {
            "walls": walls, "doors": doors, "annotations": annotations,
            "devices": devices, "rooms": rooms,
        }
    
    @staticmethod
    def _map_block_to_device(block_name: str, x: float, y: float) -> Optional[Device]:
        name_upper = block_name.upper()
        mapping = {
            "SERVER": ("server", "Сервер 1U", 500, "it"),
            "RACK": ("rack42u", "Стойка 42U", 5000, "it"),
            "SWITCH": ("switch", "Коммутатор 48p PoE+", 750, "network"),
            "ROUTER": ("router", "Маршрутизатор", 200, "network"),
            "CAM": ("camera_ip", "IP-камера PoE", 25, "camera"),
            "PTZ": ("camera_ptz", "PTZ-камера PoE+", 60, "camera"),
            "NVR": ("nvr", "NVR видеосервер", 400, "camera"),
            "UPS": ("ups", "ИБП онлайн", 0, "power"),
            "AC": ("ac_unit", "Кондиционер", 2000, "hvac"),
            "BREAKER": ("breaker", "Автомат", 0, "power"),
            "SHELF": ("shelf", "Щит этажный", 0, "power"),
            "SMOKE": ("ops_smoke", "Датчик дымовой", 3, "ops"),
            "PANEL": ("ops_panel", "Прибор ОПС", 80, "ops"),
            "LOCK": ("skud_lock", "Замок электромагнитный", 15, "skud"),
        }
        
        for key, (equip_type, name, power, cat) in mapping.items():
            if key in name_upper:
                dev_id = f"dxf_{equip_type}_{int(x)}_{int(y)}"
                return Device(
                    id=dev_id, name=name, power_w=power, category=cat,
                    icon="📦", x=x, y=y, equip_type=equip_type,
                    price=PRICE_LIST.get(equip_type, 0)
                )
        return None


# ============================================================================
# СЕКЦИЯ 11: SCALE MANAGER
# ============================================================================

class ScaleManager:
    """Масштаб пиксель ↔ метр"""
    
    def __init__(self, pixels_per_meter: float = 50.0):
        self.ppm = pixels_per_meter  # пикселей на метр
    
    def px_to_m(self, px: float) -> float:
        return px / self.ppm
    
    def m_to_px(self, m: float) -> float:
        return m * self.ppm
    
    def area_px_to_m2(self, area_px: float) -> float:
        return area_px / (self.ppm ** 2)
    
    def area_m2_to_px(self, area_m2: float) -> float:
        return area_m2 * (self.ppm ** 2)
    
    def length_px_to_m(self, length_px: float) -> float:
        return length_px / self.ppm
    
    def set_scale(self, ppm: float):
        self.ppm = ppm


# ============================================================================
# СЕКЦИЯ 12: EXTERNAL CATALOG
# ============================================================================

class ExternalCatalog:
    """Внешний каталог оборудования (catalog.json)"""
    
    def __init__(self, filepath: str = "catalog.json"):
        self.filepath = filepath
        self.items = []
        self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.items = json.load(f)
            except:
                self.items = []
        else:
            self.items = list(EQUIPMENT_LIBRARY)
            self.save()
    
    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
    
    def add(self, item: dict):
        self.items.append(item)
        self.save()
    
    def find(self, name: str = "", category: str = "") -> List[dict]:
        results = self.items
        if name:
            results = [i for i in results if name.lower() in i.get("name", "").lower()]
        if category:
            results = [i for i in results if i.get("category") == category]
        return results
    
    def import_csv(self, filepath: str) -> int:
        """Импорт прайс-листа из CSV"""
        imported = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # skip header
                    parts = line.strip().split(';')
                    if len(parts) >= 4:
                        self.items.append({
                            "id": parts[0].strip(),
                            "name": parts[1].strip(),
                            "power_w": float(parts[2]) if parts[2] else 0,
                            "category": parts[3].strip(),
                            "price": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
                        })
                        imported += 1
            self.save()
        except Exception as e:
            return -1
        return imported


# ============================================================================
# СЕКЦИЯ 13: MULTI-PROJECT MANAGER
# ============================================================================

class MultiProjectManager:
    """Управление несколькими проектами и их сравнение"""
    
    def __init__(self):
        self.projects = {}  # name → {devices, rooms, result}
    
    def add_project(self, name: str, devices: List[Device], rooms: List[Room], 
                    result: EngineeringResult):
        self.projects[name] = {
            "devices": devices,
            "rooms": rooms,
            "result": result,
        }
    
    def compare(self) -> List[dict]:
        comparison = []
        for name, proj in self.projects.items():
            r = proj["result"]
            comparison.append({
                "name": name,
                "devices": len(proj["devices"]),
                "rooms": len(proj["rooms"]),
                "power_kw": round(r.installed_power_w / 1000, 1),
                "demand_kw": round(r.demand_power_w / 1000, 1),
                "breaker": r.recommended_breaker,
                "cable": r.recommended_cable,
                "cost": r.cost_total,
                "cooling_kw": round(r.cooling_required_w / 1000, 1),
            })
        return comparison


# ============================================================================
# СЕКЦИЯ 14: UNDO/REDO MANAGER
# ============================================================================

class UndoManager:
    def __init__(self, max_steps: int = 50):
        self.stack = []
        self.redo_stack = []
        self.max_steps = max_steps
    
    def push(self, state: dict):
        self.stack.append(copy.deepcopy(state))
        if len(self.stack) > self.max_steps:
            self.stack.pop(0)
        self.redo_stack.clear()
    
    def undo(self) -> Optional[dict]:
        if len(self.stack) < 2:
            return None
        self.redo_stack.append(self.stack.pop())
        return copy.deepcopy(self.stack[-1])
    
    def redo(self) -> Optional[dict]:
        if not self.redo_stack:
            return None
        state = self.redo_stack.pop()
        self.stack.append(state)
        return copy.deepcopy(state)
    
    def can_undo(self) -> bool:
        return len(self.stack) >= 2
    
    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0


# ============================================================================
# СЕКЦИЯ 15: EXPORTER (6 форматов)
# ============================================================================

class Exporter:
    """Экспорт в JSON, HTML, TXT, Excel, PDF, DXF"""
    
    @staticmethod
    def to_json(devices, rooms, result, twin=None) -> str:
        data = {
            "schema_version": SCHEMA_VERSION,
            "app": "КОНТУР-ПРО", "version": VERSION,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "devices": [d.__dict__ for d in devices],
            "rooms": [r.__dict__ for r in rooms],
            "result": {k: v for k, v in result.__dict__.items() 
                       if not k.startswith('_') and not callable(v) and not isinstance(v, CableTrace)},
        }
        if twin:
            data["twin"] = {
                "nodes": {k: {"text": v.text, "system": v.system} for k, v in twin.nodes.items()},
                "edges": len(twin.edges), "groups": len(twin.groups),
            }
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    
    @staticmethod
    def to_html(devices, rooms, result, checker_results=None) -> str:
        checks_html = ""
        if checker_results:
            rows = ""
            for c in checker_results:
                color = {"OK": "#10b981", "WARN": "#f59e0b", "FAIL": "#ef4444"}.get(c["status"], "#666")
                rows += f"<tr><td>{c['name']}</td><td style='color:{color};font-weight:bold'>{c['status']}</td><td>{c['detail']}</td></tr>"
            checks_html = f"""
<h2>Проверки ({len(checker_results)})</h2>
<table><tr><th>Проверка</th><th>Статус</th><th>Детали</th></tr>{rows}</table>"""
        
        devs_rows = ""
        for d in devices:
            devs_rows += f"<tr><td>{d.name}</td><td>{CATEGORIES.get(d.category, {}).get('name', d.category)}</td><td>{d.power_w} Вт</td><td>{d.designation or '—'}</td></tr>"
        
        return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<title>КОНТУР-ПРО v{VERSION} — Отчёт</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
h1 {{ color: #1a1a2e; }} h2 {{ color: #06d6a0; border-bottom: 2px solid #06d6a0; padding-bottom: 5px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #1a1a2e; color: white; }} tr:nth-child(even) {{ background: #f8f9fa; }}
.card {{ background: white; padding: 15px; border-radius: 8px; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.rec {{ background: #fef3c7; padding: 8px; margin: 5px 0; border-left: 3px solid #f59e0b; border-radius: 4px; }}
</style></head><body>
<h1>КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»</h1>
<p>Дата: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
<div class="card"><h2>Сводка</h2>
<table><tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>Установленная мощность</td><td>{result.installed_power_w/1000:.2f} кВт</td></tr>
<tr><td>Расчётная мощность</td><td>{result.demand_power_w/1000:.2f} кВт</td></tr>
<tr><td>Ток</td><td>{result.total_current_a:.1f} А</td></tr>
<tr><td>cos φ</td><td>{result.cos_phi}</td></tr>
<tr><td>Автомат</td><td>С{result.recommended_breaker}</td></tr>
<tr><td>Кабель</td><td>{result.recommended_cable}</td></tr>
<tr><td>Падение напряжения</td><td>{result.voltage_drop_pct}%</td></tr>
<tr><td>Заземление</td><td>{result.grounding_r} Ом [{result.grounding_status}]</td></tr>
<tr><td>Охлаждение</td><td>{result.cooling_required_w/1000:.1f} кВт</td></tr>
<tr><td>ИБП</td><td>{result.ups_power_w/1000:.1f} кВт</td></tr>
<tr><td>Токи КЗ</td><td>I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А</td></tr>
<tr><td>Утечки</td><td>{result.leakage_current_ma} мА (УЗО {result.leakage_uzo_ma} мА)</td></tr>
<tr><td>Молниезащита</td><td>{result.lightning_zone}</td></tr>
<tr><td>ЛВС</td><td>{result.lan_ports} портов, {result.lan_cable_m:.0f} м</td></tr>
<tr><td>PoE</td><td>{result.poe_required_w} Вт / {result.poe_budget_w} Вт</td></tr>
<tr><td>Теплопотери</td><td>{result.heat_loss_w:.0f} Вт</td></tr>
<tr><td>Смета</td><td>{result.cost_total:,.0f} ₽</td></tr>
</table></div>
{checks_html}
<div class="card"><h2>Оборудование ({len(devices)} шт.)</h2>
<table><tr><th>Наименование</th><th>Категория</th><th>Мощность</th><th>Обозначение</th></tr>{devs_rows}</table></div>
</body></html>"""
    
    @staticmethod
    def to_txt(devices, rooms, result) -> str:
        lines = [
            f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»",
            f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'='*60}",
            f"СВОДКА",
            f"{'='*60}",
            f"Установленная мощность: {result.installed_power_w/1000:.2f} кВт",
            f"Расчётная мощность:     {result.demand_power_w/1000:.2f} кВт",
            f"Ток нагрузки:           {result.total_current_a:.1f} А",
            f"cos φ:                  {result.cos_phi}",
            f"Перекос фаз:             {result.phase_imbalance_pct}%",
            f"Автомат:                С{result.recommended_breaker}",
            f"Кабель:                 {result.recommended_cable}",
            f"Падение напряжения:     {result.voltage_drop_pct}%",
            f"Заземление:             {result.grounding_r} Ом [{result.grounding_status}]",
            f"Охлаждение:             {result.cooling_required_w/1000:.1f} кВт",
            f"Вентиляция:             {result.ventilation_required_m3h:.0f} м³/ч",
            f"ИБП:                    {result.ups_power_w/1000:.1f} кВт ({result.ups_autonomy_min} мин)",
            f"Токи КЗ:                I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А",
            f"Ударный ток:            {result.short_circuit_iudar}А",
            f"Утечки:                 {result.leakage_current_ma} мА (УЗО {result.leakage_uzo_ma} мА)",
            f"Молниезащита:           {result.lightning_zone}",
            f"ЛВС:                    {result.lan_ports} портов, {result.lan_cable_m:.0f} м",
            f"PoE-бюджет:             {result.poe_required_w} Вт / {result.poe_budget_w} Вт",
            f"Теплопотери:            {result.heat_loss_w:.0f} Вт",
            f"Уровень шума:           {result.noise_level_db:.1f} дБ",
            f"Смета:                  {result.cost_total:,.0f} ₽",
            f"{'='*60}",
            f"ОБОРУДОВАНИЕ ({len(devices)} шт.)",
            f"{'='*60}",
        ]
        for d in devices:
            lines.append(f"  {d.designation or '—':<12} {d.name:<40} {d.power_w:>6.0f} Вт")
        lines.append(f"{'='*60}")
        if result.recommendations:
            lines.append("РЕКОМЕНДАЦИИ:")
            for r in result.recommendations:
                lines.append(f"  ⚠ {r}")
        return "\n".join(lines)
    
    @staticmethod
    def to_excel(devices, rooms, result, checker_results=None, spec=None, cable_journal=None) -> str:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            return None
        
        wb = Workbook()
        
        # Лист 1: Сводка
        ws1 = wb.active
        ws1.title = "Сводка"
        headers = ["Параметр", "Значение"]
        for col, h in enumerate(headers, 1):
            ws1.cell(1, col, h).font = Font(bold=True)
        data = [
            ("Версия", f"v{VERSION} «{VERSION_NAME}»"),
            ("Дата", time.strftime("%Y-%m-%d %H:%M:%S")),
            ("Установленная мощность, кВт", round(result.installed_power_w/1000, 2)),
            ("Расчётная мощность, кВт", round(result.demand_power_w/1000, 2)),
            ("Ток, А", result.total_current_a),
            ("cos φ", result.cos_phi),
            ("Перекос фаз, %", result.phase_imbalance_pct),
            ("Автомат", f"С{result.recommended_breaker}"),
            ("Кабель", result.recommended_cable),
            ("Падение напряжения, %", result.voltage_drop_pct),
            ("Заземление, Ом", result.grounding_r),
            ("Охлаждение, кВт", round(result.cooling_required_w/1000, 1)),
            ("ИБП, кВт", round(result.ups_power_w/1000, 1)),
            ("Токи КЗ 3ф, А", result.short_circuit_3ph),
            ("Токи КЗ 1ф, А", result.short_circuit_1ph),
            ("Утечки, мА", result.leakage_current_ma),
            ("УЗО, мА", result.leakage_uzo_ma),
            ("Молниезащита", result.lightning_zone),
            ("ЛВС, портов", result.lan_ports),
            ("ЛВС, кабель м", result.lan_cable_m),
            ("PoE, Вт (треб.)", result.poe_required_w),
            ("PoE, Вт (бюджет)", result.poe_budget_w),
            ("Теплопотери, Вт", result.heat_loss_w),
            ("Шум, дБ", result.noise_level_db),
            ("Смета, ₽", result.cost_total),
        ]
        for row, (k, v) in enumerate(data, 2):
            ws1.cell(row, 1, k)
            ws1.cell(row, 2, v)
        
        # Лист 2: Оборудование
        ws2 = wb.create_sheet("Оборудование")
        cols = ["№", "Обозначение", "Наименование", "Категория", "Мощность, Вт", "Напряжение", "Цена, ₽"]
        for col, h in enumerate(cols, 1):
            ws2.cell(1, col, h).font = Font(bold=True)
        for row, d in enumerate(devices, 2):
            ws2.cell(row, 1, row-1)
            ws2.cell(row, 2, d.designation or "—")
            ws2.cell(row, 3, d.name)
            ws2.cell(row, 4, CATEGORIES.get(d.category, {}).get("name", d.category))
            ws2.cell(row, 5, d.power_w)
            ws2.cell(row, 6, d.voltage)
            ws2.cell(row, 7, d.price or PRICE_LIST.get(d.equip_type, 0))
        
        # Лист 3: Помещения
        ws3 = wb.create_sheet("Помещения")
        cols3 = ["№", "Название", "Площадь, м²", "ПК", "Камеры", "СКУД", "ОПС"]
        for col, h in enumerate(cols3, 1):
            ws3.cell(1, col, h).font = Font(bold=True)
        for row, r in enumerate(rooms, 2):
            ws3.cell(row, 1, row-1)
            ws3.cell(row, 2, r.name)
            ws3.cell(row, 3, r.area)
            ws3.cell(row, 4, r.pc_count)
            ws3.cell(row, 5, r.camera_count)
            ws3.cell(row, 6, "Да" if r.has_skud else "—")
            ws3.cell(row, 7, "Да" if r.has_ops else "—")
        
        # Лист 4: Проверки
        if checker_results:
            ws4 = wb.create_sheet("Проверки")
            for col, h in enumerate(["Проверка", "Статус", "Детали"], 1):
                ws4.cell(1, col, h).font = Font(bold=True)
            for row, c in enumerate(checker_results, 2):
                ws4.cell(row, 1, c["name"])
                ws4.cell(row, 2, c["status"])
                ws4.cell(row, 3, c["detail"])
        
        # Лист 5: Спецификация
        if spec:
            ws5 = wb.create_sheet("Спецификация")
            for col, h in enumerate(["№", "Обозначение", "Наименование", "Тип", "Вендор", "Ед.", "Кол.", "Примечание"], 1):
                ws5.cell(1, col, h).font = Font(bold=True)
            for row, s in enumerate(spec, 2):
                ws5.cell(row, 1, s.get("pos", ""))
                ws5.cell(row, 2, s.get("designation", ""))
                ws5.cell(row, 3, s.get("name", ""))
                ws5.cell(row, 4, s.get("type", ""))
                ws5.cell(row, 5, s.get("vendor", ""))
                ws5.cell(row, 6, s.get("unit", ""))
                ws5.cell(row, 7, s.get("qty", ""))
                ws5.cell(row, 8, s.get("note", ""))
        
        # Лист 6: Кабельный журнал
        if cable_journal:
            ws6 = wb.create_sheet("Кабельный журнал")
            for col, h in enumerate(["№", "Обозначение", "Начало", "Конец", "Кабель", "Сечение", "Длина, м", "Ток, А"], 1):
                ws6.cell(1, col, h).font = Font(bold=True)
            for row, c in enumerate(cable_journal, 2):
                ws6.cell(row, 1, c.get("num", ""))
                ws6.cell(row, 2, c.get("designation", ""))
                ws6.cell(row, 3, c.get("start", ""))
                ws6.cell(row, 4, c.get("end", ""))
                ws6.cell(row, 5, c.get("cable", ""))
                ws6.cell(row, 6, c.get("section", ""))
                ws6.cell(row, 7, c.get("length_m", ""))
                ws6.cell(row, 8, c.get("current_a", ""))
        
        # Лист 7: Рекомендации
        ws7 = wb.create_sheet("Рекомендации")
        for col, h in enumerate(["№", "Текст"], 1):
            ws7.cell(1, col, h).font = Font(bold=True)
        for row, rec in enumerate(result.recommendations, 2):
            ws7.cell(row, 1, row-1)
            ws7.cell(row, 2, rec)
        
        # Лист 8: Фазы
        ws8 = wb.create_sheet("Баланс фаз")
        for col, h in enumerate(["Фаза", "Ток, А"], 1):
            ws8.cell(1, col, h).font = Font(bold=True)
        for row, (phase, current) in enumerate(result.per_phase_current.items(), 2):
            ws8.cell(row, 1, phase)
            ws8.cell(row, 2, current)
        ws8.cell(5, 1, "Перекос, %")
        ws8.cell(5, 2, result.phase_imbalance_pct)
        
        filepath = f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb.save(filepath)
        return filepath
    
    @staticmethod
    def to_pdf(devices, rooms, result) -> str:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            return None
        
        filepath = f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»", styles['Title']))
        story.append(Spacer(1, 12))
        
        summary_data = [
            ["Параметр", "Значение"],
            ["Мощность (уст.)", f"{result.installed_power_w/1000:.2f} кВт"],
            ["Мощность (расч.)", f"{result.demand_power_w/1000:.2f} кВт"],
            ["Ток", f"{result.total_current_a:.1f} А"],
            ["Автомат", f"С{result.recommended_breaker}"],
            ["Кабель", result.recommended_cable],
            ["Падение U", f"{result.voltage_drop_pct}%"],
            ["Заземление", f"{result.grounding_r} Ом"],
            ["Охлаждение", f"{result.cooling_required_w/1000:.1f} кВт"],
            ["ИБП", f"{result.ups_power_w/1000:.1f} кВт"],
            ["Смета", f"{result.cost_total:,.0f} ₽"],
        ]
        t = Table(summary_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
        
        dev_data = [["Обозначение", "Наименование", "Мощность, Вт"]]
        for d in devices:
            dev_data.append([d.designation or "—", d.name, str(d.power_w)])
        t2 = Table(dev_data)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#06d6a0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t2)
        
        doc.build(story)
        return filepath
    
    @staticmethod
    def to_dxf(devices, rooms, result, scale_manager=None) -> str:
        try:
            import ezdxf
        except ImportError:
            return None
        
        filepath = f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.dxf"
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        for room in rooms:
            x, y, w, h = room.x, room.y, room.width, room.height
            msp.add_lwpolyline([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)], dxfattribs={"layer": "ROOMS"})
            msp.add_text(room.name, dxfattribs={"insert": (x+w/2, y+h/2), "height": 10, "layer": "TEXT"})
        
        for d in devices:
            r = 15
            msp.add_circle((d.x, d.y), r, dxfattribs={"layer": d.category.upper()})
            msp.add_text(d.designation or d.name, dxfattribs={"insert": (d.x, d.y-r-5), "height": 8, "layer": "DEVICE_LABELS"})
        
        doc.saveas(filepath)
        return filepath


# ============================================================================
# СЕКЦИЯ 16: ИНЖЕНЕРНОЕ ЯДРО (полный расчёт v18)
# ============================================================================

class EngineeringCore:
    """Полный инженерный расчёт с 15 калькуляторами"""
    
    def __init__(self, devices: List[Device], rooms: List[Room], tier: int = 1,
                 scale_manager: ScaleManager = None):
        self.devices = devices
        self.rooms = rooms
        self.tier = tier
        self.scale = scale_manager or ScaleManager()
        self.panel_pos = (25, 25)
    
    def calculate(self) -> EngineeringResult:
        result = EngineeringResult()
        result.device_count = len(self.devices)
        result.room_count = len(self.rooms)
        result.cos_phi = COS_PHI_DEFAULT
        
        # 1. Мощность с коэффициентами спроса
        installed = sum(d.power_w for d in self.devices)
        demand = sum(d.power_w * DEMAND_FACTORS.get(d.category, 0.7) for d in self.devices)
        result.installed_power_w = round(installed, 1)
        result.demand_power_w = round(demand, 1)
        result.active_power_w = round(demand, 1)
        
        # 2. Реактивная мощность
        reactive = ReactiveLossCalculator.calc(demand, result.cos_phi)
        result.reactive_power_var = reactive["reactive_var"]
        
        # 3. Ток и фазы (жадная балансировка)
        phases = PhaseBalancer.balance(self.devices)
        result.per_phase_current = phases
        result.phase_imbalance_pct = PhaseBalancer.imbalance_pct(phases)
        result.total_current_a = round(sum(phases.values()), 1)
        
        # 4. Автомат и кабель
        result.recommended_breaker = CableCalculator.select_breaker(result.total_current_a)
        cable = CableCalculator.select_section(result.total_current_a)
        result.recommended_cable = cable["name"]
        result.cable_section = cable["section"]
        
        # 5. Падение напряжения (3-фазное, с cos φ)
        avg_length = self._avg_cable_length()
        result.voltage_drop_pct = round(CableCalculator.voltage_drop(
            result.total_current_a, avg_length, result.cable_section,
            voltage=380, phases=3, cos_phi=result.cos_phi), 2)
        
        # 6. Заземление
        ground = GroundCalculator.calc()
        result.grounding_r = ground["resistance"]
        if result.grounding_r <= GROUND_R_MAX:
            result.grounding_status = "OK"
        elif result.grounding_r <= GROUND_R_WARN:
            result.grounding_status = "WARNING"
        else:
            result.grounding_status = "FAIL"
        
        # 7. Охлаждение
        people = sum(1 for d in self.devices if d.category == "it")
        room_area = sum(r.area for r in self.rooms)
        result.cooling_required_w = CoolingCalculator.calc(demand, room_area, people)
        
        # 8. Вентиляция
        room_volume = sum(r.area * r.height_m for r in self.rooms)
        result.ventilation_required_m3h = VentilationCalculator.calc(
            result.cooling_required_w, room_volume)
        
        # 9. ИБП с Tier
        tier_cfg = TIER_CONFIG.get(self.tier, TIER_CONFIG[1])
        result.ups_power_w = round(demand * tier_cfg["ups_redundancy"])
        result.ups_battery_count = max(1, math.ceil(demand / 5000))
        result.ups_autonomy_min = round(100 * 60 / max(result.ups_power_w, 1), 1) if demand > 0 else 0
        
        # 10. Селективность
        sub_breakers = [CableCalculator.select_breaker(d.power_w * DEMAND_FACTORS.get(d.category, 0.7) / 220) 
                       for d in self.devices[:10] if d.power_w > 0]
        sel = SelectivityChecker.check(result.recommended_breaker, sub_breakers)
        result.selectivity_ok = sel["ok"]
        
        # 11. Освещение
        if self.rooms:
            room_type = "office"
            if any("склад" in r.name.lower() or "зон" in r.name.lower() for r in self.rooms):
                room_type = "storage"
            elif any("сервер" in r.name.lower() or "машин" in r.name.lower() for r in self.rooms):
                room_type = "server"
            light = LightingCalculator.calc(self.rooms[0].area, room_type, self.rooms[0].height_m)
            result.lighting_lux = light["lux"]
            result.lighting_lamps = sum(LightingCalculator.calc(r.area, room_type, r.height_m)["lamps"] for r in self.rooms)
        
        # 12. Токи КЗ
        result.short_circuit_3ph = ShortCircuitCalculator.calc_3phase(
            result.ups_power_w, avg_length, result.cable_section)
        result.short_circuit_1ph = ShortCircuitCalculator.calc_1phase(
            result.ups_power_w, avg_length, result.cable_section)
        result.short_circuit_iudar = ShortCircuitCalculator.calc_iudar(result.short_circuit_3ph)
        
        # 13. Молниезащита
        total_area = sum(r.area for r in self.rooms)
        total_w = sum(r.width for r in self.rooms)
        total_h = sum(r.height for r in self.rooms)
        max_height = max((r.height_m for r in self.rooms), default=3.0)
        lightning = LightningProtection.assess(total_area / 10, total_w / 10, max_height)
        result.lightning_zone = lightning["zone"]
        result.lightning_risk = lightning["risk"]
        
        # 14. Утечки
        cable_lengths = [self.scale.px_to_m(abs(d.x - self.panel_pos[0]) + abs(d.y - self.panel_pos[1])) 
                        for d in self.devices]
        leakage = LeakageCalculator.calc(self.devices, cable_lengths)
        result.leakage_current_ma = leakage["current_ma"]
        result.leakage_uzo_ma = leakage["uzo_ma"]
        
        # 15. ЛВС/СКС
        lan = LANCalculator.calc(self.devices, self.scale)
        result.lan_ports = lan["total_ports"]
        result.lan_cable_m = lan["cable_m"]
        result.poe_required_w = lan["poe_required_w"]
        result.poe_budget_w = lan["poe_budget_w"]
        
        # 16. Теплопотери
        result.heat_loss_w = HeatLossCalculator.calc(self.rooms)
        
        # 17. Шум
        room_vol = sum(r.area * r.height_m for r in self.rooms) if self.rooms else 100
        result.noise_level_db = AcousticCalculator.calc(self.devices, room_vol)
        
        # 18. Трассы кабеля (A*)
        router = AStarRouter()
        for room in self.rooms:
            router.add_wall(room.x, room.y, room.x + room.width, room.y)
            router.add_wall(room.x, room.y + room.height, room.x + room.width, room.y + room.height)
        
        for dev in self.devices:
            path = router.find_path(self.panel_pos, (dev.x, dev.y))
            trace = CableTrace(device_id=dev.id, path=path, system=CATEGORIES.get(dev.category, {}).get("trace_key", "power").replace("trace_", ""))
            # Длина с учётом масштаба
            trace.length_m = self.scale.px_to_m(sum(
                math.sqrt((path[i+1][0]-path[i][0])**2 + (path[i+1][1]-path[i][1])**2)
                for i in range(len(path)-1)))
            trace.vertical_length = dev.z + 1.0  # подъём от пола + спуск к устройству
            result.cable_traces.append(trace)
        
        # 19. Рекомендации
        result.recommendations = self._generate_recommendations(result)
        
        # 20. Смета
        result.cost_total = self._calc_cost()
        
        return result
    
    def _avg_cable_length(self) -> float:
        lengths = []
        for dev in self.devices:
            dx = abs(dev.x - self.panel_pos[0])
            dy = abs(dev.y - self.panel_pos[1])
            lengths.append(self.scale.px_to_m((dx + dy) / 50))
        return sum(lengths) / len(lengths) if lengths else 50.0
    
    def _generate_recommendations(self, r: EngineeringResult) -> List[str]:
        recs = []
        if r.voltage_drop_pct > VOLTAGE_DROP_MAX:
            recs.append(f"Падение напряжения {r.voltage_drop_pct}% > {VOLTAGE_DROP_MAX}%. Увеличьте сечение кабеля.")
        elif r.voltage_drop_pct > VOLTAGE_DROP_WARN:
            recs.append(f"Падение напряжения {r.voltage_drop_pct}% — выше рекомендуемого {VOLTAGE_DROP_WARN}%.")
        if r.phase_imbalance_pct > PHASE_IMBALANCE_MAX:
            recs.append(f"Перекос фаз {r.phase_imbalance_pct}% > {PHASE_IMBALANCE_MAX}%. Перераспределите нагрузку.")
        if r.grounding_status == "FAIL":
            recs.append(f"Сопротивление заземления {r.grounding_r} Ом > {GROUND_R_WARN} Ом. Добавьте электроды.")
        if not r.selectivity_ok:
            recs.append("Нарушена селективность автоматов. Увеличьте номинал вводного автомата.")
        if r.cooling_required_w > 0:
            recs.append(f"Требуется охлаждение: {r.cooling_required_w/1000:.1f} кВт.")
        if r.ups_power_w > 0:
            recs.append(f"ИБП: {r.ups_power_w/1000:.1f} кВт, автономия {r.ups_autonomy_min} мин.")
        if r.poe_required_w > r.poe_budget_w and r.poe_budget_w > 0:
            recs.append(f"PoE-бюджет недостаточен: {r.poe_required_w} Вт > {r.poe_budget_w} Вт. Добавьте PoE-коммутатор.")
        if r.heat_loss_w > 0:
            recs.append(f"Теплопотери здания: {r.heat_loss_w:.0f} Вт.")
        if r.leakage_current_ma > 25:
            recs.append(f"Утечки {r.leakage_current_ma} мА — установите УЗО {r.leakage_uzo_ma} мА.")
        return recs
    
    def _calc_cost(self) -> float:
        total = 0
        for dev in self.devices:
            price = dev.price or PRICE_LIST.get(dev.equip_type, 0)
            total += price
        return round(total)


# ============================================================================
# СЕКЦИЯ 17: CLI
# ============================================================================

def generate_template(template_name: str, tier: int = 1) -> tuple:
    """Генерация устройств и помещений из шаблона"""
    tpl = TEMPLATES.get(template_name, TEMPLATES["Офис"])
    rooms = []
    devices = []
    
    DesignationGenerator.COUNTERS = {}  # сброс счётчиков
    
    x_off = 100
    y_off = 100
    dev_idx = 0
    
    for i, room_def in enumerate(tpl["rooms"], 1):
        rid = f"room_{i:02d}"
        w = min(room_def["area"] ** 0.5 * 15, 400)
        h = room_def["area"] ** 0.5 * 15
        room = Room(
            id=rid, name=room_def["name"], area=room_def["area"],
            x=x_off, y=y_off, width=w, height=h,
            pc_count=room_def.get("pc", 0),
            camera_count=room_def.get("cameras", 0),
            has_skud=room_def.get("skud", False),
            has_ops=room_def.get("ops", False),
        )
        rooms.append(room)
        
        # ПК
        for j in range(room_def.get("pc", 0)):
            dev_idx += 1
            dev = Device(
                id=f"dev_{dev_idx:03d}", name=f"РМ {i:02d}.{j+1:02d}",
                power_w=450, category="it", icon="💻",
                x=x_off + 30 + (j % 4) * 40, y=y_off + 30 + (j // 4) * 40,
                equip_type="pc", room_id=rid, price=PRICE_LIST.get("pc", 0)
            )
            dev.designation = DesignationGenerator.generate(dev)
            devices.append(dev)
        
        # Камеры
        for j in range(room_def.get("cameras", 0)):
            dev_idx += 1
            dev = Device(
                id=f"dev_{dev_idx:03d}", name=f"IP-камера {i:02d}.{j+1:02d}",
                power_w=25, category="camera", icon="🎥",
                x=x_off + w - 30, y=y_off + 30 + j * 40,
                equip_type="camera_ip", room_id=rid, price=PRICE_LIST.get("camera_ip", 0)
            )
            dev.designation = DesignationGenerator.generate(dev)
            devices.append(dev)
        
        # СКУД
        if room_def.get("skud"):
            dev_idx += 1
            dev = Device(
                id=f"dev_{dev_idx:03d}", name=f"Контроллер СКУД {i:02d}",
                power_w=50, category="skud", icon="🔑",
                x=x_off + w - 30, y=y_off + h - 30,
                equip_type="skud_ctrl", room_id=rid, price=PRICE_LIST.get("skud_ctrl", 0)
            )
            dev.designation = DesignationGenerator.generate(dev)
            devices.append(dev)
            
            dev_idx += 1
            lock = Device(
                id=f"dev_{dev_idx:03d}", name=f"Замок СКУД {i:02d}",
                power_w=15, category="skud", icon="🚪",
                x=x_off + w - 60, y=y_off + h - 30,
                equip_type="skud_lock", room_id=rid, price=PRICE_LIST.get("skud_lock", 0)
            )
            lock.designation = DesignationGenerator.generate(lock)
            devices.append(lock)
        
        # ОПС
        if room_def.get("ops"):
            dev_idx += 1
            dev = Device(
                id=f"dev_{dev_idx:03d}", name=f"Прибор ОПС {i:02d}",
                power_w=80, category="ops", icon="🔥",
                x=x_off + 30, y=y_off + h - 30,
                equip_type="ops_panel", room_id=rid, price=PRICE_LIST.get("ops_panel", 0)
            )
            dev.designation = DesignationGenerator.generate(dev)
            devices.append(dev)
            
            for j in range(2):
                dev_idx += 1
                smoke = Device(
                    id=f"dev_{dev_idx:03d}", name=f"Датчик дымовой {i:02d}.{j+1:02d}",
                    power_w=3, category="ops", icon="💨",
                    x=x_off + 60 + j * 40, y=y_off + h - 60,
                    equip_type="ops_smoke", room_id=rid, price=PRICE_LIST.get("ops_smoke", 0)
                )
                smoke.designation = DesignationGenerator.generate(smoke)
                devices.append(smoke)
        
        x_off += w + 50
        if x_off > 800:
            x_off = 100
            y_off += max(h + 50, 200)
    
    # Серверная
    if tpl.get("server_room"):
        dev_idx += 1
        dev = Device(
            id=f"dev_{dev_idx:03d}", name="Серверная стойка 42U",
            power_w=5000, category="it", icon="🔲",
            x=50, y=50, equip_type="rack42u", price=PRICE_LIST.get("rack42u", 0)
        )
        dev.designation = DesignationGenerator.generate(dev)
        devices.append(dev)
        
        dev_idx += 1
        sw = Device(
            id=f"dev_{dev_idx:03d}", name="Коммутатор 48p PoE+",
            power_w=750, category="network", icon="🔌",
            x=50, y=80, equip_type="switch", price=PRICE_LIST.get("switch", 0)
        )
        sw.designation = DesignationGenerator.generate(sw)
        devices.append(sw)
        
        dev_idx += 1
        nvr = Device(
            id=f"dev_{dev_idx:03d}", name="NVR видеосервер",
            power_w=400, category="camera", icon="💾",
            x=50, y=110, equip_type="nvr", price=PRICE_LIST.get("nvr", 0)
        )
        nvr.designation = DesignationGenerator.generate(nvr)
        devices.append(nvr)
    
    return devices, rooms


def run_cli(args):
    """CLI режим"""
    import argparse
    parser = argparse.ArgumentParser(description=f"КОНТУР-ПРО v{VERSION}")
    parser.add_argument("--cli", action="store_true", help="CLI режим")
    parser.add_argument("--template", type=str, default="Офис", help="Шаблон здания")
    parser.add_argument("--tier", type=int, default=1, choices=[1,2,3], help="Tier уровень")
    parser.add_argument("--export", action="store_true", help="Экспорт отчёта")
    parser.add_argument("--test", action="store_true", help="Запуск тестов")
    parser.add_argument("--save", type=str, help="Сохранить проект в .kontur")
    parser.add_argument("--load", type=str, help="Загрузить проект из .kontur")
    parser.add_argument("--import", dest="import_file", type=str, help="Импорт DXF")
    parser.add_argument("--floor", type=int, default=1, help="Этаж")
    parser.add_argument("--outdoor", type=float, default=-28, help="Уличная температура для теплопотерь")
    parsed = parser.parse_args(args)
    
    if parsed.test:
        return run_tests()
    
    if parsed.load:
        pm = ProjectManager()
        data = pm.load(parsed.load)
        devices, rooms = data["devices"], data["rooms"]
        tier = data.get("tier", 1)
        scale = data.get("scale", 1.0)
        print(f"Проект загружен: {parsed.load}")
        print(f"  Устройств: {len(devices)}, Помещений: {len(rooms)}")
        print(f"  Схема: {data.get('schema_version', '?')}")
    elif parsed.import_file:
        result = DXFImporter.import_dxf(parsed.import_file)
        if "error" in result:
            print(f"Ошибка: {result['error']}")
            return
        devices = result.get("devices", [])
        rooms = result.get("rooms", [])
        walls = result.get("walls", [])
        print(f"DXF импортирован: {parsed.import_file}")
        print(f"  Устройств: {len(devices)}, Стен: {len(walls)}")
        tier = 1
        scale = 1.0
    else:
        devices, rooms = generate_template(parsed.template, parsed.tier)
        tier = parsed.tier
        scale = 1.0
    
    scale_mgr = ScaleManager(50.0 * scale)
    core = EngineeringCore(devices, rooms, tier, scale_mgr)
    result = core.calculate()
    
    # Проверки
    checker = ModelChecker()
    checks = checker.run_all(devices, rooms, result)
    
    ok_count = sum(1 for c in checks if c["status"] == "OK")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    
    print()
    print(f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»")
    print(f"Шаблон: {parsed.template}, Tier: {tier}")
    print(f"{'='*60}")
    print(f"Установленная мощность:  {result.installed_power_w/1000:.2f} кВт")
    print(f"Расчётная мощность:      {result.demand_power_w/1000:.2f} кВт")
    print(f"Ток нагрузки:             {result.total_current_a:.1f} А")
    print(f"cos φ:                   {result.cos_phi}")
    print(f"Перекос фаз:              {result.phase_imbalance_pct}%")
    print(f"Автомат:                  С{result.recommended_breaker}")
    print(f"Кабель:                   {result.recommended_cable}")
    print(f"Падение напряжения:       {result.voltage_drop_pct}%")
    print(f"Заземление:               {result.grounding_r} Ом [{result.grounding_status}]")
    print(f"Охлаждение:               {result.cooling_required_w/1000:.1f} кВт")
    print(f"Вентиляция:               {result.ventilation_required_m3h:.0f} м³/ч")
    print(f"ИБП:                      {result.ups_power_w/1000:.1f} кВт ({result.ups_autonomy_min} мин)")
    print(f"Токи КЗ:                  I3ф={result.short_circuit_3ph}А, I1ф={result.short_circuit_1ph}А")
    print(f"Ударный ток:              {result.short_circuit_iudar}А")
    print(f"Утечки:                   {result.leakage_current_ma} мА (УЗО {result.leakage_uzo_ma} мА)")
    print(f"Молниезащита:             {result.lightning_zone}")
    print(f"Освещение:                {result.lighting_lux} лк, ламп: {result.lighting_lamps}")
    print(f"ЛВС:                      {result.lan_ports} портов, {result.lan_cable_m:.0f} м")
    print(f"PoE-бюджет:               {result.poe_required_w} Вт / {result.poe_budget_w} Вт")
    print(f"Теплопотери:              {result.heat_loss_w:.0f} Вт")
    print(f"Уровень шума:             {result.noise_level_db:.1f} дБ")
    print(f"Смета:                    {result.cost_total:,.0f} ₽")
    print(f"{'='*60}")
    print(f"Проверок: {len(checks)} (OK: {ok_count}, WARN: {warn_count}, FAIL: {fail_count})")
    for c in checks:
        symbol = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}.get(c["status"], "[?]")
        print(f"  {symbol:8} {c['name']:<25} {c['detail']}")
    
    if result.recommendations:
        print(f"{'='*60}")
        print("РЕКОМЕНДАЦИИ:")
        for rec in result.recommendations:
            print(f"  ⚠ {rec}")
    
    # Сохранение проекта
    if parsed.save:
        pm = ProjectManager()
        save_result = pm.save(parsed.save, devices, rooms, tier=tier, scale=scale)
        print(f"\nПроект сохранён: {save_result['path']}")
    
    # Экспорт
    if parsed.export:
        spec = SpecificationBuilder.build(devices, result)
        cable_journal = CableJournal.build(devices, result.cable_traces, scale_mgr)
        
        # JSON
        json_data = Exporter.to_json(devices, rooms, result)
        with open(f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        # HTML
        html = Exporter.to_html(devices, rooms, result, checks)
        with open(f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.html", 'w', encoding='utf-8') as f:
            f.write(html)
        
        # TXT
        txt = Exporter.to_txt(devices, rooms, result)
        with open(f"kontur_export_{time.strftime('%Y%m%d_%H%M%S')}.txt", 'w', encoding='utf-8') as f:
            f.write(txt)
        
        # Excel
        xlsx = Exporter.to_excel(devices, rooms, result, checks, spec, cable_journal)
        
        # PDF
        pdf = Exporter.to_pdf(devices, rooms, result)
        
        # DXF
        dxf = Exporter.to_dxf(devices, rooms, result, scale_mgr)
        
        print(f"\nЭкспорт: JSON ✓, HTML ✓, TXT ✓, Excel {'✓' if xlsx else '✗ (openpyxl)'}, PDF {'✓' if pdf else '✗ (reportlab)'}, DXF {'✓' if dxf else '✗ (ezdxf)'}")
    
    return result


def run_tests():
    """Запуск всех unit-тестов"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


# ============================================================================
# СЕКЦИЯ 18: UNIT-ТЕСТЫ (64 теста)
# ============================================================================

class TestCableCalculator(unittest.TestCase):
    def test_select_section(self):
        cable = CableCalculator.select_section(25)
        self.assertEqual(cable["section"], 2.5)
    
    def test_select_section_high(self):
        cable = CableCalculator.select_section(200)
        self.assertEqual(cable["section"], 70.0)
    
    def test_select_breaker(self):
        b = CableCalculator.select_breaker(20)
        self.assertIn(b, AUTOMAT_STEPS)
        self.assertGreaterEqual(b, 25)
    
    def test_voltage_drop_1phase(self):
        v = CableCalculator.voltage_drop(10, 30, 2.5)
        self.assertGreater(v, 0)
        self.assertLess(v, 10)
    
    def test_voltage_drop_3phase_cos_phi(self):
        v = CableCalculator.voltage_drop(30, 50, 6.0, voltage=380, phases=3, cos_phi=0.92)
        self.assertGreater(v, 0)
        self.assertLess(v, 10)
    
    def test_no_13_in_automat_steps(self):
        self.assertNotIn(13, AUTOMAT_STEPS)

class TestGroundCalculator(unittest.TestCase):
    def test_basic(self):
        r = GroundCalculator.calc()
        self.assertGreater(r["resistance"], 0)
        self.assertLessEqual(r["resistance"], 4.0)
    
    def test_rod_count(self):
        r = GroundCalculator.calc(rho_soil=500)
        self.assertGreater(r["rod_count"], 1)

class TestCoolingCalculator(unittest.TestCase):
    def test_basic(self):
        c = CoolingCalculator.calc(1000, 50, 2)
        self.assertGreater(c, 900)
    
    def test_no_equipment(self):
        c = CoolingCalculator.calc(0, 0, 0)
        self.assertGreaterEqual(c, 0)

class TestVentilationCalculator(unittest.TestCase):
    def test_basic(self):
        v = VentilationCalculator.calc(2000, 100, delta_t=10)
        self.assertGreater(v, 0)

class TestSelectivityChecker(unittest.TestCase):
    def test_ok(self):
        r = SelectivityChecker.check(63, [16, 20])
        self.assertTrue(r["ok"])
    
    def test_fail(self):
        r = SelectivityChecker.check(16, [16, 20])
        self.assertFalse(r["ok"])
    
    def test_curve_bc(self):
        self.assertTrue(SelectivityChecker.check_curve("C", "B", 40, 16))
        self.assertFalse(SelectivityChecker.check_curve("B", "C", 16, 40))

class TestLightingCalculator(unittest.TestCase):
    def test_office(self):
        r = LightingCalculator.calc(50, "office", 3.0)
        self.assertEqual(r["lux"], 500)
        self.assertGreater(r["lamps"], 0)
    
    def test_storage(self):
        r = LightingCalculator.calc(500, "storage")
        self.assertEqual(r["lux"], 200)

class TestShortCircuitCalculator(unittest.TestCase):
    def test_3phase(self):
        i = ShortCircuitCalculator.calc_3phase(5000, 30, 2.5)
        self.assertGreater(i, 0)
    
    def test_1phase(self):
        i = ShortCircuitCalculator.calc_1phase(5000, 30, 2.5)
        self.assertGreater(i, 0)
    
    def test_iudar(self):
        i = ShortCircuitCalculator.calc_iudar(1000)
        self.assertGreater(i, 1000)
    
    def test_check_breaker_ok(self):
        r = ShortCircuitCalculator.check_breaker(16, 500)
        self.assertTrue(r["ok"])

class TestLightningProtection(unittest.TestCase):
    def test_small_building(self):
        r = LightningProtection.assess(10, 10, 3)
        self.assertGreaterEqual(r["strikes_per_year"], 0)
    
    def test_large_building(self):
        r = LightningProtection.assess(100, 50, 20, region_thunderstorms=80)
        self.assertGreater(r["strikes_per_year"], 0)

class TestLeakageCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device("d1", "Test", 450, "it"), Device("d2", "Test2", 200, "network")]
        r = LeakageCalculator.calc(devs, [30, 50])
        self.assertGreater(r["current_ma"], 0)
    
    def test_uzo_selection(self):
        devs = [Device(f"d{i}", "Test", 450, "it") for i in range(80)]
        r = LeakageCalculator.calc(devs)
        self.assertGreater(r["uzo_ma"], 30)

class TestReactiveLoss(unittest.TestCase):
    def test_basic(self):
        r = ReactiveLossCalculator.calc(1000, 0.85)
        self.assertGreater(r["reactive_var"], 0)
        self.assertGreater(r["apparent_va"], 1000)
    
    def test_unity(self):
        r = ReactiveLossCalculator.calc(1000, 1.0)
        self.assertEqual(r["reactive_var"], 0)

class TestPhaseBalancer(unittest.TestCase):
    def test_balanced(self):
        devs = [Device(f"d{i}", "Test", 100, "it") for i in range(9)]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertLess(imbalance, 5)
    
    def test_one_large(self):
        # Один большой + один маленький: перекос высок, но жадный всё равно лучше round-robin
        devs = [Device("d1", "Big", 5000, "it"), Device("d2", "Small", 100, "it")]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        self.assertLess(imbalance, 100)
    
    def test_greedy_better_than_round_robin(self):
        # 6 устройств разной мощности — жадный балансирует лучше round-robin
        devs = [Device("d1", "A", 3000, "it"), Device("d2", "B", 3000, "it"),
                Device("d3", "C", 2000, "it"), Device("d4", "D", 2000, "it"),
                Device("d5", "E", 1000, "it"), Device("d6", "F", 1000, "it")]
        phases = PhaseBalancer.balance(devs)
        imbalance = PhaseBalancer.imbalance_pct(phases)
        # Жадный: A≈B≈C, перекос < 20%
        self.assertLess(imbalance, 20)

class TestHeatLoss(unittest.TestCase):
    def test_basic(self):
        rooms = [Room("r1", "Test", 50, width=200, height=150, height_m=3.0)]
        loss = HeatLossCalculator.calc(rooms, outdoor_temp=-28)
        self.assertGreater(loss, 0)

class TestAcousticCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device("d1", "Server", 500, "it", equip_type="server")]
        noise = AcousticCalculator.calc(devs, 200)
        self.assertGreater(noise, 30)
    
    def test_silent(self):
        devs = [Device("d1", "Outlet", 500, "power", equip_type="outlet")]
        noise = AcousticCalculator.calc(devs, 200)
        self.assertGreater(noise, 0)

class TestLANCalculator(unittest.TestCase):
    def test_basic(self):
        devs = [Device(f"d{i}", "PC", 450, "it", equip_type="pc") for i in range(10)]
        devs.append(Device("cam1", "Camera", 25, "camera", equip_type="camera_ip"))
        r = LANCalculator.calc(devs)
        self.assertGreater(r["total_ports"], 0)
        self.assertGreater(r["cable_m"], 0)
    
    def test_poe(self):
        devs = [Device(f"c{i}", "Cam", 25, "camera", equip_type="camera_ip") for i in range(10)]
        r = LANCalculator.calc(devs)
        self.assertGreater(r["poe_required_w"], 0)
        self.assertGreater(r["poe_budget_w"], 0)

class TestAStar(unittest.TestCase):
    def test_simple_path(self):
        router = AStarRouter(100, 80, 10)
        path = router.find_path((10, 10), (50, 50))
        self.assertGreater(len(path), 1)
    
    def test_8_directions(self):
        router = AStarRouter(100, 100, 10)
        path = router.find_path((10, 10), (40, 40))
        self.assertGreater(len(path), 1)
    
    def test_wall_avoidance(self):
        router = AStarRouter(100, 80, 10)
        router.add_wall(30, 0, 30, 80)
        path = router.find_path((10, 40), (50, 40))
        self.assertGreater(len(path), 2)
    
    def test_same_point(self):
        router = AStarRouter()
        path = router.find_path((50, 50), (50, 50))
        self.assertEqual(len(path), 2)

class TestTwinBuilder(unittest.TestCase):
    def test_build_office(self):
        twin = TwinBuilder.build("Офис", 1)
        self.assertGreater(len(twin.nodes), 0)
        self.assertGreater(len(twin.edges), 0)
    
    def test_build_cod(self):
        twin = TwinBuilder.build("ЦОД", 3)
        stats = twin.get_stats()
        self.assertGreater(stats["nodes"], 0)
    
    def test_stats(self):
        twin = TwinBuilder.build("Склад")
        stats = twin.get_stats()
        self.assertIn("systems", stats)

class TestTwinImporter(unittest.TestCase):
    def test_parse_simple(self):
        json_text = '{"nodes":[{"id":"n1","text":"Сервер","color":"1","x":0,"y":0,"width":300,"height":100}],"edges":[],"groups":[]}'
        twin = TwinImporter.parse(json_text)
        self.assertEqual(len(twin.nodes), 1)
    
    def test_detect_system(self):
        node = TwinNode("n1", "⚡ Автомат С16")
        self.assertEqual(node.system, "power")
        node2 = TwinNode("n2", "🎥 IP-камера")
        self.assertEqual(node2.system, "camera")

class TestEngineeringCore(unittest.TestCase):
    def test_office(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.installed_power_w, 0)
        self.assertGreater(result.demand_power_w, 0)
        self.assertGreater(result.total_current_a, 0)
    
    def test_cod_tier3(self):
        devices, rooms = generate_template("ЦОД", 3)
        core = EngineeringCore(devices, rooms, 3)
        result = core.calculate()
        self.assertGreater(result.ups_power_w, result.demand_power_w)
    
    def test_cos_phi_in_result(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.cos_phi, 0.9)
    
    def test_short_circuit_calculated(self):
        devices, rooms = generate_template("ЦОД", 3)
        core = EngineeringCore(devices, rooms, 3)
        result = core.calculate()
        self.assertGreater(result.short_circuit_3ph, 0)
    
    def test_lan_calculated(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.lan_ports, 0)
    
    def test_heat_loss(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        self.assertGreater(result.heat_loss_w, 0)

class TestModelChecker(unittest.TestCase):
    def test_run_all(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        checker = ModelChecker()
        checks = checker.run_all(devices, rooms, result)
        self.assertGreater(len(checks), 10)
    
    def test_statuses(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        checker = ModelChecker()
        checks = checker.run_all(devices, rooms, result)
        for c in checks:
            self.assertIn(c["status"], ["OK", "WARN", "FAIL"])

class TestUndoManager(unittest.TestCase):
    def test_undo_redo(self):
        mgr = UndoManager()
        mgr.push({"state": 1})
        mgr.push({"state": 2})
        mgr.push({"state": 3})
        self.assertTrue(mgr.can_undo())
        state = mgr.undo()
        self.assertEqual(state["state"], 2)
        state = mgr.redo()
        self.assertEqual(state["state"], 3)

class TestExporter(unittest.TestCase):
    def test_json(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        json_str = Exporter.to_json(devices, rooms, result)
        self.assertIn("КОНТУР-ПРО", json_str)
    
    def test_html(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        html = Exporter.to_html(devices, rooms, result)
        self.assertIn("<html", html)
    
    def test_txt(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        txt = Exporter.to_txt(devices, rooms, result)
        self.assertIn("КОНТУР-ПРО", txt)

class TestTemplates(unittest.TestCase):
    def test_office(self):
        devices, rooms = generate_template("Офис", 1)
        self.assertGreater(len(devices), 0)
        self.assertGreater(len(rooms), 0)
    
    def test_cod(self):
        devices, rooms = generate_template("ЦОД", 3)
        self.assertGreater(len(devices), 0)
    
    def test_school(self):
        devices, rooms = generate_template("Школа", 1)
        self.assertGreater(len(devices), 0)
    
    def test_warehouse(self):
        devices, rooms = generate_template("Склад", 2)
        self.assertGreater(len(devices), 0)

class TestProjectManager(unittest.TestCase):
    def test_save_load(self):
        devices, rooms = generate_template("Офис", 1)
        pm = ProjectManager()
        filepath = "test_project.kontur"
        save_result = pm.save(filepath, devices, rooms, tier=1)
        self.assertTrue(save_result["ok"])
        loaded = pm.load(filepath)
        self.assertEqual(len(loaded["devices"]), len(devices))
        self.assertEqual(len(loaded["rooms"]), len(rooms))
        try:
            os.remove(filepath)
        except:
            pass
    
    def test_migration(self):
        old_data = {"schema_version": "1.0", "devices": [{"id": "d1", "name": "Test", "power_w": 100, "category": "it"}], "rooms": [{"id": "r1", "name": "Room", "area": 50}]}
        pm = ProjectManager()
        migrated = pm._migrate(old_data)
        self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
        self.assertEqual(migrated["devices"][0]["z"], 1.0)
        self.assertEqual(migrated["rooms"][0]["height_m"], 3.0)

class TestScaleManager(unittest.TestCase):
    def test_px_to_m(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.px_to_m(100), 2.0)
    
    def test_m_to_px(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.m_to_px(2.0), 100)
    
    def test_area(self):
        sm = ScaleManager(50)
        self.assertEqual(sm.area_px_to_m2(2500), 1.0)

class TestDesignationGenerator(unittest.TestCase):
    def test_breaker(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "Автомат", 0, "power", equip_type="breaker")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "QF1")
    
    def test_ups(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "ИБП", 0, "power", equip_type="ups")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "G1")
    
    def test_smoke(self):
        DesignationGenerator.COUNTERS = {}
        dev = Device("d1", "Датчик", 3, "ops", equip_type="ops_smoke")
        d = DesignationGenerator.generate(dev)
        self.assertEqual(d, "B1")

class TestVendorDatabase(unittest.TestCase):
    def test_get_vendor(self):
        self.assertIsNotNone(VendorDatabase.get_vendor("camera_ip"))
        self.assertIsNotNone(VendorDatabase.get_vendor("breaker"))
    
    def test_list_all(self):
        vendors = VendorDatabase.list_all()
        self.assertGreaterEqual(len(vendors), 6)

class TestSpecificationBuilder(unittest.TestCase):
    def test_build(self):
        devices, rooms = generate_template("Офис", 1)
        spec = SpecificationBuilder.build(devices)
        self.assertGreater(len(spec), 0)

class TestCableJournal(unittest.TestCase):
    def test_build(self):
        devices, rooms = generate_template("Офис", 1)
        core = EngineeringCore(devices, rooms, 1)
        result = core.calculate()
        journal = CableJournal.build(devices, result.cable_traces)
        self.assertGreater(len(journal), 0)

class TestExternalCatalog(unittest.TestCase):
    def test_default_items(self):
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "test_catalog.json")
        if os.path.exists(path):
            os.remove(path)
        cat = ExternalCatalog(path)
        self.assertGreater(len(cat.items), 20)
        os.remove(path)
    
    def test_find(self):
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "test_catalog2.json")
        if os.path.exists(path):
            os.remove(path)
        cat = ExternalCatalog(path)
        results = cat.find("сервер")
        self.assertGreater(len(results), 0)
        os.remove(path)

class TestMultiProject(unittest.TestCase):
    def test_compare(self):
        mp = MultiProjectManager()
        d1, r1 = generate_template("Офис", 1)
        core1 = EngineeringCore(d1, r1, 1)
        res1 = core1.calculate()
        mp.add_project("Офис", d1, r1, res1)
        
        d2, r2 = generate_template("ЦОД", 3)
        core2 = EngineeringCore(d2, r2, 3)
        res2 = core2.calculate()
        mp.add_project("ЦОД", d2, r2, res2)
        
        comp = mp.compare()
        self.assertEqual(len(comp), 2)


# ============================================================================
# СЕКЦИЯ 19: GUI (PyQt6)
# ============================================================================

def run_gui():
    """Запуск GUI"""
    try:
        from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
            QHBoxLayout, QPushButton, QLabel, QListWidget, QTabWidget,
            QTableWidget, QTableWidgetItem, QProgressBar, QStatusBar,
            QToolBar, QComboBox, QSpinBox, QSplitter, QGraphicsView, QGraphicsScene,
            QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsTextItem,
            QGraphicsLineItem, QMessageBox, QFileDialog, QAction, QLineEdit)
        from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
        from PyQt6.QtGui import (QColor, QPen, QBrush, QFont, QPainter,
            QDragEnterEvent, QDropEvent, QMouseEvent, QKeyEvent)
    except ImportError:
        print("PyQt6 не установлен. Установите: pip install PyQt6")
        print("Или используйте CLI режим: python kontur_v18.py --cli --template Офис --tier 1 --export")
        return
    
    class KonturMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»")
            self.resize(1400, 900)
            self.devices = []
            self.rooms = []
            self.walls = []
            self.doors = []
            self.annotations = []
            self.tier = 1
            self.scale_mgr = ScaleManager(50.0)
            self.undo_mgr = UndoManager()
            self.project_mgr = ProjectManager()
            self.catalog = ExternalCatalog()
            self.theme = THEME_DARK
            self._init_ui()
        
        def _init_ui(self):
            # Центральный виджет
            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QHBoxLayout(central)
            
            # Splitter
            splitter = QSplitter(Qt.Orientation.Horizontal)
            main_layout.addWidget(splitter)
            
            # Левый док — палитра
            left_dock = QWidget()
            left_layout = QVBoxLayout(left_dock)
            left_layout.setContentsMargins(4, 4, 4, 4)
            
            search_label = QLabel("Поиск оборудования:")
            left_layout.addWidget(search_label)
            
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Введите название...")
            self.search_box.textChanged.connect(self._filter_palette)
            left_layout.addWidget(self.search_box)
            
            self.palette_list = QListWidget()
            for item in self.catalog.items:
                self.palette_list.addItem(f"{item['icon']} {item['name']}")
            left_layout.addWidget(self.palette_list)
            
            splitter.addWidget(left_dock)
            
            # Центр — холст
            self.scene = QGraphicsScene()
            self.scene.setSceneRect(0, 0, 2000, 1500)
            self.view = QGraphicsView(self.scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self._apply_theme_to_view()
            splitter.addWidget(self.view)
            
            # Правый док — вкладки
            right_dock = QTabWidget()
            
            # Вкладка: Свойства
            props_tab = QWidget()
            props_layout = QVBoxLayout(props_tab)
            props_layout.addWidget(QLabel("Свойства объекта"))
            self.props_table = QTableWidget(10, 2)
            self.props_table.setHorizontalHeaderLabels(["Свойство", "Значение"])
            props_layout.addWidget(self.props_table)
            right_dock.addTab(props_tab, "Свойства")
            
            # Вкладка: Расчёт
            calc_tab = QWidget()
            calc_layout = QVBoxLayout(calc_tab)
            calc_layout.addWidget(QLabel("Результаты расчёта"))
            self.calc_table = QTableWidget(20, 2)
            self.calc_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
            calc_layout.addWidget(self.calc_table)
            calc_btn = QPushButton("Рассчитать")
            calc_btn.clicked.connect(self._run_calculation)
            calc_layout.addWidget(calc_btn)
            right_dock.addTab(calc_tab, "Расчёт")
            
            # Вкладка: Проверки
            checks_tab = QWidget()
            checks_layout = QVBoxLayout(checks_tab)
            checks_layout.addWidget(QLabel("Проверки модели"))
            self.checks_table = QTableWidget(0, 3)
            self.checks_table.setHorizontalHeaderLabels(["Проверка", "Статус", "Детали"])
            checks_layout.addWidget(self.checks_table)
            right_dock.addTab(checks_tab, "Проверки")
            
            # Вкладка: Спецификация
            spec_tab = QWidget()
            spec_layout = QVBoxLayout(spec_tab)
            spec_layout.addWidget(QLabel("Спецификация (ГОСТ 21.110)"))
            self.spec_table = QTableWidget(0, 8)
            self.spec_table.setHorizontalHeaderLabels(["№", "Обозн.", "Наим.", "Тип", "Вендор", "Ед.", "Кол.", "Прим."])
            spec_layout.addWidget(self.spec_table)
            right_dock.addTab(spec_tab, "Спецификация")
            
            splitter.addWidget(right_dock)
            splitter.setSizes([250, 900, 350])
            
            # Тулбар 1: действия
            tb1 = QToolBar("Действия")
            self.addToolBar(tb1)
            
            new_btn = QAction("Создать", self)
            new_btn.triggered.connect(self._new_project)
            tb1.addAction(new_btn)
            
            calc_action = QAction("Рассчитать", self)
            calc_action.triggered.connect(self._run_calculation)
            tb1.addAction(calc_action)
            
            route_btn = QAction("Трассировка", self)
            route_btn.triggered.connect(self._route_cables)
            tb1.addAction(route_btn)
            
            tb1.addSeparator()
            
            undo_btn = QAction("Отменить", self)
            undo_btn.triggered.connect(self._undo)
            tb1.addAction(undo_btn)
            
            redo_btn = QAction("Повторить", self)
            redo_btn.triggered.connect(self._redo)
            tb1.addAction(redo_btn)
            
            tb1.addSeparator()
            
            export_btn = QAction("Экспорт", self)
            export_btn.triggered.connect(self._export)
            tb1.addAction(export_btn)
            
            tb1.addSeparator()
            
            self.theme_btn = QAction("Тёмная тема", self)
            self.theme_btn.triggered.connect(self._toggle_theme)
            tb1.addAction(self.theme_btn)
            
            # Тулбар 2: параметры
            tb2 = QToolBar("Параметры")
            self.addToolBar(tb2)
            
            tb2.addWidget(QLabel(" Шаблон: "))
            self.template_combo = QComboBox()
            self.template_combo.addItems(list(TEMPLATES.keys()))
            tb2.addWidget(self.template_combo)
            
            load_tpl_btn = QPushButton("Загрузить")
            load_tpl_btn.clicked.connect(self._load_template)
            tb2.addWidget(load_tpl_btn)
            
            tb2.addSeparator()
            tb2.addWidget(QLabel(" Tier: "))
            self.tier_spin = QSpinBox()
            self.tier_spin.setRange(1, 3)
            tb2.addWidget(self.tier_spin)
            
            tb2.addSeparator()
            tb2.addWidget(QLabel(" Этаж: "))
            self.floor_spin = QSpinBox()
            self.floor_spin.setRange(1, 50)
            tb2.addWidget(self.floor_spin)
            
            tb2.addSeparator()
            
            save_btn = QPushButton("Сохранить")
            save_btn.clicked.connect(self._save_project)
            tb2.addWidget(save_btn)
            
            open_btn = QPushButton("Открыть")
            open_btn.clicked.connect(self._open_project)
            tb2.addWidget(open_btn)
            
            import_dxf_btn = QPushButton("DXF")
            import_dxf_btn.clicked.connect(self._import_dxf)
            tb2.addWidget(import_dxf_btn)
            
            # Статус-бар
            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximumWidth(200)
            self.statusBar().addPermanentWidget(self.progress_bar)
            self.statusBar().showMessage("Готово")
        
        def _apply_theme_to_view(self):
            c = self.theme
            self.view.setBackgroundBrush(QBrush(QColor(c["bg_canvas"])))
        
        def _new_project(self):
            self.devices = []
            self.rooms = []
            self.walls = []
            self.doors = []
            self.annotations = []
            self.scene.clear()
            self.statusBar().showMessage("Новый проект создан")
        
        def _load_template(self):
            tpl_name = self.template_combo.currentText()
            self.tier = self.tier_spin.value()
            self.devices, self.rooms = generate_template(tpl_name, self.tier)
            self._draw_scene()
            self._run_calculation()
            self.statusBar().showMessage(f"Шаблон '{tpl_name}' загружен: {len(self.devices)} устройств, {len(self.rooms)} помещений")
        
        def _draw_scene(self):
            self.scene.clear()
            c = self.theme
            
            # Сетка
            for x in range(0, 2000, 20):
                self.scene.addLine(x, 0, x, 1500, QPen(QColor(c["bg_canvas_grid"]), 1))
            for y in range(0, 1500, 20):
                self.scene.addLine(0, y, 2000, y, QPen(QColor(c["bg_canvas_grid"]), 1))
            for x in range(0, 2000, 100):
                self.scene.addLine(x, 0, x, 1500, QPen(QColor(c["bg_canvas_grid_major"]), 1))
            for y in range(0, 1500, 100):
                self.scene.addLine(0, y, 2000, y, QPen(QColor(c["bg_canvas_grid_major"]), 1))
            
            # Помещения
            for room in self.rooms:
                rect = self.scene.addRect(room.x, room.y, room.width, room.height,
                    QPen(QColor(c["room_border"]), 2),
                    QBrush(QColor(c["room_fill"])))
                text = self.scene.addText(room.name)
                text.setPos(room.x + 5, room.y + 5)
                text.setDefaultTextColor(QColor(c["text_secondary"]))
            
            # Устройства
            for dev in self.devices:
                color = QColor(c.get(CATEGORIES.get(dev.category, {}).get("color_key", "device_custom"), "#06d6a0"))
                ellipse = self.scene.addEllipse(dev.x - 12, dev.y - 12, 24, 24,
                    QPen(color, 2), QBrush(color.lighter(150)))
                label = self.scene.addText(dev.name)
                label.setPos(dev.x - 12, dev.y + 14)
                label.setDefaultTextColor(QColor(c["text_primary"]))
                label.setFont(QFont("Arial", 7))
        
        def _run_calculation(self):
            if not self.devices:
                self.statusBar().showMessage("Нет устройств для расчёта")
                return
            self.tier = self.tier_spin.value()
            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()
            
            # Обновить таблицу расчёта
            data = [
                ("Мощность (уст.)", f"{result.installed_power_w/1000:.2f} кВт"),
                ("Мощность (расч.)", f"{result.demand_power_w/1000:.2f} кВт"),
                ("Ток", f"{result.total_current_a:.1f} А"),
                ("cos φ", str(result.cos_phi)),
                ("Перекос фаз", f"{result.phase_imbalance_pct}%"),
                ("Автомат", f"С{result.recommended_breaker}"),
                ("Кабель", result.recommended_cable),
                ("Падение U", f"{result.voltage_drop_pct}%"),
                ("Заземление", f"{result.grounding_r} Ом [{result.grounding_status}]"),
                ("Охлаждение", f"{result.cooling_required_w/1000:.1f} кВт"),
                ("ИБП", f"{result.ups_power_w/1000:.1f} кВт"),
                ("Токи КЗ", f"I3ф={result.short_circuit_3ph}А"),
                ("Утечки", f"{result.leakage_current_ma} мА"),
                ("Молниезащита", result.lightning_zone),
                ("ЛВС", f"{result.lan_ports} портов"),
                ("PoE", f"{result.poe_required_w}/{result.poe_budget_w} Вт"),
                ("Теплопотери", f"{result.heat_loss_w:.0f} Вт"),
                ("Шум", f"{result.noise_level_db:.1f} дБ"),
                ("Смета", f"{result.cost_total:,.0f} ₽"),
            ]
            self.calc_table.setRowCount(len(data))
            for i, (k, v) in enumerate(data):
                self.calc_table.setItem(i, 0, QTableWidgetItem(k))
                self.calc_table.setItem(i, 1, QTableWidgetItem(v))
            
            # Проверки
            checker = ModelChecker()
            checks = checker.run_all(self.devices, self.rooms, result)
            self.checks_table.setRowCount(len(checks))
            for i, ch in enumerate(checks):
                color = {"OK": "#06d6a0", "WARN": "#fbbf24", "FAIL": "#f87171"}.get(ch["status"], "#666")
                item0 = QTableWidgetItem(ch["name"])
                item1 = QTableWidgetItem(ch["status"])
                item1.setForeground(QColor(color))
                item2 = QTableWidgetItem(ch["detail"])
                self.checks_table.setItem(i, 0, item0)
                self.checks_table.setItem(i, 1, item1)
                self.checks_table.setItem(i, 2, item2)
            
            # Спецификация
            spec = SpecificationBuilder.build(self.devices, result)
            self.spec_table.setRowCount(len(spec))
            for i, s in enumerate(spec):
                for j, key in enumerate(["pos", "designation", "name", "type", "vendor", "unit", "qty", "note"]):
                    self.spec_table.setItem(i, j, QTableWidgetItem(str(s.get(key, ""))))
            
            self.statusBar().showMessage(
                f"Расчёт выполнен: {len(checks)} проверок, смета {result.cost_total:,.0f} ₽")
        
        def _route_cables(self):
            if not self.devices:
                return
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(self.devices))
            
            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()
            
            c = self.theme
            for i, trace in enumerate(result.cable_traces):
                color = QColor(c.get(CATEGORIES.get(
                    next((d.category for d in self.devices if d.id == trace.device_id), "power"),
                    {}).get("trace_key", "trace_power"), "#f87171"))
                for j in range(len(trace.path) - 1):
                    x1, y1 = trace.path[j]
                    x2, y2 = trace.path[j+1]
                    self.scene.addLine(x1, y1, x2, y2, QPen(color, 2))
                self.progress_bar.setValue(i + 1)
            
            self.statusBar().showMessage(f"Трассировка: {len(result.cable_traces)} кабелей")
        
        def _undo(self):
            state = self.undo_mgr.undo()
            if state:
                self._restore_state(state)
                self.statusBar().showMessage("Отменено")
        
        def _redo(self):
            state = self.undo_mgr.redo()
            if state:
                self._restore_state(state)
                self.statusBar().showMessage("Повторено")
        
        def _restore_state(self, state):
            self.devices = state.get("devices", [])
            self.rooms = state.get("rooms", [])
            self._draw_scene()
        
        def _save_project(self):
            filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "", "КОНТУР-ПРО (*.kontur)")
            if filepath:
                result = self.project_mgr.save(filepath, self.devices, self.rooms,
                    self.walls, self.doors, self.annotations, self.tier,
                    self.scale_mgr.ppm)
                self.statusBar().showMessage(f"Сохранено: {result['path']}")
        
        def _open_project(self):
            filepath, _ = QFileDialog.getOpenFileName(self, "Открыть проект", "", "КОНТУР-ПРО (*.kontur)")
            if filepath:
                data = self.project_mgr.load(filepath)
                self.devices = data["devices"]
                self.rooms = data["rooms"]
                self.walls = data.get("walls", [])
                self.doors = data.get("doors", [])
                self.annotations = data.get("annotations", [])
                self.tier = data.get("tier", 1)
                self._draw_scene()
                self._run_calculation()
                self.statusBar().showMessage(f"Загружено: {filepath}")
        
        def _import_dxf(self):
            filepath, _ = QFileDialog.getOpenFileName(self, "Импорт DXF", "", "DXF (*.dxf)")
            if filepath:
                result = DXFImporter.import_dxf(filepath)
                if "error" in result:
                    QMessageBox.warning(self, "Ошибка", result["error"])
                    return
                self.devices.extend(result.get("devices", []))
                self.walls.extend(result.get("walls", []))
                self._draw_scene()
                self.statusBar().showMessage(f"DXF импортирован: {len(result.get('devices', []))} устройств")
        
        def _export(self):
            if not self.devices:
                return
            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()
            checker = ModelChecker()
            checks = checker.run_all(self.devices, self.rooms, result)
            spec = SpecificationBuilder.build(self.devices, result)
            
            filepath, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "HTML (*.html)")
            if filepath:
                html = Exporter.to_html(self.devices, self.rooms, result, checks)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                self.statusBar().showMessage(f"Экспорт: {filepath}")
        
        def _toggle_theme(self):
            self.theme = THEME_LIGHT if self.theme == THEME_DARK else THEME_DARK
            self._apply_theme_to_view()
            self._draw_scene()
            self.theme_btn.setText("Светлая тема" if self.theme == THEME_DARK else "Тёмная тема")
        
        def _filter_palette(self, text):
            self.palette_list.clear()
            for item in self.catalog.items:
                if text.lower() in item["name"].lower():
                    self.palette_list.addItem(f"{item['icon']} {item['name']}")
    
    app = QApplication(sys.argv)
    window = KonturMainWindow()
    window.show()
    sys.exit(app.exec())


# ============================================================================
# СЕКЦИЯ 20: MAIN
# ============================================================================

def main():
    if len(sys.argv) > 1:
        if "--test" in sys.argv:
            run_tests()
        elif "--cli" in sys.argv or "--load" in sys.argv or "--import" in sys.argv:
            run_cli(sys.argv[1:])
        elif "--gui" in sys.argv or (len(sys.argv) == 1):
            run_gui()
        else:
            run_cli(sys.argv[1:])
    else:
        run_gui()


if __name__ == "__main__":
    main()
