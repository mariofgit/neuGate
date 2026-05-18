from __future__ import annotations

import threading

from neugate.models.config import ProjectConfig


class PivotSelector:
    """Selects persona pivot templates (rotation strategy)."""

    def __init__(self) -> None:
        self._cursors: dict[str, int] = {}
        self._lock = threading.Lock()

    def next_template(self, config: ProjectConfig) -> str:
        pivot = config.persona_pivot
        templates = pivot.templates

        if pivot.strategy != "rotation":
            return templates[0]

        key = config.project_id
        with self._lock:
            index = self._cursors.get(key, 0)
            template = templates[index % len(templates)]
            self._cursors[key] = index + 1

        return template


_pivot_selector: PivotSelector | None = None


def get_pivot_selector() -> PivotSelector:
    global _pivot_selector
    if _pivot_selector is None:
        _pivot_selector = PivotSelector()
    return _pivot_selector
