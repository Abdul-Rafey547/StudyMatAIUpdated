"""
StudyMate AI - AI Solutions & Study API Blueprint
Supports multi-provider execution (Google, Claude, Groq, OpenAI, DeepSeek, Ollama) and provider listing.
"""
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from ai.ai_service import generate_answer_for_task, generate_study_material
from ai.providers.factory import list_available_providers
from config import Config
from utils.logger import get_logger

logger = get_logger('studymate.api.ai')
ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/providers', methods=['GET'])
def get_providers():
    """
    List all supported AI providers (Google Gemini, Anthropic Claude, Groq, OpenAI, Ollama, etc.)
    and their active configuration status.
    """
    providers = list_available_providers()
    return jsonify({
        "success": True,
        "active_provider": Config.AI_PROVIDER,
        "active_model": Config.AI_MODEL_NAME,
        "providers": providers
    })

@ai_bp.route('/generate', methods=['POST'])
def generate_solution():
    try:
        data = request.get_json(silent=True) or {}
        task_id = data.get('task_id') or data.get('taskId')
        custom_prompt = data.get('prompt') or data.get('custom_prompt')
        context = data.get('context')
        
        # Provider options override
        provider_name = data.get('provider') or data.get('ai_provider')
        model_name = data.get('model') or data.get('ai_model')
        api_key = data.get('api_key') or data.get('apiKey')

        # If incoming provider has no key provided and Config has a configured provider with key, prefer Config
        if (not provider_name or provider_name.lower() in ('google', 'gemini')) and not api_key:
            if Config.GROQ_API_KEY:
                provider_name = 'groq'
                model_name = model_name or Config.AI_MODEL_NAME or 'openai/gpt-oss-120b'

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

        logger.info(f"Generating solution for task #{task_id} ({task_dict.get('title')}) with provider: {provider_name or Config.AI_PROVIDER}")
        answer_text = generate_answer_for_task(
            task_dict,
            provider_name=provider_name,
            model_name=model_name,
            api_key=api_key
        )

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
            "provider": provider_name or Config.AI_PROVIDER,
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

        data = request.get_json(silent=True) or {}
        topic = data.get('topic')
        course_id = data.get('course_id')

        # Provider options override
        provider_name = data.get('provider') or data.get('ai_provider')
        model_name = data.get('model') or data.get('ai_model')
        api_key = data.get('api_key') or data.get('apiKey')

        if not topic:
            return jsonify({"error": "topic is required"}), 400

        material = generate_study_material(
            action.lower(),
            topic,
            provider_name=provider_name,
            model_name=model_name,
            api_key=api_key
        )

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
            "provider": provider_name or Config.AI_PROVIDER,
            "material": material
        })

    except Exception as e:
        logger.error(f"Error executing study action '{action}': {e}")
        return jsonify({"error": str(e)}), 500
