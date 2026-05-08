from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"

_component_func = components.declare_component(
    "weekly_scheduler_component",
    path=str(_BUILD_DIR),
)


def weekly_scheduler_component(
    *,
    grid: Dict[Tuple[int, int], str],
    days: List[str],
    selected_slots: List[Tuple[int, int]],
    key: str = "weekly_scheduler_component",
) -> List[Tuple[int, int]]:
    """Render custom weekly scheduler component and return selected slots."""
    payload = {f"{d}-{h}": state for (d, h), state in grid.items()}

    if not _BUILD_DIR.exists():
        st.warning("Weekly Scheduler component frontend is not built yet. Run: npm install && npm run build in components/weekly_scheduler/frontend")
        return selected_slots

    value = _component_func(
        grid=json.dumps(payload),
        days=json.dumps(days),
        selected_slots=json.dumps(selected_slots),
        key=key,
        default=selected_slots,
    )

    if value is None:
        return selected_slots
    return [(int(x[0]), int(x[1])) for x in value]
