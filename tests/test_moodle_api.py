"""
StudyMate AI - Comprehensive Moodle API & Scanner Unit Test Suite
Tests:
1. MoodleClient communication, token masking, authentication, error handling (invalid token, missing functions, timeouts).
2. API response parsing and normalization for courses, assignments, quizzes, and resources.
3. MoodleScanner availability rules, deduplication, incremental sync, reconciliation, draft preservation.
4. Resource discovery, secure file downloads, and text extraction handling.
"""
import io
import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from database.database import init_db, get_db_connection
from moodle.moodle_client import MoodleClient
from moodle.moodle_scanner import MoodleScanner


class TestMoodleClient(unittest.TestCase):
    """Tests for MoodleClient connector implementation."""

    def setUp(self):
        self.client = MoodleClient(base_url='http://moodle.local', token='test_token_1234567890abcdef')

    def test_token_masking(self):
        """Ensure full tokens are never exposed in masked output."""
        masked = self.client.mask_token()
        self.assertTrue(masked.startswith('test...cdef') or '...' in masked)
        self.assertNotIn('1234567890', masked)

    def test_unconfigured_client(self):
        """Unconfigured client handles calls safely without making network requests."""
        empty_client = MoodleClient(base_url='', token='')
        self.assertFalse(empty_client.is_configured())
        conn = empty_client.check_connection()
        self.assertFalse(conn['connected'])
        self.assertEqual(conn['errorcode'], 'not_configured')

        call_res = empty_client.call('core_webservice_get_site_info')
        self.assertIn('error', call_res)
        self.assertEqual(call_res['errorcode'], 'not_configured')

    @patch('urllib.request.urlopen')
    def test_valid_site_info(self, mock_urlopen):
        """Valid site info response parses correctly and caches user data."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "sitename": "Test Moodle LMS",
            "username": "student1",
            "fullname": "Alice Student",
            "userid": 42,
            "release": "5.1.8 (Build: 20261001)",
            "functions": [{"name": "core_enrol_get_users_courses"}]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status = self.client.check_connection()
        self.assertTrue(status['connected'])
        self.assertEqual(status['userid'], 42)
        self.assertEqual(status['fullname'], 'Alice Student')
        self.assertIn('core_enrol_get_users_courses', status['functions'])

    @patch('urllib.request.urlopen')
    def test_invalid_token_exception(self, mock_urlopen):
        """Moodle invalidtoken exception is captured and handled safely."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "exception": "moodle_exception",
            "errorcode": "invalidtoken",
            "message": "Invalid token - token not found"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status = self.client.check_connection()
        self.assertFalse(status['connected'])
        self.assertEqual(status['errorcode'], 'invalidtoken')
        self.assertIn('Invalid token', status['error'])

    @patch('urllib.request.urlopen')
    def test_missing_function_exception(self, mock_urlopen):
        """Moodle accessexception / function not authorized handled cleanly."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "exception": "webservice_access_exception",
            "errorcode": "accessexception",
            "message": "Access to the function mod_quiz_get_quizzes_by_courses is not allowed"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.client.call('mod_quiz_get_quizzes_by_courses', {'courseids[0]': 2})
        self.assertEqual(res.get('errorcode'), 'accessexception')
        self.assertIn('Access to the function', res.get('error'))

    @patch('urllib.request.urlopen')
    def test_server_http_error(self, mock_urlopen):
        """HTTP error from Moodle server returns error dict instead of raising."""
        fp = io.BytesIO(json.dumps({"message": "Internal Server Error", "errorcode": "http_500"}).encode('utf-8'))
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://moodle.local/webservice/rest/server.php',
            code=500,
            msg='Internal Server Error',
            hdrs={},
            fp=fp
        )

        res = self.client.call('core_webservice_get_site_info')
        self.assertIn('error', res)
        self.assertEqual(res.get('errorcode'), 'http_500')

    @patch('urllib.request.urlopen')
    def test_connection_timeout(self, mock_urlopen):
        """Connection timeout handled gracefully."""
        mock_urlopen.side_effect = urllib.error.URLError("timed out")
        res = self.client.call('core_webservice_get_site_info')
        self.assertIn('error', res)
        self.assertEqual(res.get('errorcode'), 'connection_timeout')

    @patch('urllib.request.urlopen')
    def test_authenticated_resource_content_download(self, mock_urlopen):
        """File download automatically appends token parameter if absent."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"%PDF-1.4 Mock PDF Binary"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        url = "http://moodle.local/webservice/pluginfile.php/12/mod_resource/content/1/notes.pdf"
        data = self.client.get_resource_content(url)
        self.assertIsNotNone(data)
        self.assertEqual(data, b"%PDF-1.4 Mock PDF Binary")

        # Verify that urlopen was called with token attached
        called_req = mock_urlopen.call_args[0][0]
        self.assertIn("token=test_token_1234567890abcdef", called_req.full_url)


