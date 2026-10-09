# StudyMate AI - Models Module
from .user import User
from .course import Course
from .task import Task, TASK_STATUSES, TASK_TYPES, AVAILABILITY_STATUSES
from .assignment import Assignment
from .quiz import Quiz
from .solution import Solution, SOLUTION_STATUSES
from .resource import Resource, RESOURCE_TYPES

__all__ = [
    'User', 'Course', 'Task', 'TASK_STATUSES', 'TASK_TYPES',
    'AVAILABILITY_STATUSES', 'Assignment', 'Quiz', 'Solution',
    'SOLUTION_STATUSES', 'Resource', 'RESOURCE_TYPES'
]
