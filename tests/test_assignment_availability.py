"""
Unit tests for Bug 1: Moodle Assignment Availability & Categorization Logic.
Tests all 9 availability states, stable deduplication, and actionable pending filtering.
"""
import unittest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from database.database import init_db, get_db_connection
from moodle.assignment_parser import AssignmentParser

class AssignmentAvailabilityTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    def test_cat1_open_available_assignment(self):
        """Cat 1: Open assignment with no attempt appears as actionable pending."""
        payload = {
            "task": {
                "title": "Algorithms Problem Set 1",
                "description": "Solve divide-and-conquer recurrences.",
                "type": "ASSIGNMENT",
                "dueDate": "2026-11-15",
                "course": "CS 301",
                "moodle_activity_id": "101",
                "submissionStatus": "No attempt",
                "gradingStatus": "Not graded"
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'AVAILABLE')
        self.assertEqual(parsed['is_actionable_pending'], 1)
        self.assertEqual(parsed['status'], 'PENDING')

        # Sync via API
        res = self.app.post('/api/tasks/sync', data=json.dumps(payload), content_type='application/json')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['is_actionable_pending'])
        self.assertEqual(data['availability_status'], 'AVAILABLE')

        # Check pending filter
        get_res = self.app.get('/api/tasks?pending_only=true')
        tasks = json.loads(get_res.data)['tasks']
        self.assertTrue(any(t['task_id'] == data['task_id'] for t in tasks))

    def test_cat2_submitted_assignment_no_resubmission(self):
        """Cat 2: Submitted assignment does not appear as pending unless resubmission is permitted."""
        payload = {
            "task": {
                "title": "Machine Learning Lab 2",
                "description": "Neural Networks implementation.",
                "type": "ASSIGNMENT",
                "course": "AI 402",
                "moodle_activity_id": "102",
                "submissionStatus": "Submitted for grading",
                "gradingStatus": "Not graded",
                "resubmissionAllowed": False
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'SUBMITTED')
        self.assertEqual(parsed['is_actionable_pending'], 0)
        self.assertEqual(parsed['status'], 'SUBMITTED')

        # Sync and verify it does NOT appear in pending_only list
        res = self.app.post('/api/tasks/sync', data=json.dumps(payload), content_type='application/json')
        task_id = json.loads(res.data)['task_id']

        get_res = self.app.get('/api/tasks?pending_only=true')
        tasks = json.loads(get_res.data)['tasks']
        self.assertFalse(any(t['task_id'] == task_id for t in tasks))

    def test_cat2_submitted_assignment_with_resubmission_permitted(self):
        """Cat 2 (variant): Submitted assignment where Moodle explicitly allows resubmission."""
        payload = {
            "task": {
                "title": "Software Engineering Draft",
                "description": "Architecture Design Document.",
                "type": "ASSIGNMENT",
                "course": "SE 201",
                "moodle_activity_id": "103",
                "submissionStatus": "Submitted for grading",
                "gradingStatus": "Not graded",
                "resubmissionAllowed": True
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'AVAILABLE')
        self.assertEqual(parsed['is_actionable_pending'], 1)
        self.assertEqual(parsed['resubmission_allowed'], 1)

    def test_cat3_completed_or_graded_assignment(self):
        """Cat 3: Graded / completed assignment does not reappear as pending."""
        payload = {
            "task": {
                "title": "Calculus Midterm Assignment",
                "description": "Taylor series approximations.",
                "type": "ASSIGNMENT",
                "course": "MATH 101",
                "moodle_activity_id": "104",
                "submissionStatus": "Submitted for grading",
                "gradingStatus": "Graded",
                "resubmissionAllowed": False
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'COMPLETED')
        self.assertEqual(parsed['is_actionable_pending'], 0)
        self.assertEqual(parsed['status'], 'COMPLETED')

    def test_cat4_upcoming_not_yet_open(self):
        """Cat 4: Assignment not yet open does not appear as actionable pending work."""
        payload = {
            "task": {
                "title": "Final Project Phase 2",
                "description": "Will accept submissions starting next month.",
                "type": "ASSIGNMENT",
                "course": "CS 499",
                "moodle_activity_id": "105",
                "submissionStatus": "This assignment will accept submissions from Monday, 1 December 2026",
                "isUpcoming": True
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'UPCOMING')
        self.assertEqual(parsed['is_actionable_pending'], 0)

    def test_cat5_deadline_passed_closed(self):
        """Cat 5: Assignment whose deadline passed and no longer accepts submissions."""
        payload = {
            "task": {
                "title": "Physics Lab 1",
                "description": "Pendulum harmonic motion.",
                "type": "ASSIGNMENT",
                "course": "PHYS 101",
                "moodle_activity_id": "106",
                "submissionStatus": "Submissions are closed",
                "isClosed": True
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'CLOSED')
        self.assertEqual(parsed['is_actionable_pending'], 0)

    def test_cat6_hidden_or_restricted_assignment(self):
        """Cat 6: Hidden or restricted activity is not added as pending."""
        payload = {
            "task": {
                "title": "Honors Extension Project",
                "description": "Restricted to Honors students.",
                "type": "ASSIGNMENT",
                "course": "CS 301",
                "moodle_activity_id": "107",
                "isHidden": True
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'UNAVAILABLE')
        self.assertEqual(parsed['is_actionable_pending'], 0)

    def test_cat7_status_unknown_unverified(self):
        """Cat 7: Status cannot be verified; never assume unknown means pending."""
        payload = {
            "task": {
                "title": "Generic Course Link",
                "type": "ASSIGNMENT",
                "course": "CS 101",
                "moodle_activity_id": "108",
                "isUnverified": True,
                "availabilityStatus": "UNVERIFIED"
            }
        }
        parsed = AssignmentParser.parse_extension_payload(payload)
        self.assertEqual(parsed['availability_status'], 'UNVERIFIED')
        self.assertEqual(parsed['is_actionable_pending'], 0)
        self.assertEqual(parsed['status'], 'UNVERIFIED')

    def test_stable_deduplication_and_state_update(self):
        """Refreshing page or scanning repeatedly updates existing record without duplicate tasks."""
        payload = {
            "task": {
                "title": "Operating Systems Lab 3",
                "description": "Process scheduling in C.",
                "type": "ASSIGNMENT",
                "course": "CS 350",
                "moodle_activity_id": "201",
                "submissionStatus": "No attempt"
            }
        }
        # Initial scan: available pending
        res1 = self.app.post('/api/tasks/sync', data=json.dumps(payload), content_type='application/json')
        id1 = json.loads(res1.data)['task_id']

        # Second scan: same activity ID, now student submitted on Moodle
        payload['task']['submissionStatus'] = 'Submitted for grading'
        payload['task']['resubmissionAllowed'] = False
        res2 = self.app.post('/api/tasks/sync', data=json.dumps(payload), content_type='application/json')
        id2 = json.loads(res2.data)['task_id']

        # Must be the exact same database task ID, not duplicated
        self.assertEqual(id1, id2)

        # Status should be updated to SUBMITTED
        get_res = self.app.get(f'/api/tasks/{id1}')
        task = json.loads(get_res.data)['task']
        self.assertEqual(task['availability_status'], 'SUBMITTED')
        self.assertEqual(task['is_actionable_pending'], 0)

if __name__ == '__main__':
    unittest.main()
