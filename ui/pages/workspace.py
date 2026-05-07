# ui/pages/workspace.py
import streamlit as st
import pandas as pd
import plotly.express as px

def render(ctx: dict) -> None:
    df = ctx["df"]
    projects = ctx["projects"]
    registry = ctx["registry"]
    
    st.header("Weekly Performance Analytics")
    
    # 1. Project & Topic Selection
    if not projects:
        st.info("📊 No project data available for performance analytics. Please create tasks first.")
        return

    sel_col1, sel_col2 = st.columns(2)
    selected_project = sel_col1.selectbox("🌐 Select View Context (Project Filter)", projects)
    
    proj_topics = registry.get(selected_project, [])
    selected_topic = sel_col2.selectbox("🏷️ Select Topic Filter", ["All Topics"] + proj_topics)
    
    st.divider()
    
    # 2. Filter Data
    proj_df = df[df["project"] == selected_project]
    if selected_topic != "All Topics":
        proj_df = proj_df[proj_df["topic"] == selected_topic]
    
    if proj_df.empty:
        st.info("No data found for the selected project/topic.")
        return

    st.subheader(f"Week-by-Week Comparison » {selected_project}" + (f" » {selected_topic}" if selected_topic != "All Topics" else ""))
    
    # 3. Week Selection
    # Ensure week column exists and is numeric
    if "week" not in proj_df.columns:
        st.warning("Project data missing 'week' column.")
        return
        
    proj_weeks = sorted([int(w) for w in proj_df["week"].dropna().unique()])
    if not proj_weeks:
        proj_weeks = [1]
        
    st.caption("ℹ️ Select **two specific weeks** to compare side-by-side.")
    wcol1, wcol2 = st.columns(2)
    start_wk = wcol1.selectbox("📊 Week 1 (Select)", options=proj_weeks, index=0)
    end_wk = wcol2.selectbox("📊 Week 2 (Compare)", options=proj_weeks, index=len(proj_weeks)-1)

    # 4. Comparison Chart
    week_df_start = proj_df[proj_df["week"] == start_wk]
    week_df_end = proj_df[proj_df["week"] == end_wk]

    if not week_df_start.empty or not week_df_end.empty:
        frames = []
        if not week_df_start.empty:
            avg_s = week_df_start.groupby("topic")["completion_pct"].mean().reset_index() if selected_topic == "All Topics" else week_df_start.groupby("week")["completion_pct"].mean().reset_index()
            avg_s["Week_Label"] = f"Wk {start_wk}"
            frames.append(avg_s)
        
        if not week_df_end.empty and end_wk != start_wk:
            avg_e = week_df_end.groupby("topic")["completion_pct"].mean().reset_index() if selected_topic == "All Topics" else week_df_end.groupby("week")["completion_pct"].mean().reset_index()
            avg_e["Week_Label"] = f"Wk {end_wk}"
            frames.append(avg_e)
            
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            chart_col = "topic" if selected_topic == "All Topics" else "Week_Label"
            
            fig = px.bar(
                combined, 
                x="Week_Label" if selected_topic != "All Topics" else "topic", 
                y="completion_pct", 
                color="topic" if selected_topic == "All Topics" else "Week_Label",
                barmode="group",
                text_auto='.1f',
                labels={"completion_pct": "Avg Completion %", "Week_Label": "Project Week"}
            )
            fig.update_layout(yaxis=dict(range=[0, 100]), height=450)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active tasks found for the selected weeks.")
