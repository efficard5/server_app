"""
db/repositories/notes_repo.py
────────────────────────────
PostgreSQL repository for project notes.
"""

from db.base import execute_query

def get_all_notes():
    query = "SELECT project, topic, note_text FROM project_notes WHERE is_active = TRUE"
    rows = execute_query(query, fetch=True)
    
    notes = {}
    for r in rows:
        project, topic, text = r
        if project not in notes:
            notes[project] = {
                "Topics": {},
                "Project_Issues": "",
                "Project_Plans": "",
                "Phases": "{}"
            }
        
        if topic == "__PROJECT_ISSUES__":
            notes[project]["Project_Issues"] = text
        elif topic == "__PROJECT_PLANS__":
            notes[project]["Project_Plans"] = text
        elif topic == "__PHASES__":
            notes[project]["Phases"] = text
        else:
            notes[project]["Topics"][topic] = text
    return notes

def save_note(project, topic, note_text):
    execute_query("UPDATE project_notes SET is_active = FALSE WHERE project = %s AND topic = %s AND is_active = TRUE", (project, topic))
    query = """
        INSERT INTO project_notes (project, topic, note_text, is_active)
        VALUES (%s, %s, %s, TRUE)
    """
    execute_query(query, (project, topic, note_text))

def delete_note(project, topic):
    query = "UPDATE project_notes SET is_active = FALSE WHERE project = %s AND topic = %s"
    execute_query(query, (project, topic))
