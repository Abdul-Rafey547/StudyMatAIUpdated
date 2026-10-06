"""
StudyMate AI - Assignment Model
"""
from .task import Task

class Assignment(Task):
    def __init__(self, task_id=None, course_id=None, title='', description='',
                 due_date=None, status='DISCOVERED', moodle_url='',
                 submission_status='No attempt', grading_status='Not graded',
                 created_at=None, updated_at=None):
        super().__init__(
            task_id=task_id,
            course_id=course_id,
            task_type='ASSIGNMENT',
            title=title,
            description=description,
            due_date=due_date,
            status=status,
            moodle_url=moodle_url,
            created_at=created_at,
            updated_at=updated_at
        )
        self.submission_status = submission_status
        self.grading_status = grading_status

    def to_dict(self):
        d = super().to_dict()
        d['submission_status'] = self.submission_status
        d['grading_status'] = self.grading_status
        return d
