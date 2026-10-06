"""
StudyMate AI - Main Flask Application Server
Provides REST API endpoints for the Chrome Extension and Dashboard.
"""
import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure backend directory is in path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from database.database import get_db_connection, init_db
from ai.ai_service import generate_answer_for_task, generate_study_material
from utils.logger import get_logger

# Import Blueprints
from api.tasks import tasks_bp
from api.assignments import assignments_bp
from api.quizzes import quizzes_bp
from api.courses import courses_bp
from api.ai import ai_bp
from api.submissions import submissions_bp

logger = get_logger('studymate.app')

# Initialize database
init_db()

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # Allow extension to call API

# Register Modular Blueprints under /api
app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
app.register_blueprint(assignments_bp, url_prefix='/api/assignments')
app.register_blueprint(quizzes_bp, url_prefix='/api/quizzes')
app.register_blueprint(courses_bp, url_prefix='/api/courses')
app.register_blueprint(ai_bp, url_prefix='/api/ai')
app.register_blueprint(submissions_bp, url_prefix='/api/submissions')
app.register_blueprint(submissions_bp, name='solutions_bp', url_prefix='/api/solutions')

# Direct Root Routes for Backwards Compatibility
@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint for Chrome extension to verify backend is up."""
    return jsonify({
        "status": "ok",
        "message": "StudyMate AI Backend is running.",
        "ai_provider": Config.AI_PROVIDER,
        "ai_model": Config.AI_MODEL_NAME
    })

# Aliases for direct legacy calls
@app.route('/api/study/<action>', methods=['POST'])
def legacy_study_tool(action):
    from api.ai import study_action
    return study_action(action)

if __name__ == '__main__':
    logger.info(f"Starting StudyMate AI Backend on {Config.API_HOST}:{Config.API_PORT}...")
    app.run(host=Config.API_HOST, port=Config.API_PORT, debug=True)
