"""
db/repositories/task_repo.py
───────────────────────────
PostgreSQL repository for Gantt chart tasks.
"""

import pandas as pd
from db.base import execute_query, get_cursor

def get_all_tasks() -> pd.DataFrame:
    query = "SELECT * FROM tasks WHERE is_active = TRUE ORDER BY project, start_date"
    rows = execute_query(query, fetch=True)
    # Get column names
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tasks LIMIT 0")
        colnames = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=colnames)

def get_tasks_by_project(project_name: str) -> pd.DataFrame:
    query = "SELECT * FROM tasks WHERE project = %s AND is_active = TRUE ORDER BY start_date"
    rows = execute_query(query, (project_name,), fetch=True)
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tasks LIMIT 0")
        colnames = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=colnames)

def insert_task(task: dict) -> int:
    cols = ", ".join(task.keys())
    placeholders = ", ".join(["%s"] * len(task))
    query = f"INSERT INTO tasks ({cols}) VALUES ({placeholders}) RETURNING id"
    result = execute_query(query, list(task.values()), fetch=True)
    return result[0][0]

def update_task(task_id: int, task: dict) -> None:
    # Set old row to inactive
    execute_query("UPDATE tasks SET is_active = FALSE WHERE id = %s", (task_id,))
    # Insert new row (it will get a new ID, but for versioning this is expected unless we added a group_id)
    # Note: If tasks have references, changing ID breaks them. This assumes simple flat tasks.
    insert_task(task)

def delete_task(task_id: int) -> None:
    execute_query("UPDATE tasks SET is_active = FALSE WHERE id = %s", (task_id,))

def upsert_tasks_from_df(df: pd.DataFrame) -> None:
    """Bulk update tasks from a DataFrame."""
    # This is a simplified version; in production use COPY or unnest
    for _, row in df.iterrows():
        task = row.to_dict()
        # Handle project/task unique constraint if any
        insert_task(task)
