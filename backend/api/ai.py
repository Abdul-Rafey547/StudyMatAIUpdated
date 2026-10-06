"""
StudyMate AI - AI Solutions & Study API Blueprint
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from ai.ai_service import generate_answer_for_task, generate_study_material
from utils.logger import get_logger

logger = get_logger('studymate.api.ai')
ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/generate', methods=['POST'])
def generate_solution():
    try:
        data = request.json or {}
        task_id = data.get('task_id') or data.get('taskId')
        custom_prompt = data.get('prompt') or data.get('custom_prompt')
        context = data.get('context')

        if not task_id:
            return jsonify({"error": "task_id is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task = c.fetchone()

        if not task:
            conn.close()
            return jsonify({"error": "Task not found"}), 404

        task_dict = dict(task)
        if custom_prompt:
            task_dict['custom_prompt'] = custom_prompt
        if context:
            task_dict['context'] = context

        logger.info(f"Generating solution for task #{task_id} ({task_dict.get('title')})")
        answer_text = generate_answer_for_task(task_dict)

        c.execute("""
            INSERT INTO solutions (task_id, generated_answer, status)
            VALUES (?, ?, 'GENERATED')
        """, (task_id, answer_text))
        solution_id = c.lastrowid

        c.execute("UPDATE tasks SET status = 'GENERATED', updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", (task_id,))
        conn.commit()

        c.execute("SELECT * FROM solutions WHERE solution_id = ?", (solution_id,))
        solution = c.fetchone()
        conn.close()

        return jsonify({
            "success": True,
            "solution_id": solution_id,
            "solution": dict(solution) if solution else None
        })

    except Exception as e:
        logger.error(f"Error generating AI solution: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/study/<action>', methods=['POST'])
def study_action(action):
    try:
        valid_actions = ['explain', 'summarize', 'notes', 'practice']
        if action.lower() not in valid_actions:
            return jsonify({"error": f"Invalid action. Choose from: {', '.join(valid_actions)}"}), 400

        data = request.json or {}
        topic = data.get('topic')
        course_id = data.get('course_id')

        if not topic:
            return jsonify({"error": "topic is required"}), 400

        material = generate_study_material(action.lower(), topic)

        # Store session in database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO study_sessions (course_id, topic) VALUES (?, ?)", (course_id, topic))
        session_id = c.lastrowid

        c.execute("""
            INSERT INTO notes (session_id, content, type)
            VALUES (?, ?, ?)
        """, (session_id, material, action.upper()))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "action": action,
            "topic": topic,
            "material": material
        })

    except Exception as e:
        logger.error(f"Error executing study action '{action}': {e}")
        return jsonify({"error": str(e)}), 500
