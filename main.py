from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from components.weekly_scheduler import weekly_scheduler_component

STORAGE_PATH = Path(__file__).with_name("scheduler_state.json")
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@dataclass
class Task:
    """A child task that belongs to one Course."""

    title: str
    due_date: str
    category: str
    estimated_hours: float

    @staticmethod
    def from_dict(raw_task: dict) -> "Task":
        return Task(
            title=raw_task["title"],
            due_date=raw_task["due_date"],
            category=raw_task["category"],
            estimated_hours=float(raw_task["estimated_hours"]),
        )


@dataclass
class Course:
    """Parent object that owns a list of child Task objects."""

    name: str
    color: str
    difficulty: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, title: str, due_date: str, category: str, estimated_hours: float) -> None:
        self.tasks.append(
            Task(title=title, due_date=due_date, category=category, estimated_hours=estimated_hours)
        )

    def remove_task(self, task_idx: int) -> None:
        if 0 <= task_idx < len(self.tasks):
            self.tasks.pop(task_idx)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(raw_course: dict) -> "Course":
        tasks = [Task.from_dict(task) for task in raw_course.get("tasks", [])]
        return Course(
            name=raw_course["name"],
            color=raw_course["color"],
            difficulty=int(raw_course["difficulty"]),
            tasks=tasks,
        )


def load_state() -> dict:
    if not STORAGE_PATH.exists():
        return {"courses": [], "blocked_times": []}

    try:
        raw_state = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
        if "blocked_times" not in raw_state:
            raw_state["blocked_times"] = []
        return raw_state
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {"courses": [], "blocked_times": []}


def save_state() -> None:
    payload = {
        "courses": [course.to_dict() for course in st.session_state.courses],
        "blocked_times": st.session_state.blocked_times,
    }
    STORAGE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def init_state() -> None:
    raw_state = load_state()

    if "courses" not in st.session_state:
        st.session_state.courses = [Course.from_dict(course) for course in raw_state.get("courses", [])]
    if "blocked_times" not in st.session_state:
        st.session_state.blocked_times = raw_state.get("blocked_times", [])
    if "pending_course_delete" not in st.session_state:
        st.session_state.pending_course_delete = None
    if "pending_task_delete" not in st.session_state:
        st.session_state.pending_task_delete = None


def add_course(name: str, color: str, difficulty: int) -> None:
    st.session_state.courses.append(Course(name=name.strip(), color=color, difficulty=difficulty))
    save_state()


def update_course(course_idx: int, name: str, color: str, difficulty: int) -> None:
    if 0 <= course_idx < len(st.session_state.courses):
        course = st.session_state.courses[course_idx]
        course.name = name.strip()
        course.color = color
        course.difficulty = difficulty
        save_state()


def update_task(course_idx: int, task_idx: int, title: str, due_date: datetime, category: str, estimated_hours: float) -> None:
    if 0 <= course_idx < len(st.session_state.courses):
        course = st.session_state.courses[course_idx]
        if 0 <= task_idx < len(course.tasks):
            task = course.tasks[task_idx]
            task.title = title.strip()
            task.due_date = due_date.isoformat()
            task.category = category
            task.estimated_hours = float(estimated_hours)
            save_state()


def remove_course(course_idx: int) -> None:
    if 0 <= course_idx < len(st.session_state.courses):
        st.session_state.courses.pop(course_idx)
        save_state()


def get_week_start(today: date) -> date:
    return today - timedelta(days=(today.weekday() + 1) % 7)


