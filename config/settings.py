"""
config/settings.py
──────────────────
Centralised application constants and config loader.
All other modules import BASE_PROJECTS, BASE_TOPICS, etc. from here.
"""

import json

# ── Default configuration ────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "BASE_PROJECTS": [],
    "BASE_TOPICS": [],
    "BASE_EMPLOYEES": [
        "Unassigned",
    ],
    "EMPLOYEE_CREDENTIALS": [],
    "STATUS_OPTIONS": ["Planned", "In Progress", "Completed", "Delayed"],
    "DRIVE_DEFAULT_PATH": ["DefaultProject", "General"],
    "LOCAL_UPLOAD_DIR": "/opt/server_app/uploads",
}

# ── Drive folder names ───────────────────────────────────────────────────────
DATA_DRIVE_FOLDER = ["data"]

# ── Legacy project name aliases (for migration) ──────────────────────────────
LEGACY_PROJECT_NAMES = {
    "Truck Unloading Project": ["R&D Project", "Default Project"],
}


def load_app_config(config_bytes: bytes | None = None) -> dict:
    """
    Return merged config.  Pass raw bytes from Drive/local if available;
    falls back to DEFAULT_CONFIG.
    """
    if config_bytes is not None:
        try:
            overrides = json.loads(config_bytes.decode("utf-8"))
            return {**DEFAULT_CONFIG, **overrides}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_app_config_local(config: dict, path: str = "data/app_config.json") -> None:
    import os
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=4)
        