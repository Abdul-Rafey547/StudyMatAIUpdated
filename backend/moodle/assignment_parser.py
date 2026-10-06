"""
StudyMate AI - Assignment Parser
Parses and normalizes assignment payloads received from Moodle extension or API.
"""
from utils.helpers import sanitize_html, truncate_text

class AssignmentParser:
    @staticmethod
    def parse_extension_payload(payload):
        if not payload:
            return {}

        task_data = payload.get('task') or payload
        raw_description = task_data.get('description', '')
        clean_desc = sanitize_html(raw_description)

        return {
            'title': (task_data.get('title') or 'Untitled Assignment').strip(),
            'description': clean_desc,
            'due_date': task_data.get('dueDate') or task_data.get('due_date'),
            'type': 'ASSIGNMENT',
            'course_name': task_data.get('course') or task_data.get('courseName') or 'General',
            'moodle_url': task_data.get('url') or task_data.get('moodle_url', ''),
            'submission_status': task_data.get('submissionStatus', 'No attempt'),
            'grading_status': task_data.get('gradingStatus', 'Not graded')
        }
