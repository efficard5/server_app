import os
import sys
sys.path.append('/home/effica/server_app')
from db.base import execute_query, get_cursor

def migrate_db():
    queries = [
        # Milestones
        "ALTER TABLE milestones DROP CONSTRAINT IF EXISTS milestones_pkey;",
        "ALTER TABLE milestones ADD COLUMN IF NOT EXISTS row_id SERIAL PRIMARY KEY;",
        "ALTER TABLE milestones ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "CREATE INDEX IF NOT EXISTS idx_milestones_active ON milestones(is_active);",
        
        # Project Notes
        "ALTER TABLE project_notes DROP CONSTRAINT IF EXISTS project_notes_pkey;",
        "ALTER TABLE project_notes ADD COLUMN IF NOT EXISTS row_id SERIAL PRIMARY KEY;",
        "ALTER TABLE project_notes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "CREATE INDEX IF NOT EXISTS idx_project_notes_active ON project_notes(is_active);",
        
        # Daily Tasks
        "ALTER TABLE daily_tasks DROP CONSTRAINT IF EXISTS daily_tasks_pkey;",
        "ALTER TABLE daily_tasks ADD COLUMN IF NOT EXISTS row_id SERIAL PRIMARY KEY;",
        "ALTER TABLE daily_tasks ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "CREATE INDEX IF NOT EXISTS idx_daily_tasks_active ON daily_tasks(is_active);",
        
        # Tasks (Gantt)
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_pkey;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS row_id SERIAL PRIMARY KEY;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "CREATE INDEX IF NOT EXISTS idx_tasks_active ON tasks(is_active);"
    ]
    
    with get_cursor(commit=True) as cur:
        for q in queries:
            print(f"Executing: {q}")
            try:
                cur.execute(q)
            except Exception as e:
                print(f"Error (might be expected if already run): {e}")

if __name__ == '__main__':
    migrate_db()
    print("Migration complete.")
