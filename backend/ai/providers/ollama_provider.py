"""
StudyMate AI - Ollama (Local LLM) Provider
Supports local models like llama3, mistral, qwen2.5, phi3, deepseek-r1, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class OllamaProvider(BaseAIProvider):
    provider_id = "ollama"
    display_name = "Ollama (Local LLM)"
    default_model = "llama3"

    def is_configured(self) -> bool:
        # Ollama does not strictly require an API key if running locally
        return True

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        active_model = model or self.model_name or self.default_model
        base = (self.base_url or "http://localhost:11434").rstrip("/")
        endpoint = f"{base}/api/generate"
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key and self.api_key.lower() not in ("local", "none", ""):
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": active_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.4)
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 60))

        try:
            return response_data.get("response", "")
        except Exception as e:
            raise Exception(f"Failed to parse Ollama response: {e}, Raw: {response_data}")
