from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"
_component_func = None


def _fallback_html_grid(
    payload: Dict[str, str], days: List[str], selected_slots: List[Tuple[int, int]], key: str
) -> List[Tuple[int, int]]:
    preset_js = json.dumps(selected_slots)
    grid_js = json.dumps(payload)
    days_js = json.dumps(days)
    html = f"""
    <div>
      <style>
        .sched-table {{ border-collapse: collapse; width: 100%; user-select: none; }}
        .sched-table th, .sched-table td {{ border: 1px solid #333; text-align: center; font-size: 11px; }}
        .sched-table th {{ background: #111; padding: 4px; }}
        .hour-col {{ background: #111; padding: 4px; width: 54px; }}
        .slot {{ width: 60px; height: 24px; cursor: pointer; }}
        .free {{ background: #1f2937; }} .blocked {{ background: #dc2626; }}
        .study {{ background: #16a34a; }} .due {{ background: #eab308; }}
        .selected {{ box-shadow: inset 0 0 0 3px #2563eb; }}
      </style>
      <table class="sched-table" id="{key}_sched"><thead><tr><th>Hour</th></tr></thead><tbody></tbody></table>
    </div>
    <script>
      const DAYS = {days_js}, GRID = {grid_js}, PRESET = {preset_js};
      const table = document.querySelector("#{key}_sched");
      const tbody = table.querySelector("tbody"), headerRow = table.querySelector("thead tr");
      DAYS.forEach(day => {{ const th = document.createElement("th"); th.textContent = day; headerRow.appendChild(th); }});
      const selected = new Set(PRESET.map(x => `${{x[0]}}-${{x[1]}}`));
      let mouseDown = false; let lastCell = null;
      function paint() {{ document.querySelectorAll("#{key}_sched .slot").forEach(el => selected.has(el.dataset.key) ? el.classList.add("selected") : el.classList.remove("selected")); }}
      function toggle(cell, force=null) {{ const k = cell.dataset.key; if (force===true) selected.add(k); else if (force===false) selected.delete(k); else selected.has(k) ? selected.delete(k) : selected.add(k); }}
      for (let h=0; h<24; h++) {{
        const tr = document.createElement("tr"); const hour = document.createElement("td");
        hour.className = "hour-col"; hour.textContent = `${{String(h).padStart(2, "0")}}:00`; tr.appendChild(hour);
        for (let d=0; d<7; d++) {{
          const k = `${{d}}-${{h}}`; const td = document.createElement("td");
          td.className = `slot ${{GRID[k] || "free"}}`; td.dataset.key = k;
          td.onmousedown = (e) => {{ mouseDown = true; if (e.shiftKey && lastCell) {{
            const [ld, lh] = lastCell.split("-").map(Number), [cd, ch] = k.split("-").map(Number);
            for (let dd=Math.min(ld,cd); dd<=Math.max(ld,cd); dd++) for (let hh=Math.min(lh,ch); hh<=Math.max(lh,ch); hh++) {{
              const cell = document.querySelector("#{key}_sched .slot[data-key='"+dd+"-"+hh+"']"); if (cell) toggle(cell, true);
            }}
          }} else toggle(td); lastCell = k; paint(); }};
          td.onmouseover = () => {{ if (!mouseDown) return; toggle(td, true); lastCell = k; paint(); }};
          tr.appendChild(td);
        }}
        tbody.appendChild(tr);
      }}
      document.addEventListener("mouseup", () => mouseDown = false);
      paint();
      function sync() {{ const v = Array.from(selected).map(k => k.split("-").map(Number)); if (window.Streamlit) window.Streamlit.setComponentValue(v); }}
      setInterval(sync, 300); sync();
    </script>
    """
    value = components.html(html, height=760, scrolling=True)
    if value is None:
        return selected_slots
    return [(int(d), int(h)) for d, h in value]


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
        st.info("Using fallback weekly editor because compiled component assets are unavailable.")
        return _fallback_html_grid(payload, days, selected_slots, key)

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
