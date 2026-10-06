"""
StudyMate AI - Courses API Blueprint
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from utils.logger import get_logger

logger = get_logger('studymate.api.courses')
courses_bp = Blueprint('courses', __name__)

@courses_bp.route('', methods=['GET'])
def get_courses():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT c.*, COUNT(t.task_id) as task_count
            FROM courses c
            LEFT JOIN tasks t ON c.course_id = t.course_id
            GROUP BY c.course_id
            ORDER BY c.course_name ASC
        """)
        courses = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"success": True, "courses": courses})
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return jsonify({"error": str(e)}), 500
