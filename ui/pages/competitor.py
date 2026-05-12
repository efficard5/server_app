# ui/pages/competitor.py
import streamlit as st
import pandas as pd
from services.competitor_service import (
    load_competitor_data,
    save_competitor_data,
    save_category,
    remove_category,
    get_category_columns
)

def render(ctx: dict) -> None:
    st.title("Competitor Benchmarking")
    st.markdown("Track and compare competitor features, metrics, and market positioning.")
    
    comp_data = load_competitor_data()
    is_admin = st.session_state.role == "Admin"

    # --- 1. Admin: Add New Topic ---
    if is_admin:
        with st.expander("➕ Add New Benchmark Topic", expanded=False):
            c1, c2 = st.columns([2, 2])
            new_topic = c1.text_input("Topic Name", placeholder="e.g. SLAM Accuracy")
            new_cols_str = c2.text_input("Columns (comma separated)", value="Competitor, Value, Notes")
            
            if st.button("Create Benchmark Topic", type="primary", use_container_width=True):
                if new_topic:
                    if new_topic in comp_data:
                        st.error("This topic already exists.")
                    else:
                        col_list = [c.strip() for c in new_cols_str.split(",") if c.strip()]
                        if not col_list: col_list = ["Competitor", "Value"]
                        # Initialize with one empty row
                        empty_row = {c: "" for c in col_list}
                        save_category(new_topic, col_list, [empty_row])
                        st.success(f"Topic '{new_topic}' created!")
                        st.rerun()
                else:
                    st.error("Topic name is required.")

    st.divider()

    # --- 2. Display Topics ---
    if not comp_data:
        st.info("No competitor benchmarks found. Admins can add new topics above.")
        return

    for topic, rows in list(comp_data.items()):
        with st.expander(f"📊 {topic}", expanded=False):
            # Get current columns
            if rows:
                columns = list(rows[0].keys())
            else:
                columns = get_category_columns(topic)

            if is_admin:
                st.markdown("Edit the table below directly. Click **Save Changes** to apply.")
                
                # Filter out completely empty rows for the editor if they are just placeholders
                has_content = any(any(str(v).strip() for v in r.values()) for r in rows)
                df_topic = pd.DataFrame(rows) if has_content else pd.DataFrame(columns=columns)
                
                edited_df = st.data_editor(
                    df_topic, 
                    num_rows="dynamic", 
                    key=f"editor_{topic}", 
                    use_container_width=True,
                    hide_index=True
                )
                
                ec1, ec2 = st.columns([1, 1])
                if ec1.button("💾 Save Changes", key=f"save_btn_{topic}", use_container_width=True):
                    new_rows = edited_df.fillna("").to_dict(orient="records")
                    if not new_rows:
                        # Keep it alive with an empty row if all deleted
                        new_rows = [{c: "" for c in columns}]
                    save_category(topic, columns, new_rows)
                    st.success("Changes saved!")
                    st.rerun()
                
                if ec2.button("🗑️ Delete Topic", key=f"del_topic_{topic}", use_container_width=True, type="secondary"):
                    remove_category(topic)
                    st.success(f"Deleted {topic}")
                    st.rerun()

                # Column Management
                st.markdown("---")
                c_add, c_del = st.columns(2)
                
                new_col = c_add.text_input("Add Column", key=f"nc_{topic}", placeholder="Column Name")
                if c_add.button("➕ Add", key=f"nc_btn_{topic}"):
                    if new_col and new_col not in columns:
                        for r in rows: r[new_col] = ""
                        save_category(topic, columns + [new_col], rows)
                        st.rerun()
                
                del_col = c_del.selectbox("Delete Column", [""] + columns, key=f"dc_{topic}")
                if c_del.button("🗑️ Remove", key=f"dc_btn_{topic}"):
                    if del_col and del_col in columns:
                        if len(columns) > 1:
                            for r in rows: r.pop(del_col, None)
                            new_cols = [c for c in columns if c != del_col]
                            save_category(topic, new_cols, rows)
                            st.rerun()
                        else:
                            st.error("Cannot delete the last column.")
            else:
                # Employee View (Read Only)
                display_rows = [r for r in rows if any(str(v).strip() for v in r.values())]
                if display_rows:
                    st.table(pd.DataFrame(display_rows))
                else:
                    st.info("No data available for this topic yet.")

    st.divider()
