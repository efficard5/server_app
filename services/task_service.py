"""
services/task_service.py
────────────────────────
PMO task (Gantt) and daily task business logic.
Reads/writes PostgreSQL via task_repo and daily_task_repo.
No Drive, no Excel files.
"""

import pandas as pd
import streamlit as st

from db.repositories.task_repo import (
    get_all_tasks,
    get_tasks_by_project,
    insert_task,
    update_task,
    delete_task,
    upsert_tasks_from_df,
)
from db.repositories.daily_task_repo import (
    get_all_daily_tasks,
    get_daily_tasks_by_date,
    upsert_daily_tasks_from_df,
)


# ── Gantt tasks ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    """Return all tasks as a DataFrame with app-standard column names."""
    return get_all_tasks()


def save_task(task: dict) -> int:
    """Insert a new task row. Returns new id."""
    load_data.clear()
    return insert_task(task)


def update_task_row(task_id: int, task: dict) -> None:
    load_data.clear()
    update_task(task_id, task)


def delete_task_row(task_id: int) -> None:
    load_data.clear()
    delete_task(task_id)


def bulk_replace_tasks(df: pd.DataFrame) -> None:
    """Truncate and reload all tasks from a DataFrame (migration use)."""
    load_data.clear()
    upsert_tasks_from_df(df)


# ── Daily tasks ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_daily_task_data() -> pd.DataFrame:
    """Return all daily tasks as a DataFrame."""
    return get_all_daily_tasks()


def bulk_replace_daily_tasks(df: pd.DataFrame) -> None:
    """Saves the entire task sheet DataFrame to the database."""
    load_daily_task_data.clear()
    upsert_daily_tasks_from_df(df)


def get_daily_task_columns():
    from db.repositories.daily_task_repo import get_task_sheet_columns
    return get_task_sheet_columns()


def update_daily_task_columns(cols):
    from db.repositories.daily_task_repo import update_task_sheet_columns
    update_task_sheet_columns(cols)


# ── Utility ───────────────────────────────────────────────────────────────────

def calculate_project_week(project_name: str, start_date, data_df: pd.DataFrame) -> int:
    project_rows = data_df[data_df["project"] == project_name].copy()
    if project_rows.empty:
        return 1
    project_start = pd.to_datetime(project_rows["start_date"], errors="coerce").dropna()
    if project_start.empty:
        return 1
    start_dt = pd.to_datetime(start_date).tz_localize(None)
    master_start = project_start.min().tz_localize(None)
    delta_days = (start_dt - master_start).days
    return max(1, delta_days // 7 + 1)


def aggregate_topic_completion(topic_df: pd.DataFrame) -> float:
    """Matches the original logic for incremental topic completion."""
    if topic_df.empty:
        return 0.0

    col = "completion_pct" if "completion_pct" in topic_df.columns else "status"
    if col == "status":
        return 100.0 if any(topic_df["status"] == "Completed") else 0.0

    values = pd.to_numeric(topic_df[col], errors="coerce").dropna()
    if values.empty:
        return 0.0

    base = float(values.max())
    incremental = float(values[values < base].sum())
    return min(100.0, round(base + incremental, 1))