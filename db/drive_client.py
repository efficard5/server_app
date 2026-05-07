"""
db/drive_client.py
──────────────────
Temporary bridge to pull data from Google Drive for migration.
"""

import io
import os
import uuid
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ── Optional Google imports ──────────────────────────────────────────────────
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    service_account = None
    build = None
    MediaIoBaseDownload = None

GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

def _load_google_drive_credentials():
    # Try service account from environment
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_json:
        try:
            import json
            return service_account.Credentials.from_service_account_info(
                json.loads(sa_json), scopes=GOOGLE_DRIVE_SCOPES
            )
        except Exception:
            pass
            
    # Try local credentials.json for OAuth flow
    if os.path.exists("credentials.json"):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GOOGLE_DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
            return creds
        except Exception:
            pass
            
    return None

def get_google_drive_service():
    try:
        credentials = _load_google_drive_credentials()
        if not credentials:
            return None
        return build("drive", "v3", credentials=credentials)
    except Exception:
        return None

def get_google_drive_root_folder_id() -> str:
    # Get from .env or streamlit secrets
    root_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "").strip()
    if not root_id:
        try:
            root_id = st.secrets.get("gdrive_root_folder_id", "").strip()
        except Exception:
            pass
    return root_id

def _get_drive_file_id(service, parent_id: str, file_name: str):
    query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get("files", [])
    return files[0] if files else None

def restore_data_from_drive_if_needed() -> None:
    service = get_google_drive_service()
    root_id = get_google_drive_root_folder_id()
    
    if not service or not root_id:
        print("❌ Error: Google Drive credentials or Root Folder ID missing.")
        return

    os.makedirs("data", exist_ok=True)
    files_to_restore = [
        "tasks.xlsx", "daily_task_daywise.xlsx",
        "planned_milestones.json", "project_notes.json",
    ]

    for file_name in files_to_restore:
        drive_file = _get_drive_file_id(service, root_id, file_name)
        if not drive_file:
            continue
            
        request = service.files().get_media(fileId=drive_file["id"])
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
            
        with open(os.path.join("data", file_name), "wb") as f:
            f.write(buffer.getvalue())
        print(f"✅ Downloaded: {file_name}")
