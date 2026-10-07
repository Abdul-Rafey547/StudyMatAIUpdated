"""
StudyMate AI - AI Orchestration Service
Supports Google Gemini, Anthropic Claude, Groq, OpenAI, DeepSeek, Ollama, and offline fallback.
"""
import os
import json
from typing import Optional, Dict, Any
from config import Config
from ai.prompt_manager import build_assignment_prompt, build_quiz_prompt
from ai.answer_generator import generate_local_fallback
from ai.answer_validator import validate_answer
from ai.providers import get_provider
from utils.logger import get_logger

logger = get_logger('studymate.ai.service')

def generate_answer_for_task(
    task_dict: Dict[str, Any],
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Main entry point for generating assignment and quiz answers across configured or requested AI providers.
    """
    task_type = task_dict.get('type', 'ASSIGNMENT')
    title = task_dict.get('title', 'Academic Task')
    description = task_dict.get('description', '')
    custom_prompt = task_dict.get('custom_prompt')

    if task_type == 'QUIZ':
        prompt = build_quiz_prompt(title, description, custom_prompt)
        system_prompt = "You are StudyMate AI, an academic assistant specialized in accurately solving and explaining university quiz questions."
    else:
        prompt = build_assignment_prompt(title, description, custom_prompt)
        system_prompt = "You are StudyMate AI, an expert academic assistant designed to help university students solve, learn from, and understand their coursework."

    selected_provider_name = (provider_name or Config.AI_PROVIDER or "google").strip().lower()

    if selected_provider_name == "fallback":
        logger.info("[StudyMate AI] Generating solution via offline template fallback...")
        answer = generate_local_fallback(task_dict)
    else:
        try:
            provider = get_provider(
                provider_name=selected_provider_name,
                api_key=api_key,
                model_name=model_name
            )

            if provider.is_configured():
                logger.info(f"[StudyMate AI] Calling {provider.display_name} (Model: {provider.model_name}) for task '{title}'...")
                answer = provider.generate_response(prompt, system_prompt=system_prompt)
            else:
                logger.warning(f"[StudyMate AI] Provider '{selected_provider_name}' has no API key configured. Using offline fallback.")
                answer = generate_local_fallback(task_dict)

        except Exception as e:
            logger.error(f"[StudyMate AI] Error calling {selected_provider_name} API: {e}")
            if Config.AI_FALLBACK_ON_ERROR:
                logger.info("[StudyMate AI] Falling back to intelligent local template generator...")
                answer = generate_local_fallback(task_dict)
            else:
                raise e

    # Validate output
    val = validate_answer(answer, task_dict)
    logger.info(f"[StudyMate AI] Generation result validation: {val}")

    return answer

def generate_study_material(
    action: str,
    topic: str,
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Generate explanations, summaries, notes, or practice questions using configured or requested AI providers.
    """
    prompt = (
        f"StudyMate AI acting as an academic tutor. Please {action} the following topic for a university student:\n\n"
        f"Topic: {topic}\n\n"
        f"Please provide a clear, comprehensive, and well-structured response with headings, bullet points, and code/examples where applicable."
    )
    system_prompt = "You are StudyMate AI, an expert academic tutor dedicated to high quality coursework explanations, notes, and study guides."

    selected_provider_name = (provider_name or Config.AI_PROVIDER or "google").strip().lower()

    if selected_provider_name == "fallback":
        return generate_local_fallback({}, action=action, topic=topic)

    try:
        provider = get_provider(
            provider_name=selected_provider_name,
            api_key=api_key,
            model_name=model_name
        )

        if provider.is_configured():
            logger.info(f"[StudyMate AI] Generating study material via {provider.display_name} ({provider.model_name}) for '{topic}'...")
            return provider.generate_response(prompt, system_prompt=system_prompt)
        else:
            logger.warning(f"[StudyMate AI] Provider '{selected_provider_name}' has no API key configured. Using local study generator.")
            return generate_local_fallback({}, action=action, topic=topic)

    except Exception as e:
        logger.error(f"[StudyMate AI] Error generating study material via {selected_provider_name}: {e}")
        if Config.AI_FALLBACK_ON_ERROR:
            logger.info("[StudyMate AI] Falling back to local study material template...")
            return generate_local_fallback({}, action=action, topic=topic)
        else:
            raise e
