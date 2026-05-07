"""
db/repositories/storage_repo.py
──────────────────────────────
Repository for tracking file metadata in the drive_docs table.
"""

from db.base import execute_query

def add_file_record(project, topic, filename, local_path, note="", f_type="File", url="", uploaded_by=None):
    query = """
        INSERT INTO drive_docs (project, topic, file_name, local_path, url, note, type, uploaded_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (project, topic, file_name) 
        DO UPDATE SET local_path = EXCLUDED.local_path, 
                      url = EXCLUDED.url, 
                      note = EXCLUDED.note,
                      uploaded_by = EXCLUDED.uploaded_by,
                      updated_at = CURRENT_TIMESTAMP
    """
    execute_query(query, (project, topic, filename, local_path, url, note, f_type, uploaded_by))

def get_topic_files(project, topic, user_filter=None):
    if user_filter:
        query = """
            SELECT id, file_name, local_path, url, note, type, uploaded_by
            FROM drive_docs 
            WHERE project = %s AND topic = %s AND uploaded_by = %s
            ORDER BY created_at DESC
        """
        rows = execute_query(query, (project, topic, user_filter), fetch=True)
    else:
        query = """
            SELECT id, file_name, local_path, url, note, type, uploaded_by
            FROM drive_docs 
            WHERE project = %s AND topic = %s
            ORDER BY created_at DESC
        """
        rows = execute_query(query, (project, topic), fetch=True)
    return rows

def delete_file_record(file_id):
    query = "DELETE FROM drive_docs WHERE id = %s"
    execute_query(query, (file_id,))
