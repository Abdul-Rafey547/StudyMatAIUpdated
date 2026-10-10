# StudyMate AI 🎓✨

**StudyMate AI** is an AI-powered student assistant integrated with the **Moodle Learning Management System (LMS)** through a Google Chrome browser extension and Python backend.

Designed for university coursework, StudyMate AI bridges the gap between LMS task management, AI-driven study assistance, and student-in-the-loop assignment workflows.

---

## 🌟 Key Features

1. **Reliable Moodle Web Services API Integration (Primary Source of Truth)**:
   - Queries Moodle's official REST API (`core_enrol_get_users_courses`, `mod_assign_get_assignments`, `mod_quiz_get_quizzes_by_courses`, `mod_resource_get_resources_by_courses`).
   - Evaluates true availability, cut-off dates, submission status, and attempt counts.
   - Eliminates false positives and random HTML link scraping, with DOM scanning preserved only as an optional offline fallback.
   - Automatically discovers study resources (PDFs, DOCX, lecture notes) and indexes text for AI study sessions.
2. **Multi-Provider AI Solution Generation**:
   - Seamlessly connect multiple AI providers: **Google Gemini** (`gemini-1.5-flash`, `gemini-2.0-flash`, `pro`), **Anthropic Claude** (`claude-3-5-sonnet`, `haiku`, `3.7`), **Groq Cloud** (`llama-3.3-70b-versatile`, `3.1-8b`), **OpenAI** (`gpt-4o`, `gpt-4o-mini`), **DeepSeek** (`deepseek-chat`, `r1`), **Ollama** (offline local LLM), and **Intelligent Local Academic Fallback**.
3. **Human-in-the-Loop Solution Editor**:
   - Review, edit, refine, expand, and approve AI drafts prior to submission.
   - Rescanning from Moodle strictly preserves existing student drafts, notes, and approved solutions.
4. **Moodle Submission Integration**:
   - Seamlessly injects approved solutions into Moodle assignment submission text areas (Atto, TinyMCE, standard editors).
5. **AI Academic Study Tools**:
   - Concept Explanation, Topic Summarization, Structured Lecture Notes, and Practice Question generation across any configured provider.
6. **Task & Submission History**:
   - Comprehensive log of past submissions, drafts, and coursework activity.

---

## 🏗️ System Architecture

```
Moodle LMS ──(REST API)──▶ Backend (Python/Flask) ──▶ Multi-Provider AI Engine
(http://moodle.local)           │   • BaseLMSConnector         ├─ Google Gemini
                                │   • MoodleClient             ├─ Anthropic Claude
                                │   • MoodleScanner            ├─ Groq Cloud
                                │   • SQLite (studymate.db)    ├─ OpenAI GPT
                                │                              ├─ DeepSeek
                                ▼                              ├─ Ollama (Local)
                        Chrome Extension (MV3)                 └─ Local Academic Fallback
                        (Zero Token Exposure)
```

- **Frontend**: Chrome Extension (Manifest V3, HTML5, Glassmorphic CSS3, Vanilla JS).
- **Backend**: Python 3.10+ with Flask, Blueprints architecture, SQLite.
- **LMS Connector**: Abstract `BaseLMSConnector` interface implementing Moodle REST API (extensible to Canvas / Blackboard).
- **AI Engine**: Modular multi-provider architecture (Google Gemini, Claude, Groq, OpenAI, DeepSeek, Ollama, and offline fallback).

---

## 🚀 Quick Start Guide

### 1. Backend Setup
```bash
# Clone or navigate to the repository
cd C:\StudyMateAI

# Install Python requirements
pip install -r requirements.txt

# Create .env from example and configure Moodle credentials
copy .env.example .env
# Edit .env with your MOODLE_URL and MOODLE_TOKEN

# Run the backend server
python backend/app.py
```
The server will start at `http://127.0.0.1:5000`.

### 2. Configure Moodle Web Services
For complete instructions on configuring Moodle Web Services, enabling REST protocols, and generating a least-privileged student token:
➡️ **[`MOODLE_SETUP.md`](file:///C:/StudyMateAI/MOODLE_SETUP.md)**

### 3. Chrome Extension Setup
1. Open Google Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select the `C:\StudyMateAI\extension` folder.
4. Pin the **StudyMate AI** extension to your toolbar.

### 4. Running Automated Tests
Run the comprehensive test suite (56 tests covering Moodle API connector, availability scanner, draft preservation, AI generation, and submissions):
```bash
python -m unittest discover -s tests
```

---

## 📖 Documentation & Guides
- 📘 **Moodle Web Services Setup**: [`MOODLE_SETUP.md`](file:///C:/StudyMateAI/MOODLE_SETUP.md)
- 📗 **Step-by-Step Tutorial**: [`TUTORIAL.txt`](file:///C:/StudyMateAI/TUTORIAL.txt)
- 📙 **REST API Specification**: [`docs/api_specification.md`](file:///C:/StudyMateAI/docs/api_specification.md)

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
