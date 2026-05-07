# db/repositories/daily_task_repo.py
from db.base import execute_query
import json
import pandas as pd
from uuid import uuid4
import numpy as np

def sync_db_columns(cols):
    """Ensure the daily_tasks table has physical columns for all active fields."""
    from db.base import get_cursor
    with get_cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_tasks'")
        existing = [r[0].lower() for r in cur.fetchall()]
    
    for col in cols:
        db_col = col.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        if db_col not in existing and db_col not in ["task_id", "date", "responsible_person", "extra_data", "delete"]:
            try:
                execute_query(f'ALTER TABLE daily_tasks ADD COLUMN "{db_col}" TEXT')
            except Exception as e:
                print(f"Skipping ALTER TABLE for {db_col}: {e}")

def get_all_daily_tasks():
    query = "SELECT * FROM daily_tasks"
    rows = execute_query(query, fetch=True)
    
    from db.base import get_cursor
    with get_cursor() as cur:
        cur.execute("SELECT * FROM daily_tasks LIMIT 0")
        colnames = [desc[0] for desc in cur.description]
    
    if not rows:
        return pd.DataFrame(columns=colnames)
    
    df = pd.DataFrame(rows, columns=colnames)
    
    # Map DB names back to UI names
    active_cols = get_task_sheet_columns()
    for ui_col in active_cols:
        db_col = ui_col.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        if db_col in df.columns and ui_col != db_col:
            df.rename(columns={db_col: ui_col}, inplace=True)
            
    # Merge JSON extra_data if any (for backward compatibility)
    if "extra_data" in df.columns:
        for idx, row in df.iterrows():
            extra = row["extra_data"]
            if extra:
                if isinstance(extra, str): extra = json.loads(extra)
                for k, v in extra.items():
                    if k not in df.columns:
                        df.at[idx, k] = v
    return df

def get_daily_tasks_by_date(assigned_date):
    query = "SELECT * FROM daily_tasks WHERE date = %s"
    rows = execute_query(query, [assigned_date], fetch=True)
    
    from db.base import get_cursor
    with get_cursor() as cur:
        cur.execute("SELECT * FROM daily_tasks LIMIT 0")
        colnames = [desc[0] for desc in cur.description]
        
    if not rows:
        return pd.DataFrame(columns=colnames)
    
    df = pd.DataFrame(rows, columns=colnames)
    
    active_cols = get_task_sheet_columns()
    for ui_col in active_cols:
        db_col = ui_col.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        if db_col in df.columns and ui_col != db_col:
            df.rename(columns={db_col: ui_col}, inplace=True)
            
    return df

def upsert_daily_tasks_from_df(df: pd.DataFrame):
    """Saves rows using ON CONFLICT, mapping UI columns to DB columns."""
    from db.base import get_cursor
    with get_cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_tasks'")
        db_cols = [r[0] for r in cur.fetchall()]

    for _, row in df.iterrows():
        tid = row.get("task_id")
        if pd.isna(tid) or str(tid).strip() in ["", "NEW", "nan"]:
            tid = str(uuid4())
            
        new_date = row.get("date")
        if hasattr(new_date, "strftime"): new_date = new_date.strftime("%Y-%m-%d")
        
        person = row.get("responsible_person")
        if not new_date or not person: continue

        # Prepare dynamic UPSERT
        update_map = {
            "task_id": tid,
            "date": new_date,
            "responsible_person": person
        }
        
        # Add values for real columns
        extra_json = {}
        for ui_col in df.columns:
            if ui_col in ["task_id", "date", "responsible_person", "Delete"]: continue
            
            val = str(row[ui_col]) if not pd.isna(row[ui_col]) else ""
            db_col = ui_col.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
            
            if db_col in db_cols:
                update_map[db_col] = val
            else:
                extra_json[ui_col] = val
        
        update_map["extra_data"] = json.dumps(extra_json)
        
        cols = list(update_map.keys())
        vals = list(update_map.values())
        placeholders = ", ".join(["%s"] * len(vals))
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != "task_id"])
        
        query = f"""
            INSERT INTO daily_tasks ({", ".join(cols)})
            VALUES ({placeholders})
            ON CONFLICT (task_id) DO UPDATE SET {set_clause}
        """
        execute_query(query, vals)

def get_task_sheet_columns():
    query = "SELECT value FROM app_settings WHERE key = 'daily_task_columns'"
    res = execute_query(query, fetch=True)
    if res:
        return res[0][0]
    return ["Department", "Task Description", "Task Status", "Allocated Hrs"]

def update_task_sheet_columns(cols):
    # 1. Save to settings
    query = "INSERT INTO app_settings (key, value) VALUES ('daily_task_columns', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
    execute_query(query, [json.dumps(cols)])
    
    # 2. Sync DB Schema (Literal columns)
    sync_db_columns(cols)
