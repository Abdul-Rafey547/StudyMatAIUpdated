"""
StudyMate AI - Quiz Model
"""
from .task import Task

class Quiz(Task):
    def __init__(self, task_id=None, course_id=None, title='', description='',
                 due_date=None, status='DISCOVERED', moodle_url='',
                 questions=None, time_limit=None, attempts_allowed=None,
                 created_at=None, updated_at=None):
        super().__init__(
            task_id=task_id,
            course_id=course_id,
            task_type='QUIZ',
            title=title,
            description=description,
            due_date=due_date,
            status=status,
            moodle_url=moodle_url,
            created_at=created_at,
            updated_at=updated_at
        )
        self.questions = questions or []
        self.time_limit = time_limit
        self.attempts_allowed = attempts_allowed

    def to_dict(self):
        d = super().to_dict()
        d['questions'] = self.questions
        d['time_limit'] = self.time_limit
        d['attempts_allowed'] = self.attempts_allowed
        return d
