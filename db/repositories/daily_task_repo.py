# db/repositories/daily_task_repo.py
from db.base import execute_query, get_cursor
import json
import pandas as pd
import numpy as np

def _ui_col_to_db_col(ui_col):
    """Standardize UI column names to database-safe identifiers."""
    return ui_col.lower().replace(" ", "_").replace("/", "_").replace("-", "_").replace("%", "pct")

# ── Cache known columns in memory (avoids information_schema hit every rerun) ──
_synced_cols_cache: set = set()

def sync_db_columns(cols):
    """Ensure the daily_tasks table has physical columns for all active fields.
    Uses an in-process cache to avoid hitting information_schema on every render.
    """
    global _synced_cols_cache
    all_needed = set(cols) | {"completed_checkpoint", "ms_ref", "ms_task_ref"}
    if all_needed <= _synced_cols_cache:
        return  # Already synced this session — skip DB hit

    with get_cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_tasks'")
        existing = {r[0].lower() for r in cur.fetchall()}

    skip = {"task_id", "date", "responsible_person", "extra_data", "delete"}
    for col in all_needed:
        db_col = _ui_col_to_db_col(col)
        if db_col not in existing and db_col not in skip:
            try:
                execute_query(f'ALTER TABLE daily_tasks ADD COLUMN "{db_col}" TEXT')
                existing.add(db_col)
            except Exception as e:
                print(f"Skipping ALTER TABLE for {db_col}: {e}")

    _synced_cols_cache = all_needed  # Mark as synced

def get_all_daily_tasks():
    """Fetch all daily tasks in a single DB round-trip."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM daily_tasks WHERE is_active = TRUE ORDER BY date DESC")
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=colnames)

    df = pd.DataFrame(rows, columns=colnames)

    # Map DB names back to UI names
    active_cols = get_task_sheet_columns()
    for ui_col in active_cols:
        db_col = _ui_col_to_db_col(ui_col)
        if db_col in df.columns and ui_col != db_col:
            df.rename(columns={db_col: ui_col}, inplace=True)

    # Merge JSON extra_data if any (for backward compatibility)
    if "extra_data" in df.columns:
        for idx, row in df.iterrows():
            extra = row["extra_data"]
            if extra:
                if isinstance(extra, str):
                    extra = json.loads(extra)
                for k, v in extra.items():
                    if k not in df.columns:
                        df.at[idx, k] = v
    return df

def get_daily_tasks_by_date(assigned_date):
    """Fetch daily tasks for a specific date — single round-trip."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM daily_tasks WHERE date = %s AND is_active = TRUE", [assigned_date])
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=colnames)

    df = pd.DataFrame(rows, columns=colnames)
    active_cols = get_task_sheet_columns()
    for ui_col in active_cols:
        db_col = _ui_col_to_db_col(ui_col)
        if db_col in df.columns and ui_col != db_col:
            df.rename(columns={db_col: ui_col}, inplace=True)
    return df

def upsert_daily_tasks_from_df(df: pd.DataFrame):
    """Saves rows using a single transaction — no per-row DB round-trips."""
    with get_cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_tasks'")
        db_cols = {r[0] for r in cur.fetchall()}

    inserts = []       # (cols, vals) for new rows
    updates = []       # (set_clause_vals, task_id) for existing rows

    for _, row in df.iterrows():
        tid = row.get("task_id")
        is_new = pd.isna(tid) or str(tid).strip() in ["", "NEW", "nan"]

        new_date = row.get("date")
        if hasattr(new_date, "strftime"):
            new_date = new_date.strftime("%Y-%m-%d")
        person = row.get("responsible_person")
        if not new_date or not person:
            continue

        update_map = {"date": new_date, "responsible_person": person}
        if not is_new:
            update_map["task_id"] = int(tid)

        extra_json = {}
        for ui_col in df.columns:
            if ui_col in ["task_id", "date", "responsible_person", "Delete"]:
                continue
            val = row[ui_col]
            if pd.isna(val):
                val = ""
            db_col = _ui_col_to_db_col(ui_col)
            if db_col in db_cols:
                update_map[db_col] = val
            else:
                extra_json[ui_col] = str(val)

        update_map["extra_data"] = json.dumps(extra_json)

        cols = list(update_map.keys())
        vals = list(update_map.values())
        quoted_cols = [f'"{c}"' for c in cols] + ['"is_active"']
        placeholders = ", ".join(["%s"] * len(vals)) + ", TRUE"

        if is_new:
            inserts.append((quoted_cols, placeholders, vals))
        else:
            updates.append((int(tid), quoted_cols, placeholders, vals))

    # ── Execute all writes in a SINGLE transaction ─────────────────────────────
    with get_cursor(commit=True) as cur:
        for quoted_cols, placeholders, vals in inserts:
            cur.execute(
                f'INSERT INTO daily_tasks ({", ".join(quoted_cols)}) VALUES ({placeholders})',
                vals
            )
        for tid, quoted_cols, placeholders, vals in updates:
            # 1. Soft delete old versions
            cur.execute("UPDATE daily_tasks SET is_active = FALSE WHERE task_id = %s", [tid])
            # 2. Insert new version
            cur.execute(
                f'INSERT INTO daily_tasks ({", ".join(quoted_cols)}) VALUES ({placeholders})',
                vals
            )

def get_task_sheet_columns():
    query = "SELECT value FROM app_settings WHERE key = 'daily_task_columns'"
    res = execute_query(query, fetch=True)
    if res:
        return res[0][0]
    return ["Department", "Task Description", "Task Status", "Allocated Hrs"]

def update_task_sheet_columns(cols):
    query = "INSERT INTO app_settings (key, value) VALUES ('daily_task_columns', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
    execute_query(query, [json.dumps(cols)])
    sync_db_columns(cols)
