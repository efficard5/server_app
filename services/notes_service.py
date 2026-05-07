"""
services/notes_service.py
──────────────────────────
Project notes — reads/writes PostgreSQL.
"""

from db.repositories.notes_repo import get_all_notes, save_note, delete_note


def load_notes() -> dict:
    return get_all_notes()


def save_notes(notes: dict) -> None:
    """Bulk save all notes from the {project: {Topics: {topic: text}, Project_Issues: str, ...}} structure."""
    for project, project_info in notes.items():
        # 1. Save standard topics
        for topic, note_text in (project_info.get("Topics") or {}).items():
            save_note(project, topic, note_text)
        
        # 2. Save project-level notes
        if "Project_Issues" in project_info:
            save_note(project, "__PROJECT_ISSUES__", project_info["Project_Issues"])
        if "Project_Plans" in project_info:
            save_note(project, "__PROJECT_PLANS__", project_info["Project_Plans"])


def upsert_note(project: str, topic: str, note_text: str) -> None:
    save_note(project, topic, note_text)


def remove_note(project: str, topic: str) -> None:
    delete_note(project, topic)