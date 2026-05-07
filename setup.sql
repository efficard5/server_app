-- setup.sql
-- Run this script in your PostgreSQL database to initialize the schema.

-- 1. Tasks (Gantt Chart / Project Tasks)
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project TEXT NOT NULL,
    task_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    employee TEXT,
    status TEXT,
    topic TEXT,
    week INTEGER DEFAULT 1,
    completion_pct INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Daily Tasks
CREATE TABLE IF NOT EXISTS daily_tasks (
    task_id TEXT PRIMARY KEY, -- Unique string/UUID
    date DATE NOT NULL,
    project TEXT,
    responsible_person TEXT,
    status TEXT,
    task_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document Metadata (formerly Google Drive docs)
CREATE TABLE IF NOT EXISTS drive_docs (
    id SERIAL PRIMARY KEY,
    project TEXT NOT NULL,
    topic TEXT NOT NULL,
    file_name TEXT,
    local_path TEXT, -- Path to file in /opt/server_app/uploads
    url TEXT,        -- External link
    note TEXT,
    type TEXT,       -- 'file' or 'url'
    uploaded_by TEXT, -- User who uploaded the file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project, topic, file_name)
);

-- 4. Employees (Auth)
CREATE TABLE IF NOT EXISTS employees (
    name TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'employee',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Project Notes
CREATE TABLE IF NOT EXISTS project_notes (
    project TEXT NOT NULL,
    topic TEXT NOT NULL,
    note_text TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project, topic)
);

-- 6. Milestones (JSON storage for flexibility)
CREATE TABLE IF NOT EXISTS milestones (
    milestone_id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Seed initial admin account
INSERT INTO employees (name, password, role) 
VALUES ('Admin', 'admin123', 'admin') 
ON CONFLICT (name) DO NOTHING;
