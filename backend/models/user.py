"""
StudyMate AI - User Model
"""

class User:
    def __init__(self, user_id=None, username='', moodle_id=None, created_at=None):
        self.user_id = user_id
        self.username = username
        self.moodle_id = moodle_id
        self.created_at = created_at

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'moodle_id': self.moodle_id,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data):
        return User(
            user_id=data.get('user_id'),
            username=data.get('username', ''),
            moodle_id=data.get('moodle_id'),
            created_at=data.get('created_at')
        )
