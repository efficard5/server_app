# ui/pages/gantt.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.task_service import save_task, calculate_project_week, update_task_row, delete_task_row
from utils.formatters import format_bullet_markdown, format_single_line_text


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
        
        t_progress = st.slider("Completion Progress %", 0, 100, step=5, key="n_progress")

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
                    "completion_pct": t_progress,
                    "notes": t_notes.strip(),
                    "file_link": t_file.strip(),
                    "image_link": t_img.strip()
                }
                save_task(new_task)
                # Also sync note to dashboard
                if t_notes.strip():
                    from services.notes_service import upsert_note
                    upsert_note(actual_proj, actual_topic, t_notes.strip())
                
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

    # --- Sync Dashboard Notes ---
    from services.notes_service import load_notes, upsert_note
    import json
    
    notes_db = load_notes()
    
    def get_dash_note(row):
        proj = row["project"]
        topic = row["topic"]
        raw = notes_db.get(proj, {}).get("Topics", {}).get(topic, "")
        try:
            d = json.loads(raw)
            # Combine major, problematic, future for display without emojis
            lines = []
            if d.get("Major"): lines.append(f"**Completed:**\n{format_bullet_markdown(d['Major'])}")
            if d.get("Problematic"): lines.append(f"**In Progress:**\n{format_bullet_markdown(d['Problematic'])}")
            if d.get("Future"): lines.append(f"**Future:**\n{format_bullet_markdown(d['Future'])}")
            return "\n\n".join(lines) if lines else ""
        except:
            return format_bullet_markdown(raw)


    # If the user wants the "same notes", we should probably show them.
    # We'll use the 'notes' column for this.
    display_df["notes"] = display_df.apply(get_dash_note, axis=1)

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
                
                # Use st.session_state to find what actually changed if possible, 
                # but for now we compare with the original display_df for safety.
                for _, row in edited_df.iterrows():
                    task_id = row.get("id")
                    if not task_id: continue
                    
                    # Find the original row to check for changes
                    orig_matches = display_df[display_df["id"] == task_id]
                    if orig_matches.empty: continue
                    orig_row = orig_matches.iloc[0]
                    
                    if row.get("Delete") == True:
                        delete_task_row(int(task_id))
                        deleted_count += 1
                    else:
                        # Check if anything actually changed
                        row_dict = row.to_dict()
                        # Remove keys that shouldn't be compared or aren't in the DB
                        comp_row = {k: v for k, v in row_dict.items() if k not in ["Delete", "id"]}
                        comp_orig = {k: v for k, v in orig_row.to_dict().items() if k in comp_row}
                        
                        # Handle date comparisons if any (though not in view_cols right now)
                        changed = False
                        for k in comp_row:
                            if str(comp_row[k]) != str(comp_orig[k]):
                                changed = True
                                break
                        
                        if changed:
                            update_data = comp_row.copy()
                            
                            # If notes changed, update dashboard notes
                            if update_data.get("notes") != comp_orig.get("notes"):
                                upsert_note(row["project"], row["topic"], update_data["notes"])
                            
                            # Clean up data for DB
                            for k, v in update_data.items():
                                if hasattr(v, "strftime"): update_data[k] = v.strftime("%Y-%m-%d")
                            
                            update_task_row(int(task_id), update_data)
                            updated_count += 1
                
                if updated_count > 0 or deleted_count > 0:
                    st.toast(f"✅ Sync Complete: {updated_count} updated, {deleted_count} deleted.", icon="💾")
                    st.success(f"Successfully updated {updated_count} tasks and deleted {deleted_count} tasks.")
                    import time; time.sleep(1.0)
                    st.rerun()
                else:
                    st.info("No changes detected.")
        else:
            # READ-ONLY VIEW (Weekly Dashboard Style)
            hcols = st.columns([0.5, 1.5, 1.3, 2.5, 1.0, 0.8, 1.2, 1.0])
            headers = ["#", "Project", "Topic", "Task Name", "Week", "Done %", "Employee", "Status"]
            for h, col in zip(headers, hcols):
                col.markdown(f"**{h}**")
            st.divider()

            from services.milestone_service import load_planned_milestones, get_planned_topic_adjustments
            milestones_db = load_planned_milestones()
            
            for i, (_, row) in enumerate(display_df.iterrows()):
                rcols = st.columns([0.5, 1.5, 1.3, 2.5, 1.0, 0.8, 1.2, 1.0])
                rcols[0].write(i + 1)
                rcols[1].write(row["project"])
                rcols[2].write(row["topic"])
                rcols[3].write(row["task_name"])
                rcols[4].write(str(row.get("week", 1)))
                
                # Progress with milestone adjustment
                base_pct = int(row.get('completion_pct', 0))
                adj_map = get_planned_topic_adjustments(row["project"], milestones_db, [row["topic"]])
                adj = adj_map.get(row["topic"], 0.0)
                total_pct = min(100, int(base_pct + adj))
                
                if adj > 0:
                    rcols[5].markdown(f"**{total_pct}%**  \n*(+{int(adj)}% MS)*")
                else:
                    rcols[5].write(f"{base_pct}%")
                    
                rcols[6].write(row.get("employee", "Unassigned"))
                rcols[7].write(row["status"])

                
                # Show dashboard notes if they exist
                note_content = get_dash_note(row)
                if note_content and note_content != "-":
                    with st.expander(f"📝 Topic Context: {row['topic']}", expanded=False):
                        st.markdown(note_content)
                
                st.divider()

