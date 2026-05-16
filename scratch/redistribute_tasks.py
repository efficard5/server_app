
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add the server_app directory to the path
sys.path.append('/home/effica/server_app')

from services.milestone_service import load_planned_milestones, save_single_milestone, remove_milestone

def get_milestone_id(date_str):
    if not date_str or date_str == 'None':
        return 'M7'
    
    try:
        dt = pd.to_datetime(date_str).tz_localize(None)
    except:
        return 'M7'
        
    # Ranges
    if datetime(2026, 5, 15) <= dt <= datetime(2026, 5, 17):
        return 'M7'
    elif datetime(2026, 5, 18) <= dt <= datetime(2026, 5, 24):
        return 'M8'
    elif datetime(2026, 5, 25) <= dt <= datetime(2026, 5, 31):
        return 'M10'
    elif datetime(2026, 6, 1) <= dt <= datetime(2026, 6, 7):
        return 'M11'
    elif datetime(2026, 6, 8) <= dt <= datetime(2026, 6, 13):
        return 'M12'
    
    return 'M7' # Default to M7 if outside ranges (per user's description "added all in M7")

def main():
    milestones = load_planned_milestones()
    if 'M7' not in milestones:
        print("Error: Milestone M7 not found.")
        return

    m7_data = milestones['M7']
    all_tasks = m7_data.get('tasks', {})
    
    print(f"Total tasks in M7: {len(all_tasks)}")
    
    # New milestones data
    # We copy the project context and other metadata from M7
    new_milestones = {
        'M8': {'name': 'M8', 'project_context': m7_data.get('project_context'), 'tasks': {}, 'milestone_errors': {}, 'completed': False, 'progress_increase': 0},
        'M10': {'name': 'M10', 'project_context': m7_data.get('project_context'), 'tasks': {}, 'milestone_errors': {}, 'completed': False, 'progress_increase': 0},
        'M11': {'name': 'M11', 'project_context': m7_data.get('project_context'), 'tasks': {}, 'milestone_errors': {}, 'completed': False, 'progress_increase': 0},
        'M12': {'name': 'M12', 'project_context': m7_data.get('project_context'), 'tasks': {}, 'milestone_errors': {}, 'completed': False, 'progress_increase': 0}
    }
    
    remaining_m7_tasks = {}
    
    for tid, task in all_tasks.items():
        start_date = task.get('start_date')
        target_mid = get_milestone_id(start_date)
        
        if target_mid == 'M7':
            remaining_m7_tasks[tid] = task
        else:
            new_milestones[target_mid]['tasks'][tid] = task
            # Also move corresponding errors if any
            m7_errors = m7_data.get('milestone_errors', {})
            for eid, error in m7_errors.items():
                if tid in error.get('task_ids', []):
                    new_milestones[target_mid]['milestone_errors'][eid] = error

    # Update M7
    m7_data['tasks'] = remaining_m7_tasks
    # Clean up errors in M7 (remove those that were moved)
    moved_error_ids = set()
    for mid in ['M8', 'M10', 'M11', 'M12']:
        moved_error_ids.update(new_milestones[mid]['milestone_errors'].keys())
    
    m7_data['milestone_errors'] = {eid: err for eid, err in m7_data.get('milestone_errors', {}).items() if eid not in moved_error_ids}
    
    # Save updates
    print(f"Updating M7: {len(remaining_m7_tasks)} tasks remaining.")
    save_single_milestone('M7', m7_data)
    
    for mid, data in new_milestones.items():
        if len(data['tasks']) > 0:
            print(f"Creating/Updating {mid}: {len(data['tasks'])} tasks.")
            save_single_milestone(mid, data)
        else:
            print(f"Skipping {mid}: No tasks found for this range.")

if __name__ == "__main__":
    main()
