import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key')
    API_PORT = int(os.getenv('API_PORT', 5000))
    API_HOST = os.getenv('API_HOST', '0.0.0.0')

    # AI Configuration
    # Supported: google (gemini), claude (anthropic), groq, openai, deepseek, ollama, fallback
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'groq').lower()
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL_NAME = os.getenv('AI_MODEL_NAME', 'openai/gpt-oss-120b')
    AI_FALLBACK_ON_ERROR = os.getenv('AI_FALLBACK_ON_ERROR', 'true').lower() in ('true', '1', 'yes')

    # Provider-Specific API Keys (takes precedence over generic AI_API_KEY if specified)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

    # Moodle Configuration
    MOODLE_URL = os.getenv('MOODLE_URL', 'http://moodle.local')
    MOODLE_TOKEN = os.getenv('MOODLE_TOKEN', '')
