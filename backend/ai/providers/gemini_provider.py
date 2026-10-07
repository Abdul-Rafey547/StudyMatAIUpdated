"""
StudyMate AI - Google Gemini Provider
Supports Gemini 1.5 Flash, Gemini 1.5 Pro, Gemini 2.0 Flash, etc.
"""
from typing import Optional, Dict, Any
from .base import BaseAIProvider

class GeminiProvider(BaseAIProvider):
    provider_id = "google"
    display_name = "Google Gemini"
    default_model = "gemini-1.5-flash"

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        if not self.is_configured():
            raise ValueError("Google Gemini API key is missing or not configured.")

        active_model = model or self.model_name or self.default_model
        # Strip any prefix like 'models/' if user added it
        if active_model.startswith("models/"):
            active_model = active_model.replace("models/", "")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }

        # Build payload according to Google Generative Language API schema
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.4),
                "maxOutputTokens": kwargs.get("max_tokens", 4096)
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [
                    {"text": system_prompt}
                ]
            }

        response_data = self._http_post_json(endpoint, payload, headers, timeout=kwargs.get("timeout", 45))

        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                # Check for promptFeedback or safety block
                feedback = response_data.get("promptFeedback", {})
                block_reason = feedback.get("blockReason")
                if block_reason:
                    raise Exception(f"Gemini blocked content generation: {block_reason}")
                raise Exception("Gemini returned empty candidates in response.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise Exception("No text parts returned in Gemini candidate response.")

            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Gemini response: {e}, Raw: {response_data}")
