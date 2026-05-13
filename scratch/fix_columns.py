# scratch/fix_columns.py
from db.base import execute_query

def fix():
    cols = ["completed_checkpoint", "ms_ref", "ms_task_ref"]
    for col in cols:
        try:
            print(f"Adding column {col}...")
            execute_query(f'ALTER TABLE daily_tasks ADD COLUMN "{col}" TEXT')
        except Exception as e:
            print(f"Column {col} might already exist or error: {e}")

if __name__ == "__main__":
    fix()
