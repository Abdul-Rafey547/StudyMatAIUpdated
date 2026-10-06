# StudyMate AI – System Architecture

StudyMate AI is an AI-assisted academic assistant for university students using the Moodle LMS.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Moodle LMS                          │
│               (Courses, Assignments, Quizzes)               │
└──────────────────────────────┬──────────────────────────────┘
                               │ DOM / Page Data
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 StudyMate Chrome Extension                  │
│  ├─ Content Scripts (Detector, Scanners, Form Injector)     │
│  ├─ Background Service Worker (Router, Storage, API Proxy)   │
│  ├─ Popup UI (Status, Quick Scan, Overview)                 │
│  └─ Full Dashboard (Answer Editor, Study Tools, History)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (JSON / HTTP)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  StudyMate Python Backend                   │
│  ├─ Flask Server & Blueprints (Tasks, AI, Submissions)      │
│  ├─ AI Orchestration (Prompt Manager, Validator, Generator)  │
│  ├─ Moodle Parsers & Web Services Client                    │
│  └─ SQLite Relational Database (Tasks, Solutions, History)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ API Requests
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       AI Provider                           │
│           (OpenAI GPT-4o / Local Fallback Engine)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Chrome Extension (Manifest V3)
- **`content/moodle_detector.js`**: Analyzes URL routes and DOM markers to classify pages (Assignment, Quiz, Course).
- **`content/assignment_scanner.js`**: Extracts assignment titles, instructions, due dates, submission statuses, and grading criteria.
- **`content/quiz_scanner.js`**: Extracts quiz titles, attempt counts, time limits, question prompts, and options.
- **`content/content.js`**: Orchestrates scanning across tabs and injects generated solutions into Moodle editors (Atto, TinyMCE, textareas).
- **`background/background.js`**: Asynchronous service worker managing extension state, Chrome local storage caches, and REST communications.
- **`popup/`**: Compact extension popup with glassmorphic purple theme, connection status indicators, and quick actions.
- **`dashboard/`**: Complete desktop dashboard featuring the **Answer Editor**, AI Academic Study Tools, task filters, and submission history.
- **`components/`**: Modular, reusable UI components (`AnswerEditor`, `TaskCard`, `AssignmentCard`, `QuizCard`, `StudyMateNotification`).

### 2. Python Backend (Flask & SQLite)
- **`app.py`**: Entry point configuring CORS, blueprints, error handlers, and health probes.
- **`api/`**: Modular REST blueprints:
  - `tasks.py`: Task ingestion and listing
  - `assignments.py` & `quizzes.py`: Specialized activity querying
  - `ai.py`: Generation endpoints and on-demand study assistance
  - `submissions.py`: Solution draft saving and submission logging
- **`models/`**: Data models (`Task`, `Assignment`, `Quiz`, `Solution`, `Course`, `User`).
- **`ai/`**:
  - `ai_service.py`: Orchestrates generation, validation, and fallback logic
  - `prompt_manager.py`: Formulates academic prompts with structured instructions
  - `answer_generator.py`: Connects to OpenAI or executes the offline academic blueprint engine
  - `answer_validator.py`: Verifies output completeness, length, and code block formatting
- **`moodle/`**:
  - `assignment_parser.py` & `quiz_parser.py`: Sanitizes and structures incoming payloads
  - `moodle_client.py`: Integrates with Moodle REST Web Services
  - `submission_manager.py`: Records submission events
- **`database/`**: Relational SQLite schema with automated table creation and foreign key constraints.

## Human-in-the-Loop Workflow
1. **Discovery**: Moodle page is detected and scanned.
2. **Generation**: AI generates an initial draft solution.
3. **Review & Edit**: Student reviews draft in the **Answer Editor**, can regenerate, expand, or manually edit content.
4. **Student Approval**: Student explicitly clicks "Approve Draft".
5. **Submission**: Solution is submitted to Moodle with student confirmation.
