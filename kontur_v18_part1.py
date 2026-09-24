#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
КОНТУР-ПРО v18.0 «Квант+ Commercial»
Универсальная система проектирования инженерных систем зданий

Объединение лучших компонентов из v12.0, v13.0, v14.0, v15.1, v16.1, v16.2
+ 7 новых подсистем: ProjectManager, DXFImporter, ScaleManager,
  Z-координаты, ExternalCatalog, MultiProjectManager, HeatLoss+Acoustic

Возможности:
  - Конструктор произвольных зданий и помещений
  - 30 типов оборудования (11 систем)
  - 8 расчётов по СП 256, ПУЭ, ГОСТ 28249, СО 153, СП 52.13330
  - A* 8-направлений с closed_set и heapq (O(n log n))
  - Жадная балансировка фаз (перекос 0-15%)
  - Цифровой двойник (графовая модель)
  - TwinImporter: Obsidian Canvas + Figma
  - UGOPainter: 16 типов УГО по ГОСТ 21.210-2014
  - DesignationGenerator: позиционные обозначения по ГОСТ 2.710-81
  - LANCalculator, VendorDatabase, SpecificationBuilder
  - ModelChecker: 35+ проверок с цветовой подсветкой
  - ShortCircuitCalculator, ReactiveLossCalculator
  - ExtendedSelectivityChecker: B/C/D
  - HeatLossCalculator, AcousticCalculator
  - ProjectManager: сохранение/загрузка .kontur (JSON)
  - DXFImporter: импорт из AutoCAD/nanoCAD
  - ScaleManager: масштаб пиксель-метр
  - Z-координаты: высота установки + вертикальная длина кабеля
  - ExternalCatalog: внешний catalog.json
  - MultiProjectManager: несколько проектов, сравнение
  - Undo/Redo, горячие клавиши
  - Экспорт: Excel (8 листов), HTML, JSON, DXF, PDF, TXT
  - CLI и GUI режимы
  - 64 unit-теста

Запуск:
  python kontur_v18.py                           # GUI
  python kontur_v18.py --cli --template ЦОД --tier 3 --export
  python kontur_v18.py --test
  python kontur_v18.py --import "plan.dxf"
  python kontur_v18.py --save "project.kontur"
  python kontur_v18.py --load "project.kontur"

Зависимости (опционально):
  pip install openpyxl reportlab ezdxf
