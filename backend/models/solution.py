"""
StudyMate AI - Solution Model
Represents an AI-generated solution for a task.
"""

SOLUTION_STATUSES = ['GENERATED', 'DRAFT', 'APPROVED', 'SUBMITTED']

class Solution:
    def __init__(self, solution_id=None, task_id=None, generated_answer='',
                 edited_answer=None, status='GENERATED', created_at=None, updated_at=None):
        self.solution_id = solution_id
        self.task_id = task_id
        self.generated_answer = generated_answer
        self.edited_answer = edited_answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            'solution_id': self.solution_id,
            'id': self.solution_id,
            'task_id': self.task_id,
            'generated_answer': self.generated_answer,
            'edited_answer': self.edited_answer,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Solution(
            solution_id=data.get('solution_id') or data.get('id'),
            task_id=data.get('task_id'),
            generated_answer=data.get('generated_answer', ''),
            edited_answer=data.get('edited_answer'),
            status=data.get('status', 'GENERATED'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def get_best_answer(self):
        return self.edited_answer or self.generated_answer
