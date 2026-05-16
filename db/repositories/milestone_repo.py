"""
db/repositories/milestone_repo.py
────────────────────────────────
PostgreSQL repository for planned milestones.
"""

import json
from db.base import execute_query

def get_all_milestones():
    query = "SELECT milestone_id, data FROM milestones WHERE is_active = TRUE"
    rows = execute_query(query, fetch=True)
    return {r[0]: r[1] for r in rows}

def save_milestone(milestone_id, mil_info):
    execute_query("UPDATE milestones SET is_active = FALSE WHERE milestone_id = %s AND is_active = TRUE", (milestone_id,))
    query = "INSERT INTO milestones (milestone_id, data, is_active) VALUES (%s, %s, TRUE)"
    execute_query(query, (milestone_id, json.dumps(mil_info)))

def delete_milestone(milestone_id):
    query = "UPDATE milestones SET is_active = FALSE WHERE milestone_id = %s"
    execute_query(query, (milestone_id,))

def save_all_milestones(milestones):
    execute_query("UPDATE milestones SET is_active = FALSE")
    for mid, info in milestones.items():
        save_milestone(mid, info)
