"""
StudyMate AI - DeepSeek Provider
Supports DeepSeek-Chat (V3) and DeepSeek-Reasoner (R1).
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class DeepSeekProvider(BaseAIProvider):
    provider_id = "deepseek"
    display_name = "DeepSeek"
    default_model = "deepseek-chat"

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("DeepSeek API key is missing or not configured.")

        active_model = model or self.model_name or self.default_model
        base = (self.base_url or "https://api.deepseek.com").rstrip("/")
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

        response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 60))

        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise Exception("Empty choices returned from DeepSeek API.")
            return choices[0].get("message", {}).get("content", "")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse DeepSeek response: {e}, Raw: {response_data}")
