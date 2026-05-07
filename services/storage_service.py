"""
services/storage_service.py
──────────────────────────
Service for handling file storage on the local server with database tracking.
"""

import os
import shutil
import streamlit as st
from db.repositories.storage_repo import add_file_record, get_topic_files, delete_file_record

# Base directory for all uploads on the server
UPLOAD_BASE_DIR = os.path.abspath("server_storage")

def ensure_storage_dir(project, topic):
    """Ensure the physical directory exists for a topic."""
    path = os.path.join(UPLOAD_BASE_DIR, project, topic)
    os.makedirs(path, exist_ok=True)
    return path

def save_file_to_server(file_obj, project, topic, note="", f_type="File", uploaded_by=None):
    """
    Save an uploaded file to the server disk and record it in the DB.
    """
    try:
        # 1. Prepare directory
        dest_dir = ensure_storage_dir(project, topic)
        filename = file_obj.name
        local_path = os.path.join(dest_dir, filename)
        
        # 2. Write file to disk
        with open(local_path, "wb") as f:
            f.write(file_obj.getbuffer())
        
        # 3. Record in Database
        add_file_record(project, topic, filename, local_path, note, f_type, uploaded_by=uploaded_by)
        
        return True, None
    except Exception as e:
        return False, str(e)

def add_link_to_server(project, topic, url, note=""):
    """Record a web link for a topic in the DB."""
    try:
        add_file_record(project, topic, url, "", note, "Link", url)
        return True, None
    except Exception as e:
        return False, str(e)

def get_files_for_topic(project, topic, user_filter=None):
    """Fetch all files and links for a topic from the DB."""
    return get_topic_files(project, topic, user_filter=user_filter)

def remove_file(file_id, local_path):
    """Delete file from disk and record from DB."""
    try:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
        delete_file_record(file_id)
        return True
    except:
        return False

# Legacy Compatibility (can be removed later if not needed)
def get_drive_service():
    return None # We are now using local server storage

def upload_file(file_obj, path_parts, filename):
    # Mapping old 'path_parts' logic to new project/topic logic
    # path_parts usually is ['Topic_Files', project, topic]
    if len(path_parts) >= 3:
        proj, topic = path_parts[1], path_parts[2]
        current_user = st.session_state.get("auth_name", "Unknown")
        success, err = save_file_to_server(file_obj, proj, topic, uploaded_by=current_user)
        return "local_id", err
    return None, "Invalid path parts"

def list_files(path_parts):
    """Legacy alias to fetch files from DB in a Drive-compatible format."""
    if len(path_parts) >= 3:
        proj, topic = path_parts[1], path_parts[2]
        db_files = get_files_for_topic(proj, topic)
        # Convert to Drive-like format: list of {'name': ..., 'webViewLink': ...}
        drive_formatted = []
        for f in db_files:
            # f: (id, file_name, local_path, url, note, type, uploaded_by)
            drive_formatted.append({
                "name": f[1],
                "webViewLink": f[3] if f[3] else None # Use URL if it's a link
            })
        return drive_formatted
    return []
