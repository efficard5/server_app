"""
services/auth_service.py
────────────────────────
Employee authentication — reads/writes PostgreSQL via auth_repo.
No Drive, no JSON files.
"""

from db.repositories.auth_repo import (
    get_all_employees,
    employee_exists as _repo_exists,
    insert_employee,
    authenticate as _repo_authenticate,
    delete_employee,
    update_employee_password,
)


def get_employee_credentials() -> list[dict]:
    return get_all_employees()


def employee_exists(name: str) -> bool:
    return _repo_exists(str(name or "").strip())


def register_employee(name: str, password: str) -> tuple[bool, str]:
    name = str(name or "").strip()
    password = str(password or "").strip()
    if not name or not password:
        return False, "Name and password are required."
    if employee_exists(name):
        return False, "Employee name already exists."
    insert_employee(name, password)
    return True, ""


def authenticate_employee(name: str, password: str) -> bool:
    return _repo_authenticate(
        str(name or "").strip(),
        str(password or "").strip(),
    )


def remove_employee(name: str) -> None:
    delete_employee(str(name or "").strip())


def change_password(name: str, new_password: str) -> None:
    update_employee_password(
        str(name or "").strip(),
        str(new_password or "").strip(),
    )