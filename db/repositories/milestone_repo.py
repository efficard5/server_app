"""
db/repositories/milestone_repo.py
────────────────────────────────
PostgreSQL repository for planned milestones.
"""

import json
from db.base import execute_query

def get_all_milestones():
    query = "SELECT milestone_id, data FROM milestones"
    rows = execute_query(query, fetch=True)
    return {r[0]: r[1] for r in rows}

def save_milestone(milestone_id, mil_info):
    query = """
        INSERT INTO milestones (milestone_id, data)
        VALUES (%s, %s)
        ON CONFLICT (milestone_id) DO UPDATE SET data = EXCLUDED.data
    """
    execute_query(query, (milestone_id, json.dumps(mil_info)))

def delete_milestone(milestone_id):
    query = "DELETE FROM milestones WHERE milestone_id = %s"
    execute_query(query, (milestone_id,))

def save_all_milestones(milestones):
    # Simplified replace: delete all and insert new
    execute_query("DELETE FROM milestones")
    for mid, info in milestones.items():
        save_milestone(mid, info)
