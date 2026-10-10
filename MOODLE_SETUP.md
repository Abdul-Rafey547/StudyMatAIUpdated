# Moodle Web Services Integration & Setup Guide 🎓🔌

This guide provides end-to-end instructions for configuring **Moodle Web Services (REST)** for **StudyMate AI**, securing credentials, verifying API functionality, and maintaining student privacy with least-privilege tokens.

Tested and verified on **Moodle 5.1.8+ (branch `MOODLE_501_STABLE`)** with Python Flask backend and Chrome Manifest V3 extension.

---

## 📋 Table of Contents
1. [Overview & Architecture](#1-overview--architecture)
2. [Step-by-Step Moodle Web Services Configuration](#2-step-by-step-moodle-web-services-configuration)
   - [Step 1: Enable Web Services](#step-1-enable-web-services)
   - [Step 2: Enable the REST Protocol](#step-2-enable-the-rest-protocol)
   - [Step 3: Create External Service](#step-3-create-external-service)
   - [Step 4: Add Required API Functions](#step-4-add-required-api-functions)
   - [Step 5: Authorize Student Role Permissions](#step-5-authorize-student-role-permissions)
   - [Step 6: Generate Least-Privilege Student Token](#step-6-generate-least-privilege-student-token)
3. [Required Moodle API Functions Reference](#3-required-moodle-api-functions-reference)
4. [Backend Environment Configuration](#4-backend-environment-configuration)
5. [Token Security & Multi-User Architecture](#5-token-security--multi-user-architecture)
6. [Pre-Flight Verification & Testing](#6-pre-flight-verification--testing)
7. [Troubleshooting Common Errors](#7-troubleshooting-common-errors)
8. [Extending to Other LMS Platforms (Canvas / Blackboard)](#8-extending-to-other-lms-platforms-canvas--blackboard)

---

## 1. Overview & Architecture

StudyMate AI uses the **Moodle Web Services REST API as the primary source of truth** for coursework discovery. Rather than relying on fragile DOM scraping of rendered HTML links, StudyMate AI queries official REST endpoints for:
- Student's enrolled courses.
- Available assignments, cut-off dates, submission status, and grading state.
- Quizzes, availability windows, attempt counts, and completion status.
- Course materials (PDF notes, lecture slides, syllabus documents) and extracts searchable text for AI study tools.

```
┌────────────────────────────────────────────────────────┐
│               Chrome Extension (MV3)                   │
│   Popup / Dashboard / Content Scripts (Zero Tokens)    │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP REST
                           ▼
┌────────────────────────────────────────────────────────┐
│               StudyMate AI Flask Backend               │
│   • BaseLMSConnector Interface                         │
│   • MoodleClient (REST HTTP Connector)                 │
│   • MoodleScanner (Normalizer, Deduplication, Drafts)  │
│   • SQLite Database (studymate.db)                     │
│   • Token Management (.env: MOODLE_URL, MOODLE_TOKEN)  │
└──────────────────────────┬─────────────────────────────┘
                           │ REST (server.php?wstoken=...)
                           ▼
┌────────────────────────────────────────────────────────┐
│                 Moodle LMS Server                      │
│   http://moodle.local/webservice/rest/server.php       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Moodle Web Services Configuration

Log in to your Moodle instance as an Administrator (e.g. `http://moodle.local`).

### Step 1: Enable Web Services
1. Go to **Site administration** ➔ **Server** ➔ **Web services** ➔ **Overview**.
2. Click **Enable web services** (or navigate to **Site administration** ➔ **General** ➔ **Advanced features**).
3. Check the box for **Enable web services** (`enablewebservices = 1`).
4. Click **Save changes**.

> *CLI / SQL Equivalent:*
> ```sql
> UPDATE mdl_config SET value = '1' WHERE name = 'enablewebservices';
> ```

### Step 2: Enable the REST Protocol
1. Go to **Site administration** ➔ **Server** ➔ **Web services** ➔ **Manage protocols**.
2. Locate the row for **REST protocol**.
3. Click the eye icon to enable it (ensure the status icon is uncrossed).

> *CLI / SQL Equivalent:*
> ```sql
> UPDATE mdl_config SET value = 'rest' WHERE name = 'webserviceprotocols';
> ```

### Step 3: Create External Service
1. Go to **Site administration** ➔ **Server** ➔ **Web services** ➔ **External services**.
2. Under **Custom services**, click **Add**.
3. Enter the service parameters:
   - **Name**: `StudyMate AI Service`
   - **Short name**: `studymate_service`
   - **Enabled**: Checked (Yes)
   - **Authorized users only**: Checked (Yes) — *ensures only explicitly authorized accounts can generate tokens*
   - **Can download files**: Checked (Yes) — *required to download lecture notes, PDFs, and assignment files*
   - **Can upload files**: Checked (Yes) — *required for submitting assignment files*
4. Click **Add service**.

### Step 4: Add Required API Functions
1. In the **External services** list, click **Functions** next to `StudyMate AI Service` (or click **Add functions**).
2. Add the **15 core functions** required by StudyMate AI (see [Section 3](#3-required-moodle-api-functions-reference) for the complete list):
   - `core_webservice_get_site_info`
   - `core_enrol_get_users_courses`
   - `core_course_get_courses`
   - `core_course_get_contents`
   - `mod_assign_get_assignments`
   - `mod_assign_get_submission_status`
   - `mod_assign_save_submission`
   - `mod_quiz_get_quizzes_by_courses`
   - `mod_quiz_get_quiz_access_information`
   - `mod_quiz_get_user_attempts`
   - `mod_resource_get_resources_by_courses`
   - `mod_page_get_pages_by_courses`
   - `mod_book_get_books_by_courses`
   - `core_files_get_files`
   - `core_user_get_users_by_field`
3. Click **Add functions**.

### Step 5: Authorize Student Role Permissions
By default in Moodle, authenticated users need permission to communicate via REST:
1. Go to **Site administration** ➔ **Users** ➔ **Permissions** ➔ **Define roles**.
2. Click **Edit** next to **Authenticated user** (or create a dedicated `StudyMate User` role).
3. Search for capability `webservice/rest:use`.
4. Check **Allow**.
5. Search for capability `moodle/webservice:createtoken` (if allowing users to generate their own tokens).
6. Click **Save changes**.

> *SQL Verification:*
> ```sql
> SELECT * FROM mdl_role_capabilities 
> WHERE capability = 'webservice/rest:use' AND roleid = 7;
> ```

### Step 6: Generate Least-Privilege Student Token
> [!IMPORTANT]
> **Never use an administrator token for the student assistant!** Generate a token for the student account (`student1`). An administrator token sees hidden courses, draft instructor files, and lacks student-specific submission statuses.

1. Go to **Site administration** ➔ **Server** ➔ **Web services** ➔ **External services**.
2. Click **Authorized users** next to `StudyMate AI Service`.
3. Add your student user (e.g., `student1`, User ID: `3`) to the authorized users list.
4. Go to **Site administration** ➔ **Server** ➔ **Web services** ➔ **Manage tokens**.
5. Click **Create token**.
6. Select:
   - **User**: Search and select `student1`.
   - **Service**: Select `StudyMate AI Service`.
   - **IP restriction**: Leave blank (or `127.0.0.1` for local dev).
   - **Valid until**: Set desired expiration date (or leave unrestricted for development).
7. Click **Save changes**.
8. Copy the generated 32-character hexadecimal token (e.g. `fc628508599b8251fb3e2a40af365124`).

---

## 3. Required Moodle API Functions Reference

| Function Name | Purpose | Minimum Parameters |
|:---|:---|:---|
| `core_webservice_get_site_info` | Verifies connection, discovers user ID, full name, site name, and enabled service capabilities. | None |
| `core_enrol_get_users_courses` | Retrieves the courses the authenticated student is actively enrolled in. | `userid=<ID>` |
| `core_course_get_courses` | Fallback course directory when enrolment function is restricted. | `ids[0]=<ID>` |
| `core_course_get_contents` | Retrieves module sections, visibility flags (`visible`, `uservisible`), and direct links. | `courseid=<ID>` |
| `mod_assign_get_assignments` | Retrieves assignments, prompt instructions, due dates, and cut-off dates. | `courseids[0]=<ID>` |
| `mod_assign_get_submission_status` | Obtains student submission state (`submitted`, `draft`, `notgraded`, resubmission permissions). | `assignid=<ID>`, `userid=<ID>` |
| `mod_assign_save_submission` | Allows saving or updating assignment text submissions. | `assignmentid=<ID>`, `plugindata[...]` |
| `mod_quiz_get_quizzes_by_courses` | Discovers quizzes, time limits, opening and closing timestamps. | `courseids[0]=<ID>` |
| `mod_quiz_get_quiz_access_information` | Checks if student is blocked from quiz attempt (`canattempt`, `preventaccessreasons`). | `quizid=<ID>` |
| `mod_quiz_get_user_attempts` | Queries previous quiz attempts to identify completed vs actionable quizzes. | `quizid=<ID>`, `userid=<ID>` |
| `mod_resource_get_resources_by_courses` | Retrieves PDF files, slides, and syllabus documents. | `courseids[0]=<ID>` |
| `mod_page_get_pages_by_courses` | Retrieves Moodle Page materials for text indexing. | `courseids[0]=<ID>` |
| `mod_book_get_books_by_courses` | Retrieves Moodle Book chapters for study material synthesis. | `courseids[0]=<ID>` |
| `core_files_get_files` | Queries authenticated course file directory. | `contextid=<ID>`, `component=mod_assign` |
| `core_user_get_users_by_field` | Looks up user profiles by username or email. | `field='username'`, `values[0]='student1'` |

---

## 4. Backend Environment Configuration

All credentials are kept exclusively on the backend in `backend/.env` (or root `.env`).

### `.env` Setup
Create or edit `.env` in `C:\StudyMateAI\.env`:

```env
# ==============================================================================
# StudyMate AI Configuration
# ==============================================================================

# Flask Server Configuration
PORT=5000
DEBUG=True
SECRET_KEY=studymate-secret-key-change-in-production

# Moodle LMS REST API Credentials
MOODLE_URL=http://moodle.local
MOODLE_TOKEN=fc628508599b8251fb3e2a40af365124
MOODLE_TIMEOUT=15

# Chrome Extension Backend Target
STUDYMATE_API_URL=http://localhost:5000/api
```

> [!CAUTION]
> Ensure `.env` is listed in `.gitignore`. Never commit tokens to version control.
> `.env.example` provides the template with blank/masked placeholders.

---

## 5. Token Security & Multi-User Architecture

### Security Principles Enforced
1. **Zero Tokens in Chrome Extension**:
   - The Chrome extension never receives, stores, or transmits the Moodle token.
   - When the user clicks **Scan**, the extension sends an internal message `TRIGGER_API_SCAN` to `background.js`, which issues a POST request to `http://localhost:5000/api/tasks/scan`.
   - The backend performs all authenticated Moodle calls server-to-server.
2. **Automated Token Masking**:
   - Diagnostic logs mask tokens automatically:
     ```python
     # Example log output:
     [Moodle API] Calling core_enrol_get_users_courses (token: fc62...5124)
     ```
3. **Authenticated Resource Downloads**:
   - Moodle `pluginfile.php` downloads require authentication. The backend appends `?token=...` safely on the server side to stream binaries, extracts text (via `pypdf`/`python-docx`), and returns only sanitized text to the student UI.
4. **Multi-User Architecture Support**:
   - `BaseLMSConnector` is designed with per-user session parameters (`user_id`). In multi-user deployment, tokens are encrypted in user session vaults (`user_credentials` table) rather than a single shared environment variable.

---

## 6. Pre-Flight Verification & Testing

### Verification Option A: Python Verification Script
Run the automated pre-flight check in PowerShell:
```powershell
python -c "import sys; sys.path.insert(0, 'backend'); from moodle.moodle_client import MoodleClient; c = MoodleClient(); print(c.check_connection())"
```
*Expected Output:*
```json
{
  "connected": true,
  "sitename": "Local Moodle LMS",
  "username": "student1",
  "fullname": "Student One",
  "userid": 3,
  "release": "5.1.8+ (Build: 20261001)",
  "downloadfiles": true,
  "uploadfiles": true,
  "functions": ["core_webservice_get_site_info", "core_enrol_get_users_courses", ...]
}
```

### Verification Option B: cURL Direct Test
```bash
curl -X POST "http://moodle.local/webservice/rest/server.php" \
  -d "wstoken=fc628508599b8251fb3e2a40af365124" \
  -d "wsfunction=core_webservice_get_site_info" \
  -d "moodlewsrestformat=json"
```

### Verification Option C: Full Automated Test Suite
Run the 56 comprehensive unit and integration tests:
```powershell
python -m unittest discover -s tests
```
*Expected Output:*
```text
Ran 56 tests in 1.310s
OK
```

---

## 7. Troubleshooting Common Errors

### Error: `invalidtoken`
- **Cause**: The token does not exist in `mdl_external_tokens`, was deleted, or belongs to a disabled user.
- **Fix**: Re-check **Site administration** ➔ **Server** ➔ **Web services** ➔ **Manage tokens**, verify the token string matches `.env`, and ensure the token expiration date has not passed.

### Error: `accessexception` / "Access to the function [name] is not allowed"
- **Cause**: The specific Moodle function has not been added to `StudyMate AI Service` in Moodle.
- **Fix**: Navigate to **External services** ➔ **Functions** next to `StudyMate AI Service` and add the missing function name.

### Error: `webservice_protocol_disabled`
- **Cause**: REST protocol is disabled in Moodle.
- **Fix**: Navigate to **Site administration** ➔ **Server** ➔ **Web services** ➔ **Manage protocols** and enable the eye icon next to **REST protocol**.

### Error: `enablewebservices_disabled`
- **Cause**: Global web services toggle is off.
- **Fix**: Navigate to **Site administration** ➔ **Advanced features** and check **Enable web services**.

### Error: `nopermissions` / "webservice/rest:use capability required"
- **Cause**: The student's role lacks the `webservice/rest:use` capability.
- **Fix**: Go to **Define roles** ➔ **Authenticated user** ➔ edit permissions and allow `webservice/rest:use`.

### Error: "Cannot connect to Moodle server: [WinError 10061]"
- **Cause**: Local Apache / PHP server is not running on port 80.
- **Fix**: In XAMPP Control Panel, ensure Apache is started (`C:\xampp\apache\bin\httpd.exe`).

---

## 8. Extending to Other LMS Platforms (Canvas / Blackboard)

StudyMate AI uses an abstract strategy pattern via [`BaseLMSConnector`](file:///C:/StudyMateAI/backend/moodle/lms_interface.py). To add support for Canvas LMS or Blackboard:

1. **Subclass `BaseLMSConnector`**:
   ```python
   # backend/connectors/canvas_client.py
   from moodle.lms_interface import BaseLMSConnector

   class CanvasLMSConnector(BaseLMSConnector):
       def __init__(self, base_url: str, api_token: str):
           self.base_url = base_url
           self.token = api_token

       def check_connection(self) -> dict:
           # Query /api/v1/users/self
           pass

       def get_courses(self) -> list:
           # Query /api/v1/courses?enrollment_state=active
           pass

       def get_assignments(self, course_ids=None) -> list:
           # Query /api/v1/courses/:id/assignments
           pass
   ```
2. **Factory Selection**:
   In `config.py` or user settings, specify `LMS_TYPE = 'moodle'` or `LMS_TYPE = 'canvas'`.
3. **Normalized Models**:
   Because `MoodleScanner` normalizes all records into uniform schema fields (`course_id`, `moodle_activity_id`, `type`, `title`, `due_date`, `availability_status`, `is_actionable_pending`), the Chrome extension and AI generation engine work identically across any LMS platform without modifying frontend code.
