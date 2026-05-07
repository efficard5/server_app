# ui/pages/gantt.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.task_service import save_task, calculate_project_week

def render(ctx: dict) -> None:
    df = ctx["df"]
    projects = ctx["projects"]
    topics = ctx["topics"]
    employees = ctx["employees"]
    
    st.header("Task Management")

    # --- 1. ADD NEW TASK FORM ---
    with st.expander("➕ Add New Task", expanded=False):
        st.markdown("**1. Project Assignment**")
        pc1, pc2 = st.columns(2)
        t_proj_sel = pc1.selectbox("Map to Existing Project", [""] + projects, key="n_proj_sel")
        t_proj_new = pc2.text_input("...OR Create New Project", key="n_proj_new")
        
        actual_proj = t_proj_new.strip() if t_proj_new.strip() else t_proj_sel
        
        st.markdown("**2. Topic Classification**")
        tc1, tc2 = st.columns(2)
        t_topic_sel = tc1.selectbox("Select Topic", [""] + topics, key="n_topic_sel")
        t_topic_new = tc2.text_input("...OR New Topic", key="n_topic_new")
        actual_topic = t_topic_new.strip() if t_topic_new.strip() else t_topic_sel

        st.markdown("**3. Task Details**")
        ac1, ac2 = st.columns([2, 1])
        t_name = ac1.text_area("Task Description", key="n_name", height=70)
        t_emp = ac2.selectbox("Assigned To", employees, key="n_emp")
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        t_start = sc1.date_input("Start Date", datetime.now(), key="n_start")
        t_end = sc2.date_input("End Date", datetime.now() + timedelta(days=7), key="n_end")
        
        # Calculate derived week
        derived_week = calculate_project_week(actual_proj, t_start, df)
        t_week = sc3.number_input("Project Week", min_value=1, value=derived_week, key="n_week")
        t_status = sc4.selectbox("Status", ["Planned", "In Progress", "Completed", "Delayed"], key="n_status")

        st.markdown("**4. Additional Context & Attachments**")
        t_notes = st.text_area("Notes / Remarks", key="n_notes", height=60)
        lc1, lc2 = st.columns(2)
        t_file = lc1.text_input("📁 Document / Server File Link", key="n_file", placeholder="e.g. /nas/docs/blueprint.pdf")
        t_img = lc2.text_input("🖼️ Image Link", key="n_img", placeholder="e.g. /data/images/photo.jpg")

        if st.button("💾 Save Task to Project Database", type="primary", use_container_width=True):
            if not actual_proj or not actual_topic or not t_name.strip():
                st.error("Please fill Project, Topic, and Task Name.")
            else:
                new_task = {
                    "project": actual_proj,
                    "topic": actual_topic,
                    "task_name": t_name.strip(),
                    "start_date": t_start.strftime("%Y-%m-%d"),
                    "end_date": t_end.strftime("%Y-%m-%d"),
                    "employee": t_emp,
                    "status": t_status,
                    "week": int(t_week),
                    "completion_pct": 100 if t_status == "Completed" else 0,
                    "notes": t_notes.strip(),
                    "file_link": t_file.strip(),
                    "image_link": t_img.strip()
                }
                save_task(new_task)
                st.toast(f"✅ Task '{t_name}' saved to '{actual_proj}'!", icon='💾')
                st.success(f"Task '{t_name}' saved to '{actual_proj}'!")
                st.rerun()

    st.divider()

    # --- 2. FILTERED TASK LIST ---
    st.subheader("📋 Task List")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    filter_project = f1.selectbox("Filter by Project", ["All"] + (projects if projects else []))
    filter_topic = f2.selectbox("Filter by Topic", ["All"] + (topics if topics else []))
    filter_status = f3.selectbox("Filter by Status", ["All", "Planned", "In Progress", "Completed", "Delayed"])
    edit_mode = f4.toggle("📝 Edit Mode", value=False)

    display_df = df.copy()
    if filter_project != "All":
        display_df = display_df[display_df["project"] == filter_project]
    if filter_topic != "All":
        display_df = display_df[display_df["topic"] == filter_topic]
    if filter_status != "All":
        display_df = display_df[display_df["status"] == filter_status]

    if display_df.empty:
        st.info("No tasks found matching these filters.")
    else:
        if edit_mode:
            # EDITABLE VIEW
            display_df["Delete"] = False
            view_cols = ["Delete", "id", "project", "topic", "task_name", "status", "completion_pct", "week", "employee", "notes", "file_link", "image_link"]
            final_view_cols = [c for c in view_cols if c in display_df.columns]
            
            edited_df = st.data_editor(
                display_df[final_view_cols],
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "completion_pct": st.column_config.NumberColumn("Progress %", min_value=0, max_value=100, step=5),
                    "status": st.column_config.SelectboxColumn("Status", options=["Planned", "In Progress", "Completed", "Delayed"]),
                    "Delete": st.column_config.CheckboxColumn("🗑️", default=False),
                },
                hide_index=True,
                key="gantt_editor"
            )
            
            if st.button("💾 Save All Changes", type="primary", use_container_width=True):
                updated_count = 0
                deleted_count = 0
                for _, row in edited_df.iterrows():
                    task_id = row.get("id")
                    if not task_id: continue
                    if row.get("Delete") == True:
                        delete_task_row(task_id)
                        deleted_count += 1
                    else:
                        update_data = row.to_dict()
                        update_data.pop("Delete", None); update_data.pop("id", None)
                        for k, v in update_data.items():
                            if hasattr(v, "strftime"): update_data[k] = v.strftime("%Y-%m-%d")
                        update_task_row(task_id, update_data)
                        updated_count += 1
                
                if updated_count > 0 or deleted_count > 0:
                    st.toast(f"✅ Sync Complete: {updated_count} updated, {deleted_count} deleted.", icon="💾")
                    import time; time.sleep(0.5)
                    st.rerun()
        else:
            # READ-ONLY VIEW
            view_cols = ["id", "project", "topic", "task_name", "status", "completion_pct", "week", "employee", "notes", "file_link", "image_link"]
            final_view_cols = [c for c in view_cols if c in display_df.columns]
            st.dataframe(
                display_df[final_view_cols],
                use_container_width=True,
                column_config={
                    "completion_pct": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100, format="%d%%"),
                    "file_link": st.column_config.LinkColumn("📂 File"),
                    "image_link": st.column_config.LinkColumn("🖼️ Image"),
                },
                hide_index=True
            )
