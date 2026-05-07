"""
db/repositories/auth_repo.py
───────────────────────────
PostgreSQL repository for employee authentication.
"""

from db.base import execute_query

def get_all_employees():
    query = "SELECT name, password FROM employees"
    rows = execute_query(query, fetch=True)
    return [{"name": r[0], "password": r[1]} for r in rows]

def employee_exists(name):
    query = "SELECT 1 FROM employees WHERE name = %s"
    row = execute_query(query, (name,), fetch=True)
    return len(row) > 0

def insert_employee(name, password):
    query = "INSERT INTO employees (name, password) VALUES (%s, %s)"
    execute_query(query, (name, password))

def authenticate(name, password):
    query = "SELECT 1 FROM employees WHERE name = %s AND password = %s"
    row = execute_query(query, (name, password), fetch=True)
    return len(row) > 0

def delete_employee(name):
    query = "DELETE FROM employees WHERE name = %s"
    execute_query(query, (name,))

def update_employee_password(name, new_password):
    query = "UPDATE employees SET password = %s WHERE name = %s"
    execute_query(query, (new_password, name))
