import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key')
    API_PORT = int(os.getenv('API_PORT', 5000))
    API_HOST = os.getenv('API_HOST', '0.0.0.0')

    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai') # e.g. openai, anthropic, gemini
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL_NAME = os.getenv('AI_MODEL_NAME', 'gpt-4o')

    # Moodle Configuration
    MOODLE_URL = os.getenv('MOODLE_URL', 'http://moodle.local')
    MOODLE_TOKEN = os.getenv('MOODLE_TOKEN', '')
