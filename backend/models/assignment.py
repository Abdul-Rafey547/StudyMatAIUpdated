"""
StudyMate AI - Assignment Model
"""
from .task import Task

class Assignment(Task):
    def __init__(self, task_id=None, course_id=None, moodle_activity_id=None,
                 title='', description='', due_date=None, cutoff_date=None,
                 status='DISCOVERED', moodle_url='',
                 submission_status='No attempt', grading_status='Not graded',
                 availability_status='AVAILABLE', is_actionable_pending=True,
                 resubmission_allowed=False, created_at=None, updated_at=None):
        super().__init__(
            task_id=task_id,
            course_id=course_id,
            moodle_activity_id=moodle_activity_id,
            task_type='ASSIGNMENT',
            title=title,
            description=description,
            due_date=due_date,
            cutoff_date=cutoff_date,
            status=status,
            submission_status=submission_status,
            grading_status=grading_status,
            availability_status=availability_status,
            is_actionable_pending=is_actionable_pending,
            resubmission_allowed=resubmission_allowed,
            moodle_url=moodle_url,
            created_at=created_at,
            updated_at=updated_at
        )
