# StudyMate AI 🎓✨

**StudyMate AI** is an AI-powered student assistant integrated with the **Moodle Learning Management System (LMS)** through a Google Chrome browser extension and Python backend.

Designed for university coursework, StudyMate AI bridges the gap between LMS task management, AI-driven study assistance, and student-in-the-loop assignment workflows.

---

## 🌟 Key Features

1. **Intelligent Moodle Detection & Scanning**:
   - Automatically detects Moodle course pages, assignments, and quizzes.
   - Extracts instructions, precise due dates, attempt counts, and submission statuses.
2. **AI-Assisted Solution Generation**:
   - Generates step-by-step academic solutions using OpenAI GPT-4o or an offline intelligent fallback engine.
3. **Human-in-the-Loop Solution Editor**:
   - Review, edit, refine, expand, and approve AI drafts prior to submission.
4. **Moodle Submission Integration**:
   - Seamlessly injects approved solutions into Moodle assignment submission text areas (Atto, TinyMCE, standard editors).
5. **AI Academic Study Tools**:
   - Concept Explanation, Topic Summarization, Structured Lecture Notes, and Practice Question generation.
6. **Task & Submission History**:
   - Comprehensive log of past submissions, drafts, and coursework activity.

---

## 🏗️ System Architecture

```
Moodle LMS ──▶ Chrome Extension (Manifest V3) ──▶ Flask Backend (REST) ──▶ AI Engine / Fallback
                                                        │
                                                        ▼
                                                  SQLite Database
```

- **Frontend**: Chrome Extension (Manifest V3, HTML5, Glassmorphic CSS3, Vanilla JS).
- **Backend**: Python 3.10+ with Flask, Blueprints architecture, SQLite.
- **AI Engine**: Modular provider support (OpenAI `gpt-4o`, offline academic blueprint fallback).

---

## 🚀 Quick Start Guide

### 1. Backend Setup
```bash
# Clone or navigate to the repository
cd C:\StudyMateAI

# Install Python requirements
pip install -r requirements.txt

# Create .env from example (optional for custom API keys)
copy .env.example .env

# Run the backend server
python backend/app.py
```
The server will start at `http://127.0.0.1:5000`.

### 2. Chrome Extension Setup
1. Open Google Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select the `C:\StudyMateAI\extension` folder.
4. Pin the **StudyMate AI** extension to your toolbar.

### 3. Running Automated Tests
```bash
python -m unittest discover -s tests
```

---

## 📖 Step-by-Step Tutorial
For a complete walkthrough on how to use every feature of StudyMate AI with your local Moodle environment, please read:
➡️ **[`TUTORIAL.txt`](file:///C:/StudyMateAI/TUTORIAL.txt)**

---

## 📁 Repository Structure

```
StudyMateAI/
├── backend/
│   ├── app.py                     # Central Flask server & Blueprint registration
│   ├── config.py                  # Configuration & environment variables
│   ├── ai/                        # AI Service orchestration & fallback engine
│   ├── api/                       # Modular REST Blueprints (tasks, ai, submissions, courses)
│   ├── database/                  # SQLite schema & DB connection
│   ├── models/                    # Domain data models (Task, Solution, Course, User)
│   ├── moodle/                    # Parsers & Moodle Web Services client
│   └── utils/                     # Centralized logger & helpers
├── extension/
│   ├── manifest.json              # Manifest V3 configuration with icons
│   ├── background/                # Service worker message router
│   ├── content/                   # Content scripts & DOM scanners
│   ├── popup/                     # Glassmorphic popup UI & controller
│   ├── dashboard/                 # Desktop dashboard & study tools
│   ├── components/                # Reusable UI components (AnswerEditor, TaskCard)
│   └── assets/                    # Extension icons
├── docs/                          # Architecture & REST API specifications
├── tests/                         # Complete automated test suite
├── TUTORIAL.txt                   # Step-by-step user guide & manual
└── requirements.txt               # Python package dependencies
```