"""

import os
import sys
import json
import math
import time
import copy
import hashlib
import heapq
import re
import csv
import unittest
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from collections import defaultdict, deque

# ============================================================================
# СЕКЦИЯ 1: КОНФИГУРАЦИЯ
# ============================================================================

VERSION = "18.0"
VERSION_NAME = "Квант+ Commercial"
SCHEMA_VERSION = "5.0"
BUILD_TS = datetime.now().strftime("%Y-%m-%d_%H%M")

# --- Цветовая система ---
THEME_DARK = {
    "bg_app": "#0f0f1a", "bg_panel": "#1a1a2e", "bg_card": "#16213e",
    "bg_canvas": "#ffffff", "bg_canvas_grid": "#e0e0e0",
    "text_primary": "#ffffff", "text_secondary": "#a0a0b0",
    "accent": "#06d6a0", "success": "#34d399", "warning": "#fbbf24",
    "danger": "#f87171", "border": "#4a4a52", "hover": "#533483",
    "room_fill": "#e8f0fe", "room_border": "#06d6a0",
    "device_power": "#f87171", "device_it": "#60a5fa", "device_net": "#34d399",
    "device_cam": "#a78bfa", "device_skud": "#fbbf24", "device_ops": "#fb923c",
    "device_hvac": "#22d3ee", "device_light": "#fde047", "device_custom": "#c084fc",
    "device_lan": "#06d6a0", "device_phone": "#f472b6",
    "trace_power": "#f87171", "trace_net": "#34d399", "trace_cam": "#a78bfa",
    "trace_skud": "#fbbf24", "trace_ops": "#fb923c", "trace_lan": "#06d6a0",
}

THEME_LIGHT = {
    "bg_app": "#f0f0f5", "bg_panel": "#ffffff", "bg_card": "#f8f8fc",
    "bg_canvas": "#ffffff", "bg_canvas_grid": "#e8e8e8",
    "text_primary": "#1a1a2e", "text_secondary": "#6b6b80",
    "accent": "#0d9488", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "border": "#d1d5db", "hover": "#e8eaf0",
    "room_fill": "#e8f0fe", "room_border": "#0d9488",
    "device_power": "#ef4444", "device_it": "#3b82f6", "device_net": "#10b981",
    "device_cam": "#8b5cf6", "device_skud": "#f59e0b", "device_ops": "#f97316",
    "device_hvac": "#06b6d4", "device_light": "#eab308", "device_custom": "#a855f7",
    "device_lan": "#0d9488", "device_phone": "#ec4899",
    "trace_power": "#ef4444", "trace_net": "#10b981", "trace_cam": "#8b5cf6",
    "trace_skud": "#f59e0b", "trace_ops": "#f97316", "trace_lan": "#0d9488",
}

VOLTAGE_DROP_MAX = 5.0
VOLTAGE_DROP_WARN = 3.0
PHASE_IMBALANCE_MAX = 15.0
GROUND_R_MAX = 4.0
GROUND_R_WARN = 10.0

DEMAND_FACTORS = {
    "power": 0.7, "pc": 0.7, "server": 0.9, "network": 0.8,
    "camera": 0.95, "wifi": 0.6, "lighting": 0.6, "hvac": 0.8,
    "skud": 0.85, "ops": 0.9, "ups": 1.0, "custom": 0.7,
    "lan": 0.8, "phone": 0.7, "panel": 1.0, "socket": 0.5,
}

CABLE_TABLE = [
    {"section": 1.5, "max_current": 19, "name": "ВВГнг(А)-LS 3x1.5"},
    {"section": 2.5, "max_current": 27, "name": "ВВГнг(А)-LS 3x2.5"},
    {"section": 4.0, "max_current": 38, "name": "ВВГнг(А)-LS 3x4"},
    {"section": 6.0, "max_current": 50, "name": "ВВГнг(А)-LS 3x6"},
    {"section": 10.0, "max_current": 70, "name": "ВВГнг(А)-LS 3x10"},
    {"section": 16.0, "max_current": 90, "name": "ВВГнг(А)-LS 3x16"},
    {"section": 25.0, "max_current": 120, "name": "ВВГнг(А)-LS 3x25"},
    {"section": 35.0, "max_current": 150, "name": "ВВГнг(А)-LS 3x35"},
    {"section": 50.0, "max_current": 185, "name": "ВВГнг(А)-LS 3x50"},
    {"section": 70.0, "max_current": 230, "name": "ВВГнг(А)-LS 3x70"},
    {"section": 95.0, "max_current": 280, "name": "ВВГнг(А)-LS 3x95"},
    {"section": 120.0, "max_current": 320, "name": "ВВГнг(А)-LS 3x120"},
    {"section": 150.0, "max_current": 350, "name": "ВВГнг(А)-LS 3x150"},
    {"section": 185.0, "max_current": 390, "name": "ВВГнг(А)-LS 3x185"},
    {"section": 240.0, "max_current": 460, "name": "ВВГнг(А)-LS 3x240"},
]

CABLE_AMPACITY = {row["section"]: row["max_current"] for row in CABLE_TABLE}
CABLE_SECTIONS = [row["section"] for row in CABLE_TABLE]

AUTOMAT_STEPS = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250]
BREAKER_RATINGS = AUTOMAT_STEPS
CU_RESISTIVITY = 0.0175
AL_RESISTIVITY = 0.0294

TIER_CONFIG = {
    1: {"name": "Tier I (Базовый)", "ups": False, "cooling": "base", "ups_redundancy": "N", "cooling_redundancy": "N", "color": "#4CAF50", "desc": "Базовый"},
    2: {"name": "Tier II (Бизнес)", "ups": True, "cooling": "enhanced", "ups_redundancy": "N+1", "cooling_redundancy": "N+1", "color": "#FF9800", "desc": "Резервированный"},
    3: {"name": "Tier III (Enterprise)", "ups": True, "cooling": "precision", "ups_redundancy": "2N", "cooling_redundancy": "2N", "color": "#F44336", "desc": "Высоконадёжный"},
}

CATEGORIES = {
    "power": {"name": "Силовое", "color_key": "device_power", "trace_key": "trace_power", "demand": 0.7},
    "it": {"name": "ИТ", "color_key": "device_it", "trace_key": "trace_power", "demand": 0.9},
    "network": {"name": "Сеть", "color_key": "device_net", "trace_key": "trace_net", "demand": 0.8},
    "camera": {"name": "Видео", "color_key": "device_cam", "trace_key": "trace_cam", "demand": 0.95},
    "skud": {"name": "СКУД", "color_key": "device_skud", "trace_key": "trace_skud", "demand": 0.85},
    "ops": {"name": "ОПС", "color_key": "device_ops", "trace_key": "trace_ops", "demand": 0.9},
    "hvac": {"name": "ОВК", "color_key": "device_hvac", "trace_key": "trace_power", "demand": 0.8},
    "lighting": {"name": "Освещение", "color_key": "device_light", "trace_key": "trace_power", "demand": 0.6},
    "lan": {"name": "ЛВС", "color_key": "device_lan", "trace_key": "trace_lan", "demand": 0.8},
    "phone": {"name": "Телефония", "color_key": "device_phone", "trace_key": "trace_net", "demand": 0.7},
    "grounding": {"name": "Заземление", "color_key": "device_power", "trace_key": "trace_power", "demand": 1.0},
    "custom": {"name": "Прочее", "color_key": "device_custom", "trace_key": "trace_power", "demand": 0.7},
}

EQUIPMENT_LIBRARY = [
    {"id": "panel_main", "name": "ВРУ", "power_w": 0, "category": "power", "voltage": 380, "price": 45000},
    {"id": "panel_floor", "name": "Щит этажный", "power_w": 0, "category": "power", "voltage": 380, "price": 18000},
    {"id": "panel_light", "name": "Щит освещения", "power_w": 0, "category": "power", "voltage": 220, "price": 12000},
    {"id": "socket", "name": "Розетка 2П+З", "power_w": 100, "category": "power", "voltage": 220, "price": 350},
    {"id": "ups_10", "name": "ИБП 10кВА", "power_w": 10000, "category": "power", "voltage": 220, "price": 120000},
    {"id": "ups_30", "name": "ИБП 30кВА", "power_w": 30000, "category": "power", "voltage": 220, "price": 350000},
    {"id": "pc", "name": "Рабочее место (ПК)", "power_w": 450, "category": "it", "voltage": 220, "price": 50000},
    {"id": "server", "name": "Сервер 1U", "power_w": 500, "category": "it", "voltage": 220, "price": 250000},
    {"id": "rack42u", "name": "Стойка 42U", "power_w": 5000, "category": "it", "voltage": 220, "price": 80000},
    {"id": "switch_l2", "name": "Коммутатор L2 48p", "power_w": 150, "category": "network", "voltage": 220, "price": 15000},
    {"id": "switch_l3", "name": "Коммутатор L3 48p PoE+", "power_w": 750, "category": "network", "voltage": 220, "price": 80000},
    {"id": "router", "name": "Маршрутизатор", "power_w": 200, "category": "network", "voltage": 220, "price": 60000},
    {"id": "wifi", "name": "Точка Wi-Fi", "power_w": 30, "category": "network", "voltage": 220, "price": 8000},
    {"id": "cam_ip", "name": "IP-камера купольная", "power_w": 15, "category": "camera", "voltage": 220, "price": 12000},
    {"id": "cam_ptz", "name": "PTZ-камера цилиндрическая", "power_w": 60, "category": "camera", "voltage": 220, "price": 45000},
    {"id": "nvr", "name": "NVR видеорегистратор", "power_w": 400, "category": "camera", "voltage": 220, "price": 35000},
    {"id": "skud_ctrl", "name": "Контроллер СКУД", "power_w": 50, "category": "skud", "voltage": 220, "price": 20000},
    {"id": "skud_reader", "name": "Считыватель", "power_w": 5, "category": "skud", "voltage": 220, "price": 5000},
    {"id": "skud_lock", "name": "Замок электромагнитный", "power_w": 15, "category": "skud", "voltage": 220, "price": 4000},
    {"id": "turnstile", "name": "Турникет", "power_w": 50, "category": "skud", "voltage": 220, "price": 35000},
    {"id": "ops_panel", "name": "ППКПУ ОПС", "power_w": 80, "category": "ops", "voltage": 220, "price": 28000},
    {"id": "ops_smoke", "name": "Датчик дымовой", "power_w": 1, "category": "ops", "voltage": 12, "price": 800},
    {"id": "ops_heat", "name": "Датчик тепловой", "power_w": 1, "category": "ops", "voltage": 12, "price": 600},
    {"id": "ops_manual", "name": "Извещатель ручной (ИПР)", "power_w": 1, "category": "ops", "voltage": 12, "price": 1200},
    {"id": "ops_siren", "name": "Сирена", "power_w": 20, "category": "ops", "voltage": 12, "price": 2500},
    {"id": "ops_beacon", "name": "Оповещатель световой", "power_w": 5, "category": "ops", "voltage": 12, "price": 1800},
    {"id": "ac_5kw", "name": "Кондиционер 5кВт", "power_w": 5000, "category": "hvac", "voltage": 220, "price": 55000},
    {"id": "ac_15kw", "name": "Прецизионный 15кВт", "power_w": 15000, "category": "hvac", "voltage": 380, "price": 280000},
    {"id": "light_led", "name": "Светильник LED", "power_w": 40, "category": "lighting", "voltage": 220, "price": 3500},
    {"id": "patch_panel", "name": "Патч-панель 48p", "power_w": 0, "category": "lan", "voltage": 0, "price": 12000},
]

EQUIPMENT_BY_ID = {item["id"]: item for item in EQUIPMENT_LIBRARY}
PRICE_LIST = {item["id"]: item["price"] for item in EQUIPMENT_LIBRARY}

VENDORS = {
    "IEK": {"country": "Китай/Россия", "cert": "EAC", "warranty": 60},
    "КЭАЗ": {"country": "Россия", "cert": "EAC", "warranty": 120},
    "Systeme_Electric": {"country": "Россия", "cert": "EAC", "warranty": 60},
    "ABB": {"country": "Швейцария", "cert": "CE/EAC", "warranty": 120},
    "Schneider": {"country": "Франция", "cert": "CE/EAC", "warranty": 120},
    "Legrand": {"country": "Франция", "cert": "CE/EAC", "warranty": 60},
}

DESIGNATION_PREFIX = {
    "panel_main": "ВРУ", "panel_floor": "ЩР", "panel_light": "ЩО", "socket": "R",
    "ups_10": "ИБП", "ups_30": "ИБП", "pc": "РМ", "server": "С", "rack42u": "СТ",
    "switch_l2": "SW", "switch_l3": "SW", "router": "RT", "wifi": "AP",
    "cam_ip": "К", "cam_ptz": "К", "nvr": "NVR",
    "skud_ctrl": "СКУД", "skud_reader": "СЧ", "skud_lock": "Z", "turnstile": "Т",
    "ops_panel": "ППКПУ", "ops_smoke": "Д", "ops_heat": "Т", "ops_manual": "ИПР",
    "ops_siren": "С", "ops_beacon": "ОС",
    "ac_5kw": "КНД", "ac_15kw": "ПРК", "light_led": "L", "patch_panel": "ПП",
}

UGO_TYPES = {
    "panel_main": "panel", "panel_floor": "panel", "panel_light": "panel",
    "socket": "socket", "ups_10": "ups", "ups_30": "ups",
    "pc": "pc", "server": "server", "rack42u": "rack",
    "switch_l2": "switch", "switch_l3": "switch", "router": "router", "wifi": "wifi",
    "cam_ip": "cam_dome", "cam_ptz": "cam_cyl", "nvr": "nvr",
    "skud_ctrl": "ctrl", "skud_reader": "reader", "skud_lock": "lock", "turnstile": "turnstile",
    "ops_panel": "ppkpu", "ops_smoke": "smoke", "ops_heat": "heat",
    "ops_manual": "manual", "ops_siren": "siren", "ops_beacon": "beacon",
    "ac_5kw": "ac", "ac_15kw": "ac", "light_led": "light", "patch_panel": "patch",
}

TEMPLATES = {
    "Офис": {"area": 500, "rooms": 6, "floors": 1, "height": 3.5, "people": 50, "tier": 1,
        "devices": [("panel_main",1),("panel_floor",1),("panel_light",1),("switch_l2",2),("wifi",3),("pc",20),
            ("cam_ip",6),("skud_reader",4),("skud_lock",2),("ops_smoke",10),("ops_heat",4),("ops_panel",1),
            ("ac_5kw",2),("light_led",8),("socket",30)]},
    "Склад": {"area": 1000, "rooms": 3, "floors": 1, "height": 8, "people": 10, "tier": 1,
        "devices": [("panel_main",1),("panel_floor",1),("switch_l2",1),("cam_ip",4),("cam_ptz",4),("nvr",1),
            ("skud_reader",2),("turnstile",1),("ops_smoke",15),("ops_heat",8),("ops_panel",1),
            ("ac_5kw",3),("light_led",12)]},
    "ЦОД": {"area": 200, "rooms": 2, "floors": 1, "height": 4, "people": 2, "tier": 3,
        "devices": [("panel_main",1),("ups_30",2),("switch_l3",2),("router",1),("server",10),("rack42u",2),
            ("cam_ip",3),("skud_reader",2),("skud_lock",1),("ops_smoke",8),("ops_panel",1),
            ("ac_15kw",2),("patch_panel",2)]},
    "Школа": {"area": 2000, "rooms": 15, "floors": 2, "height": 3.2, "people": 200, "tier": 2,
        "devices": [("panel_main",1),("panel_floor",2),("panel_light",2),("switch_l2",3),("wifi",5),("pc",30),
            ("cam_ip",10),("skud_reader",6),("skud_lock",4),("turnstile",1),
            ("ops_smoke",20),("ops_heat",10),("ops_manual",5),("ops_panel",1),("ac_5kw",4),("light_led",30)]},
}

LIGHTING_NORMS = {"office": 300, "school": 300, "datacenter": 500, "warehouse": 200, "corridor": 150}
POE_BUDGET_W = 740

CABLE_REACTANCE = {1.5: 0.1, 2.5: 0.095, 4: 0.09, 6: 0.087, 10: 0.082, 16: 0.078,
                    25: 0.066, 35: 0.064, 50: 0.063, 70: 0.061, 95: 0.058,
                    120: 0.057, 150: 0.056, 185: 0.055, 240: 0.053}
