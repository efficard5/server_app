# ui/pages/dashboard.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import json
import uuid
from services.task_service import aggregate_topic_completion

from services.milestone_service import get_planned_topic_adjustments
from services.storage_service import save_file_to_server, add_link_to_server, get_files_for_topic, remove_file
from services.notes_service import load_notes, save_notes
from utils.formatters import format_bullet_html, format_bullet_markdown


def render(ctx: dict) -> None:
    df = ctx["df"]
    projects = ctx["projects"]
    registry = ctx["registry"]
    
    st.title("R&D Project Overview & Analytics")
    
    # --- UI Component: Topic Files Helper ---
    def render_topic_files(t_proj, t_topic, btn_key=""):
        current_user = st.session_state.get("auth_name", "Unknown")
        is_admin = st.session_state.get("role") == "Admin"

        with st.popover("📂 Topic Files", use_container_width=True):
            st.markdown(f"**Files & Links for {t_topic}**")
            
            # 1. Upload/Add Section
            up_type = st.radio("Type", ["File", "Link"], horizontal=True, key=f"uptype_{btn_key}_{t_topic}")
            up_note = st.text_input("Note (Optional)", key=f"upnote_{btn_key}_{t_topic}")
            
            if up_type == "File":
                up_file = st.file_uploader("Upload Document", key=f"upfile_{btn_key}_{t_topic}")
                if st.button("💾 Save File", key=f"btn_up_{btn_key}_{t_topic}", use_container_width=True):
                    if up_file:
                        success, error = save_file_to_server(
                            up_file, t_proj, t_topic, 
                            note=up_note, 
                            uploaded_by=current_user
                        )
                        if success:
                            st.success("File saved to Server Storage!")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {error}")
            else:
                up_link = st.text_input("URL Link", key=f"uplink_{btn_key}_{t_topic}")
                if st.button("🔗 Add Link", key=f"btn_link_{btn_key}_{t_topic}", use_container_width=True):
                    if up_link:
                        success, error = add_link_to_server(t_proj, t_topic, up_link, note=up_note)
                        if success:
                            st.success("Link added!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add link: {error}")

            st.divider()
            # 2. List Section (From DB)
            user_filter = None if is_admin else current_user
            all_items = get_files_for_topic(t_proj, t_topic, user_filter=user_filter)

            if all_items:
                for item in all_items:
                    # item: (id, file_name, local_path, url, note, type, uploaded_by)
                    i_id, i_name, i_path, i_url, i_note, i_type, i_owner = item
                    
                    col_file, col_del = st.columns([4, 1])
                    with col_file:
                        label = f"{'📄' if i_type == 'File' else '🔗'} {i_name}"
                        if i_note: label += f" (*{i_note}*)"
                        
                        if i_type == "Link":
                            st.markdown(f"[{label}]({i_url})")
                        else:
                            st.markdown(f"**{label}**")
                            st.caption(f"Owner: {i_owner}")
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_{btn_key}_{i_id}"):
                            if remove_file(i_id, i_path):
                                st.rerun()

            else:
                st.info("No files or links yet.")

    
    # 1. Project Selection
    if not projects:
        st.info("👋 Welcome! It looks like you haven't created any projects yet.")
        st.write("To see your dashboard in action:")
        st.markdown("""
        1. Go to **Tasks & Milestones** in the sidebar.
        2. Expand **Add New Task**.
        3. Enter a project name and at least one task.
        4. Come back here to see the analytics!
        """)
        return

    # Find index of "Truck unloading Project" for default selection
    default_ix = 0
    if "Truck unloading Project" in projects:
        default_ix = projects.index("Truck unloading Project")
    elif "Truck Unloading Project" in projects:
        default_ix = projects.index("Truck Unloading Project")
        
    selected_project = st.selectbox("🌐 Select View Context (Project Filter)", projects, index=default_ix)
    st.divider()

    # 2. Filter data
    proj_df = df[df["project"] == selected_project]
    proj_topics = registry.get(selected_project, [])

    if not proj_topics:
        st.info(f"No active topics found for '{selected_project}'.")
        return

    st.subheader(f"Dashboard » {selected_project}")

    # --- PHASE & FOCUS SELECTION ---
    notes_db = ctx.get("notes_db", {})
    if selected_project not in notes_db:
        notes_db[selected_project] = {"Topics": {}, "Project_Issues": "", "Project_Plans": "", "Phases": "{}"}
    proj_notes = notes_db[selected_project]
    
    phases = {}
    try:
        phases = json.loads(proj_notes.get("Phases", "{}"))
    except:
        phases = {}
        
    pcol1, pcol2 = st.columns([3, 1])
    phase_opts = ["Show All Topics"] + list(phases.keys()) + ["➕ Add Focus Area/Phase"]
    selected_phase = pcol1.selectbox("🎯 Select Project Phase / Focus Area", phase_opts)
    
    active_topics = proj_topics
    if selected_phase == "➕ Add Focus Area/Phase":
        with st.form("new_phase_form"):
            new_p_name = st.text_input("Phase/Focus Name (e.g., Robot Integration)")
            new_p_topics = st.multiselect("Select Topics", proj_topics)
            if st.form_submit_button("💾 Create Phase"):
                if new_p_name:
                    phases[new_p_name] = new_p_topics
                    proj_notes["Phases"] = json.dumps(phases)
                    save_notes(notes_db)
                    st.rerun()
    elif selected_phase != "Show All Topics":
        active_topics = phases.get(selected_phase, [])
        with pcol1.popover("⚙️ Edit Phase Topics"):
            updated_p_topics = st.multiselect("Modify Topics for this Focus Area", proj_topics, default=active_topics)
            
            c1, c2 = st.columns(2)
            if c1.button("💾 Save Changes", use_container_width=True):
                phases[selected_phase] = updated_p_topics
                proj_notes["Phases"] = json.dumps(phases)
                save_notes(notes_db)
                st.rerun()
                
            if c2.button("🗑️ Delete Phase", type="secondary", use_container_width=True):
                del phases[selected_phase]
                proj_notes["Phases"] = json.dumps(phases)
                save_notes(notes_db)
                st.rerun()

    # --- DATA CALCULATION ---
    milestones = ctx.get("milestones", {})
    milestone_adjustments = get_planned_topic_adjustments(selected_project, milestones, proj_topics)
    
    # Calculate progress for all active topics to show summary
    topic_progress_values = {}
    for topic in proj_topics:
        topic_tasks = proj_df[proj_df["topic"] == topic]
        base_comp = aggregate_topic_completion(topic_tasks)
        milestone_comp = milestone_adjustments.get(topic, 0.0)
        topic_progress_values[topic] = min(100.0, base_comp + milestone_comp)
    
    if selected_phase != "Show All Topics" and active_topics:
        phase_avg = sum(topic_progress_values.get(t, 0) for t in active_topics) / len(active_topics)
        pcol2.metric(f"📈 {selected_phase}", f"{phase_avg:.1f}%")
        
        # --- PHASE MILESTONES (Navigation Buttons) ---
        phase_mils = [mid for mid, info in milestones.items() if info.get("phase_context") == selected_phase and not info.get("completed")]
        if phase_mils:
            st.caption(f"🚀 Active Milestones in {selected_phase}:")
            m_btn_cols = st.columns(min(len(phase_mils), 5))
            for i, mid in enumerate(phase_mils):
                if m_btn_cols[i % 5].button(f"🎯 {mid}", key=f"dash_ms_{mid}", use_container_width=True):
                    st.session_state.current_page = "Planned Milestones"
                    st.rerun()
    else:
        # Overall project progress as fallback for pcol2
        if topic_progress_values:
            overall_avg = sum(topic_progress_values.values()) / len(topic_progress_values)
            pcol2.metric("Overall Progress", f"{overall_avg:.1f}%")

    st.divider()

    # 3. TOP GAUGES
    display_topics = active_topics if active_topics else proj_topics
    cols = st.columns(max(len(display_topics), 1))
    t_font_size = 13 if len(display_topics) <= 4 else 11
    for i, topic in enumerate(display_topics):
        avg_comp = topic_progress_values.get(topic, 0.0)


        with cols[i]:
            # Circular Gauge (Half-rounded style) - Adjusted for better single-row fit
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_comp,
                title={'text': f"<b>{topic}</b>", 'font': {'size': t_font_size}},
                number={'font': {'size': 20}, 'suffix': "%"},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#2ecc71"},
                    'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "#e0e0e0",
                    'shape': 'angular'
                }
            ))
            fig.update_layout(
                height=150, 
                margin=dict(l=10, r=10, t=40, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # Topic Files Button
            render_topic_files(selected_project, topic, btn_key="gauge")


    st.divider()

    # 4. Topic Progression Bar Chart (Horizontal)
    st.subheader(f"Topic Progression » {selected_project}")
    if not proj_df.empty:
        # Calculate progress per topic (using the values we already calculated)
        prog_rows = [{"topic": t, "completion_pct": topic_progress_values.get(t, 0.0)} for t in display_topics]
        
        prog_df = pd.DataFrame(prog_rows)

        fig_bar = px.bar(
            prog_df, 
            y="topic", 
            x="completion_pct",
            color="topic", 
            orientation='h',
            text_auto='.1f',
            labels={"completion_pct": "Avg Completion %", "topic": "System/Topic"}
        )
        fig_bar.update_layout(xaxis=dict(range=[0, 105]), height=max(200, len(proj_topics) * 40))
        fig_bar.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    col_hdr, col_tgl = st.columns([4, 1])
    col_hdr.subheader("Project Context & Analytics")
    edit_notes = col_tgl.toggle("📝 Enable Notes Editor", value=False)
    
    # Use existing notes_db loaded at top
    proj_notes = notes_db[selected_project]

    def parse_note_json(text):
        try:
            d = json.loads(text)
            if isinstance(d, dict): return d
        except: pass
        return {"Major": str(text or ""), "Problematic": "", "Future": ""}

    col_l, col_r = st.columns([3, 1])
    with col_l:
        ctx_header_l, ctx_header_r = st.columns([2, 1])
        ctx_header_l.markdown("**Topic Context Library**")
        expand_all = ctx_header_r.toggle("Unfold All Topic Details", value=False)
        
        for i in range(0, len(display_topics), 3):
            grid_cols = st.columns(3)
            for j, topic in enumerate(display_topics[i:i+3]):
                with grid_cols[j]:
                    raw_note = proj_notes.get("Topics", {}).get(topic, "")
                    tn = parse_note_json(raw_note)
                    
                    if edit_notes:
                        st.markdown(f"#### 📦 {topic}")
                        new_maj = st.text_area("Completed tasks", tn.get("Major", ""), key=f"nm_{topic}", height=80)
                        new_prob = st.text_area("In progress", tn.get("Problematic", ""), key=f"np_{topic}", height=80)
                        new_fut = st.text_area("Future Phase", tn.get("Future", ""), key=f"nf_{topic}", height=80)
                        
                        # Store back as JSON string
                        proj_notes["Topics"][topic] = json.dumps({
                            "Major": new_maj,
                            "Problematic": new_prob,
                            "Future": new_fut
                        })
                    else:
                        with st.expander(f"📦 {topic}", expanded=expand_all):
                            maj_html = format_bullet_html(tn.get("Major", ""))
                            prob_html = format_bullet_html(tn.get("Problematic", ""))
                            fut_html = format_bullet_html(tn.get("Future", ""))
                            st.markdown(f"**Completed:**{maj_html}", unsafe_allow_html=True)
                            st.markdown(f"**In Progress:**{prob_html}", unsafe_allow_html=True)
                            st.markdown(f"**Future:**{fut_html}", unsafe_allow_html=True)

    with col_r:
        if edit_notes:
            st.markdown("#### ⚠️ Issues & Plans")
            new_iss = st.text_area("Project Issues", proj_notes.get("Project_Issues", ""), height=150)
            new_pl = st.text_area("Further Plans", proj_notes.get("Project_Plans", ""), height=150)
            proj_notes["Project_Issues"] = new_iss
            proj_notes["Project_Plans"] = new_pl
            
            if st.button("💾 Save All Notes", type="primary", use_container_width=True):
                save_notes(notes_db)
                st.toast("✅ Project Notes saved to Database!", icon="💾")
                import time
                time.sleep(0.5)
                st.rerun()
        else:
            with st.expander("Project Issues", expanded=False):
                st.markdown(format_bullet_markdown(proj_notes.get("Project_Issues", "")))
            with st.expander("Further Plans", expanded=False):
                st.markdown(format_bullet_markdown(proj_notes.get("Project_Plans", "")))
