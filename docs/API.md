# StudyMate AI – Backend REST API Documentation

Base URL: `http://localhost:5000/api`

## Endpoints

### 1. Health & Status
- **`GET /api/health`**
  - **Response**:
    ```json
    {
      "status": "ok",
      "message": "StudyMate AI Backend is running.",
      "ai_provider": "openai",
      "ai_model": "gpt-4o"
    }
    ```

### 2. Tasks
- **`POST /api/tasks/sync`**
  - **Request Body**:
    ```json
    {
      "task": {
        "title": "Assignment Title",
        "description": "Task instructions...",
        "type": "ASSIGNMENT",
        "dueDate": "2026-12-01",
        "course": "Computer Science 101",
        "url": "http://moodle.local/mod/assign/view.php?id=2"
      }
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "task_id": 1,
      "message": "Task synced successfully"
    }
    ```

- **`GET /api/tasks`**
  - **Response**: Array of all tracked tasks.

- **`GET /api/tasks/<task_id>`**
  - **Response**: Specific task details and its latest generated solution.

### 3. AI Generation & Study Tools
- **`POST /api/ai/generate`**
  - **Request Body**:
    ```json
    {
      "task_id": 1,
      "prompt": "Custom student guidance (optional)",
      "context": "Additional context (optional)"
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "solution_id": 1,
      "solution": {
        "solution_id": 1,
        "task_id": 1,
        "generated_answer": "...",
        "status": "GENERATED"
      }
    }
    ```

- **`POST /api/study/<action>`**
  - **URL Parameter**: `action` (`explain`, `summarize`, `notes`, `practice`)
  - **Request Body**:
    ```json
    {
      "topic": "Binary Search Trees",
      "course_id": 1
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "action": "explain",
      "topic": "Binary Search Trees",
      "material": "..."
    }
    ```

### 4. Solutions & Submissions
- **`POST /api/solutions/draft`**
  - **Request Body**:
    ```json
    {
      "task_id": 1,
      "solution_id": 1,
      "edited_answer": "Student-modified answer text...",
      "status": "APPROVED"
    }
    ```

- **`POST /api/submissions/submit`**
  - **Request Body**:
    ```json
    {
      "task_id": 1,
      "solution_id": 1
    }
    ```
