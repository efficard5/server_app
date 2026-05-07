
import pandas as pd
import json
from db.repositories.daily_task_repo import upsert_daily_tasks_from_df
from db.base import execute_query

# two rows same date and person
rows = [
    {"task_id": None, "date": "2026-05-20", "responsible_person": "Alice", "Task Description": "Task A"},
    {"task_id": None, "date": "2026-05-20", "responsible_person": "Alice", "Task Description": "Task B"}
]

df = pd.DataFrame(rows)
print('Upserting...')
upsert_daily_tasks_from_df(df)
print('Done')

res = execute_query("SELECT task_id, date, responsible_person, extra_data FROM daily_tasks WHERE date='2026-05-20' AND responsible_person='Alice'", fetch=True)
print('Rows in DB:', len(res))
for r in res:
    print(r)
