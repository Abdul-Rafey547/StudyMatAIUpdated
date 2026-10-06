import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai.ai_service import generate_answer_for_task, generate_study_material
from ai.prompt_manager import build_assignment_prompt, build_quiz_prompt
from ai.answer_validator import validate_answer

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
        # Without OpenAI key, it uses intelligent local fallback
        task = {
            "type": "ASSIGNMENT",
            "title": "OS Scheduling",
            "description": "Explain Round Robin scheduling algorithm."
        }
        answer = generate_answer_for_task(task)
        self.assertIsInstance(answer, str)
        self.assertIn("OS Scheduling", answer)

    def test_study_material_generation(self):
        material = generate_study_material("explain", "Dijkstra Algorithm")
        self.assertIsInstance(material, str)
        self.assertTrue(len(material) > 0)

if __name__ == '__main__':
    unittest.main()
