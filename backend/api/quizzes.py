"""
StudyMate AI - Quizzes API Blueprint
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from utils.logger import get_logger

logger = get_logger('studymate.api.quizzes')
quizzes_bp = Blueprint('quizzes', __name__)

@quizzes_bp.route('', methods=['GET'])
def get_quizzes():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.*, c.course_name
            FROM tasks t
            LEFT JOIN courses c ON t.course_id = c.course_id
            WHERE t.type = 'QUIZ'
            ORDER BY t.created_at DESC
        """)
        quizzes = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"success": True, "quizzes": quizzes})
    except Exception as e:
        logger.error(f"Error fetching quizzes: {e}")
        return jsonify({"error": str(e)}), 500
