# ui/pages/dashboard.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from services.task_service import aggregate_topic_completion

def render(ctx: dict) -> None:
    df = ctx["df"]
    projects = ctx["projects"]
    registry = ctx["registry"]
    
    st.title("📊 R&D Project Overview & Analytics")
    
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

    selected_project = st.selectbox("🌐 Select View Context (Project Filter)", projects)
    st.divider()

    # 2. Filter data
    proj_df = df[df["project"] == selected_project]
    proj_topics = registry.get(selected_project, [])

    if not proj_topics:
        st.info(f"No active topics found for '{selected_project}'.")
        return

    st.subheader(f"Dashboard » {selected_project}")

    # 3. TOP GAUGES (Matching Original UI)
    cols = st.columns(max(len(proj_topics), 1))
    for i, topic in enumerate(proj_topics):
        topic_tasks = proj_df[proj_df["topic"] == topic]
        avg_comp = aggregate_topic_completion(topic_tasks)

        with cols[i]:
            # Circular Gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_comp,
                title={'text': f"<b>{topic}</b>", 'font': {'size': 14}},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#2ecc71"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "#e0e0e0"
                }
            ))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 4. Topic Progression Bar Chart (Horizontal)
    st.subheader(f"Topic Progression » {selected_project}")
    if not proj_df.empty:
        # Calculate progress per topic
        prog_rows = []
        for topic in proj_topics:
            t_df = proj_df[proj_df["topic"] == topic]
            prog_rows.append({"topic": topic, "completion_pct": aggregate_topic_completion(t_df)})
        
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

    # 5. Topic Context Library (Notes)
    from utils.formatters import format_bullet_html, format_bullet_markdown
    from services.notes_service import load_notes, save_notes
    import json

    col_hdr, col_tgl = st.columns([4, 1])
    col_hdr.subheader("Project Context & Analytics")
    edit_notes = col_tgl.toggle("📝 Enable Notes Editor", value=False)
    
    notes_db = load_notes()
    if selected_project not in notes_db:
        notes_db[selected_project] = {
            "Topics": {},
            "Project_Issues": "",
            "Project_Plans": ""
        }
    proj_notes = notes_db[selected_project]

    def parse_note_json(text):
        try:
            d = json.loads(text)
            if isinstance(d, dict): return d
        except: pass
        return {"Major": str(text or ""), "Problematic": "", "Future": ""}

    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.markdown("**Topic Context Library**")
        for i in range(0, len(proj_topics), 3):
            grid_cols = st.columns(3)
            for j, topic in enumerate(proj_topics[i:i+3]):
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
                        maj_html = format_bullet_html(tn.get("Major", ""))
                        prob_html = format_bullet_html(tn.get("Problematic", ""))
                        fut_html = format_bullet_html(tn.get("Future", ""))
                        st.markdown(f"""
                        <div class="card">
                            <h4 style='margin-bottom:10px;'>📦 {topic}</h4>
                            <p style='margin-bottom:2px;'><b>Completed:</b></p>{maj_html}
                            <p style='margin-bottom:2px;'><b>In Progress:</b></p>{prob_html}
                            <p style='margin-bottom:2px;'><b>Future:</b></p>{fut_html}
                        </div>
                        """, unsafe_allow_html=True)

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
            st.markdown("#### ⚠️ Project Issues")
            st.markdown(format_bullet_markdown(proj_notes.get("Project_Issues", "")))
            st.markdown("#### 🚀 Further Plans")
            st.markdown(format_bullet_markdown(proj_notes.get("Project_Plans", "")))