def render_course_controls() -> None:
    st.title("📚 Smart Scheduler")
    st.caption("Course tracker + automatic weekly study planner")

    with st.popover("➕ Add Course", use_container_width=False):
        with st.form("add_course_form", clear_on_submit=True):
            name = st.text_input("Course Name", placeholder="e.g., Algorithms")
            color = st.color_picker("Course Color", value="#4F46E5")
            difficulty = st.slider("Estimated Difficulty", min_value=1, max_value=10, value=5)
            submitted = st.form_submit_button("Create Course", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.warning("Please enter a course name.")
                else:
                    add_course(name, color, difficulty)
                    st.success(f"Created course: {name}")
                    st.rerun()


def render_blocked_time_controls(week_start: date) -> None:
    st.subheader("⛔ Weekly blocked time")
    st.caption("Add sleep, class, meals, work, and other unavailable windows.")

    with st.form("add_blocked_form", clear_on_submit=True):
        day_name = st.selectbox("Day", DAYS)
        start_hour = st.number_input("Start hour (0-23)", min_value=0, max_value=23, value=22)
        end_hour = st.number_input("End hour (1-24)", min_value=1, max_value=24, value=24)
        label = st.text_input("Reason", placeholder="Sleep / Class / Work")
        submitted = st.form_submit_button("Add blocked time", use_container_width=True)
        if submitted:
            if end_hour <= start_hour:
                st.warning("End hour must be greater than start hour.")
            else:
                st.session_state.blocked_times.append(
                    {
                        "day": day_name,
                        "start_hour": int(start_hour),
                        "end_hour": int(end_hour),
                        "label": label.strip() or "Blocked",
                    }
                )
                save_state()
                st.rerun()

    if st.session_state.blocked_times:
        st.caption(f"Saved blocked-time entries: {len(st.session_state.blocked_times)}")


def build_schedule(week_start: date) -> tuple[dict[tuple[int, int], str], dict[tuple[int, int], str], list[str]]:
    """Returns (grid_map, diagnostics). grid value is one of free/blocked/study/due."""
    grid: Dict[Tuple[int, int], str] = {(d, h): "free" for d in range(7) for h in range(24)}
    labels: Dict[Tuple[int, int], str] = {}
    diagnostics: List[str] = []

    for block in st.session_state.blocked_times:
        day_idx = DAYS.index(block["day"])
        for hour in range(block["start_hour"], block["end_hour"]):
            if 0 <= hour <= 23:
                grid[(day_idx, hour)] = "blocked"
                labels[(day_idx, hour)] = block["label"]

    now = datetime.now()
    planned_hours = 0
    unscheduled_hours = 0
    flattened_tasks = []
    for course in st.session_state.courses:
        for task in course.tasks:
            due_dt = datetime.fromisoformat(task.due_date)
            days_left = max((due_dt - now).total_seconds() / 86400, 0.1)
            urgency = (course.difficulty * task.estimated_hours) / days_left
            flattened_tasks.append((urgency, due_dt, course, task))

    flattened_tasks.sort(key=lambda x: (-x[0], x[1]))

    for _, due_dt, course, task in flattened_tasks:
        due_day = (due_dt.date() - week_start).days
        if 0 <= due_day < 7:
            due_hour = due_dt.hour
            grid[(due_day, due_hour)] = "due"
            labels[(due_day, due_hour)] = f"DUE: {task.title}"

        remaining = int(round(task.estimated_hours))
        if remaining <= 0:
            continue

        for day in range(7):
            for hour in range(24):
                slot_dt = datetime.combine(week_start + timedelta(days=day), time(hour=hour))
                if slot_dt < now or slot_dt > due_dt:
                    continue
                if grid[(day, hour)] == "free":
                    grid[(day, hour)] = "study"
                    labels[(day, hour)] = f"{course.name}: {task.title}"
                    remaining -= 1
                    planned_hours += 1
                    if remaining == 0:
                        break
            if remaining == 0:
                break

        if remaining > 0:
            unscheduled_hours += remaining
            diagnostics.append(f"Could not schedule {remaining}h for '{task.title}' ({course.name}).")

    diagnostics.insert(0, f"Total planned study hours this week: {planned_hours}")
    if unscheduled_hours:
        diagnostics.append(f"Unscheduled task hours due to limited free time: {unscheduled_hours}")

    return grid, labels, diagnostics


def render_weekly_schedule() -> None:
    week_start = get_week_start(date.today())
    st.subheader(f"🗓️ Weekly plan ({week_start.isoformat()} to {(week_start + timedelta(days=6)).isoformat()})")
    render_blocked_time_controls(week_start)

    grid, labels, diagnostics = build_schedule(week_start)

    for msg in diagnostics:
        st.caption(msg)

    st.markdown("#### Interactive weekly editor")
    st.caption("Click to select, drag across slots, or Shift+Click to select a rectangle.")
    selected_slots = weekly_scheduler_component(
        grid=grid,
        days=DAYS,
        selected_slots=st.session_state.get("selected_slots", []),
        key="weekly_scheduler_grid",
    )
    st.session_state.selected_slots = selected_slots
    st.caption(f"Selected slots: {len(selected_slots)}")

    with st.popover("Apply action to selected slots"):
        if not selected_slots:
            st.info("Select one or more slots from the interactive grid first.")
        else:
            action = st.selectbox("Action", ["Blocked Time", "Assignment", "Study Time", "Free Time"])
            if action == "Blocked Time":
                block_label = st.text_input("Reason", value="Blocked")
                if st.button("Apply blocked time", use_container_width=True):
                    for day_idx, hour in selected_slots:
                        st.session_state.blocked_times.append(
                            {"day": DAYS[day_idx], "start_hour": hour, "end_hour": hour + 1, "label": block_label}
                        )
                    save_state()
                    st.success("Blocked time added from selected slots.")
                    st.rerun()
            elif action == "Assignment":
                if not st.session_state.courses:
                    st.warning("Create a course first before adding tasks.")
                else:
                    course_name = st.selectbox("Course", [c.name for c in st.session_state.courses], key="assign_course")
                    task_title = st.text_input("Task title")
                    task_category = st.selectbox("Category", ["Assignment", "Quiz", "Exam"], key="assign_category")
                    estimated_hours = st.number_input("Estimated hours", min_value=0.5, value=float(max(1, len(selected_slots))))
                    due_day_idx, due_hour = max(selected_slots, key=lambda s: (s[0], s[1]))
                    due_dt = datetime.combine(week_start + timedelta(days=due_day_idx), time(hour=due_hour))
                    chosen_course = next(c for c in st.session_state.courses if c.name == course_name)
                    if st.button("Create assignment", use_container_width=True):
                        if not task_title.strip():
                            st.warning("Task title is required.")
                        else:
                            chosen_course.add_task(task_title.strip(), due_dt.isoformat(), task_category, float(estimated_hours))
                            save_state()
                            st.success("Assignment created.")
                            st.rerun()
            elif action == "Study Time":
                if not st.session_state.courses:
                    st.warning("Create a course and task first.")
                else:
                    course_name = st.selectbox("Course", [c.name for c in st.session_state.courses], key="study_course")
                    course = next(c for c in st.session_state.courses if c.name == course_name)
                    if not course.tasks:
                        st.warning("Selected course has no tasks.")
                    else:
                        task_title = st.selectbox("Task", [t.title for t in course.tasks], key="study_task")
                        task = next(t for t in course.tasks if t.title == task_title)
                        manual_hours = st.number_input("Manual study hours", min_value=0.5, value=float(len(selected_slots)))
                        if st.button("Apply manual study hours", use_container_width=True):
                            task.estimated_hours = float(manual_hours)
                            save_state()
                            st.success("Task study hours updated.")
                            st.rerun()
            else:
                if st.button("Clear selected blocked slots", use_container_width=True):
                    selected_set = {(day_idx, hour) for day_idx, hour in selected_slots}
                    filtered_blocks = []
                    for block in st.session_state.blocked_times:
                        day_idx = DAYS.index(block["day"])
                        if (day_idx, block["start_hour"]) not in selected_set:
                            filtered_blocks.append(block)
                    removed_count = len(st.session_state.blocked_times) - len(filtered_blocks)
                    st.session_state.blocked_times = filtered_blocks
                    save_state()
                    st.success(f"Cleared {removed_count} blocked slot(s).")
                    st.rerun()


def render_board() -> None:
    courses: List[Course] = st.session_state.courses

    if not courses:
        st.info("No courses yet. Use **Add Course** to create your first column.")
        return

    columns = st.columns(len(courses), gap="medium")

    for idx, course in enumerate(courses):
        with columns[idx]:
            st.markdown(
                f"""
                <div style="
                    border-left: 8px solid {course.color};
                    background: rgba(255,255,255,0.04);
                    border-radius: 14px;
                    padding: 0.85rem 1rem;
                    margin-bottom: 0.75rem;
                ">
                    <h4 style="margin:0;">{course.name}</h4>
                    <p style="margin: 0.25rem 0 0 0; opacity: 0.8;">
                        Difficulty: {course.difficulty}/10
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("🗑️ Remove Course", key=f"remove_course_btn_{idx}", use_container_width=True):
                st.session_state.pending_course_delete = idx

            with st.popover("✏️ Edit Course", use_container_width=True):
                with st.form(f"edit_course_form_{idx}"):
                    edit_name = st.text_input("Course Name", value=course.name, key=f"edit_course_name_{idx}")
                    edit_color = st.color_picker("Course Color", value=course.color, key=f"edit_course_color_{idx}")
                    edit_difficulty = st.slider(
                        "Estimated Difficulty", min_value=1, max_value=10, value=course.difficulty, key=f"edit_course_diff_{idx}"
                    )
                    if st.form_submit_button("Save Course", use_container_width=True):
                        if not edit_name.strip():
                            st.warning("Course name cannot be empty.")
                        else:
                            update_course(idx, edit_name, edit_color, edit_difficulty)
                            st.success("Course updated.")
                            st.rerun()

            if st.session_state.pending_course_delete == idx:
                st.warning(
                    f"Are you sure you want to remove '{course.name}'? This deletes all tasks in this course."
                )
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm Course Removal", key=f"confirm_remove_course_{idx}", use_container_width=True):
                        remove_course(idx)
                        st.session_state.pending_course_delete = None
                        st.rerun()
                with cancel_col:
                    if st.button("Cancel", key=f"cancel_remove_course_{idx}", use_container_width=True):
                        st.session_state.pending_course_delete = None
                        st.rerun()

            with st.form(f"add_task_form_{idx}", clear_on_submit=True):
                task_title = st.text_input("Task", key=f"task_title_{idx}")
                task_category = st.selectbox(
                    "Category",
                    options=["Assignment", "Quiz", "Exam"],
                    key=f"task_category_{idx}",
                )
                estimated_hours = st.number_input(
                    "Estimated Hours",
                    min_value=0.5,
                    max_value=100.0,
                    value=1.0,
                    step=0.5,
                    key=f"estimated_hours_{idx}",
                )
                due_date = st.datetime_input("Due Date", step=300)
                add_task_submitted = st.form_submit_button("Add Task", use_container_width=True)

                if add_task_submitted:
                    if not task_title.strip():
                        st.warning("Task title cannot be empty.")
                    else:
                        course.add_task(task_title, due_date.isoformat(), task_category, float(estimated_hours))
                        save_state()
                        st.rerun()

            st.markdown("#### Tasks")
            if not course.tasks:
                st.caption("No tasks for this course yet.")
            else:
                for task_idx, task in enumerate(course.tasks):
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid rgba(255,255,255,0.12);
                            border-radius: 10px;
                            padding: 0.7rem;
                            margin-bottom: 0.55rem;
                        ">
                            <strong>{task.title}</strong>
                            <p style="margin: 0.075rem 0 0 0; opacity: 1;">Due Date: {task.due_date}</p>
                            <p style="margin: 0.3rem 0 0 0; opacity: 0.85;">Category: {task.category}</p>
                            <p style="margin: 0.15rem 0 0 0; opacity: 0.75;">Estimated Hours: {task.estimated_hours:g}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button("Remove Task", key=f"remove_task_btn_{idx}_{task_idx}", use_container_width=True):
                        st.session_state.pending_task_delete = (idx, task_idx)

                    with st.popover("✏️ Edit Task", use_container_width=True):
                        with st.form(f"edit_task_form_{idx}_{task_idx}"):
                            edit_task_title = st.text_input("Task", value=task.title, key=f"edit_task_title_{idx}_{task_idx}")
                            edit_task_category = st.selectbox(
                                "Category",
                                options=["Assignment", "Quiz", "Exam"],
                                index=["Assignment", "Quiz", "Exam"].index(task.category)
                                if task.category in ["Assignment", "Quiz", "Exam"]
                                else 0,
                                key=f"edit_task_category_{idx}_{task_idx}",
                            )
                            edit_estimated_hours = st.number_input(
                                "Estimated Hours",
                                min_value=0.5,
                                max_value=100.0,
                                value=float(task.estimated_hours),
                                step=0.5,
                                key=f"edit_estimated_hours_{idx}_{task_idx}",
                            )
                            edit_due_date = st.datetime_input(
                                "Due Date",
                                value=datetime.fromisoformat(task.due_date),
                                step=300,
                                key=f"edit_due_date_{idx}_{task_idx}",
                            )
                            if st.form_submit_button("Save Task", use_container_width=True):
                                if not edit_task_title.strip():
                                    st.warning("Task title cannot be empty.")
                                else:
                                    update_task(
                                        idx,
                                        task_idx,
                                        edit_task_title,
                                        edit_due_date,
                                        edit_task_category,
                                        float(edit_estimated_hours),
                                    )
                                    st.success("Task updated.")
                                    st.rerun()

                    if st.session_state.pending_task_delete == (idx, task_idx):
                        st.warning(f"Remove task '{task.title}' from '{course.name}'?")
                        confirm_col, cancel_col = st.columns(2)
                        with confirm_col:
                            if st.button(
                                "Confirm Task Removal",
                                key=f"confirm_remove_task_{idx}_{task_idx}",
                                use_container_width=True,
                            ):
                                course.remove_task(task_idx)
                                save_state()
                                st.session_state.pending_task_delete = None
                                st.rerun()
                        with cancel_col:
                            if st.button("Cancel", key=f"cancel_remove_task_{idx}_{task_idx}", use_container_width=True):
                                st.session_state.pending_task_delete = None
                                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Smart Scheduler", layout="wide")
    init_state()
    render_course_controls()
    render_weekly_schedule()
    st.divider()
    render_board()


if __name__ == "__main__":
    main()
