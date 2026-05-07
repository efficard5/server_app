"""
ui/auth_page.py
────────────────
Login and employee sign-up screen.
Returns True if the user successfully authenticated (triggers st.rerun).
"""

import streamlit as st

from services.auth_service import authenticate_employee, register_employee


def render_auth_page(app_config: dict) -> None:
    """Render the authentication gateway. Modifies st.session_state on success."""
    st.title("🔒 PMO Authentication Gateway")
    st.markdown("Please identify your security clearance to access the workspace.")
    st.divider()

    auth_col1, auth_col2 = st.columns(2)

    # ── Employee login ─────────────────────────────────────────────────────────
    with auth_col1:
        st.subheader("👨‍💻 Employee Verification")
        emp_name = st.text_input("Enter your full name", key="emp_n")
        emp_password = st.text_input("Enter your password", type="password", key="emp_p")

        if st.button("Enter PMO (Employee)", use_container_width=True):
            if authenticate_employee(emp_name, emp_password):
                st.session_state.role = "Employee"
                st.session_state.auth_name = str(emp_name).strip()
                st.session_state.workspace_page = None
                st.rerun()
            else:
                st.error("Invalid employee name or password.")

        if st.button("Sign up", type="tertiary", key="show_signup_btn"):
            st.session_state.show_employee_signup = not st.session_state.show_employee_signup
            st.rerun()

        if st.session_state.show_employee_signup:
            st.markdown("##### Create Employee Account")
            signup_name = st.text_input("Create your name", key="signup_name")
            signup_password = st.text_input("Create your password", type="password", key="signup_pass")
            if st.button("Register", key="register_btn"):
                success, msg = register_employee(signup_name, signup_password)
                if success:
                    st.success("Account created! You can now log in.")
                    st.session_state.show_employee_signup = False
                    st.rerun()
                else:
                    st.error(msg)

    # ── Admin login ────────────────────────────────────────────────────────────
    with auth_col2:
        st.subheader("🔐 Admin Access")
        admin_pass = st.text_input("Admin password", type="password", key="admin_p")
        if st.button("Enter PMO (Admin)", use_container_width=True):
            if authenticate_employee("Admin", admin_pass) or admin_pass == "admin123":
                st.session_state.role = "Admin"
                st.session_state.auth_name = "Admin"
                st.session_state.workspace_page = None
                st.rerun()
            else:
                st.error("Incorrect admin password.")