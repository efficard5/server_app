# scripts/migrate_to_postgres.py
import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv

# Path to your unzipped Drive data
SOURCE_PATH = "/home/effica/dash board docs/Industrial_Automation_PMO/data"

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.task_service import bulk_replace_tasks, bulk_replace_daily_tasks
from services.milestone_service import save_planned_milestones

def run_migration():
    print(f"🚀 Starting Migration from local folder: {SOURCE_PATH}")
    
    # 1. Migrate Tasks (Excel)
    task_file = os.path.join(SOURCE_PATH, "tasks.xlsx")
    if os.path.exists(task_file):
        df = pd.read_excel(task_file)
        
        # Mapping Excel Columns to DB Columns
        mapping = {
            "Project": "project",
            "Topic": "topic",
            "Task Name": "task_name",
            "Start Date": "start_date",
            "End Date": "end_date",
            "Employee": "employee",
            "Status": "status",
            "Completion %": "completion_pct"
        }
        
        # Ensure only existing columns are mapped
        available_cols = [c for c in mapping.keys() if c in df.columns]
        df = df[available_cols].rename(columns={k: mapping[k] for k in available_cols})
        
        # Clean completion column
        if "completion_pct" in df.columns:
            df["completion_pct"] = pd.to_numeric(df["completion_pct"], errors="coerce").fillna(0).astype(int)
        
        bulk_replace_tasks(df)
        print("✅ Tasks migrated.")

    # 2. Migrate Daily Tasks (Excel)
    daily_file = os.path.join(SOURCE_PATH, "daily_task_daywise.xlsx")
    if os.path.exists(daily_file):
        df_daily = pd.read_excel(daily_file)
        # Fix column names to match DB
        df_daily.columns = [c.lower().replace(" ", "_").replace("%", "pct") for c in df_daily.columns]
        # Only keep columns present in daily_tasks table
        daily_cols = ["task_id", "date", "project", "responsible_person", "status", "task_details"]
        df_daily = df_daily[[c for c in daily_cols if c in df_daily.columns]]
        
        bulk_replace_daily_tasks(df_daily)
        print("✅ Daily Tasks migrated.")

    # 3. Migrate Milestones (JSON)
    milestone_file = os.path.join(SOURCE_PATH, "planned_milestones.json")
    if os.path.exists(milestone_file):
        with open(milestone_file, "r") as f:
            milestones = json.load(f)
            save_planned_milestones(milestones)
            print("✅ Milestones migrated.")

    print("\n🏁 Local Migration Complete! You can now start the app.")

if __name__ == "__main__":
    run_migration()
