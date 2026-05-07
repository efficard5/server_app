"""
services/file_service.py
──────────────────────────────
Handles file upload (local storage) + metadata in PostgreSQL.
"""

import os
import uuid

from db.repositories.drive_doc_repo import (
    get_metadata_for_topic,
    save_file_note,
    add_url,
    delete_url,
    delete_file_entry,
    save_local_file_path,
)

UPLOAD_FOLDER = "/opt/server_app/uploads"


def handle_file_upload(file_obj, project: str, topic: str):
    """Streamlit Upload -> Local FS -> PostgreSQL"""

    try:
        # 1. Create unique file name
        unique_name = f"{uuid.uuid4()}_{file_obj.name}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_name)

        # 2. Save file to server
        with open(file_path, "wb") as f:
            f.write(file_obj.getbuffer())

        # 3. Save path in PostgreSQL
        save_local_file_path(project, topic, unique_name, file_path)

        return file_path, None

    except Exception as e:
        return None, str(e)


def load_topic_metadata(project: str, topic: str) -> dict:
    return get_metadata_for_topic(project, topic)


def upsert_file_note(project: str, topic: str, file_name: str, note: str) -> None:
    save_file_note(project, topic, file_name, note)


def attach_url(project: str, topic: str, url: str, note: str) -> None:
    add_url(project, topic, url, note)


def remove_url(row_id: int) -> None:
    delete_url(row_id)


def remove_file_entry(project: str, topic: str, file_name: str) -> None:
    delete_file_entry(project, topic, file_name)