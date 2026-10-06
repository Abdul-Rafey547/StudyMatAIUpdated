"""
StudyMate AI - Task Model
Represents an academic task (assignment or quiz) detected from Moodle.
"""
from datetime import datetime

TASK_STATUSES = [
    'DISCOVERED',
    'PENDING',
    'PROCESSING',
    'GENERATED',
    'REVIEW',
    'APPROVED',
    'SUBMITTED',
    'COMPLETED',
    'FAILED'
]

TASK_TYPES = ['ASSIGNMENT', 'QUIZ']

class Task:
    def __init__(self, task_id=None, course_id=None, task_type='ASSIGNMENT',
                 title='', description='', due_date=None, status='DISCOVERED',
                 moodle_url='', created_at=None, updated_at=None):
        self.task_id = task_id
        self.course_id = course_id
        self.type = task_type
        self.title = title
        self.description = description
        self.due_date = due_date
        self.status = status
        self.moodle_url = moodle_url
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'id': self.task_id,
            'course_id': self.course_id,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'dueDate': self.due_date,
            'status': self.status,
            'moodle_url': self.moodle_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Task(
            task_id=data.get('task_id') or data.get('id'),
            course_id=data.get('course_id'),
            task_type=data.get('type', 'ASSIGNMENT'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            due_date=data.get('due_date') or data.get('dueDate'),
            status=data.get('status', 'DISCOVERED'),
            moodle_url=data.get('moodle_url') or data.get('url', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def is_overdue(self):
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            return datetime.now().astimezone() > due
        except Exception:
            return False
