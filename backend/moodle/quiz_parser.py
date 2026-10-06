"""
StudyMate AI - Quiz Parser
Parses and normalizes quiz payloads received from Moodle extension or API.
"""
from utils.helpers import sanitize_html

class QuizParser:
    @staticmethod
    def parse_extension_payload(payload):
        if not payload:
            return {}

        task_data = payload.get('task') or payload
        raw_questions = task_data.get('questions', [])
        clean_questions = []

        for q in raw_questions:
            q_text = sanitize_html(q.get('question', ''))
            raw_options = q.get('options', [])
            if isinstance(raw_options, list):
                clean_options = [sanitize_html(opt) for opt in raw_options]
            else:
                clean_options = [sanitize_html(str(raw_options))]

            clean_questions.append({
                'index': q.get('index', 0),
                'question': q_text,
                'options': clean_options
            })

        return {
            'title': (task_data.get('title') or 'Untitled Quiz').strip(),
            'description': task_data.get('description', ''),
            'questions': clean_questions,
            'type': 'QUIZ',
            'course_name': task_data.get('course') or task_data.get('courseName') or 'General',
            'moodle_url': task_data.get('url') or task_data.get('moodle_url', ''),
            'due_date': task_data.get('dueDate') or task_data.get('due_date'),
            'time_limit': task_data.get('timeLimit'),
            'attempts': task_data.get('attempts')
        }
