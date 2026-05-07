"""
db/repositories/drive_doc_repo.py
──────────────────────────────────
PostgreSQL repository for file metadata and documentation links.
"""

from db.base import execute_query, get_cursor

def save_local_file_path(project, topic, file_name, file_path):
    """Save metadata for an uploaded file."""
    query = """
        INSERT INTO drive_docs (project, topic, file_name, local_path, type)
        VALUES (%s, %s, %s, %s, 'file')
        ON CONFLICT (project, topic, file_name) 
        DO UPDATE SET local_path = EXCLUDED.local_path, updated_at = CURRENT_TIMESTAMP
    """
    execute_query(query, (project, topic, file_name, file_path))

def get_metadata_for_topic(project, topic):
    """Retrieve all files and URLs for a specific topic."""
    query = """
        SELECT id, file_name, local_path, url, note, type 
        FROM drive_docs 
        WHERE project = %s AND topic = %s
    """
    rows = execute_query(query, (project, topic), fetch=True)
    
    files = []
    urls = []
    for r in rows:
        item = {
            "id": r[0],
            "name": r[1],
            "path": r[2],
            "url": r[3],
            "note": r[4],
            "type": r[5]
        }
        if r[5] == 'file':
            files.append(item)
        else:
            urls.append(item)
            
    return {"files": files, "urls": urls}

def save_file_note(project, topic, file_name, note):
    query = "UPDATE drive_docs SET note = %s WHERE project = %s AND topic = %s AND file_name = %s"
    execute_query(query, (note, project, topic, file_name))

def add_url(project, topic, url, note):
    query = """
        INSERT INTO drive_docs (project, topic, url, note, type)
        VALUES (%s, %s, %s, %s, 'url')
    """
    execute_query(query, (project, topic, url, note))

def delete_url(row_id):
    query = "DELETE FROM drive_docs WHERE id = %s"
    execute_query(query, (row_id,))

def delete_file_entry(project, topic, file_name):
    query = "DELETE FROM drive_docs WHERE project = %s AND topic = %s AND file_name = %s"
    execute_query(query, (project, topic, file_name))
