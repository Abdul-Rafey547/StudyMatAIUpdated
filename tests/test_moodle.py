import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from moodle.assignment_parser import AssignmentParser
from moodle.quiz_parser import QuizParser
from moodle.moodle_client import MoodleClient

class MoodleParsersTestCase(unittest.TestCase):
    def test_assignment_parser(self):
        payload = {
            "task": {
                "title": "Machine Learning Lab 1",
                "description": "<p>Train a <strong>Linear Regression</strong> model.</p>",
                "dueDate": "Friday, 12 December 2026",
                "course": "AI 401"
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['title'], "Machine Learning Lab 1")
        self.assertEqual(parsed['course_name'], "AI 401")
        self.assertNotIn("<p>", parsed['description'])
        self.assertIn("Linear Regression", parsed['description'])

    def test_quiz_parser(self):
        payload = {
            "task": {
                "title": "Discrete Math Quiz",
                "questions": [
                    {
                        "index": 1,
                        "question": "<p>Is empty set a subset of every set?</p>",
                        "options": ["A. Yes", "B. No"]
                    }
                ]
            }
        }
        parsed = QuizParser.parse_extension_payload(payload)
        self.assertEqual(parsed['title'], "Discrete Math Quiz")
        self.assertEqual(len(parsed['questions']), 1)
        self.assertNotIn("<p>", parsed['questions'][0]['question'])

    def test_moodle_client_unconfigured(self):
        client = MoodleClient(base_url='', token='')
        self.assertFalse(client.is_configured())
        res = client.get_courses()
        self.assertIn('error', res)

if __name__ == '__main__':
    unittest.main()
