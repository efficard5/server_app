# scratch/migrate_extra_data.py
from db.base import execute_query
import json

def migrate():
    # 1. Get all rows with extra_data
    rows = execute_query("SELECT task_id, extra_data FROM daily_tasks WHERE extra_data IS NOT NULL", fetch=True)
    if not rows:
        print("No rows to migrate.")
        return

    for tid, extra_json in rows:
        if not extra_json: continue
        if isinstance(extra_json, str):
            extra = json.loads(extra_json)
        else:
            extra = extra_json
        
        # Check for our technical columns
        updates = {}
        for key in ["completed_checkpoint", "ms_ref", "ms_task_ref"]:
            if key in extra:
                updates[key] = extra[key]
        
        if updates:
            cols = ", ".join([f'"{k}" = %s' for k in updates.keys()])
            vals = list(updates.values()) + [tid]
            print(f"Updating task {tid} with {updates}")
            execute_query(f'UPDATE daily_tasks SET {cols} WHERE task_id = %s', vals)

if __name__ == "__main__":
    migrate()
