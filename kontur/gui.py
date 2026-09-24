"""КОНТУР-ПРО: модуль gui.

Графический интерфейс на PyQt6. Импорт PyQt6 — опциональный: при его
отсутствии модуль импортируется без ошибок (флаг ``QT_AVAILABLE`` = False),
а :func:`run_gui` поднимает :class:`GuiUnavailableError` с понятным
сообщением вместо падения с ``ImportError``.

Логика без зависимости от Qt (подготовка данных для таблиц) вынесена в
отдельные функции модуля — их можно тестировать без PyQt6. Виджеты и
обработчики событий остаются в :class:`KonturMainWindow`.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from kontur.checker import ModelChecker
from kontur.config import CATEGORIES, TEMPLATES, THEME_DARK, THEME_LIGHT, VERSION, VERSION_NAME
from kontur.core import EngineeringCore
from kontur.export import Exporter
from kontur.persistence.catalog import ExternalCatalog
from kontur.persistence.dxf_import import DXFImporter
from kontur.persistence.project import ProjectManager
from kontur.scale import ScaleManager
from kontur.specification import SpecificationBuilder
from kontur.templates import generate_template
from kontur.undo import UndoManager

if TYPE_CHECKING:
    from kontur.models import Device, EngineeringResult, Room

logger = logging.getLogger(__name__)

# ============================================================================
# СЕКЦИЯ: GUI (PyQt6, опционально)
# ============================================================================

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QFont,
        QPainter,
        QPen,
    )
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QGraphicsScene,
        QGraphicsView,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSpinBox,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    QT_AVAILABLE = False
else:
    QT_AVAILABLE = True


class GuiUnavailableError(RuntimeError):
    """PyQt6 не установлен — графический интерфейс недоступен."""


# ----------------------------------------------------------------------------
# Логика без Qt: подготовка данных для таблиц (тестируема без PyQt6)
# ----------------------------------------------------------------------------


def build_calc_rows(result: EngineeringResult) -> list[tuple[str, str]]:
    """Строки таблицы «Расчёт» (параметр, значение) по результату расчёта."""
    return [
        ("Мощность (уст.)", f"{result.installed_power_w / 1000:.2f} кВт"),
        ("Мощность (расч.)", f"{result.demand_power_w / 1000:.2f} кВт"),
        ("Ток", f"{result.total_current_a:.1f} А"),
        ("cos φ", str(result.cos_phi)),
        ("Перекос фаз", f"{result.phase_imbalance_pct}%"),
        ("Автомат", f"С{result.recommended_breaker}"),
        ("Кабель", result.recommended_cable),
        ("Падение U", f"{result.voltage_drop_pct}%"),
        ("Заземление", f"{result.grounding_r} Ом [{result.grounding_status}]"),
        ("Охлаждение", f"{result.cooling_required_w / 1000:.1f} кВт"),
        ("ИБП", f"{result.ups_power_w / 1000:.1f} кВт"),
        ("Токи КЗ", f"I3ф={result.short_circuit_3ph}А"),
        ("Утечки", f"{result.leakage_current_ma} мА"),
        ("Молниезащита", result.lightning_zone),
        ("ЛВС", f"{result.lan_ports} портов"),
        ("PoE", f"{result.poe_required_w}/{result.poe_budget_w} Вт"),
        ("Теплопотери", f"{result.heat_loss_w:.0f} Вт"),
        ("Шум", f"{result.noise_level_db:.1f} дБ"),
        ("Смета", f"{result.cost_total:,.0f} ₽"),
    ]


def device_marker_color(theme: dict[str, str], device: Device) -> str:
    """Цвет маркера устройства на схеме по его категории и текущей теме."""
    color_key = CATEGORIES.get(device.category, {}).get("color_key", "device_custom")
    return theme.get(color_key, "#06d6a0")


def check_status_color(status: str) -> str:
    """Цвет текста статуса проверки модели (OK/WARN/FAIL) в таблице."""
    return {"OK": "#06d6a0", "WARN": "#fbbf24", "FAIL": "#f87171"}.get(status, "#666")


if QT_AVAILABLE:

    class KonturMainWindow(QMainWindow):
        """Главное окно КОНТУР-ПРО: палитра, холст плана, вкладки результатов."""

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"КОНТУР-ПРО v{VERSION} «{VERSION_NAME}»")
            self.resize(1400, 900)
            self.devices: list[Device] = []
            self.rooms: list[Room] = []
            self.walls: list = []
            self.doors: list = []
            self.annotations: list = []
            self.tier = 1
            self.scale_mgr = ScaleManager(50.0)
            self.undo_mgr = UndoManager()
            self.project_mgr = ProjectManager()
            self.catalog = ExternalCatalog()
            self.theme = THEME_DARK
            self._init_ui()

        def _init_ui(self) -> None:
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
            self.spec_table.setHorizontalHeaderLabels(
                ["№", "Обозн.", "Наим.", "Тип", "Вендор", "Ед.", "Кол.", "Прим."]
            )
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

        def _apply_theme_to_view(self) -> None:
            c = self.theme
            self.view.setBackgroundBrush(QBrush(QColor(c["bg_canvas"])))

        def _new_project(self) -> None:
            self.devices = []
            self.rooms = []
            self.walls = []
            self.doors = []
            self.annotations = []
            self.scene.clear()
            self.statusBar().showMessage("Новый проект создан")

        def _load_template(self) -> None:
            tpl_name = self.template_combo.currentText()
            self.tier = self.tier_spin.value()
            self.devices, self.rooms = generate_template(tpl_name, self.tier)
            self._draw_scene()
            self._run_calculation()
            self.statusBar().showMessage(
                f"Шаблон '{tpl_name}' загружен: {len(self.devices)} устройств, {len(self.rooms)} помещений"
            )

        def _draw_scene(self) -> None:
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
                self.scene.addRect(
                    room.x,
                    room.y,
                    room.width,
                    room.height,
                    QPen(QColor(c["room_border"]), 2),
                    QBrush(QColor(c["room_fill"])),
                )
                text = self.scene.addText(room.name)
                text.setPos(room.x + 5, room.y + 5)
                text.setDefaultTextColor(QColor(c["text_secondary"]))

            # Устройства
            for dev in self.devices:
                color = QColor(device_marker_color(c, dev))
                self.scene.addEllipse(
                    dev.x - 12, dev.y - 12, 24, 24, QPen(color, 2), QBrush(color.lighter(150))
                )
                label = self.scene.addText(dev.name)
                label.setPos(dev.x - 12, dev.y + 14)
                label.setDefaultTextColor(QColor(c["text_primary"]))
                label.setFont(QFont("Arial", 7))

        def _run_calculation(self) -> None:
            if not self.devices:
                self.statusBar().showMessage("Нет устройств для расчёта")
                return
            self.tier = self.tier_spin.value()
            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()

            data = build_calc_rows(result)
            self.calc_table.setRowCount(len(data))
            for i, (k, v) in enumerate(data):
                self.calc_table.setItem(i, 0, QTableWidgetItem(k))
                self.calc_table.setItem(i, 1, QTableWidgetItem(v))

            # Проверки
            checker = ModelChecker()
            checks = checker.run_all(self.devices, self.rooms, result)
            self.checks_table.setRowCount(len(checks))
            for i, ch in enumerate(checks):
                item0 = QTableWidgetItem(ch["name"])
                item1 = QTableWidgetItem(ch["status"])
                item1.setForeground(QColor(check_status_color(ch["status"])))
                item2 = QTableWidgetItem(ch["detail"])
                self.checks_table.setItem(i, 0, item0)
                self.checks_table.setItem(i, 1, item1)
                self.checks_table.setItem(i, 2, item2)

            # Спецификация
            spec = SpecificationBuilder.build(self.devices, result)
            self.spec_table.setRowCount(len(spec))
            for i, s in enumerate(spec):
                for j, key in enumerate(
                    ["pos", "designation", "name", "type", "vendor", "unit", "qty", "note"]
                ):
                    self.spec_table.setItem(i, j, QTableWidgetItem(str(s.get(key, ""))))

            self.statusBar().showMessage(
                f"Расчёт выполнен: {len(checks)} проверок, смета {result.cost_total:,.0f} ₽"
            )

        def _route_cables(self) -> None:
            if not self.devices:
                return
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(self.devices))

            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()

            c = self.theme
            for i, trace in enumerate(result.cable_traces):
                category = next((d.category for d in self.devices if d.id == trace.device_id), "power")
                trace_key = CATEGORIES.get(category, {}).get("trace_key", "trace_power")
                color = QColor(c.get(trace_key, "#f87171"))
                for j in range(len(trace.path) - 1):
                    x1, y1 = trace.path[j]
                    x2, y2 = trace.path[j + 1]
                    self.scene.addLine(x1, y1, x2, y2, QPen(color, 2))
                self.progress_bar.setValue(i + 1)

            self.statusBar().showMessage(f"Трассировка: {len(result.cable_traces)} кабелей")

        def _undo(self) -> None:
            state = self.undo_mgr.undo()
            if state:
                self._restore_state(state)
                self.statusBar().showMessage("Отменено")

        def _redo(self) -> None:
            state = self.undo_mgr.redo()
            if state:
                self._restore_state(state)
                self.statusBar().showMessage("Повторено")

        def _restore_state(self, state: dict) -> None:
            self.devices = state.get("devices", [])
            self.rooms = state.get("rooms", [])
            self._draw_scene()

        def _save_project(self) -> None:
            filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "", "КОНТУР-ПРО (*.kontur)")
            if filepath:
                result = self.project_mgr.save(
                    filepath,
                    self.devices,
                    self.rooms,
                    self.walls,
                    self.doors,
                    self.annotations,
                    self.tier,
                    self.scale_mgr.ppm,
                )
                self.statusBar().showMessage(f"Сохранено: {result['path']}")

        def _open_project(self) -> None:
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

        def _import_dxf(self) -> None:
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

        def _export(self) -> None:
            if not self.devices:
                return
            core = EngineeringCore(self.devices, self.rooms, self.tier, self.scale_mgr)
            result = core.calculate()
            checker = ModelChecker()
            checks = checker.run_all(self.devices, self.rooms, result)
            SpecificationBuilder.build(self.devices, result)

            filepath, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "HTML (*.html)")
            if filepath:
                html = Exporter.to_html(self.devices, self.rooms, result, checks)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                self.statusBar().showMessage(f"Экспорт: {filepath}")

        def _toggle_theme(self) -> None:
            self.theme = THEME_LIGHT if self.theme == THEME_DARK else THEME_DARK
            self._apply_theme_to_view()
            self._draw_scene()
            self.theme_btn.setText("Светлая тема" if self.theme == THEME_DARK else "Тёмная тема")

        def _filter_palette(self, text: str) -> None:
            self.palette_list.clear()
            for item in self.catalog.items:
                if text.lower() in item["name"].lower():
                    self.palette_list.addItem(f"{item['icon']} {item['name']}")


def run_gui() -> int:
    """Запускает GUI-приложение. Возвращает код завершения (из `QApplication.exec`).

    :raises GuiUnavailableError: если PyQt6 не установлен.
    """
    if not QT_AVAILABLE:
        raise GuiUnavailableError("PyQt6 не установлен. Установите: pip install PyQt6")
    logger.info("Запуск GUI КОНТУР-ПРО v%s", VERSION)
    app = QApplication(sys.argv)
    window = KonturMainWindow()
    window.show()
    return app.exec()
