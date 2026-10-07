"""
StudyMate AI - Anthropic Claude Provider
Supports Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus, Claude 3.7 Sonnet, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class ClaudeProvider(BaseAIProvider):
    provider_id = "claude"
    display_name = "Anthropic Claude"
    default_model = "claude-3-5-sonnet-20241022"

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("Anthropic Claude API key is missing or not configured.")

        active_model = model or self.model_name or self.default_model
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": active_model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.4)
        }

        if system_prompt:
            payload["system"] = system_prompt

        response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 45))

        try:
            content_blocks = response_data.get("content", [])
            text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            if not text_blocks:
                raise Exception("No text content returned from Claude API.")
            return "".join(text_blocks)
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Claude response: {e}, Raw: {response_data}")
