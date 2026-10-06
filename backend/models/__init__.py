# StudyMate AI - Models Module
from .user import User
from .course import Course
from .task import Task, TASK_STATUSES, TASK_TYPES
from .assignment import Assignment
from .quiz import Quiz
from .solution import Solution, SOLUTION_STATUSES

__all__ = ['User', 'Course', 'Task', 'TASK_STATUSES', 'TASK_TYPES', 'Assignment', 'Quiz', 'Solution', 'SOLUTION_STATUSES']
