"""
StudyMate AI - Tasks API Blueprint
Handles task listing, syncing, detail viewing, and status updates with strict availability verification.
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from moodle.assignment_parser import AssignmentParser
from moodle.quiz_parser import QuizParser
from moodle.moodle_client import MoodleClient
from moodle.moodle_scanner import MoodleScanner
from utils.logger import get_logger

logger = get_logger('studymate.api.tasks')
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/scan', methods=['POST', 'GET'])
def scan_moodle_tasks():
    """
    Trigger a fresh backend scan using the Moodle Web Services API as the source of truth.
    Scans student's enrolled courses, verifies availability, and stores fresh normalized activities.
    """
    try:
        data = request.json or {} if request.is_json else {}
        user_id = data.get('user_id') or request.args.get('user_id')
        scanner = MoodleScanner()
        scan_result = scanner.scan_enrolled_courses(user_id=int(user_id) if user_id else None)

        if not scan_result.get('success'):
            status_code = 503 if scan_result.get('errorcode') == 'connection_failed' else 400
            return jsonify(scan_result), status_code

        return jsonify(scan_result)

    except Exception as e:
        logger.error(f"Error executing Moodle API scan: {e}")
        return jsonify({"success": False, "error": str(e), "errorcode": "scan_exception"}), 500


@tasks_bp.route('/moodle-status', methods=['GET'])
def moodle_status():
    """
    Verify backend connection to Moodle LMS Web Services without modifying data.
    """
    try:
        client = MoodleClient()
        conn_info = client.check_connection()
        return jsonify(conn_info)
    except Exception as e:
        logger.error(f"Error checking Moodle connection: {e}")
        return jsonify({"connected": False, "error": str(e)}), 500

@tasks_bp.route('/sync', methods=['POST'])
def sync_task():
    """
    Sync an assignment or quiz task scanned from Moodle.
    Applies strict availability categorization and stable ID deduplication.
    """
    conn = None
    try:
        data = request.json or {}
        raw_task = data.get('task') or data
        if not raw_task:
            return jsonify({"error": "No task data provided"}), 400

        task_type = (raw_task.get('type') or 'ASSIGNMENT').upper()

        if task_type == 'QUIZ':
            parsed = QuizParser.parse_extension_payload({'task': raw_task})
            # Default quiz parsed fields
            title = parsed.get('title', 'Untitled Quiz')
            description = parsed.get('description', '')
            due_date = raw_task.get('dueDate') or raw_task.get('due_date')
            cutoff_date = raw_task.get('cutoffDate') or raw_task.get('cutoff_date')
            course_name = raw_task.get('course') or raw_task.get('courseName') or 'General'
            moodle_url = raw_task.get('url') or raw_task.get('moodle_url', '')
            moodle_activity_id = str(raw_task.get('id') or raw_task.get('moodle_activity_id') or '')
            submission_status = raw_task.get('submissionStatus', 'No attempt')
            grading_status = raw_task.get('gradingStatus', 'Not graded')
            availability_status = raw_task.get('availabilityStatus', 'AVAILABLE')
            is_actionable_pending = 1 if availability_status == 'AVAILABLE' else 0
            resubmission_allowed = 0
            initial_status = raw_task.get('status', 'PENDING' if is_actionable_pending else availability_status)
        else:
            parsed = AssignmentParser.parse_extension_payload({'task': raw_task})
            title = parsed['title']
            description = parsed['description']
            due_date = parsed['due_date']
            cutoff_date = parsed['cutoff_date']
            course_name = parsed['course_name']
            moodle_url = parsed['moodle_url']
            moodle_activity_id = parsed['moodle_activity_id']
            submission_status = parsed['submission_status']
            grading_status = parsed['grading_status']
            availability_status = parsed['availability_status']
            is_actionable_pending = parsed['is_actionable_pending']
            resubmission_allowed = parsed['resubmission_allowed']
            initial_status = parsed['status']

        if not title:
            return jsonify({"error": "Task title is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        # Deduplicate course
        c.execute("SELECT course_id FROM courses WHERE course_name = ?", (course_name,))
        course_row = c.fetchone()
        if course_row:
            course_id = course_row['course_id']
            c.execute("UPDATE courses SET scanned_at = CURRENT_TIMESTAMP WHERE course_id = ?", (course_id,))
        else:
            c.execute("INSERT INTO courses (course_name, scanned_at) VALUES (?, CURRENT_TIMESTAMP)", (course_name,))
            course_id = c.lastrowid

        # Stable task deduplication by (moodle_activity_id, course_id) or (title, course_id) or moodle_url
        existing_task = None
        if moodle_activity_id:
            c.execute("SELECT * FROM tasks WHERE moodle_activity_id = ? AND course_id = ?", (moodle_activity_id, course_id))
            existing_task = c.fetchone()

        if not existing_task and moodle_url:
            c.execute("SELECT * FROM tasks WHERE moodle_url = ? AND course_id = ?", (moodle_url, course_id))
            existing_task = c.fetchone()

        if not existing_task:
            c.execute("SELECT * FROM tasks WHERE title = ? AND course_id = ?", (title, course_id))
            existing_task = c.fetchone()

        if existing_task:
            task_id = existing_task['task_id']
            current_status = existing_task['status']

            # If task already had active draft or approved solution, preserve its workflow state unless Moodle confirmed submission
            if current_status in ('GENERATED', 'Draft Ready', 'REVIEW', 'In Draft', 'APPROVED') and availability_status == 'AVAILABLE':
                new_status = current_status
            elif availability_status in ('SUBMITTED', 'COMPLETED', 'CLOSED', 'UPCOMING', 'UNAVAILABLE', 'UNVERIFIED'):
                new_status = availability_status
            else:
                new_status = initial_status

            c.execute("""
                UPDATE tasks
                SET description = ?, due_date = ?, cutoff_date = ?, moodle_url = ?,
                    type = ?, moodle_activity_id = ?, submission_status = ?,
                    grading_status = ?, availability_status = ?, is_actionable_pending = ?,
                    resubmission_allowed = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (description, due_date, cutoff_date, moodle_url, task_type,
                  moodle_activity_id, submission_status, grading_status,
                  availability_status, is_actionable_pending, resubmission_allowed,
                  new_status, task_id))
        else:
            c.execute("""
                INSERT INTO tasks (
                    course_id, moodle_activity_id, type, title, description,
                    due_date, cutoff_date, status, submission_status, grading_status,
                    availability_status, is_actionable_pending, resubmission_allowed, moodle_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (course_id, moodle_activity_id, task_type, title, description,
                  due_date, cutoff_date, initial_status, submission_status, grading_status,
                  availability_status, is_actionable_pending, resubmission_allowed, moodle_url))
            task_id = c.lastrowid

        conn.commit()

        logger.info(f"Task synced successfully: id={task_id}, title='{title}', avail={availability_status}, actionable={is_actionable_pending}")
        return jsonify({
            "success": True,
            "task_id": task_id,
            "availability_status": availability_status,
            "is_actionable_pending": bool(is_actionable_pending),
            "message": "Task synced successfully"
        })

    except Exception as e:
        logger.error(f"Error syncing task: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@tasks_bp.route('', methods=['GET'])
def get_tasks():
    """
    Fetch all tasks with optional filters for actionable pending only, course, or type.
    """
    conn = None
    try:
        pending_only = request.args.get('pending_only', '').lower() in ('true', '1', 'yes')
        course_id = request.args.get('course_id')
        task_type = request.args.get('type')

        conn = get_db_connection()
        c = conn.cursor()

        query = """
            SELECT t.*, c.course_name,
                   s.solution_id, s.generated_answer, s.edited_answer, s.status as solution_status
            FROM tasks t
            LEFT JOIN courses c ON t.course_id = c.course_id
            LEFT JOIN solutions s ON s.task_id = t.task_id AND s.solution_id = (
                SELECT solution_id FROM solutions WHERE task_id = t.task_id ORDER BY created_at DESC LIMIT 1
            )
            WHERE 1=1
        """
        params = []

        if pending_only:
            query += " AND t.is_actionable_pending = 1 AND t.status NOT IN ('SUBMITTED', 'COMPLETED', 'CLOSED', 'UNAVAILABLE', 'ARCHIVED')"

        if course_id:
            query += " AND t.course_id = ?"
            params.append(course_id)

        if task_type:
            query += " AND t.type = ?"
            params.append(task_type.upper())

        query += " ORDER BY t.created_at DESC"

        c.execute(query, tuple(params))
        rows = c.fetchall()

        tasks = []
        for r in rows:
            t_dict = dict(r)
            t_dict['id'] = t_dict['task_id']
            t_dict['dueDate'] = t_dict['due_date']
            t_dict['courseName'] = t_dict['course_name']
            if t_dict.get('solution_id'):
                t_dict['solution'] = {
                    'solution_id': t_dict['solution_id'],
                    'id': t_dict['solution_id'],
                    'generated_answer': t_dict.get('generated_answer'),
                    'edited_answer': t_dict.get('edited_answer'),
                    'status': t_dict.get('solution_status')
                }
            tasks.append(t_dict)

        return jsonify({"success": True, "tasks": tasks, "total": len(tasks)})

    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get detailed task record with solution history.
    """
    conn = None
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
            return jsonify({"error": "Task not found"}), 404

        task_dict = dict(task)
        task_dict['id'] = task_dict['task_id']
        task_dict['dueDate'] = task_dict['due_date']
        task_dict['courseName'] = task_dict['course_name']

        # Get latest solution
        c.execute("""
            SELECT * FROM solutions
            WHERE task_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (task_id,))
        solution = c.fetchone()
        task_dict['solution'] = dict(solution) if solution else None

        return jsonify({"success": True, "task": task_dict})
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