class TestMoodleScanner(unittest.TestCase):
    """Tests for MoodleScanner business logic, availability, and database reconciliation."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

        # Clean up test-specific courses and tasks to ensure strict test isolation
        conn = get_db_connection()
        try:
            c = conn.cursor()
            test_cids = "('201', '301', '401', '501', '601', '701')"
            c_filter = f"moodle_course_id IN {test_cids} OR course_name = 'AI 701 Advanced Machine Learning'"
            c.execute(f"DELETE FROM solutions WHERE task_id IN (SELECT task_id FROM tasks WHERE course_id IN (SELECT course_id FROM courses WHERE {c_filter}))")
            c.execute(f"DELETE FROM submissions WHERE task_id IN (SELECT task_id FROM tasks WHERE course_id IN (SELECT course_id FROM courses WHERE {c_filter}))")
            c.execute(f"DELETE FROM tasks WHERE course_id IN (SELECT course_id FROM courses WHERE {c_filter})")
            c.execute(f"DELETE FROM resources WHERE course_id IN (SELECT course_id FROM courses WHERE {c_filter})")
            c.execute(f"DELETE FROM courses WHERE {c_filter}")
            conn.commit()
        finally:
            conn.close()

        self.mock_client = MagicMock(spec=MoodleClient)
        self.mock_client.base_url = 'http://moodle.local'
        self.mock_client.check_connection.return_value = {
            "connected": True,
            "sitename": "Test Moodle",
            "userid": 10,
            "fullname": "Test Student"
        }
        self.scanner = MoodleScanner(client=self.mock_client)

    def test_scan_empty_courses(self):
        """Student enrolled in no courses completes cleanly."""
        self.mock_client.get_courses.return_value = []
        result = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['courses']), 0)
        self.assertEqual(len(result['tasks']), 0)
        self.assertEqual(len(result['resources']), 0)

    def test_scan_assignments_and_quizzes_availability(self):
        """
        Verify scanner categorizes tasks accurately:
        - Open assignment with no attempt -> AVAILABLE, actionable pending = 1
        - Submitted assignment -> SUBMITTED, actionable pending = 0
        - Future assignment -> UPCOMING, actionable pending = 0
        - Hidden assignment -> UNAVAILABLE, actionable pending = 0
        - Quiz with finished attempt -> COMPLETED, actionable pending = 0
        """
        now = int(time.time())

        self.mock_client.get_courses.return_value = [{
            'course_id': 201,
            'course_name': 'CS 201: Data Structures',
            'shortname': 'CS201'
        }]

        self.mock_client.get_course_contents.return_value = [
            {
                'modules': [
                    {'id': 11, 'instance': 1, 'modname': 'assign', 'visible': 1, 'uservisible': True},
                    {'id': 12, 'instance': 2, 'modname': 'assign', 'visible': 1, 'uservisible': True},
                    {'id': 13, 'instance': 3, 'modname': 'assign', 'visible': 1, 'uservisible': True},
                    {'id': 14, 'instance': 4, 'modname': 'assign', 'visible': 0, 'uservisible': False},  # Hidden
                    {'id': 15, 'instance': 1, 'modname': 'quiz', 'visible': 1, 'uservisible': True},
                ]
            }
        ]

        self.mock_client.get_assignments.return_value = [
            {
                'id': 1,
                'course': 201,
                'name': 'Open Assignment',
                'intro': 'Open assignment description',
                'duedate': now + 86400,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': 0,
                'cmid': 11
            },
            {
                'id': 2,
                'course': 201,
                'name': 'Submitted Assignment',
                'intro': 'Submitted assignment description',
                'duedate': now + 86400,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': 0,
                'cmid': 12
            },
            {
                'id': 3,
                'course': 201,
                'name': 'Upcoming Assignment',
                'intro': 'Upcoming assignment description',
                'duedate': now + 172800,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': now + 86400,  # opens in 1 day
                'cmid': 13
            },
            {
                'id': 4,
                'course': 201,
                'name': 'Hidden Assignment',
                'intro': 'Hidden assignment description',
                'duedate': now + 86400,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': 0,
                'cmid': 14
            }
        ]

        def mock_sub_status(assign_id, user_id=None):
            if assign_id == 1:
                return {'submission_status': 'No attempt', 'grading_status': 'notgraded', 'is_submitted': False, 'is_graded': False, 'can_edit': True}
            elif assign_id == 2:
                return {'submission_status': 'Submitted for grading', 'grading_status': 'notgraded', 'is_submitted': True, 'is_graded': False, 'can_edit': False}
            elif assign_id == 3:
                return {'submission_status': 'No attempt', 'grading_status': 'notgraded', 'is_submitted': False, 'is_graded': False, 'can_edit': True}
            else:
                return {'submission_status': 'No attempt', 'grading_status': 'notgraded', 'is_submitted': False, 'is_graded': False, 'can_edit': True}

        self.mock_client.get_submission_status.side_effect = mock_sub_status

        self.mock_client.get_quizzes.return_value = [
            {
                'id': 1,
                'course': 201,
                'name': 'Finished Quiz',
                'intro': 'Quiz instructions',
                'timeopen': now - 86400,
                'timeclose': now + 86400,
                'coursemodule': 15
            }
        ]
        self.mock_client.get_quiz_access_information.return_value = {'canattempt': False, 'preventaccessreasons': ['No more attempts allowed']}
        self.mock_client.get_quiz_user_attempts.return_value = [{'state': 'finished', 'attempt': 1}]

        self.mock_client.get_resources.return_value = []

        scan_result = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertTrue(scan_result['success'])

        tasks_by_title = {t['title']: t for t in scan_result['tasks']}

        # Verify Open Assignment
        open_task = tasks_by_title['Open Assignment']
        self.assertEqual(open_task['availability_status'], 'AVAILABLE')
        self.assertEqual(open_task['is_actionable_pending'], 1)

        # Verify Submitted Assignment
        sub_task = tasks_by_title['Submitted Assignment']
        self.assertEqual(sub_task['availability_status'], 'SUBMITTED')
        self.assertEqual(sub_task['is_actionable_pending'], 0)

        # Verify Upcoming Assignment
        up_task = tasks_by_title['Upcoming Assignment']
        self.assertEqual(up_task['availability_status'], 'UPCOMING')
        self.assertEqual(up_task['is_actionable_pending'], 0)

        # Verify Hidden Assignment
        hidden_task = tasks_by_title['Hidden Assignment']
        self.assertEqual(hidden_task['availability_status'], 'UNAVAILABLE')
        self.assertEqual(hidden_task['is_actionable_pending'], 0)

        # Verify Finished Quiz
        quiz_task = tasks_by_title['Finished Quiz']
        self.assertEqual(quiz_task['availability_status'], 'COMPLETED')
        self.assertEqual(quiz_task['is_actionable_pending'], 0)

        # Verify actionable pending count is exactly 1
        self.assertEqual(scan_result['pending_tasks'], 1)

    def test_substring_notgraded_bug_prevention(self):
        """
        Verify that grading_status='notgraded' does not trigger 'graded' check
        and wrongly mark the task as COMPLETED.
        """
        now = int(time.time())
        self.mock_client.get_courses.return_value = [{'course_id': 301, 'course_name': 'Bug Check 101'}]
        self.mock_client.get_course_contents.return_value = []
        self.mock_client.get_assignments.return_value = [{
            'id': 99,
            'course': 301,
            'name': 'Unattempted Homework',
            'intro': 'Desc',
            'duedate': now + 86400,
            'cutoffdate': 0,
            'allowsubmissionsfromdate': 0,
            'cmid': 991
        }]
        # Moodle returns 'notgraded' as grading_status
        self.mock_client.get_submission_status.return_value = {
            'submission_status': 'No attempt',
            'grading_status': 'notgraded',
            'is_submitted': False,
            'is_graded': False,
            'can_edit': True
        }
        self.mock_client.get_quizzes.return_value = []
        self.mock_client.get_resources.return_value = []

        scan_result = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertTrue(scan_result['success'])
        task = scan_result['tasks'][0]
        self.assertNotEqual(task['availability_status'], 'COMPLETED')
        self.assertEqual(task['availability_status'], 'AVAILABLE')
        self.assertEqual(task['is_actionable_pending'], 1)

    def test_incremental_scan_and_deduplication(self):
        """
        Verify that repeated scans update existing rows without duplicating them,
        and that a newly created assignment is discovered on subsequent scan.
        """
        now = int(time.time())
        self.mock_client.get_courses.return_value = [{'course_id': 401, 'course_name': 'Math 101'}]
        self.mock_client.get_course_contents.return_value = []
        self.mock_client.get_submission_status.return_value = {
            'submission_status': 'No attempt',
            'grading_status': 'notgraded',
            'is_submitted': False,
            'is_graded': False,
            'can_edit': True
        }
        self.mock_client.get_quizzes.return_value = []
        self.mock_client.get_resources.return_value = []

        # Scan 1: Single assignment
        self.mock_client.get_assignments.return_value = [{
            'id': 101,
            'course': 401,
            'name': 'Math Problem Set 1',
            'intro': 'Week 1 problems',
            'duedate': now + 86400,
            'cutoffdate': 0,
            'allowsubmissionsfromdate': 0,
            'cmid': 1001
        }]
        res1 = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertEqual(res1['total_tasks'], 1)
        first_task_id = res1['tasks'][0]['task_id']

        # Scan 2: Same assignment, unchanged
        res2 = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertEqual(res2['total_tasks'], 1)
        self.assertEqual(res2['tasks'][0]['task_id'], first_task_id, "Existing task must be refreshed, not duplicated.")

        # Scan 3: A new assignment is added
        self.mock_client.get_assignments.return_value = [
            {
                'id': 101,
                'course': 401,
                'name': 'Math Problem Set 1',
                'intro': 'Week 1 problems',
                'duedate': now + 86400,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': 0,
                'cmid': 1001
            },
            {
                'id': 102,
                'course': 401,
                'name': 'Math Problem Set 2',
                'intro': 'Week 2 problems',
                'duedate': now + 172800,
                'cutoffdate': 0,
                'allowsubmissionsfromdate': 0,
                'cmid': 1002
            }
        ]
        res3 = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertEqual(res3['total_tasks'], 2)
        task_ids = [t['task_id'] for t in res3['tasks']]
        self.assertIn(first_task_id, task_ids)

    def test_preserves_user_drafts_on_rescan(self):
        """
        Verify that student draft states (e.g. APPROVED, GENERATED, Draft Ready)
        are preserved when the scanner refreshes the activity from Moodle.
        """
        now = int(time.time())
        self.mock_client.get_courses.return_value = [{'course_id': 501, 'course_name': 'Writing 101'}]
        self.mock_client.get_course_contents.return_value = []
        self.mock_client.get_submission_status.return_value = {
            'submission_status': 'No attempt',
            'grading_status': 'notgraded',
            'is_submitted': False,
            'is_graded': False,
            'can_edit': True
        }
        self.mock_client.get_assignments.return_value = [{
            'id': 201,
            'course': 501,
            'name': 'Research Essay',
            'intro': 'Write 1000 words.',
            'duedate': now + 86400,
            'cutoffdate': 0,
            'allowsubmissionsfromdate': 0,
            'cmid': 2001
        }]
        self.mock_client.get_quizzes.return_value = []
        self.mock_client.get_resources.return_value = []

        res1 = self.scanner.scan_enrolled_courses(user_id=10)
        task_id = res1['tasks'][0]['task_id']

        # Simulate user creating and approving a solution draft in StudyMate AI
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'APPROVED' WHERE task_id = ?", (task_id,))
            cursor.execute("""
                INSERT INTO solutions (task_id, generated_answer, status)
                VALUES (?, 'My approved AI draft solution text...', 'APPROVED')
            """, (task_id,))
            conn.commit()
        finally:
            conn.close()

        # Rescan from Moodle
        res2 = self.scanner.scan_enrolled_courses(user_id=10)
        rescanned_task = res2['tasks'][0]
        self.assertEqual(rescanned_task['task_id'], task_id)
        # Status should still be APPROVED, not overwritten to PENDING!
        self.assertEqual(rescanned_task['status'], 'APPROVED')

        # Check solution row in DB is still intact
        conn = get_db_connection()
        sol = conn.cursor().execute("SELECT * FROM solutions WHERE task_id = ?", (task_id,)).fetchone()
        self.assertIsNotNone(sol)
        self.assertEqual(sol['status'], 'APPROVED')
        conn.close()

    def test_reconciliation_marks_deleted_activity_unavailable(self):
        """
        Verify that an activity previously in DB but no longer returned by Moodle API
        is marked UNAVAILABLE and not actionable pending, without deleting the row or user data.
        """
        now = int(time.time())
        self.mock_client.get_courses.return_value = [{'course_id': 601, 'course_name': 'Bio 101'}]
        self.mock_client.get_course_contents.return_value = []
        self.mock_client.get_submission_status.return_value = {
            'submission_status': 'No attempt',
            'grading_status': 'notgraded',
            'is_submitted': False,
            'is_graded': False,
            'can_edit': True
        }
        self.mock_client.get_quizzes.return_value = []
        self.mock_client.get_resources.return_value = []

        # Scan 1: returns Assignment A
        self.mock_client.get_assignments.return_value = [{
            'id': 301,
            'course': 601,
            'name': 'Genetics Lab',
            'intro': 'Desc',
            'duedate': now + 86400,
            'cutoffdate': 0,
            'allowsubmissionsfromdate': 0,
            'cmid': 3001
        }]
        res1 = self.scanner.scan_enrolled_courses(user_id=10)
        task_id = res1['tasks'][0]['task_id']
        self.assertEqual(res1['pending_tasks'], 1)

        # Scan 2: Assignment A is deleted or unassigned from student in Moodle
        self.mock_client.get_assignments.return_value = []
        res2 = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertEqual(res2['pending_tasks'], 0)

        # Verify task row was preserved in DB but marked UNAVAILABLE and is_actionable_pending = 0
        conn = get_db_connection()
        row = conn.cursor().execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        self.assertIsNotNone(row, "Task must not be deleted from database.")
        self.assertEqual(row['is_actionable_pending'], 0)
        self.assertEqual(row['availability_status'], 'UNAVAILABLE')
        conn.close()

    def test_resource_discovery_and_extraction(self):
        """
        Verify PDF resource discovery and text extraction handling.
        """
        self.mock_client.get_courses.return_value = [{'course_id': 701, 'course_name': 'AI 701 Advanced Machine Learning'}]
        self.mock_client.get_course_contents.return_value = []
        self.mock_client.get_assignments.return_value = []
        self.mock_client.get_quizzes.return_value = []

        self.mock_client.get_resources.return_value = [
            {
                'id': 10,
                'course': 701,
                'name': 'Lecture 1 Slides Notes',
                'intro': 'Lecture notes description',
                'coursemodule': 7001,
                'contentfiles': [
                    {
                        'filename': 'lecture1.txt',
                        'filesize': 1024,
                        'fileurl': 'http://moodle.local/pluginfile.php/701/mod_resource/content/1/lecture1.txt',
                        'mimetype': 'text/plain'
                    }
                ]
            }
        ]

        # Mock download returning text bytes
        self.mock_client.get_resource_content.return_value = b"Introduction to Neural Networks and Search Algorithms."

        scan_result = self.scanner.scan_enrolled_courses(user_id=10)
        self.assertTrue(scan_result['success'])
        self.assertEqual(scan_result['total_resources'], 1)

        res = scan_result['resources'][0]
        self.assertEqual(res['title'], 'Lecture 1 Slides Notes')
        self.assertEqual(res['resource_type'], 'TXT')
        self.assertIn("Neural Networks", res['extracted_text'])


class TestTaskScanApi(unittest.TestCase):
    """Test the Flask HTTP endpoint for API scan."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    @patch('moodle.moodle_client.MoodleClient.check_connection')
    def test_moodle_status_endpoint(self, mock_conn):
        """GET /api/tasks/moodle-status returns connector connection status."""
        mock_conn.return_value = {
            "connected": True,
            "sitename": "Live Moodle",
            "fullname": "John Doe",
            "userid": 5,
            "version": "5.1.8"
        }
        res = self.app.get('/api/tasks/moodle-status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['connected'])
        self.assertEqual(data['fullname'], 'John Doe')

    @patch('moodle.moodle_scanner.MoodleScanner.scan_enrolled_courses')
    def test_tasks_scan_post_endpoint(self, mock_scan):
        """POST /api/tasks/scan triggers API scan and returns JSON."""
        mock_scan.return_value = {
            "success": True,
            "total_tasks": 3,
            "pending_tasks": 2,
            "total_resources": 1,
            "tasks": [],
            "resources": []
        }
        res = self.app.post('/api/tasks/scan')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['pending_tasks'], 2)


if __name__ == '__main__':
    unittest.main()
