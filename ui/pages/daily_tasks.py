# ui/pages/daily_tasks.py
import streamlit as st
import pandas as pd
from datetime import datetime
from services.task_service import (
    load_daily_task_data, 
    bulk_replace_daily_tasks, 
    get_daily_task_columns, 
    update_daily_task_columns
)
from db.base import execute_query

def render(ctx: dict) -> None:
    st.title("Task Sheet")
    
    # 1. Configuration & Data
    all_daily_df = load_daily_task_data()
    active_cols = get_daily_task_columns()
    employees = ctx["employees"]
    is_admin = st.session_state.role == "Admin"
    current_user = st.session_state.auth_name
    
    # Initialize save counter for editor key stability/refresh
    if "daily_save_count" not in st.session_state:
        st.session_state.daily_save_count = 0

    # 2. Top Filter Selection
    f1, f2 = st.columns(2)
    
    # Filter global DF for the current user to populate dates
    user_df = all_daily_df.copy()
    if not is_admin:
        user_df = user_df[user_df["responsible_person"] == current_user]
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    existing_dates = sorted([str(d) for d in user_df["date"].unique()], reverse=True)
    date_options = ["All Dates"] + existing_dates + ["➕ Add New Date"]
    
    default_date_idx = 0
    if today_str in existing_dates:
        default_date_idx = date_options.index(today_str)
    
    selected_option = f1.selectbox("📅 Assigned Date Selection", date_options, index=default_date_idx)
    
    # Handle "Add New Date" logic
    final_selected_date = selected_option
    if selected_option == "➕ Add New Date":
        new_date_val = f1.date_input("Pick a New Date", value=datetime.now())
        final_selected_date = str(new_date_val)
    
    if is_admin:
        emp_options = ["All Employees"] + employees
        selected_person = f2.selectbox("👤 Employee Selection", emp_options)
    else:
        selected_person = current_user
        f2.text_input("👤 Employee Selection", value=selected_person, disabled=True)

    # 3. Dynamic Column Management (Admin Only)
    if is_admin:
        with st.expander("🛠️ Manage Table Columns", expanded=False):
            c1, c2, c3 = st.columns([2, 1, 1])
            new_col = c1.text_input("New Column Name")
            if c2.button("➕ Add Column", use_container_width=True):
                if new_col and new_col not in active_cols:
                    active_cols.append(new_col)
                    update_daily_task_columns(active_cols)
                    st.rerun()
            
            del_col = c3.selectbox("Delete Column", [""] + active_cols)
            if st.button("🗑️ Delete Selected Column", type="secondary"):
                if del_col:
                    active_cols.remove(del_col)
                    update_daily_task_columns(active_cols)
                    st.rerun()

    st.divider()
    st.subheader(f"Manage Daily Tasks - {selected_person} ({final_selected_date})")

    # 4. Prepare Data for Editor
    editor_df = all_daily_df.copy()
    
    # Standardize date objects immediately
    if not editor_df.empty:
        editor_df["date"] = pd.to_datetime(editor_df["date"], errors="coerce").dt.date

    # Filter by date
    target_date = None
    if final_selected_date != "All Dates":
        # Convert final_selected_date to date object for comparison if it's a string
        target_date = final_selected_date
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except:
                pass
        editor_df = editor_df[editor_df["date"] == target_date]
        
    # Filter by person
    if selected_person != "All Employees":
        editor_df = editor_df[editor_df["responsible_person"] == selected_person]

    # Ensure all active columns exist in the DataFrame
    for col in active_cols:
        if col not in editor_df.columns:
            editor_df[col] = ""

    # Define base columns and final column order
    base_cols = ["task_id", "date", "responsible_person"]
    final_cols = base_cols + active_cols
    # Reindex to ensure all columns are present (fills missing with empty string)
    editor_df = editor_df.reindex(columns=final_cols, fill_value="")

    # Add explicit Delete and Unplanned checklist columns
    editor_df.insert(0, "Delete", False)
    # Handle unplanned_checklist if it exists in data, else default to False
    unplanned_vals = editor_df["unplanned_checklist"] if "unplanned_checklist" in editor_df.columns else False
    editor_df.insert(1, "unplanned checklist", unplanned_vals)
    
    # Ensure a clean integer index for hide_index to work correctly
    editor_df = editor_df.reset_index(drop=True)

    # If there are no rows (after filtering), provide a placeholder row for entry
    if editor_df.empty and final_selected_date != "All Dates":
        placeholder = {
            "task_id": "NEW",
            "date": target_date if 'target_date' in locals() else None,
            "responsible_person": current_user if selected_person == "All Employees" else selected_person,
        }
        # Initialize with active columns empty
        for col in active_cols:
            placeholder[col] = ""
        editor_df = pd.DataFrame([placeholder])
        editor_df.insert(0, "Delete", False)
        editor_df.insert(1, "unplanned checklist", False)
        editor_df = editor_df.reset_index(drop=True)

    # Render the editable table
    edited_df = st.data_editor(
        editor_df,
        num_rows="dynamic" if is_admin or final_selected_date != "All Dates" else "fixed",
        width='stretch',

        hide_index=True,
        key=f"editor_{final_selected_date}_{selected_person}_{st.session_state.daily_save_count}",
        column_config={
            "Delete": st.column_config.CheckboxColumn("🗑️", default=False),
            "unplanned checklist": st.column_config.CheckboxColumn("📝 Unplanned", default=False),
            "task_id": st.column_config.NumberColumn("ID", disabled=True, format="%d"),
            "date": st.column_config.DateColumn("Date", required=True),
            "responsible_person": st.column_config.SelectboxColumn("Responsible", options=employees, required=True),
        }
    )

    # 6. Save Logic
    if st.button("💾 Save Daily Task Sheet", type="primary", use_container_width=True):
        # Prepare lists for deletions and upserts
        rows_to_upsert = []
        delete_count = 0
        for _, row in edited_df.iterrows():
            # Handle explicit deletions
            if row.get("Delete"):
                tid = row.get("task_id")
                if tid and str(tid) not in ["", "NEW", "nan"]:
                    execute_query("DELETE FROM daily_tasks WHERE task_id = %s", [str(tid)])
                    delete_count += 1
                continue

            # Prepare data for upsert
            task_id = row.get("task_id")
            is_new = pd.isna(task_id) or str(task_id).strip() in ["", "NEW", "nan"]
            # Ensure date is a proper date object
            d = row.get("date")
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                except Exception:
                    d = None
            # Autofill missing date/person from current filters
            if (pd.isna(d) or not d) and final_selected_date != "All Dates":
                d = target_date
            p = row.get("responsible_person")
            if (pd.isna(p) or not p) and selected_person != "All Employees":
                p = selected_person

            # Skip rows without required fields
            if not d or not p:
                continue

            row_dict = {
                "task_id": None if is_new else str(task_id),
                "date": d,
                "responsible_person": p,
                "unplanned_checklist": bool(row.get("unplanned checklist", False))
            }
            # Add any extra dynamic columns
            for col in active_cols:
                if col in row:
                    val = row[col]
                    row_dict[col] = val if not pd.isna(val) else ""
            rows_to_upsert.append(row_dict)

        # Perform bulk upsert if there are rows
        if rows_to_upsert:
            bulk_replace_daily_tasks(pd.DataFrame(rows_to_upsert))

        # Feedback to user
        msg = []
        if rows_to_upsert:
            msg.append(f"Saved {len(rows_to_upsert)} task(s)")
        if delete_count:
            msg.append(f"Deleted {delete_count} task(s)")
        if msg:
            st.success(" – ".join(msg))
        else:
            st.info("No changes to save.")
        # Refresh view
        st.session_state.daily_save_count += 1
        st.rerun()
