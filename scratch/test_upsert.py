
import pandas as pd
import json
from uuid import uuid4
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from db.repositories.daily_task_repo import upsert_daily_tasks_from_df
from db.base import execute_query

# Create a dummy DF
df = pd.DataFrame([
    {
        "task_id": None,
        "date": "2026-05-15",
        "responsible_person": "TestUser",
        "Task Description": "Scratch Test Task",
        "Task Status": "In Progress"
    }
])

print("Attempting upsert...")
try:
    upsert_daily_tasks_from_df(df)
    print("Upsert completed successfully.")
    
    # Verify
    res = execute_query("SELECT * FROM daily_tasks WHERE responsible_person = 'TestUser' AND date = '2026-05-15';", fetch=True)
    print(f"Found {len(res)} rows in DB.")
    for r in res:
        print(r)
except Exception as e:
    print(f"Error: {e}")
