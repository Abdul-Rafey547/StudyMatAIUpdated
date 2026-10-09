import sqlite3
import os

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database')
DATABASE_FILE = os.path.join(DATABASE_DIR, 'studymate.db')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db_connection():
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def init_db():
    conn = get_db_connection()
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # Safe migrations for existing tables
    c = conn.cursor()
    
    # Columns to check for tasks table
    task_columns = {
        'moodle_activity_id': 'TEXT',
        'cutoff_date': 'TEXT',
        'submission_status': "TEXT DEFAULT 'No attempt'",
        'grading_status': "TEXT DEFAULT 'Not graded'",
        'availability_status': "TEXT DEFAULT 'AVAILABLE'",
        'is_actionable_pending': 'INTEGER DEFAULT 1',
        'resubmission_allowed': 'INTEGER DEFAULT 0'
    }
    c.execute("PRAGMA table_info(tasks)")
    existing_task_cols = [row['name'] for row in c.fetchall()]
    for col, col_type in task_columns.items():
        if col not in existing_task_cols:
            try:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    # Columns to check for submissions table
    sub_columns = {
        'file_name': 'TEXT',
        'file_format': 'TEXT',
        'moodle_status': 'TEXT',
        'verified': 'INTEGER DEFAULT 0'
    }
    c.execute("PRAGMA table_info(submissions)")
    existing_sub_cols = [row['name'] for row in c.fetchall()]
    for col, col_type in sub_columns.items():
        if col not in existing_sub_cols:
            try:
                c.execute(f"ALTER TABLE submissions ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    # Columns to check for courses table
    course_columns = {
        'scanned_at': 'TIMESTAMP'
    }
    c.execute("PRAGMA table_info(courses)")
    existing_course_cols = [row['name'] for row in c.fetchall()]
    for col, col_type in course_columns.items():
        if col not in existing_course_cols:
            try:
                c.execute(f"ALTER TABLE courses ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    # Columns to check for study_sessions table
    session_columns = {
        'resource_id': 'INTEGER'
    }
    c.execute("PRAGMA table_info(study_sessions)")
    existing_session_cols = [row['name'] for row in c.fetchall()]
    for col, col_type in session_columns.items():
        if col not in existing_session_cols:
            try:
                c.execute(f"ALTER TABLE study_sessions ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()

# Automatically initialize database if it doesn't exist
if not os.path.exists(DATABASE_FILE):
    init_db()
else:
    # Run migration checks on load
    try:
        init_db()
    except Exception:
        pass
