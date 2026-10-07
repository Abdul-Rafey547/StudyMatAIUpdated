"""
StudyMate AI - AI Provider Factory & Registry
"""
from typing import Dict, Type, Optional, List, Any
from .base import BaseAIProvider
from .gemini_provider import GeminiProvider
from .claude_provider import ClaudeProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .deepseek_provider import DeepSeekProvider
from .ollama_provider import OllamaProvider

PROVIDER_REGISTRY: Dict[str, Type[BaseAIProvider]] = {
    "google": GeminiProvider,
    "gemini": GeminiProvider,
    "google-gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "anthropic": ClaudeProvider,
    "anthropic-claude": ClaudeProvider,
    "groq": GroqProvider,
    "groq-cloud": GroqProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "ollama": OllamaProvider,
    "local": OllamaProvider
}

PROVIDER_METADATA: Dict[str, Dict[str, Any]] = {
    "google": {
        "id": "google",
        "name": "Google Gemini",
        "default_model": "gemini-1.5-flash",
        "recommended_models": [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite"
        ],
        "env_key": "GEMINI_API_KEY",
        "doc_url": "https://aistudio.google.com/app/apikey"
    },
    "claude": {
        "id": "claude",
        "name": "Anthropic Claude",
        "default_model": "claude-3-5-sonnet-20241022",
        "recommended_models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-haiku-20240307",
            "claude-3-7-sonnet-20250219"
        ],
        "env_key": "ANTHROPIC_API_KEY",
        "doc_url": "https://console.anthropic.com/settings/keys"
    },
    "groq": {
        "id": "groq",
        "name": "Groq Cloud (Ultra Fast)",
        "default_model": "llama-3.3-70b-versatile",
        "recommended_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        "env_key": "GROQ_API_KEY",
        "doc_url": "https://console.groq.com/keys"
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI GPT",
        "default_model": "gpt-4o",
        "recommended_models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        "env_key": "OPENAI_API_KEY",
        "doc_url": "https://platform.openai.com/api-keys"
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek",
        "default_model": "deepseek-chat",
        "recommended_models": [
            "deepseek-chat",
            "deepseek-reasoner"
        ],
        "env_key": "DEEPSEEK_API_KEY",
        "doc_url": "https://platform.deepseek.com/api_keys"
    },
    "ollama": {
        "id": "ollama",
        "name": "Ollama (Local LLM)",
        "default_model": "llama3",
        "recommended_models": [
            "llama3",
            "llama3.1",
            "mistral",
            "qwen2.5",
            "deepseek-r1"
        ],
        "env_key": "OLLAMA_BASE_URL",
        "doc_url": "https://ollama.com"
    }
}

def resolve_provider_key(provider_id: str) -> Optional[str]:
    """
    Look up API key for a provider from Config or environment variables.
    Checks provider-specific key first, then generic AI_API_KEY if this provider is active.
    """
    from config import Config
    p = (provider_id or "").strip().lower()
    active_p = (Config.AI_PROVIDER or "").strip().lower()

    if p in ("google", "gemini", "google-gemini"):
        if Config.GEMINI_API_KEY:
            return Config.GEMINI_API_KEY
        if active_p in ("google", "gemini", "google-gemini", ""):
            return Config.AI_API_KEY
        return ""
    elif p in ("claude", "anthropic", "anthropic-claude"):
        if Config.ANTHROPIC_API_KEY:
            return Config.ANTHROPIC_API_KEY
        if active_p in ("claude", "anthropic", "anthropic-claude"):
            return Config.AI_API_KEY
        return ""
    elif p in ("groq", "groq-cloud"):
        if Config.GROQ_API_KEY:
            return Config.GROQ_API_KEY
        if active_p in ("groq", "groq-cloud"):
            return Config.AI_API_KEY
        return ""
    elif p in ("openai", "gpt"):
        if Config.OPENAI_API_KEY:
            return Config.OPENAI_API_KEY
        if active_p in ("openai", "gpt"):
            return Config.AI_API_KEY
        return ""
    elif p in ("deepseek",):
        if Config.DEEPSEEK_API_KEY:
            return Config.DEEPSEEK_API_KEY
        if active_p in ("deepseek",):
            return Config.AI_API_KEY
        return ""
    elif p in ("ollama", "local"):
        return "local"

    return Config.AI_API_KEY if active_p == p else ""

def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> BaseAIProvider:
    """
    Instantiate and return the requested AI Provider.
    Falls back to Config.AI_PROVIDER if not specified.
    """
    from config import Config

    target_name = (provider_name or Config.AI_PROVIDER or "google").strip().lower()
    provider_cls = PROVIDER_REGISTRY.get(target_name)

    if not provider_cls:
        # Fallback to google provider if unknown
        provider_cls = GeminiProvider
        target_name = "google"

    # Resolve API Key
    effective_key = api_key if (api_key and api_key.strip()) else resolve_provider_key(target_name)
    
    # Resolve Model Name
    effective_model = (model_name or "").strip()
    if not effective_model:
        if Config.AI_MODEL_NAME and target_name in ((Config.AI_PROVIDER or "").lower(),):
            effective_model = Config.AI_MODEL_NAME
        else:
            effective_model = provider_cls.default_model

    # Resolve Base URL
    effective_base_url = base_url
    if not effective_base_url and target_name in ("ollama", "local"):
        effective_base_url = getattr(Config, 'OLLAMA_BASE_URL', 'http://localhost:11434')

    return provider_cls(
        api_key=effective_key,
        model_name=effective_model,
        base_url=effective_base_url,
        **kwargs
    )

def list_available_providers() -> List[Dict[str, Any]]:
    """
    List supported providers with configuration status for UI and client apps.
    """
    from config import Config
    result = []
    for pid, meta in PROVIDER_METADATA.items():
        key = resolve_provider_key(pid)
        is_active = (Config.AI_PROVIDER or "google").lower() in (pid, meta["name"].lower())
        result.append({
            "id": pid,
            "name": meta["name"],
            "default_model": meta["default_model"],
            "recommended_models": meta["recommended_models"],
            "configured": bool(key and key.strip()) or (pid == "ollama"),
            "is_active": is_active,
            "doc_url": meta.get("doc_url", "")
        })
    return result
