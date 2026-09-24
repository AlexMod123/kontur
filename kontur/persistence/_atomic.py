"""КОНТУР-ПРО: модуль persistence._atomic.

Общая утилита атомарной записи файлов, используемая ``project.py`` и
``catalog.py`` (устраняет дублирование ``_atomic_write_json``).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def atomic_write_text(path: Path, text: str) -> None:
    """Записывает текст атомарно: во временный файл в той же директории, затем os.replace."""
    directory = path.parent if str(path.parent) else Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(directory))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except OSError:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Не удалось удалить временный файл %s", tmp_path)
        raise


def atomic_write_json(path: Path, data: Any, **dump_kwargs: Any) -> None:
    """Записывает JSON атомарно: во временный файл в той же директории, затем os.replace."""
    atomic_write_text(path, json.dumps(data, **dump_kwargs))
