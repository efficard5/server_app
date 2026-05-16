
import os
import sys
import pandas as pd

# Add the server_app directory to the path so we can import modules
sys.path.append('/home/effica/server_app')

from services.milestone_service import load_planned_milestones
from services.task_service import load_data

def main():
    milestones = load_planned_milestones()
    print("--- Milestones ---")
    for mid, info in milestones.items():
        print(f"ID: {mid}, Name: {info.get('name')}, Project: {info.get('project_context')}")
    
    tasks_df = load_data()
    print("\n--- Tasks Summary ---")
    print(f"Total tasks: {len(tasks_df)}")
    if not tasks_df.empty:
        # Check if there's a milestone column
        cols = tasks_df.columns.tolist()
        print(f"Columns: {cols}")
        
        # Look for m7
        # Note: The user said they added tasks in m7 milestone. 
        # In planned milestones, tasks are usually nested inside the milestone object.
        # But Gantt tasks might also have a reference.
        
        for mid, info in milestones.items():
            tasks = info.get('tasks', {})
            print(f"Milestone {mid} has {len(tasks)} tasks.")
            if len(tasks) > 0:
                # Sample task
                first_task_id = list(tasks.keys())[0]
                print(f"  Sample task: {tasks[first_task_id].get('task_name')} - Date: {tasks[first_task_id].get('start_date')}")

if __name__ == "__main__":
    main()
