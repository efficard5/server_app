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
from services.milestone_service import save_single_milestone
from db.base import execute_query
import uuid

def render(ctx: dict) -> None:
    st.title("Task Sheet")
    
    all_daily_df = ctx["daily_task_df"]
    active_cols = get_daily_task_columns()
    
    # Ensure technical columns exist (runs once per session ideally)
    from db.repositories.daily_task_repo import sync_db_columns
    sync_db_columns(active_cols)
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

    # 2.5 Milestone & Task Link
    st.markdown("### 🔗 Milestone Task Link")
    m_col1, m_col2 = st.columns(2)
    
    milestones_dict = ctx["milestones"]
    # Filter active milestones (not completed)
    active_mils = {mid: info for mid, info in milestones_dict.items() if not info.get("completed", False)}
    milestone_options = ["-- Select Milestone --"] + sorted(list(active_mils.keys()))
    
    selected_milestone = m_col1.selectbox("🎯 Select Planned Milestone", milestone_options)
    
    # --- Sync Milestone Status (Moved below filtering for efficiency) ---

    if selected_milestone != "-- Select Milestone --":
        mil_info = active_mils[selected_milestone]
        m_tasks = mil_info.get("tasks", {})
        task_names = sorted([t_info.get("name") for t_info in m_tasks.values() if t_info.get("name")])
        
        selected_m_tasks = m_col2.multiselect("📋 Select Milestone Tasks", task_names)
        
        if selected_m_tasks:
            if st.button("➕ Add Selected Tasks to Sheet"):
                if "pending_injections" not in st.session_state:
                    st.session_state.pending_injections = []
                # Add each task as a separate row with milestone references
                for task_name in selected_m_tasks:
                    # Find the task_id for this name
                    tid = next((tid for tid, t in m_tasks.items() if t.get("name") == task_name), None)
                    t_info = m_tasks.get(tid, {})
                    st.session_state.pending_injections.append({
                        "content": task_name,
                        "ms_ref": selected_milestone,
                        "ms_task_ref": tid,
                        "Actual % Completion": t_info.get("completion_pct", 0.0)
                    })
                st.rerun()

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
    
    # 2.6 Milestone Issues (Errors) mirroring
    if selected_milestone != "-- Select Milestone --":
        mil_info = active_mils[selected_milestone]
        st.markdown(f"### ⚠️ Milestone Issues: {selected_milestone}")
        
        m_errors = mil_info.get("milestone_errors", {})
        if m_errors:
            error_rows = []
            for eid, einfo in m_errors.items():
                linked_tasks = [m_tasks[tid]["name"] for tid in einfo.get("task_ids", []) if tid in m_tasks]
                error_rows.append({
                    "Issue": einfo.get("error_name"),
                    "Description": einfo.get("description"),
                    "Status": "✅ Resolved" if einfo.get("completed") else "❌ Open",
                    "Impact": einfo.get("time_variance"),
                    "Linked Tasks": ", ".join(linked_tasks)
                })
            st.table(pd.DataFrame(error_rows))
        else:
            st.info("No issues recorded for this milestone.")

        # Add New Issue Form
        with st.expander("➕ Report New Milestone Issue", expanded=False):
            with st.form(key="daily_add_error_form"):
                e_name = st.text_input("Issue Name")
                e_desc = st.text_area("Description")
                e_time = st.text_input("Time Impact", value="0")
                
                # Task selection from current milestone
                task_opts = {f"{t_info['name']}": tid for tid, t_info in m_tasks.items()}
                sel_task_names = st.multiselect("Affected Tasks", list(task_opts.keys()))
                
                if st.form_submit_button("💾 Save Issue"):
                    if e_name and sel_task_names:
                        new_e_id = str(uuid.uuid4())
                        if "milestone_errors" not in mil_info: mil_info["milestone_errors"] = {}
                        mil_info["milestone_errors"][new_e_id] = {
                            "error_name": e_name,
                            "description": e_desc,
                            "time_variance": e_time,
                            "task_ids": [task_opts[tn] for tn in sel_task_names],
                            "completed": False
                        }
                        mil_info["updated_at"] = datetime.now().isoformat()
                        save_single_milestone(selected_milestone, mil_info)
                        st.success("Issue recorded and mirrored to Planned Milestones!")
                        st.rerun()
                    else:
                        st.error("Name and at least one task are required.")

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

    # --- Sync Milestone Status to Daily Tasks (In-Memory for Display) ---
    # Only sync filtered rows for performance
    for idx, row in editor_df.iterrows():
        mid = row.get("ms_ref")
        tid = row.get("ms_task_ref")
        if mid and pd.notna(mid) and tid and pd.notna(tid):
            if mid in milestones_dict and tid in milestones_dict[mid].get("tasks", {}):
                ms_task = milestones_dict[mid]["tasks"][tid]
                ms_done = bool(ms_task.get("completed", False))
                ms_pct = float(ms_task.get("completion_pct", 100.0 if ms_done else 0.0))
                
                editor_df.at[idx, "completed_checkpoint"] = str(ms_done)
                editor_df.at[idx, "Actual % Completion"] = ms_pct

    # Ensure all active columns exist in the DataFrame
    for col in active_cols:
        if col not in editor_df.columns:
            editor_df[col] = ""

    # Define base columns and final column order (including technical sync columns)
    base_cols = ["task_id", "date", "responsible_person"]
    tech_cols = ["completed_checkpoint", "ms_ref", "ms_task_ref"]
    final_cols = base_cols + active_cols + tech_cols
    
    # Reindex to ensure all columns are present (fills missing with empty string)
    editor_df = editor_df.reindex(columns=final_cols, fill_value="")

    # Add explicit Delete and Unplanned checklist columns
    editor_df.insert(0, "Delete", False)
    # Handle unplanned_checklist if it exists in data, else default to False
    unplanned_vals = editor_df["unplanned_checklist"] if "unplanned_checklist" in editor_df.columns else False
    editor_df.insert(1, "unplanned checklist", unplanned_vals)
    
    # Add Task Completed Checkpoint and Progress at the very end
    if "completed_checkpoint" in editor_df.columns:
        # Standardize strings/None/Booleans to boolean for the editor
        def to_bool(x):
            if isinstance(x, bool): return x
            if not x or pd.isna(x): return False
            return str(x).lower() == "true"
            
        editor_df["Task Completed"] = editor_df["completed_checkpoint"].apply(to_bool)
    else:
        editor_df["Task Completed"] = False

    if "Actual % Completion" not in editor_df.columns:
        editor_df["Actual % Completion"] = 0.0
    else:
        editor_df["Actual % Completion"] = pd.to_numeric(editor_df["Actual % Completion"], errors="coerce").fillna(0.0)
    
    # Ensure a clean integer index for hide_index to work correctly
    editor_df = editor_df.reset_index(drop=True)

    # Inject pending milestone tasks
    if "pending_injections" in st.session_state and st.session_state.pending_injections:
        new_rows = []
        for inj in st.session_state.pending_injections:
            content = inj["content"]
            row_data = {
                "Delete": False,
                "unplanned checklist": False,
                "task_id": "NEW",
                "date": target_date if target_date else datetime.now().date(),
                "responsible_person": selected_person if selected_person != "All Employees" else current_user,
                "Task Completed": False,
                "ms_ref": inj.get("ms_ref"),
                "ms_task_ref": inj.get("ms_task_ref"),
                "Actual % Completion": inj.get("Actual % Completion", 0.0)
            }
            # Identify the task description column (look for "description" or fallback to first available)
            desc_col = next((c for c in active_cols if "description" in c.lower()), active_cols[0] if active_cols else None)
            
            for col in active_cols:
                if col == desc_col:
                    row_data[col] = content
                else:
                    row_data[col] = ""
            new_rows.append(row_data)
        
        if new_rows:
            inj_df = pd.DataFrame(new_rows)
            # Standardize date format for merging
            if not inj_df.empty:
                inj_df["date"] = pd.to_datetime(inj_df["date"]).dt.date
            editor_df = pd.concat([editor_df, inj_df], ignore_index=True)
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
            "Task Completed": st.column_config.CheckboxColumn("✅ Done", default=False),
            "Actual % Completion": st.column_config.NumberColumn("Actual % Completion", min_value=0.0, max_value=100.0, step=1.0, format="%d%%"),
            "task_id": st.column_config.NumberColumn("ID", disabled=True, format="%d"),
            "date": st.column_config.DateColumn("Date", required=True),
            "responsible_person": st.column_config.SelectboxColumn("Responsible", options=employees, required=True),
            "ms_ref": None, # Hidden reference
            "ms_task_ref": None # Hidden reference
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
                "unplanned_checklist": bool(row.get("unplanned checklist", False)),
                "completed_checkpoint": bool(row.get("Task Completed", False)),
                "Actual % Completion": float(row.get("Actual % Completion") or 0.0),
                "ms_ref": row.get("ms_ref"),
                "ms_task_ref": row.get("ms_task_ref")
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
            
            # --- Sync completion status back to Planned Milestones ---
            # Use fresh milestone data (cache was cleared by bulk_replace_daily_tasks)
            from services.milestone_service import load_planned_milestones
            all_mils = load_planned_milestones()
            updated_mils = set()
            for r in rows_to_upsert:
                mid = r.get("ms_ref")
                tid = r.get("ms_task_ref")
                if not mid or pd.isna(mid) or not tid or pd.isna(tid):
                    continue
                
                done = bool(r.get("completed_checkpoint", False))
                pct = float(r.get("Actual % Completion") or 0.0)
                
                if pct >= 100.0: done = True
                if done and pct < 100.0: pct = 100.0
                
                if mid in all_mils and tid in all_mils[mid].get("tasks", {}):
                    ms_task = all_mils[mid]["tasks"][tid]
                    if bool(ms_task.get("completed", False)) != done or float(ms_task.get("completion_pct", 0.0)) != pct:
                        ms_task["completed"] = done
                        ms_task["completion_pct"] = pct
                        all_mils[mid]["updated_at"] = datetime.now().isoformat()
                        updated_mils.add(mid)
            
            for mid in updated_mils:
                save_single_milestone(mid, all_mils[mid])

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
        if "pending_injections" in st.session_state:
            st.session_state.pending_injections = []
        st.session_state.daily_save_count += 1
        st.rerun()
