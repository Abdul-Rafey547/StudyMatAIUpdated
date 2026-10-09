"""
StudyMate AI - Assignment Parser
Parses, normalizes, and categorizes assignment payloads received from Moodle extension or API.
Accurately distinguishes between all 9 availability and submission states.
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

        raw_sub_status = task_data.get('submissionStatus') or task_data.get('submission_status') or 'No attempt'
        raw_grading_status = task_data.get('gradingStatus') or task_data.get('grading_status') or 'Not graded'
        resubmission_allowed = bool(task_data.get('resubmissionAllowed') or task_data.get('resubmission_allowed', False))
        is_hidden = bool(task_data.get('isHidden') or task_data.get('is_hidden') or task_data.get('is_restricted', False))
        is_closed = bool(task_data.get('isClosed') or task_data.get('is_closed', False))
        is_upcoming = bool(task_data.get('isUpcoming') or task_data.get('is_upcoming', False))
        is_unverified = bool(task_data.get('isUnverified') or task_data.get('is_unverified', False))
        explicit_avail = task_data.get('availabilityStatus') or task_data.get('availability_status')

        sub_lower = raw_sub_status.lower().strip()
        grade_lower = raw_grading_status.lower().strip()

        is_graded = (
            ('graded' in grade_lower or 'bewertet' in grade_lower) and
            'not graded' not in grade_lower and
            'nicht bewertet' not in grade_lower
        )

        is_submitted_for_grading = (
            'submitted for grading' in sub_lower or
            'abgegeben zur bewertung' in sub_lower or
            'rendu pour évaluation' in sub_lower
        )

        # Determine Availability Status
        if is_hidden:
            availability_status = 'UNAVAILABLE'
            is_actionable = False
        elif is_upcoming or 'will accept submissions from' in sub_lower:
            availability_status = 'UPCOMING'
            is_actionable = False
        elif is_closed or 'submissions are closed' in sub_lower or 'not accepting submissions' in sub_lower:
            availability_status = 'CLOSED'
            is_actionable = False
        elif is_unverified or explicit_avail == 'UNVERIFIED':
            availability_status = 'UNVERIFIED'
            is_actionable = False
        elif is_graded and not resubmission_allowed:
            availability_status = 'COMPLETED'
            is_actionable = False
        elif is_submitted_for_grading and not resubmission_allowed:
            availability_status = 'SUBMITTED'
            is_actionable = False
        elif explicit_avail in ('AVAILABLE', 'SUBMITTED', 'COMPLETED', 'UPCOMING', 'CLOSED', 'UNAVAILABLE', 'UNVERIFIED'):
            availability_status = explicit_avail
            is_actionable = (availability_status == 'AVAILABLE')
        else:
            # Open and available for attempt
            availability_status = 'AVAILABLE'
            is_actionable = True

        # Map to task status
        if availability_status == 'SUBMITTED':
            status = 'SUBMITTED'
        elif availability_status == 'COMPLETED':
            status = 'COMPLETED'
        elif availability_status == 'UPCOMING':
            status = 'UPCOMING'
        elif availability_status == 'CLOSED':
            status = 'CLOSED'
        elif availability_status == 'UNAVAILABLE':
            status = 'UNAVAILABLE'
        elif availability_status == 'UNVERIFIED':
            status = 'UNVERIFIED'
        else:
            status = task_data.get('status') or 'PENDING'

        # Extract Moodle Activity ID
        url = task_data.get('url') or task_data.get('moodle_url', '')
        activity_id = task_data.get('moodle_activity_id') or task_data.get('id')
        if not activity_id and url:
            import re
            m = re.search(r'id=(\d+)', url)
            if m:
                activity_id = m.group(1)

        return {
            'title': (task_data.get('title') or 'Untitled Assignment').strip(),
            'description': clean_desc,
            'due_date': task_data.get('dueDate') or task_data.get('due_date'),
            'cutoff_date': task_data.get('cutoffDate') or task_data.get('cutoff_date'),
            'type': 'ASSIGNMENT',
            'course_name': task_data.get('course') or task_data.get('courseName') or 'General',
            'moodle_url': url,
            'moodle_activity_id': str(activity_id) if activity_id else None,
            'submission_status': raw_sub_status,
            'grading_status': raw_grading_status,
            'availability_status': availability_status,
            'is_actionable_pending': 1 if is_actionable else 0,
            'resubmission_allowed': 1 if resubmission_allowed else 0,
            'status': status
        }
