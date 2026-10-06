"""
Core generation logic, supporting OpenAI, Anthropic, or an intelligent fallback system if no API key is present.
"""
import os
import json
import urllib.request
import urllib.error
from config import Config
from ai.prompt_manager import build_assignment_prompt, build_quiz_prompt
from ai.answer_generator import call_openai_api, generate_local_fallback
from ai.answer_validator import validate_answer

def generate_answer_for_task(task_dict):
    """
    Main entry point for generating answers.
    """
    api_key = Config.AI_API_KEY
    model_name = Config.AI_MODEL_NAME
    task_type = task_dict.get('type', 'ASSIGNMENT')
    title = task_dict.get('title', 'Academic Task')
    description = task_dict.get('description', '')
    custom_prompt = task_dict.get('custom_prompt')

    # If API key is available, use live API
    if api_key and api_key.strip():
        if task_type == 'QUIZ':
            prompt = build_quiz_prompt(title, description, custom_prompt)
        else:
            prompt = build_assignment_prompt(title, description, custom_prompt)

        answer = call_openai_api(api_key, model_name, prompt)
    else:
        # Fallback to local intelligent template generator
        answer = generate_local_fallback(task_dict)

    # Validate output
    val = validate_answer(answer, task_dict)
    print(f"[StudyMate AI] Generation result validation: {val}")

    return answer

def generate_study_material(action, topic):
    """
    Generate explanations, summaries, notes, or practice questions.
    """
    # Simply mapping to structured prompts for various study actions
    prompt = f"StudyMate AI acting as an academic tutor. Please {action} the following topic for a university student:\n\nTopic: {topic}\n\nPlease provide a clear, concise, and structured response."

    api_key = Config.AI_API_KEY
    if api_key and api_key.strip():
        return call_openai_api(api_key, Config.AI_MODEL_NAME, prompt)

    return f"### {action.capitalize()}: {topic.capitalize()}\n\n[StudyMate AI Demo] \nThis is a generated example of {action} material for the topic '{topic}'. Configure your API key to get real, context-aware AI study materials."
