
import os
import sys
import pandas as pd

# Add the server_app directory to the path
sys.path.append('/home/effica/server_app')

from services.milestone_service import load_planned_milestones

def main():
    milestones = load_planned_milestones()
    target_mids = ['M7', 'M8', 'M10', 'M11', 'M12']
    
    found_tasks = []
    
    for mid in target_mids:
        if mid not in milestones:
            print(f"Warning: Milestone {mid} not found.")
            continue
            
        tasks = milestones[mid].get('tasks', {})
        for tid, tinfo in tasks.items():
            found_tasks.append({
                'Milestone': mid,
                'Task Name': tinfo.get('name'),
                'Date': tinfo.get('start_date'),
                'Topic': tinfo.get('topic')
            })
            
    df = pd.DataFrame(found_tasks)
    if not df.empty:
        # Sort by date and topic
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by=['Date', 'Topic'])
        
        # Display tasks per day
        for date, group in df.groupby('Date'):
            print(f"\nDate: {date.strftime('%Y-%m-%d')}")
            for _, row in group.iterrows():
                print(f"  - [{row['Topic']}] {row['Task Name']} ({row['Milestone']})")
    else:
        print("No tasks found in M7-M12.")

if __name__ == "__main__":
    main()
