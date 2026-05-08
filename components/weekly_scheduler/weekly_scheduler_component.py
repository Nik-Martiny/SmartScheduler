from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"
_component_func = components.declare_component(
    "weekly_scheduler_component",
    url="http://localhost:5173",
)

def weekly_scheduler_component(
    *,
    grid: Dict[Tuple[int, int], str],
    days: List[str],
    selected_slots: List[Tuple[int, int]],
    key: str = "weekly_scheduler_component",
) -> List[Tuple[int, int]]:
    """Render custom weekly scheduler component and return selected slots."""
    global _component_func
    payload = {f"{d}-{h}": state for (d, h), state in grid.items()}

    if not _BUILD_DIR.exists():
        st.error("Compiled component assets are unavailable. Try building the assets using npm build")


    if _component_func is None:
        _component_func = components.declare_component(
            "weekly_scheduler_component",
            path=str(_BUILD_DIR),
        )

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
