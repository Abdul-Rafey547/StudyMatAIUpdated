"""
StudyMate AI - Course Model
Represents a Moodle course.
"""

class Course:
    def __init__(self, course_id=None, course_name='', moodle_course_id=None, created_at=None):
        self.course_id = course_id
        self.course_name = course_name
        self.moodle_course_id = moodle_course_id
        self.created_at = created_at

    def to_dict(self):
        return {
            'course_id': self.course_id,
            'course_name': self.course_name,
            'moodle_course_id': self.moodle_course_id,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data):
        return Course(
            course_id=data.get('course_id'),
            course_name=data.get('course_name', ''),
            moodle_course_id=data.get('moodle_course_id'),
            created_at=data.get('created_at')
        )
