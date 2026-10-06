"""
StudyMate AI - Tasks API Blueprint
Handles task listing, syncing, detail viewing, and status updates.
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from utils.logger import get_logger

logger = get_logger('studymate.api.tasks')
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/sync', methods=['POST'])
def sync_task():
    try:
        data = request.json or {}
        task_data = data.get('task')
        if not task_data:
            return jsonify({"error": "No task data provided"}), 400

        title = task_data.get('title')
        description = task_data.get('description', '')
        task_type = task_data.get('type', 'ASSIGNMENT').upper()
        due_date = task_data.get('dueDate') or task_data.get('due_date')
        moodle_url = task_data.get('url') or task_data.get('moodle_url', '')
        course_name = task_data.get('course') or task_data.get('courseName') or 'General'

        if not title:
            return jsonify({"error": "Task title is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        # Deduplicate course by course_name
        c.execute("SELECT course_id FROM courses WHERE course_name = ?", (course_name,))
        course_row = c.fetchone()
        if course_row:
            course_id = course_row['course_id']
        else:
            c.execute("INSERT INTO courses (course_name) VALUES (?)", (course_name,))
            course_id = c.lastrowid

        # Check existing task
        c.execute("SELECT task_id FROM tasks WHERE title = ? AND course_id = ?", (title, course_id))
        existing_task = c.fetchone()

        if existing_task:
            task_id = existing_task['task_id']
            c.execute("""
                UPDATE tasks
                SET description = ?, due_date = ?, moodle_url = ?, type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (description, due_date, moodle_url, task_type, task_id))
        else:
            c.execute("""
                INSERT INTO tasks (course_id, type, title, description, due_date, status, moodle_url)
                VALUES (?, ?, ?, ?, ?, 'DISCOVERED', ?)
            """, (course_id, task_type, title, description, due_date, moodle_url))
            task_id = c.lastrowid

        conn.commit()
        conn.close()

        logger.info(f"Task synced successfully: id={task_id}, title='{title}'")
        return jsonify({"success": True, "task_id": task_id, "message": "Task synced successfully"})

    except Exception as e:
        logger.error(f"Error syncing task: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('', methods=['GET'])
def get_tasks():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.*, c.course_name
            FROM tasks t
            LEFT JOIN courses c ON t.course_id = c.course_id
            ORDER BY t.created_at DESC
        """)
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"success": True, "tasks": tasks})
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.*, c.course_name
            FROM tasks t
            LEFT JOIN courses c ON t.course_id = c.course_id
            WHERE t.task_id = ?
        """, (task_id,))
        task = c.fetchone()

        if not task:
            conn.close()
            return jsonify({"error": "Task not found"}), 404

        task_dict = dict(task)

        # Get latest solution
        c.execute("""
            SELECT * FROM solutions
            WHERE task_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (task_id,))
        solution = c.fetchone()
        task_dict['solution'] = dict(solution) if solution else None

        conn.close()
        return jsonify({"success": True, "task": task_dict})
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500
