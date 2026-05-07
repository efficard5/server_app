"""
ui/session.py
──────────────
Centralised session state initialisation.
Call init_session_state() once at the top of app.py (after layout).
"""

import streamlit as st


def init_session_state() -> None:
    defaults = {
        "role": None,
        "auth_name": None,
        "preferred_weekly_project": None,
        "preferred_weekly_week": None,
        "workspace_page": None,
        "show_employee_signup": False,
        "last_full_nav_page": "Dashboard",
        "topic_images": {},
        "last_drive_status": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value