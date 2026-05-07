"""
services/competitor_service.py
───────────────────────────────
Competitor data — reads/writes PostgreSQL.
"""

from db.repositories.competitor_repo import (
    get_all_competitors,
    save_competitor_category,
    save_all_competitors,
)


def load_competitor_data() -> dict:
    return get_all_competitors()


def save_competitor_data(data: dict) -> None:
    save_all_competitors(data)


def save_category(category: str, rows: list) -> None:
    save_competitor_category(category, rows)