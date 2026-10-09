"""
Unit tests for Bug 3: Assignment File Generation & Truthful Moodle Submission Verification.
Tests real file generation (DOCX, TXT), human-approved content integrity, draft vs final submission, and unverified state handling.
"""
import unittest
import json
import base64
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from database.database import init_db
import docx

class SubmissionsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    def test_docx_file_generation_from_approved_answer(self):
        """Generate a valid DOCX assignment file from student-approved solution."""
        # 1. Sync task
        t_res = self.app.post('/api/tasks/sync', data=json.dumps({
            "task": {
                "title": "Data Structures Assignment 2",
                "description": "Implement AVL Tree balancing operations.",
                "course": "Computer Science 201",
                "type": "ASSIGNMENT"
            }
        }), content_type='application/json')
        task_id = json.loads(t_res.data)['task_id']

        # 2. Save approved draft
        approved_solution = (
            "# AVL Tree Implementation\n\n"
            "An AVL tree is a self-balancing binary search tree where the difference between heights "
            "of left and right subtrees cannot be more than one for all nodes.\n\n"
            "```python\n"
            "class AVLNode:\n"
            "    def __init__(self, key):\n"
            "        self.key = key\n"
            "        self.left = None\n"
            "        self.right = None\n"
            "        self.height = 1\n"
            "```\n\n"
            "Rotations maintain balance in O(log n) time complexity."
        )

        d_res = self.app.post('/api/solutions/draft', data=json.dumps({
            "task_id": task_id,
            "edited_answer": approved_solution,
            "status": "APPROVED"
        }), content_type='application/json')
        solution_id = json.loads(d_res.data)['solution_id']

        # 3. Generate DOCX file
        f_res = self.app.post('/api/submissions/generate-file', data=json.dumps({
            "task_id": task_id,
            "solution_id": solution_id,
            "format": "DOCX"
        }), content_type='application/json')
        file_data = json.loads(f_res.data)
        self.assertEqual(f_res.status_code, 200)
        self.assertTrue(file_data['success'])
        self.assertTrue(file_data['file_name'].endswith('.docx'))
        self.assertIn("application/vnd.openxmlformats-officedocument", file_data['mime_type'])

        # Verify binary validity using python-docx
        file_bytes = base64.b64decode(file_data['file_base64'])
        doc = docx.Document(io.BytesIO(file_bytes))
        doc_text = " ".join(p.text for p in doc.paragraphs)
        self.assertIn("Data Structures Assignment 2", doc_text)
        self.assertIn("AVL Tree Implementation", doc_text)
        self.assertIn("class AVLNode", doc_text)

    def test_txt_file_generation(self):
        """Generate a valid TXT assignment file."""
        t_res = self.app.post('/api/tasks/sync', data=json.dumps({
            "task": {
                "title": "Ethics Essay",
                "course": "Philosophy 101",
                "type": "ASSIGNMENT"
            }
        }), content_type='application/json')
        task_id = json.loads(t_res.data)['task_id']

        f_res = self.app.post('/api/submissions/generate-file', data=json.dumps({
            "task_id": task_id,
            "answer": "Ethical implications of automated algorithmic decision making.",
            "format": "TXT"
        }), content_type='application/json')
        file_data = json.loads(f_res.data)
        self.assertEqual(f_res.status_code, 200)
        self.assertTrue(file_data['success'])
        self.assertTrue(file_data['file_name'].endswith('.txt'))
        raw_text = base64.b64decode(file_data['file_base64']).decode('utf-8')
        self.assertIn("ETHICS ESSAY", raw_text)
        self.assertIn("Philosophy 101", raw_text)

    def test_empty_answer_rejection(self):
        """Empty answer cannot generate a submission file."""
        f_res = self.app.post('/api/submissions/generate-file', data=json.dumps({
            "answer": "   ",
            "format": "DOCX"
        }), content_type='application/json')
        self.assertEqual(f_res.status_code, 400)

    def test_truthful_verification_confirmed_submission(self):
        """Moodle confirmed submission ('Submitted for grading') is truthfully verified."""
        t_res = self.app.post('/api/tasks/sync', data=json.dumps({
            "task": {
                "title": "Robotics Lab 3",
                "course": "Engineering 301",
                "type": "ASSIGNMENT"
            }
        }), content_type='application/json')
        task_id = json.loads(t_res.data)['task_id']

        v_res = self.app.post('/api/submissions/verify', data=json.dumps({
            "task_id": task_id,
            "moodle_status": "Submitted for grading",
            "file_name": "Robotics_Lab_3.docx",
            "file_format": "DOCX"
        }), content_type='application/json')
        data = json.loads(v_res.data)
        self.assertEqual(v_res.status_code, 200)
        self.assertTrue(data['success'])
        self.assertTrue(data['verified'])
        self.assertEqual(data['status'], 'SUBMITTED')

        # Check task state in database
        t_get = self.app.get(f'/api/tasks/{task_id}')
        task = json.loads(t_get.data)['task']
        self.assertEqual(task['status'], 'SUBMITTED')
        self.assertEqual(task['availability_status'], 'SUBMITTED')
        self.assertEqual(task['is_actionable_pending'], 0)

    def test_truthful_verification_draft_upload_state(self):
        """Moodle draft state ('Draft (not submitted)') is NOT marked as completed submission."""
        t_res = self.app.post('/api/tasks/sync', data=json.dumps({
            "task": {
                "title": "Quantum Physics Essay",
                "course": "Physics 401",
                "type": "ASSIGNMENT"
            }
        }), content_type='application/json')
        task_id = json.loads(t_res.data)['task_id']

        v_res = self.app.post('/api/submissions/verify', data=json.dumps({
            "task_id": task_id,
            "moodle_status": "Draft (not submitted)",
            "file_name": "Quantum_Physics_Essay.docx",
            "file_format": "DOCX"
        }), content_type='application/json')
        data = json.loads(v_res.data)
        self.assertEqual(v_res.status_code, 200)
        self.assertFalse(data['verified'])
        self.assertTrue(data['is_draft'])
        self.assertEqual(data['status'], 'DRAFT')

        # Check task state in database: must be 'In Draft', NOT 'Submitted'
        t_get = self.app.get(f'/api/tasks/{task_id}')
        task = json.loads(t_get.data)['task']
        self.assertNotEqual(task['status'], 'SUBMITTED')
        self.assertEqual(task['status'], 'In Draft')

    def test_truthful_verification_unverified_attempt(self):
        """Inconclusive status does NOT produce a false success message."""
        t_res = self.app.post('/api/tasks/sync', data=json.dumps({
            "task": {
                "title": "Economics Quiz",
                "course": "ECON 101",
                "type": "ASSIGNMENT"
            }
        }), content_type='application/json')
        task_id = json.loads(t_res.data)['task_id']

        v_res = self.app.post('/api/submissions/verify', data=json.dumps({
            "task_id": task_id,
            "moodle_status": "Unknown navigation state",
            "verified": False
        }), content_type='application/json')
        data = json.loads(v_res.data)
        self.assertEqual(v_res.status_code, 200)
        self.assertFalse(data['verified'])
        self.assertTrue(data['unverified'])

        # Check database: NOT marked as submitted
        t_get = self.app.get(f'/api/tasks/{task_id}')
        task = json.loads(t_get.data)['task']
        self.assertNotEqual(task['status'], 'SUBMITTED')

if __name__ == '__main__':
    unittest.main()
