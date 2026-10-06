"""
StudyMate AI - Assignments API Blueprint
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from utils.logger import get_logger

logger = get_logger('studymate.api.assignments')
assignments_bp = Blueprint('assignments', __name__)

@assignments_bp.route('', methods=['GET'])
def get_assignments():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.*, c.course_name
            FROM tasks t
            LEFT JOIN courses c ON t.course_id = c.course_id
            WHERE t.type = 'ASSIGNMENT'
            ORDER BY t.created_at DESC
        """)
        assignments = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"success": True, "assignments": assignments})
    except Exception as e:
        logger.error(f"Error fetching assignments: {e}")
        return jsonify({"error": str(e)}), 500
