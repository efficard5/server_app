"""
db/repositories/notes_repo.py
────────────────────────────
PostgreSQL repository for project notes.
"""

from db.base import execute_query

def get_all_notes():
    query = "SELECT project, topic, note_text FROM project_notes"
    rows = execute_query(query, fetch=True)
    
    notes = {}
    for r in rows:
        project, topic, text = r
        if project not in notes:
            notes[project] = {
                "Topics": {},
                "Project_Issues": "",
                "Project_Plans": ""
            }
        
        if topic == "__PROJECT_ISSUES__":
            notes[project]["Project_Issues"] = text
        elif topic == "__PROJECT_PLANS__":
            notes[project]["Project_Plans"] = text
        else:
            notes[project]["Topics"][topic] = text
    return notes

def save_note(project, topic, note_text):
    query = """
        INSERT INTO project_notes (project, topic, note_text)
        VALUES (%s, %s, %s)
        ON CONFLICT (project, topic) DO UPDATE SET note_text = EXCLUDED.note_text
    """
    execute_query(query, (project, topic, note_text))

def delete_note(project, topic):
    query = "DELETE FROM project_notes WHERE project = %s AND topic = %s"
    execute_query(query, (project, topic))
