"""КОНТУР-ПРО: модуль undo."""

from __future__ import annotations

import copy
from collections import deque
from typing import Any

# ============================================================================
# СЕКЦИЯ 14: UNDO/REDO MANAGER
# ============================================================================


class UndoManager:
    """Менеджер отмены действий с ограниченной историей."""

    def __init__(self, max_steps: int = 50) -> None:
        """Инициализация менеджера отмены.

        Args:
            max_steps: Максимальное количество шагов в истории отмены.
        """
        self.stack: deque[dict[str, Any]] = deque(maxlen=max_steps)
        self.redo_stack: list[dict[str, Any]] = []
        self.max_steps = max_steps

    def push(self, state: dict[str, Any]) -> None:
        """Добавить состояние в историю отмены.

        Args:
            state: Состояние для добавления.
        """
        self.stack.append(copy.deepcopy(state))
        self.redo_stack.clear()

    def undo(self) -> dict[str, Any] | None:
        """Отменить последнее действие.

        Returns:
            Предыдущее состояние или None если истории нет.
        """
        if len(self.stack) < 2:
            return None
        self.redo_stack.append(self.stack.pop())
        return copy.deepcopy(self.stack[-1])

    def redo(self) -> dict[str, Any] | None:
        """Повторить отменённое действие.

        Returns:
            Восстановленное состояние или None если нечего повторять.
        """
        if not self.redo_stack:
            return None
        state = self.redo_stack.pop()
        self.stack.append(state)
        return copy.deepcopy(state)

    def can_undo(self) -> bool:
        """Проверить возможность отмены.

        Returns:
            True если есть что отменять.
        """
        return len(self.stack) >= 2

    def can_redo(self) -> bool:
        """Проверить возможность повтора.

        Returns:
            True если есть что повторять.
        """
        return len(self.redo_stack) > 0
