"""
StudyMate AI - Submissions & Solutions API Blueprint
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from utils.logger import get_logger

logger = get_logger('studymate.api.submissions')
submissions_bp = Blueprint('submissions', __name__)

@submissions_bp.route('/draft', methods=['POST'])
def save_draft():
    try:
        data = request.json or {}
        solution_id = data.get('solution_id') or data.get('solutionId')
        task_id = data.get('task_id') or data.get('taskId')
        edited_answer = data.get('edited_answer') or data.get('editedAnswer', '')
        status = data.get('status', 'DRAFT')

        conn = get_db_connection()
        c = conn.cursor()

        if solution_id:
            c.execute("""
                UPDATE solutions
                SET edited_answer = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE solution_id = ?
            """, (edited_answer, status, solution_id))
        elif task_id:
            c.execute("""
                INSERT INTO solutions (task_id, generated_answer, edited_answer, status)
                VALUES (?, ?, ?, ?)
            """, (task_id, edited_answer, edited_answer, status))
            solution_id = c.lastrowid
        else:
            conn.close()
            return jsonify({"error": "task_id or solution_id is required"}), 400

        if task_id:
            c.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", (status, task_id))

        conn.commit()
        conn.close()

        logger.info(f"Draft saved for solution #{solution_id}")
        return jsonify({"success": True, "solution_id": solution_id, "message": "Draft saved successfully."})

    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        return jsonify({"error": str(e)}), 500


@submissions_bp.route('/submit', methods=['POST'])
def submit_solution():
    try:
        data = request.json or {}
        task_id = data.get('task_id') or data.get('taskId')
        solution_id = data.get('solution_id') or data.get('solutionId')
        result_text = data.get('result', 'Success (Submitted via StudyMate AI)')

        if not task_id:
            return jsonify({"error": "task_id is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        # If no solution_id given, find latest
        if not solution_id:
            c.execute("SELECT solution_id FROM solutions WHERE task_id = ? ORDER BY created_at DESC LIMIT 1", (task_id,))
            sol = c.fetchone()
            if sol:
                solution_id = sol['solution_id']

        if solution_id:
            c.execute("""
                INSERT INTO submissions (task_id, solution_id, result)
                VALUES (?, ?, ?)
            """, (task_id, solution_id, result_text))
            submission_id = c.lastrowid
            c.execute("UPDATE solutions SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE solution_id = ?", (solution_id,))
        else:
            submission_id = None

        c.execute("UPDATE tasks SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()

        logger.info(f"Task #{task_id} marked as submitted (submission #{submission_id})")
        return jsonify({"success": True, "submission_id": submission_id, "message": "Task marked as submitted."})

    except Exception as e:
        logger.error(f"Error submitting solution: {e}")
        return jsonify({"error": str(e)}), 500
