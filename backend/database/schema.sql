-- StudyMate AI Database Schema

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    moodle_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    moodle_course_id TEXT UNIQUE,
    scanned_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    moodle_activity_id TEXT,
    type TEXT NOT NULL, -- 'ASSIGNMENT', 'QUIZ'
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    cutoff_date TEXT,
    status TEXT DEFAULT 'DISCOVERED', -- DISCOVERED, PENDING, PROCESSING, GENERATED, REVIEW, APPROVED, SUBMITTED, COMPLETED, FAILED
    submission_status TEXT DEFAULT 'No attempt',
    grading_status TEXT DEFAULT 'Not graded',
    availability_status TEXT DEFAULT 'AVAILABLE', -- AVAILABLE, SUBMITTED, COMPLETED, UPCOMING, CLOSED, UNAVAILABLE, UNVERIFIED
    is_actionable_pending INTEGER DEFAULT 1,
    resubmission_allowed INTEGER DEFAULT 0,
    moodle_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS solutions (
    solution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    generated_answer TEXT NOT NULL,
    edited_answer TEXT,
    status TEXT DEFAULT 'GENERATED', -- GENERATED, DRAFT, APPROVED, SUBMITTED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    solution_id INTEGER NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result TEXT,
    file_name TEXT,
    file_format TEXT,
    moodle_status TEXT,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
    FOREIGN KEY(solution_id) REFERENCES solutions(solution_id)
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    moodle_resource_id TEXT,
    title TEXT NOT NULL,
    resource_type TEXT NOT NULL, -- 'PDF', 'DOCX', 'PPTX', 'TXT', 'PAGE', 'BOOK', 'URL', 'FILE'
    file_name TEXT,
    mime_type TEXT,
    file_size TEXT,
    description TEXT,
    moodle_url TEXT NOT NULL,
    direct_url TEXT,
    availability_status TEXT DEFAULT 'AVAILABLE',
    extracted_text TEXT,
    is_scanned_image INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(course_id) REFERENCES courses(course_id),
    UNIQUE(moodle_url)
);

CREATE TABLE IF NOT EXISTS study_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER, -- Optional, if linked to a quiz/assignment
    resource_id INTEGER, -- Optional, if linked to a resource
    course_id INTEGER,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
    FOREIGN KEY(resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY(course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL, -- 'EXPLANATION', 'SUMMARY', 'NOTES', 'PRACTICE', 'MCQS', 'GUIDE'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES study_sessions(session_id)
);
