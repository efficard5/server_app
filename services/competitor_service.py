"""
services/competitor_service.py
───────────────────────────────
Competitor data — reads/writes PostgreSQL.
"""

from db.repositories.competitor_repo import (
    get_all_competitors,
    save_competitor_category,
    save_all_competitors,
    delete_competitor_category,
    get_competitor_columns
)


def load_competitor_data() -> dict:
    return get_all_competitors()


def save_competitor_data(data: dict) -> None:
    save_all_competitors(data)


def save_category(category: str, columns: list, rows: list) -> None:
    save_competitor_category(category, columns, rows)

def remove_category(category: str) -> None:
    delete_competitor_category(category)

def get_category_columns(category: str) -> list:
    cols_map = get_competitor_columns()
    return cols_map.get(category, ["Competitor", "Value"])