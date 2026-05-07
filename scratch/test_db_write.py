import os
import psycopg2
from db.base import execute_query

def test_update():
    print("Testing DB update...")
    # Check current value
    res = execute_query("SELECT id, completion_pct FROM tasks LIMIT 1", fetch=True)
    if not res:
        print("No tasks found.")
        return
    
    tid, old_val = res[0]
    new_val = (old_val + 10) % 105
    print(f"Task {tid}: Changing progress from {old_val} to {new_val}")
    
    execute_query("UPDATE tasks SET completion_pct = %s WHERE id = %s", (new_val, tid))
    
    # Verify
    res2 = execute_query("SELECT completion_pct FROM tasks WHERE id = %s", (tid,), fetch=True)
    actual_val = res2[0][0]
    print(f"Verified value in DB: {actual_val}")
    
    if actual_val == new_val:
        print("SUCCESS: DB update works and persists.")
    else:
        print("FAILURE: DB update did not stick.")

if __name__ == "__main__":
    test_update()
