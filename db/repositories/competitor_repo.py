# db/repositories/competitor_repo.py
from db.base import execute_query
import json

def get_all_competitors():
    """Returns a dict of {category: rows_list} and also tracks columns."""
    query = "SELECT category, columns, rows FROM competitors"
    results = execute_query(query, fetch=True)
    
    comp_data = {}
    if results:
        for cat, cols, rows in results:
            # We return rows as they are, but the UI needs to know the columns too
            # To match the previous logic where rows[0].keys() defines columns:
            if rows:
                comp_data[cat] = rows
            else:
                # If no rows, create an empty row with the defined columns
                col_list = cols if isinstance(cols, list) else ["Competitor", "Value"]
                comp_data[cat] = [{c: "" for c in col_list}]
    return comp_data

def get_competitor_columns():
    """Returns a dict of {category: columns_list}."""
    query = "SELECT category, columns FROM competitors"
    results = execute_query(query, fetch=True)
    return {r[0]: r[1] for r in results} if results else {}

def save_competitor_category(category, columns, rows):
    """Saves or updates a single category's data."""
    query = """
        INSERT INTO competitors (category, columns, rows)
        VALUES (%s, %s, %s)
        ON CONFLICT (category) DO UPDATE SET
            columns = EXCLUDED.columns,
            rows = EXCLUDED.rows
    """
    execute_query(query, [category, json.dumps(columns), json.dumps(rows)])

def delete_competitor_category(category):
    query = "DELETE FROM competitors WHERE category = %s"
    execute_query(query, [category])

def save_all_competitors(comp_data):
    """
    Helper to save the entire dictionary. 
    Note: In SQL we do it per category, but this maintains the service interface.
    """
    # 1. Get existing to see if any were deleted
    existing = get_all_competitors()
    for cat in existing:
        if cat not in comp_data:
            delete_competitor_category(cat)
            
    # 2. Save new/updated
    for cat, rows in comp_data.items():
        if rows:
            cols = list(rows[0].keys())
        else:
            cols = ["Competitor", "Value"]
        save_competitor_category(cat, cols, rows)
