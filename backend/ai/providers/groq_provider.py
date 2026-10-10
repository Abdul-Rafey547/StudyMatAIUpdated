"""
StudyMate AI - Groq Cloud Provider
Supports ultra-fast Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class GroqProvider(BaseAIProvider):
    provider_id = "groq"
    display_name = "Groq Cloud"
    default_model = "openai/gpt-oss-120b"
    fallback_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("Groq API key is missing or not configured.")

        requested_model = (model or self.model_name or self.default_model).strip()
        models_to_try = [requested_model]
        for fb in self.fallback_models:
            if fb not in models_to_try:
                models_to_try.append(fb)

        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for active_model in models_to_try:
            payload: Dict[str, Any] = {
                "model": active_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.3)
            }

            try:
                response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 50))
                choices = response_data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content
                last_error = Exception(f"Empty choices returned from Groq model {active_model}.")
            except Exception as e:
                last_error = e
                # Continue to next candidate model if available
                continue

        raise Exception(f"All Groq models failed. Last error: {last_error}")
