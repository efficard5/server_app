# ui/components/contribution_graph.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

def render_contribution_graph(ctx: dict):
    user = st.session_state.auth_name
    daily_df = ctx["daily_task_df"]
    milestones = ctx["milestones"]
    
    # 1. Employee & Topic Selection
    available_topics = ["All Topics"] + sorted(list(set(ctx["topics"])))
    employees = ctx["employees"]
    is_admin = st.session_state.role == "Admin"
    
    col1, col2 = st.columns(2)
    sel_topic = col1.selectbox("🎯 Topic:", available_topics)
    
    target_user = user
    if is_admin:
        sel_user = col2.selectbox("👤 View Activity for:", ["All Employees", "Admin (Self)"] + [e for e in employees if e != user])
        if sel_user == "All Employees":
            target_user = "All"
        elif sel_user == "Admin (Self)":
            target_user = user
        else:
            target_user = sel_user
    
    # 2. Filter Data and Ensure Date Types
    df = daily_df.copy()
    # Convert date column to date objects safely
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    
    # Filter for the target user
    if target_user == "All":
        user_tasks = df.copy()
        display_name = "All Employees"
    else:
        user_tasks = df[df["responsible_person"] == target_user].copy()
        display_name = target_user

    if user_tasks.empty:
        st.info(f"No activity recorded for **{display_name}** in the last 6 months.")
        return

    # 3. Determine Date Range (Last 6 Months or 1 Year)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180) # 6 months
    
    # 4. Process Status per Date
    date_status = {}
    current_d = start_date
    while current_d <= end_date:
        day_tasks = user_tasks[user_tasks["date"] == current_d]
        
        if day_tasks.empty:
            date_status[current_d] = "empty"
        else:
            # Filter by topic if selected
            is_relevant = True
            if sel_topic != "All Topics":
                # Check if any task on this day belongs to the selected topic
                is_relevant = False
                for _, t_row in day_tasks.iterrows():
                    mid = t_row.get("ms_ref")
                    tid = t_row.get("ms_task_ref")
                    if mid in milestones and tid in milestones[mid].get("tasks", {}):
                        if milestones[mid]["tasks"][tid].get("topic") == sel_topic:
                            is_relevant = True
                            break
            
            if not is_relevant:
                date_status[current_d] = "empty"
            else:
                # Check Completion
                all_done = True
                has_unsolved_error = False
                
                for _, t_row in day_tasks.iterrows():
                    done = str(t_row.get("completed_checkpoint", "")).lower() == "true"
                    # Safe float conversion
                    val = t_row.get("actual_pct_completion")
                    pct = float(val) if val and str(val).strip() != "" else (100.0 if done else 0.0)
                    if pct < 100.0:
                        all_done = False
                    
                    # Check for errors in milestone
                    mid = t_row.get("ms_ref")
                    tid = t_row.get("ms_task_ref")
                    if mid in milestones and tid:
                        m_errs = milestones[mid].get("milestone_errors", {})
                        for eid, einfo in m_errs.items():
                            if tid in einfo.get("task_ids", []) and not einfo.get("completed"):
                                has_unsolved_error = True
                                break
                
                if not all_done:
                    date_status[current_d] = "red"
                elif has_unsolved_error:
                    date_status[current_d] = "yellow"
                else:
                    date_status[current_d] = "green"
                    
        current_d += timedelta(days=1)

    # 5. Render Heatmap (HTML/CSS)
    # We'll use a CSS Grid
    st.markdown("""
    <style>
    .heatmap-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 20px;
        background: #1e1e1e;
        border-radius: 12px;
        border: 1px solid #333;
        overflow-x: auto;
    }
    .heatmap-grid {
        display: grid;
        grid-template-rows: repeat(7, 12px);
        grid-auto-flow: column;
        grid-auto-columns: 12px;
        gap: 4px;
    }
    .heatmap-cell {
        width: 12px;
        height: 12px;
        border-radius: 2px;
        transition: transform 0.2s;
    }
    .heatmap-cell:hover {
        transform: scale(1.5);
        z-index: 10;
        cursor: pointer;
    }
    .cell-empty { background: #2d2d2d; }
    .cell-green { background: #39d353; box-shadow: 0 0 5px #39d353; }
    .cell-yellow { background: #f1c40f; box-shadow: 0 0 5px #f1c40f; }
    .cell-red { background: #e74c3c; box-shadow: 0 0 5px #e74c3c; }
    
    .heatmap-legend {
        display: flex;
        gap: 15px;
        font-size: 12px;
        color: #888;
        margin-top: 10px;
        justify-content: flex-end;
    }
    .legend-item { display: flex; align-items: center; gap: 5px; }
    </style>
    """, unsafe_allow_html=True)
    
    grid_html = '<div class="heatmap-container"><div class="heatmap-grid">'
    
    current_d = start_date
    while current_d <= end_date:
        status = date_status.get(current_d, "empty")
        color_class = f"cell-{status}"
        grid_html += f'<div class="heatmap-cell {color_class}" title="{current_d}: {status}"></div>'
        current_d += timedelta(days=1)
    
    grid_html += '</div>'
    
    # Legend
    grid_html += """
    <div class="heatmap-legend">
        <div class="legend-item"><div class="heatmap-cell cell-green"></div> Completed</div>
        <div class="legend-item"><div class="heatmap-cell cell-yellow"></div> Pending Error</div>
        <div class="legend-item"><div class="heatmap-cell cell-red"></div> Not Done</div>
        <div class="legend-item"><div class="heatmap-cell cell-empty"></div> No Activity</div>
    </div>
    </div>
    """
    
    st.markdown(grid_html, unsafe_allow_html=True)
    st.caption(f"Daily Involvement Heatmap: **{display_name}** | Topic: **{sel_topic}**")
