"""
services/notes_service.py
──────────────────────────
Project notes — reads/writes PostgreSQL.
"""

import streamlit as st
from db.repositories.notes_repo import get_all_notes, save_note, delete_note


@st.cache_data(ttl=60)
def load_notes() -> dict:
    return get_all_notes()


def save_notes(notes: dict) -> None:
    """Bulk save all notes — targeted cache clear only."""
    for project, project_info in notes.items():
        for topic, note_text in (project_info.get("Topics") or {}).items():
            save_note(project, topic, note_text)
        if "Project_Issues" in project_info:
            save_note(project, "__PROJECT_ISSUES__", project_info["Project_Issues"])
        if "Project_Plans" in project_info:
            save_note(project, "__PROJECT_PLANS__", project_info["Project_Plans"])
        if "Phases" in project_info:
            save_note(project, "__PHASES__", project_info["Phases"])
    load_notes.clear()


def upsert_note(project: str, topic: str, note_text: str) -> None:
    load_notes.clear()
    save_note(project, topic, note_text)


def remove_note(project: str, topic: str) -> None:
    load_notes.clear()
    delete_note(project, topic)