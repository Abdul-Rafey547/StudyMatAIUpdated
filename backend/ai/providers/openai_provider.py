"""
StudyMate AI - OpenAI Provider
Supports GPT-4o, GPT-4o-mini, GPT-4 Turbo, GPT-3.5-Turbo, o1, o3, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class OpenAIProvider(BaseAIProvider):
    provider_id = "openai"
    display_name = "OpenAI"
    default_model = "gpt-4o"

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("OpenAI API key is missing or not configured.")

        active_model = model or self.model_name or self.default_model
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        endpoint = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.4)
        }

        response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 45))

        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise Exception("Empty choices returned from OpenAI API.")
            return choices[0].get("message", {}).get("content", "")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse OpenAI response: {e}, Raw: {response_data}")
