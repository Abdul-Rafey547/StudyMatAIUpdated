"""
StudyMate AI - Groq Cloud Provider
Supports ultra-fast Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class GroqProvider(BaseAIProvider):
    provider_id = "groq"
    display_name = "Groq Cloud"
    default_model = "llama-3.3-70b-versatile"

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("Groq API key is missing or not configured.")

        active_model = model or self.model_name or self.default_model
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
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
                raise Exception("Empty choices returned from Groq API.")
            return choices[0].get("message", {}).get("content", "")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Groq response: {e}, Raw: {response_data}")
