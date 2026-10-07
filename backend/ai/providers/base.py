"""
StudyMate AI - Base AI Provider Interface
"""
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

class BaseAIProvider:
    """
    Abstract Base Class for all LLM Providers (Google Gemini, Anthropic Claude, Groq, OpenAI, etc.)
    """
    provider_id: str = "base"
    display_name: str = "Base Provider"
    default_model: str = "default"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "").strip() or self.default_model
        self.base_url = (base_url or "").strip()
        self.extra_config = kwargs

    def is_configured(self) -> bool:
        """Check if provider has required credentials or configuration."""
        return bool(self.api_key)

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> str:
        """
        Generate completion for a given prompt and optional system prompt.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_response")

    def _http_post_json(self, url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 45) -> Dict[str, Any]:
        """
        Helper method to execute HTTP POST requests with JSON payload using standard urllib.
        """
        json_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_text = response.read().decode('utf-8')
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                error_body = str(e)
            raise Exception(f"{self.display_name} API Error (HTTP {e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed for {self.display_name} API: {e.reason}")
        except Exception as e:
            raise Exception(f"Error communicating with {self.display_name} API: {str(e)}")
