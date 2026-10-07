import unittest
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from database.database import init_db

class StudyMateAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    def test_health(self):
        response = self.app.get('/api/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'ok')

    def test_task_sync_and_get(self):
        payload = {
            "task": {
                "title": "Calculus Assignment 1",
                "description": "Solve derivatives and integrals.",
                "type": "ASSIGNMENT",
                "dueDate": "2026-12-01",
                "course": "Mathematics 101"
            }
        }
        res_sync = self.app.post('/api/tasks/sync',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        sync_data = json.loads(res_sync.data)
        self.assertEqual(res_sync.status_code, 200)
        self.assertTrue(sync_data['success'])
        task_id = sync_data['task_id']

        # Get all tasks
        res_get = self.app.get('/api/tasks')
        get_data = json.loads(res_get.data)
        self.assertEqual(res_get.status_code, 200)
        self.assertTrue(get_data['success'])
        self.assertTrue(any(t['task_id'] == task_id for t in get_data['tasks']))

        # Get single task
        res_single = self.app.get(f'/api/tasks/{task_id}')
        single_data = json.loads(res_single.data)
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(single_data['task']['title'], "Calculus Assignment 1")

    def test_ai_generate_and_draft_and_submit(self):
        # 1. Sync task
        payload = {
            "task": {
                "title": "Python Data Structures",
                "description": "Implement a binary search tree in Python.",
                "type": "ASSIGNMENT",
                "course": "Computer Science"
            }
        }
        res_sync = self.app.post('/api/tasks/sync',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        task_id = json.loads(res_sync.data)['task_id']

        # 2. Generate solution (offline fallback)
        res_ai = self.app.post('/api/ai/generate',
                               data=json.dumps({"task_id": task_id}),
                               content_type='application/json')
        ai_data = json.loads(res_ai.data)
        self.assertEqual(res_ai.status_code, 200)
        self.assertTrue(ai_data['success'])
        solution_id = ai_data['solution_id']
        self.assertTrue(len(ai_data['solution']['generated_answer']) > 0)

        # 3. Save draft
        res_draft = self.app.post('/api/solutions/draft',
                                  data=json.dumps({
                                      "task_id": task_id,
                                      "solution_id": solution_id,
                                      "edited_answer": "Edited by student: custom binary tree code.",
                                      "status": "APPROVED"
                                  }),
                                  content_type='application/json')
        self.assertEqual(res_draft.status_code, 200)

        # 4. Submit
        res_sub = self.app.post('/api/submissions/submit',
                                data=json.dumps({
                                    "task_id": task_id,
                                    "solution_id": solution_id
                                }),
                                content_type='application/json')
        self.assertEqual(res_sub.status_code, 200)
        self.assertTrue(json.loads(res_sub.data)['success'])

    def test_study_tool(self):
        res = self.app.post('/api/study/explain',
                            data=json.dumps({"topic": "Recursion in Computer Science", "provider": "fallback"}),
                            content_type='application/json')
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['provider'], 'fallback')
        self.assertTrue('Recursion' in data['material'] or len(data['material']) > 0)

    def test_ai_providers_endpoint(self):
        res = self.app.get('/api/ai/providers')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('providers', data)
        self.assertIn('active_provider', data)
        provider_ids = [p['id'] for p in data['providers']]
        self.assertIn('google', provider_ids)
        self.assertIn('claude', provider_ids)
        self.assertIn('groq', provider_ids)
        self.assertIn('openai', provider_ids)

    def test_ai_generate_with_custom_provider(self):
        # 1. Sync task
        payload = {
            "task": {
                "title": "Dijkstra Graph Search",
                "description": "Shortest path algorithm.",
                "type": "ASSIGNMENT",
                "course": "Algorithms"
            }
        }
        res_sync = self.app.post('/api/tasks/sync',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        task_id = json.loads(res_sync.data)['task_id']

        # 2. Generate using fallback provider explicitly
        res_ai = self.app.post('/api/ai/generate',
                               data=json.dumps({
                                   "task_id": task_id,
                                   "provider": "fallback"
                               }),
                               content_type='application/json')
        ai_data = json.loads(res_ai.data)
        self.assertEqual(res_ai.status_code, 200)
        self.assertTrue(ai_data['success'])
        self.assertEqual(ai_data['provider'], 'fallback')
        self.assertIn("Dijkstra Graph Search", ai_data['solution']['generated_answer'])

if __name__ == '__main__':
    unittest.main()
