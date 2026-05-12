# migrate_competitors.py
import json
import os
from db.repositories.competitor_repo import save_competitor_category

JSON_PATH = "/home/effica/weekly_dashboard/data/competitors.json"

def migrate():
    if not os.path.exists(JSON_PATH):
        print(f"No file found at {JSON_PATH}")
        return

    print(f"Reading data from {JSON_PATH}...")
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    for category, rows in data.items():
        if not rows:
            continue
        
        # Determine columns from the first row
        columns = list(rows[0].keys())
        print(f"Migrating category: {category} ({len(rows)} rows, {len(columns)} columns)")
        
        save_competitor_category(category, columns, rows)
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
