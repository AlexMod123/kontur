"""КОНТУР-ПРО: модуль persistence.catalog."""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

from kontur.config import EQUIPMENT_LIBRARY
from kontur.persistence._atomic import atomic_write_json

# ============================================================================
# СЕКЦИЯ 12: EXTERNAL CATALOG
# ============================================================================

logger = logging.getLogger(__name__)

#: Разделитель полей в прайс-листах CSV (исторически ";", т.к. запятая —
#: десятичный разделитель в русской локали Excel).
CSV_DELIMITER = ";"

#: Ожидаемые колонки прайс-листа CSV, в порядке следования.
CSV_COLUMNS = ("id", "name", "power_w", "category", "price")

#: Минимальное число заполненных колонок, при котором строка считается валидной
#: (id, name, power_w, category обязательны; price опциональна).
CSV_REQUIRED_COLUMNS = 4


class ExternalCatalog:
    """Внешний каталог оборудования (catalog.json)"""

    def __init__(self, filepath: str | os.PathLike[str] = "catalog.json") -> None:
        self.filepath = Path(filepath)
        self.items: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if self.filepath.exists():
            try:
                with self.filepath.open(encoding="utf-8") as f:
                    self.items = json.load(f)
            except (OSError, json.JSONDecodeError):
                logger.warning("Не удалось загрузить каталог %s", self.filepath, exc_info=True)
                self.items = []
        else:
            self.items = list(EQUIPMENT_LIBRARY)
            self.save()

    def save(self) -> None:
        atomic_write_json(self.filepath, self.items, ensure_ascii=False, indent=2)

    def add(self, item: dict[str, Any]) -> None:
        self.items.append(item)
        self.save()

    def find(self, name: str = "", category: str = "") -> list[dict[str, Any]]:
        results = self.items
        if name:
            results = [i for i in results if name.lower() in i.get("name", "").lower()]
        if category:
            results = [i for i in results if i.get("category") == category]
        return results

    def import_csv(self, filepath: str | os.PathLike[str]) -> int:
        """Импорт прайс-листа из CSV.

        Возвращает число успешно импортированных строк, либо -1 при ошибке
        чтения файла (сохраняя поведение прежней реализации).
        Строки с недостаточным числом колонок или нечисловыми
        power_w/price пропускаются с предупреждением в лог.
        """
        path = Path(filepath)
        imported = 0
        try:
            with path.open(encoding="utf-8", newline="") as f:
                reader = csv.reader(f, delimiter=CSV_DELIMITER)
                next(reader, None)  # пропустить заголовок
                for line_no, row in enumerate(reader, start=2):
                    item = self._parse_csv_row(row, line_no)
                    if item is not None:
                        self.items.append(item)
                        imported += 1
            self.save()
        except OSError as e:
            logger.warning("Не удалось импортировать CSV %s: %s", path, e)
            return -1
        return imported

    @staticmethod
    def _parse_csv_row(row: list[str], line_no: int) -> dict[str, Any] | None:
        if len(row) < CSV_REQUIRED_COLUMNS:
            logger.warning("Строка %d прайс-листа пропущена: недостаточно колонок (%s)", line_no, row)
            return None

        row_id, name, power_raw, category = (v.strip() for v in row[:4])
        price_raw = row[4].strip() if len(row) > 4 else ""

        if not row_id or not name:
            logger.warning("Строка %d прайс-листа пропущена: пустой id или name", line_no)
            return None

        try:
            power_w = float(power_raw) if power_raw else 0.0
        except ValueError:
            logger.warning("Строка %d прайс-листа пропущена: некорректный power_w=%r", line_no, power_raw)
            return None

        try:
            price = float(price_raw) if price_raw else 0.0
        except ValueError:
            logger.warning("Строка %d прайс-листа пропущена: некорректный price=%r", line_no, price_raw)
            return None

        return {
            "id": row_id,
            "name": name,
            "power_w": power_w,
            "category": category,
            "price": price,
        }
