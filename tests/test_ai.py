import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai.ai_service import generate_answer_for_task, generate_study_material
from ai.prompt_manager import build_assignment_prompt, build_quiz_prompt
from ai.answer_validator import validate_answer

from ai.providers import (
    get_provider,
    list_available_providers,
    GeminiProvider,
    ClaudeProvider,
    GroqProvider,
    OpenAIProvider,
    DeepSeekProvider,
    OllamaProvider
)

class AITestCase(unittest.TestCase):
    def test_prompt_manager(self):
        prompt = build_assignment_prompt("Sorting Assignment", "Implement QuickSort")
        self.assertIn("Sorting Assignment", prompt)
        self.assertIn("QuickSort", prompt)

        quiz_prompt = build_quiz_prompt("Database Quiz", "1. What is primary key?")
        self.assertIn("Database Quiz", quiz_prompt)

    def test_answer_validator(self):
        val_empty = validate_answer("", {})
        self.assertFalse(val_empty['valid'])

        val_good = validate_answer("This is a comprehensive academic answer with more than twenty characters explaining the solution.", {})
        self.assertTrue(val_good['valid'])
        self.assertGreater(val_good['word_count'], 5)

    def test_local_fallback_generation(self):
        task = {
            "type": "ASSIGNMENT",
            "title": "OS Scheduling",
            "description": "Explain Round Robin scheduling algorithm."
        }
        answer = generate_answer_for_task(task, provider_name="fallback")
        self.assertIsInstance(answer, str)
        self.assertIn("OS Scheduling", answer)

    def test_study_material_generation(self):
        material = generate_study_material("explain", "Dijkstra Algorithm", provider_name="fallback")
        self.assertIsInstance(material, str)
        self.assertTrue(len(material) > 0)
        self.assertIn("Dijkstra", material)

    def test_provider_factory_and_classes(self):
        gemini = get_provider("google", api_key="test-key")
        self.assertIsInstance(gemini, GeminiProvider)
        self.assertEqual(gemini.api_key, "test-key")
        self.assertEqual(gemini.model_name, "gemini-1.5-flash")

        claude = get_provider("claude", api_key="test-key", model_name="claude-3-5-haiku-20241022")
        self.assertIsInstance(claude, ClaudeProvider)
        self.assertEqual(claude.model_name, "claude-3-5-haiku-20241022")

        groq = get_provider("groq", api_key="gsk_test")
        self.assertIsInstance(groq, GroqProvider)
        self.assertEqual(groq.model_name, "llama-3.3-70b-versatile")

        openai_p = get_provider("openai", api_key="sk-test")
        self.assertIsInstance(openai_p, OpenAIProvider)
        self.assertEqual(openai_p.model_name, "gpt-4o")

        deepseek = get_provider("deepseek", api_key="sk-ds-test")
        self.assertIsInstance(deepseek, DeepSeekProvider)
        self.assertEqual(deepseek.model_name, "deepseek-chat")

        ollama = get_provider("ollama", model_name="llama3.1")
        self.assertIsInstance(ollama, OllamaProvider)
        self.assertEqual(ollama.model_name, "llama3.1")
        self.assertTrue(ollama.is_configured())

    def test_list_available_providers(self):
        providers = list_available_providers()
        self.assertIsInstance(providers, list)
        provider_ids = [p['id'] for p in providers]
        self.assertIn('google', provider_ids)
        self.assertIn('claude', provider_ids)
        self.assertIn('groq', provider_ids)
        self.assertIn('openai', provider_ids)
        self.assertIn('deepseek', provider_ids)
        self.assertIn('ollama', provider_ids)

if __name__ == '__main__':
    unittest.main()
