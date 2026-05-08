from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import streamlit as st


@dataclass
class Task:
    """A child task that belongs to one Course."""

    title: str
    details: str = ""


@dataclass
class Course:
    """Parent object that owns a list of child Task objects."""

    name: str
    color: str
    difficulty: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, title: str, details: str = "") -> None:
        self.tasks.append(Task(title=title, details=details))


def init_state() -> None:
    if "courses" not in st.session_state:
        st.session_state.courses: List[Course] = []


def add_course(name: str, color: str, difficulty: int) -> None:
    st.session_state.courses.append(
        Course(name=name.strip(), color=color, difficulty=difficulty)
    )


def render_course_controls() -> None:
    st.title("📚 Smart Scheduler")
    st.caption("Kanban-style course planning board")

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

            with st.form(f"add_task_form_{idx}", clear_on_submit=True):
                task_title = st.text_input("Task", key=f"task_title_{idx}")
                task_details = st.text_area(
                    "Task Details (optional)",
                    key=f"task_details_{idx}",
                    height=80,
                )
                add_task_submitted = st.form_submit_button(
                    "Add Task", use_container_width=True
                )

                if add_task_submitted:
                    if not task_title.strip():
                        st.warning("Task title cannot be empty.")
                    else:
                        course.add_task(task_title, task_details)
                        st.rerun()

            st.markdown("#### Tasks")
            if not course.tasks:
                st.caption("No tasks for this course yet.")
            else:
                for task in course.tasks:
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid rgba(255,255,255,0.12);
                            border-radius: 10px;
                            padding: 0.7rem;
                            margin-bottom: 0.55rem;
                        ">
                            <strong>{task.title}</strong>
                            <p style="margin: 0.3rem 0 0 0; opacity: 0.8;">{task.details}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def main() -> None:
    st.set_page_config(page_title="Smart Scheduler", layout="wide")
    init_state()
    render_course_controls()
    render_board()


if __name__ == "__main__":
    main()
