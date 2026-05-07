import pandas as pd
from datetime import datetime

def format_bullet_markdown(text):
    lines = []
    for raw_line in str(text or "").splitlines():
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("-->"):
            cleaned = cleaned[3:].strip()
        elif cleaned.startswith("->"):
            cleaned = cleaned[2:].strip()
        cleaned = cleaned.lstrip("-*•").strip()
        if cleaned:
            lines.append(f"- {cleaned}")
    return "\n".join(lines) if lines else "-"

def format_single_line_text(text):
    parts = []
    for raw_line in str(text or "").splitlines():
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("-->"):
            cleaned = cleaned[3:].strip()
        elif cleaned.startswith("->"):
            cleaned = cleaned[2:].strip()
        cleaned = cleaned.lstrip("-*•").strip()
        if cleaned:
            parts.append(cleaned)
    return " | ".join(parts)

def format_bullet_html(text):
    items = []
    for raw_line in str(text or "").splitlines():
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("-->"):
            cleaned = cleaned[3:].strip()
        elif cleaned.startswith("->"):
            cleaned = cleaned[2:].strip()
        cleaned = cleaned.lstrip("-*•").strip()
        if cleaned:
            items.append(f"<li>{cleaned}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else "<ul><li>-</li></ul>"

def clean_label(value):
    text = str(value or "").strip()
    return "" if text.lower() == "nan" else text

def escape_drive_query_value(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")
"""
utils/formatters.py
────────────────────
Pure text / HTML formatting helpers. No Streamlit, no I/O.
"""


def _clean_line(raw_line: str) -> str:
    cleaned = raw_line.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("-->"):
        cleaned = cleaned[3:].strip()
    elif cleaned.startswith("->"):
        cleaned = cleaned[2:].strip()
    cleaned = cleaned.lstrip("-*•").strip()
    return cleaned


def format_bullet_markdown(text) -> str:
    lines = [_clean_line(raw) for raw in str(text or "").splitlines()]
    return "\n".join(f"- {line}" for line in lines if line) or "-"


def format_single_line_text(text) -> str:
    parts = [_clean_line(raw) for raw in str(text or "").splitlines()]
    return " | ".join(p for p in parts if p)


def format_bullet_html(text) -> str:
    items = [f"<li>{_clean_line(raw)}</li>" for raw in str(text or "").splitlines() if _clean_line(raw)]
    return "<ul>" + "".join(items) + "</ul>" if items else "<ul><li>-</li></ul>"