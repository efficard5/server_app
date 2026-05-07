# ui/pages/milestones.py
import streamlit as st
import pandas as pd
from services.milestone_service import (
    load_planned_milestones, 
    save_single_milestone, 
    remove_milestone,
    get_milestone_topic_increases
)
from services.notes_service import load_notes, upsert_note
import json
import plotly.express as px
from datetime import datetime, timedelta
import uuid



def render(ctx: dict) -> None:
    milestones = ctx["milestones"]
    projects = ctx["projects"]
    topics = ctx["topics"]
    
    st.title("🚩 Planned Milestones")
    st.markdown("Manage major milestones and their progress contributions.")

    # --- 1. GANTT CHART VIEW ---
    show_gantt = st.toggle("📊 View Task Timeline (Gantt)", value=False)
    if show_gantt:
        gantt_data = []
        for mid, info in milestones.items():
            m_tasks = info.get("tasks", {})
            if not m_tasks:
                # Fallback to milestone dates if no tasks
                start = info.get("from_date")
                end = info.get("to_date")
                if start and end:
                    gantt_data.append(dict(
                        Task=f"MS: {mid}",
                        Start=start,
                        Finish=end,
                        Milestone=mid,
                        Status="Completed" if info.get("completed") else "Planned"
                    ))
                continue
            
            for tid, tinfo in m_tasks.items():
                start = tinfo.get("start_date")
                end = tinfo.get("end_date")
                if not start or not end: continue
                gantt_data.append(dict(
                    Task=tinfo.get("name"),
                    Start=start,
                    Finish=end,
                    Milestone=mid,
                    Status="Completed" if info.get("completed") else "Planned"
                ))
        
        if gantt_data:
            df_gantt = pd.DataFrame(gantt_data)
            # Ensure Start is datetime for correct sorting
            df_gantt['Start'] = pd.to_datetime(df_gantt['Start'])
            df_gantt = df_gantt.sort_values(by='Start')
            
            fig_gantt = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Task", color="Status", 
                                    hover_data=["Milestone"],
                                    color_discrete_map={"Completed": "#2ecc71", "Planned": "#3498db"},
                                    title="Milestone Task Timeline")
            fig_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_gantt, use_container_width=True)
        else:
            st.info("No tasks with dates found to show on Gantt.")
    
    st.divider()

    # --- 2. ADD NEW MILESTONE ---
    with st.expander("➕ Add New Milestone", expanded=False):
        m_row1 = st.columns([3, 1, 1, 1.5])
        new_m_name = m_row1[0].text_input("Milestone Name", key="nm_name")
        new_m_time = m_row1[1].number_input("Hours Needed", min_value=0.0, step=0.5, value=0.0, key="nm_time")
        new_m_start = m_row1[2].date_input("From Date", key="nm_start")
        new_m_end = m_row1[3].date_input("To Date", key="nm_end")
        
        new_m_project = st.selectbox("Project Context", projects, key="nm_project")
        new_m_desc = st.text_area("Description / Milestone Strategy", key="nm_desc")
        
        # Topic Progress Increases
        with st.expander("📈 Topic Progress Contribution (Click to set %)", expanded=False):
            nm_proj_topics = ctx["registry"].get(new_m_project, [])
            nm_topic_increases = {}
            if nm_proj_topics:
                t_cols = st.columns(min(len(nm_proj_topics), 4))
                for ti, tname in enumerate(nm_proj_topics):
                    col = t_cols[ti % 4]
                    nm_topic_increases[tname] = col.number_input(f"+% {tname}", 0.0, 100.0, 0.0, key=f"nm_t_{tname}")
            else:
                st.info("Select a project with topics to set progress increases.")

        if st.button("💾 Save Milestone", type="primary", use_container_width=True):
            if not new_m_name:
                st.error("Please enter a milestone name.")
            else:
                new_mil = {
                    "project_context": new_m_project,
                    "name": new_m_name,
                    "description": new_m_desc,
                    "time_needed": new_m_time,
                    "from_date": new_m_start.strftime("%Y-%m-%d"),
                    "to_date": new_m_end.strftime("%Y-%m-%d"),
                    "completed": False,
                    "progress_increase": nm_topic_increases,
                    "tasks": {}
                }
                save_single_milestone(new_m_name, new_mil)
                st.success(f"Milestone '{new_m_name}' added!")
                st.rerun()

    st.divider()

    # --- 3. MILESTONE LIST ---
    st.subheader("📋 Active Milestones")
    
    active_mils = {mid: info for mid, info in milestones.items() if not info.get("completed", False)}
    completed_mils = {mid: info for mid, info in milestones.items() if info.get("completed", False)}

    if not active_mils and not completed_mils:
        st.info("No milestones found.")
        return

    for mid, info in active_mils.items():
        with st.container():
            h1, h2, h3, h4 = st.columns([5, 1.2, 0.9, 0.9])
            h1.markdown(f"### 🎯 {mid}")
            
            if h2.checkbox("Completed", value=False, key=f"done_{mid}"):
                info["completed"] = True
                save_single_milestone(mid, info)
                st.rerun()
            
            edit_key = f"edit_m_{mid}"
            if edit_key not in st.session_state: st.session_state[edit_key] = False
            
            if h3.button("✏️", key=f"btn_e_{mid}"):
                st.session_state[edit_key] = not st.session_state[edit_key]
                st.rerun()
                
            if h4.button("🗑️", key=f"btn_d_{mid}"):
                remove_milestone(mid)
                st.rerun()

            if st.session_state[edit_key]:
                # Inline Editor
                ec1, ec2, ec3 = st.columns([3, 1, 1])
                e_name = ec1.text_input("Name", value=mid, key=f"en_{mid}")
                e_time = ec2.number_input("Hours", value=float(info.get("time_needed", 0)), key=f"et_{mid}")
                e_proj = ec3.selectbox("Project", projects, index=projects.index(info["project_context"]) if info["project_context"] in projects else 0, key=f"ep_{mid}")
                
                ed1, ed2 = st.columns(2)
                e_start = ed1.date_input("From", value=datetime.strptime(info.get("from_date", "2024-01-01"), "%Y-%m-%d"), key=f"es_{mid}")
                e_end = ed2.date_input("To", value=datetime.strptime(info.get("to_date", "2024-01-01"), "%Y-%m-%d"), key=f"ee_{mid}")
                
                e_desc = st.text_area("Description", value=info.get("description", ""), key=f"edesc_{mid}")
                
                if st.button("💾 Apply Changes", key=f"save_e_{mid}"):
                    if not e_name:
                        st.error("Name cannot be empty.")
                    else:
                        updated_info = info.copy()
                        updated_info.update({
                            "name": e_name,
                            "project_context": e_proj,
                            "time_needed": e_time,
                            "from_date": e_start.strftime("%Y-%m-%d"),
                            "to_date": e_end.strftime("%Y-%m-%d"),
                            "description": e_desc
                        })
                        # If name changed, delete old and save new
                        if e_name != mid:
                            remove_milestone(mid)
                        save_single_milestone(e_name, updated_info)
                        st.session_state[edit_key] = False
                        st.rerun()
            else:
                st.markdown(f"**Description:** {info.get('description', 'No description provided.')}")
                st.caption(f"📅 {info.get('from_date')} to {info.get('to_date')} | ⏳ {info.get('time_needed')} Hours | 🌐 {info.get('project_context')}")
                
                # Show topic increases
                inc = get_milestone_topic_increases(info)
                with st.expander("📈 Topic Progress Contribution", expanded=False):
                    edit_inc_key = f"edit_inc_{mid}"
                    if edit_inc_key not in st.session_state: st.session_state[edit_inc_key] = False
                    
                    if not st.session_state[edit_inc_key]:
                        if inc:
                            st.markdown(", ".join([f"**{k}**: +{v}%" for k, v in inc.items()]))
                        else:
                            st.info("No contributions set.")
                        if st.button("✏️ Edit Progress", key=f"btn_edit_inc_{mid}"):
                            st.session_state[edit_inc_key] = True
                            st.rerun()
                    else:
                        nm_proj_topics = ctx["registry"].get(info["project_context"], [])
                        updated_inc = {}
                        if nm_proj_topics:
                            t_cols = st.columns(min(len(nm_proj_topics), 4))
                            for ti, tname in enumerate(nm_proj_topics):
                                col = t_cols[ti % 4]
                                current_val = float(inc.get(tname, 0.0))
                                updated_inc[tname] = col.number_input(f"+% {tname}", 0.0, 100.0, current_val, key=f"edit_t_{mid}_{tname}")
                        
                        save_col1, save_col2 = st.columns(2)
                        if save_col1.button("💾 Save Progress", key=f"save_inc_{mid}"):
                            info["progress_increase"] = updated_inc
                            save_single_milestone(mid, info)
                            st.session_state[edit_inc_key] = False
                            st.rerun()
                        if save_col2.button("Cancel", key=f"cancel_inc_{mid}"):
                            st.session_state[edit_inc_key] = False
                            st.rerun()
                
                # ── Milestone Tasks ──
                m_tasks = info.get("tasks", {})
                
                with st.expander("📋 Manage Tasks", expanded=False):
                    if m_tasks:
                        for t_id, t_info in m_tasks.items():
                            edit_task_key = f"edit_task_{t_id}"
                            if edit_task_key not in st.session_state: st.session_state[edit_task_key] = False
                            
                            if st.session_state[edit_task_key]:
                                with st.form(key=f"form_edit_task_{t_id}"):
                                    et_name = st.text_input("Task Name", value=t_info.get("name"))
                                    et_desc = st.text_area("Task Description", value=t_info.get("description"))
                                    etc1, etc2 = st.columns(2)
                                    et_start = etc1.date_input("Start Date", value=datetime.strptime(t_info.get("start_date", "2024-01-01"), "%Y-%m-%d"))
                                    et_end = etc2.date_input("End Date", value=datetime.strptime(t_info.get("end_date", "2024-01-01"), "%Y-%m-%d"))
                                    
                                    f_col1, f_col2 = st.columns(2)
                                    if f_col1.form_submit_button("💾 Update Task"):
                                        info["tasks"][t_id] = {
                                            "name": et_name,
                                            "description": et_desc,
                                            "start_date": et_start.strftime("%Y-%m-%d"),
                                            "end_date": et_end.strftime("%Y-%m-%d"),
                                            "errors": t_info.get("errors", {})
                                        }
                                        save_single_milestone(mid, info)
                                        st.session_state[edit_task_key] = False
                                        st.rerun()
                                    if f_col2.form_submit_button("Cancel"):
                                        st.session_state[edit_task_key] = False
                                        st.rerun()
                            else:
                                tc1, tc2, tc3 = st.columns([8, 1, 1])
                                tc1.markdown(f"**{t_info.get('name')}** ({t_info.get('start_date')} to {t_info.get('end_date')})")
                                if tc2.button("✏️", key=f"btn_edit_t_{t_id}"):
                                    st.session_state[edit_task_key] = True
                                    st.rerun()
                                if tc3.button("🗑️", key=f"btn_del_t_{t_id}"):
                                    del info["tasks"][t_id]
                                    save_single_milestone(mid, info)
                                    st.rerun()
                                
                                if t_info.get('description'):
                                    st.caption(t_info.get('description'))
                            
                            t_errors = t_info.get("errors", {})
                            if t_errors:
                                for e_id, e_info in t_errors.items():
                                    ec1, ec2 = st.columns([10, 1])
                                    ec1.markdown(f"> ⚠️ **{e_info.get('error_name')}**: {e_info.get('description')}  \n> *(Time impact: {e_info.get('time_variance')} hrs | Checkpoint: {e_info.get('checkpoint')})*")
                                    if ec2.button("🗑️", key=f"btn_del_e_{e_id}", help="Delete Issue"):
                                        del info["tasks"][t_id]["errors"][e_id]
                                        save_single_milestone(mid, info)
                                        st.rerun()
                            st.divider()
                    else:
                        st.info("No tasks added yet.")
                    
                    st.markdown("**Add New Task**")
                    with st.form(key=f"form_add_task_{mid}"):
                        t_name = st.text_input("Task Name")
                        t_desc = st.text_area("Task Description")
                        tc1, tc2 = st.columns(2)
                        t_start = tc1.date_input("Start Date")
                        t_end = tc2.date_input("End Date")
                        if st.form_submit_button("💾 Save Task", use_container_width=True):
                            if t_name:
                                new_t_id = str(uuid.uuid4())
                                if "tasks" not in info: info["tasks"] = {}
                                info["tasks"][new_t_id] = {
                                    "name": t_name,
                                    "description": t_desc,
                                    "start_date": t_start.strftime("%Y-%m-%d"),
                                    "end_date": t_end.strftime("%Y-%m-%d"),
                                    "errors": {}
                                }
                                save_single_milestone(mid, info)
                                st.rerun()
                            else:
                                st.error("Task Name is required.")

                # ── Add Error to Task ──
                with st.expander("⚠️ Add Error / Issue to Task", expanded=False):
                    if not m_tasks:
                        st.warning("Please add a task first before adding an error.")
                    else:
                        with st.form(key=f"form_add_error_{mid}"):
                            task_options = {t_info["name"]: t_id for t_id, t_info in m_tasks.items()}
                            sel_task_name = st.selectbox("Select Task", list(task_options.keys()))
                            
                            e_name = st.text_input("Error / Issue Name")
                            e_desc = st.text_area("Description")
                            ec1, ec2 = st.columns(2)
                            e_time = ec1.text_input("Time May Vary (e.g., +2 Hrs)", value="0")
                            e_check = ec2.text_input("Check Point")
                            
                            if st.form_submit_button("💾 Save Error", use_container_width=True):
                                if e_name and sel_task_name:
                                    t_id = task_options[sel_task_name]
                                    new_e_id = str(uuid.uuid4())
                                    if "errors" not in info["tasks"][t_id]:
                                        info["tasks"][t_id]["errors"] = {}
                                    info["tasks"][t_id]["errors"][new_e_id] = {
                                        "error_name": e_name,
                                        "description": e_desc,
                                        "time_variance": e_time,
                                        "checkpoint": e_check
                                    }
                                    save_single_milestone(mid, info)
                                    st.rerun()
                                else:
                                    st.error("Error Name is required.")
            
            st.divider()


    if completed_mils:
        with st.expander("✅ Show Completed Milestones", expanded=False):
            for mid, info in completed_mils.items():
                st.markdown(f"**{mid}** - {info.get('project_context')} (Completed)")
                if st.button("Undo Completion", key=f"undo_{mid}"):
                    info["completed"] = False
                    save_single_milestone(mid, info)
                    st.rerun()

