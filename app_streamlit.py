"""
app.py — Streamlit entry point for server_app
──────────────────────────────────────────────
Wires together layout, session, data loading, and page routing.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ── 1. Layout (must be first Streamlit call) ─────────────────────────────────
from ui.layout import apply_layout
apply_layout()

# ── 2. Session state ──────────────────────────────────────────────────────────
from ui.session import init_session_state
init_session_state()

# Initialize workspace_page state if missing
if "workspace_page" not in st.session_state:
    st.session_state.workspace_page = None

# ── 3. Config ─────────────────────────────────────────────────────────────────
from config.settings import load_app_config
APP_CONFIG = load_app_config()
BASE_PROJECTS = APP_CONFIG["BASE_PROJECTS"]
BASE_TOPICS   = APP_CONFIG["BASE_TOPICS"]

# ── 4. Load data ──────────────────────────────────────────────────────────────
from services.task_service import load_data, load_daily_task_data
from services.auth_service import get_employee_credentials
from services.notes_service import load_notes
from services.milestone_service import load_planned_milestones
from services.project_service import build_project_topic_registry

df               = load_data()
daily_task_df    = load_daily_task_data()
employee_accounts = get_employee_credentials()
notes_db         = load_notes()
planned_milestones_db = load_planned_milestones()

projects, topics, PROJECT_TOPIC_REGISTRY = build_project_topic_registry(
    df, planned_milestones_db, notes_db, BASE_PROJECTS, BASE_TOPICS
)

# Employees list (Database + Unassigned)
base_emps       = APP_CONFIG["BASE_EMPLOYEES"]
credential_emps = [row["name"] for row in employee_accounts]
employees       = list(dict.fromkeys(base_emps + credential_emps))

STATUS_OPTIONS = APP_CONFIG["STATUS_OPTIONS"]

ctx = {
    "df": df,
    "daily_task_df": daily_task_df,
    "projects": projects,
    "topics": topics,
    "registry": PROJECT_TOPIC_REGISTRY,
    "milestones": planned_milestones_db,
    "notes_db": notes_db,
    "employees": employees,
    "employee_accounts": employee_accounts,
    "app_config": APP_CONFIG,
    "status_options": STATUS_OPTIONS,
}

# ── 5. Authentication gate ────────────────────────────────────────────────────
if st.session_state.role is None:
    from ui.auth_page import render_auth_page
    render_auth_page(APP_CONFIG)
    st.stop()

# ── 6. Selection Screen (Dashboard vs Task Sheet) ───────────────────────────
if st.session_state.workspace_page is None:
    st.title("Workspace")
    st.write("Choose where you want to go.")
    go_col1, go_col2 = st.columns(2)
    if go_col1.button("Dashboard", use_container_width=True):
        st.session_state.workspace_page = "Dashboard"
        st.rerun()
    if go_col2.button("Task Sheet", use_container_width=True):
        st.session_state.workspace_page = "Task Sheet"
        st.rerun()
    
    # ── 6.1 Contribution Graph (LeetCode style) ────────────────────────────────
    st.divider()
    from ui.components.contribution_graph import render_contribution_graph
    render_contribution_graph(ctx)
    
    st.stop()

# ── 7. Sidebar navigation ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("PMO Navigation")
    st.caption(f"Logged in as: **{st.session_state.auth_name}** ({st.session_state.role})")
    if st.button("Logout/Change View"):
        st.session_state.workspace_page = None
        st.rerun()
    st.divider()

    if st.session_state.workspace_page == "Task Sheet":
        nav_options = ["Task Sheet"]
    else:
        nav_options = [
            "Dashboard",
            "Weekly Performance",
            "Tasks & Milestones",
            "Planned Milestones",
            "Competitor List",
            "Files and Images",
            "Drive Documents",
        ]
    
    page = st.selectbox("Navigation", nav_options)

# ── 8. Page routing ───────────────────────────────────────────────────────────
from ui.pages import (
    dashboard, workspace, gantt, milestones,
    competitor, document_drive, daily_tasks, image_gallery
)

PAGE_MAP = {
    "Dashboard":           dashboard,
    "Weekly Performance":  workspace,
    "Tasks & Milestones":  gantt,
    "Planned Milestones":  milestones,
    "Competitor List":     competitor,
    "Files and Images":    image_gallery,
    "Drive Documents":     document_drive,
    "Task Sheet":          daily_tasks,
}

PAGE_MAP[page].render(ctx)
