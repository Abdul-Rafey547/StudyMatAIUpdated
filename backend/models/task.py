"""
StudyMate AI - Task Model
Represents an academic task (assignment or quiz) detected from Moodle with verified availability tracking.
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
    'FAILED',
    'UPCOMING',
    'CLOSED',
    'UNAVAILABLE',
    'UNVERIFIED'
]

AVAILABILITY_STATUSES = [
    'AVAILABLE',     # Cat 1: Open, submissions accepted, not submitted
    'SUBMITTED',     # Cat 2: Already submitted
    'COMPLETED',     # Cat 3: Graded / completed
    'UPCOMING',      # Cat 4: Not yet open
    'CLOSED',        # Cat 5: Deadline passed, no submissions accepted
    'UNAVAILABLE',   # Cat 6: Hidden or restricted
    'UNVERIFIED'     # Cat 7: Needs inspection, not assumed pending
]

TASK_TYPES = ['ASSIGNMENT', 'QUIZ']

class Task:
    def __init__(self, task_id=None, course_id=None, moodle_activity_id=None,
                 task_type='ASSIGNMENT', title='', description='', due_date=None,
                 cutoff_date=None, status='DISCOVERED', submission_status='No attempt',
                 grading_status='Not graded', availability_status='AVAILABLE',
                 is_actionable_pending=True, resubmission_allowed=False,
                 moodle_url='', created_at=None, updated_at=None,
                 lms_type='moodle', lms_instance=None, open_date=None,
                 close_date=None, source='api', last_scanned_at=None):
        self.task_id = task_id
        self.course_id = course_id
        self.moodle_activity_id = moodle_activity_id
        self.type = task_type
        self.title = title
        self.description = description
        self.due_date = due_date
        self.cutoff_date = cutoff_date
        self.status = status
        self.submission_status = submission_status
        self.grading_status = grading_status
        self.availability_status = availability_status
        self.is_actionable_pending = bool(is_actionable_pending)
        self.resubmission_allowed = bool(resubmission_allowed)
        self.moodle_url = moodle_url
        self.created_at = created_at
        self.updated_at = updated_at
        self.lms_type = lms_type or 'moodle'
        self.lms_instance = lms_instance
        self.open_date = open_date
        self.close_date = close_date
        self.source = source or 'api'
        self.last_scanned_at = last_scanned_at

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'id': self.task_id,
            'activity_id': self.moodle_activity_id,
            'course_id': self.course_id,
            'moodle_activity_id': self.moodle_activity_id,
            'type': self.type,
            'activity_type': self.type,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'dueDate': self.due_date,
            'cutoff_date': self.cutoff_date,
            'open_date': self.open_date,
            'close_date': self.close_date,
            'status': self.status,
            'submission_status': self.submission_status,
            'submissionStatus': self.submission_status,
            'grading_status': self.grading_status,
            'gradingStatus': self.grading_status,
            'availability_status': self.availability_status,
            'availabilityStatus': self.availability_status,
            'is_actionable_pending': self.is_actionable_pending,
            'isActionablePending': self.is_actionable_pending,
            'resubmission_allowed': self.resubmission_allowed,
            'moodle_url': self.moodle_url,
            'url': self.moodle_url,
            'activity_url': self.moodle_url,
            'lms_type': self.lms_type,
            'lms_instance': self.lms_instance,
            'source': self.source,
            'last_scanned_at': self.last_scanned_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Task(
            task_id=data.get('task_id') or data.get('id'),
            course_id=data.get('course_id'),
            moodle_activity_id=data.get('moodle_activity_id') or data.get('activity_id'),
            task_type=data.get('type') or data.get('activity_type') or 'ASSIGNMENT',
            title=data.get('title', ''),
            description=data.get('description', ''),
            due_date=data.get('due_date') or data.get('dueDate'),
            cutoff_date=data.get('cutoff_date') or data.get('cutoffDate'),
            status=data.get('status', 'DISCOVERED'),
            submission_status=data.get('submission_status') or data.get('submissionStatus', 'No attempt'),
            grading_status=data.get('grading_status') or data.get('gradingStatus', 'Not graded'),
            availability_status=data.get('availability_status') or data.get('availabilityStatus', 'AVAILABLE'),
            is_actionable_pending=data.get('is_actionable_pending', True),
            resubmission_allowed=data.get('resubmission_allowed', False),
            moodle_url=data.get('moodle_url') or data.get('url') or data.get('activity_url', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            lms_type=data.get('lms_type', 'moodle'),
            lms_instance=data.get('lms_instance'),
            open_date=data.get('open_date'),
            close_date=data.get('close_date'),
            source=data.get('source', 'api'),
            last_scanned_at=data.get('last_scanned_at')
        )

    def is_overdue(self):
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            return datetime.now().astimezone() > due
        except Exception:
            return False
