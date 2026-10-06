import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.task import Task
from models.course import Course
from models.solution import Solution
from models.assignment import Assignment
from models.quiz import Quiz

class ModelsTestCase(unittest.TestCase):
    def test_task_model(self):
        task = Task(task_id=1, title="Test Task", task_type="ASSIGNMENT", status="PENDING")
        d = task.to_dict()
        self.assertEqual(d['task_id'], 1)
        self.assertEqual(d['title'], "Test Task")
        
        recreated = Task.from_dict(d)
        self.assertEqual(recreated.title, "Test Task")

    def test_course_model(self):
        course = Course(course_id=10, course_name="Algorithms")
        d = course.to_dict()
        self.assertEqual(d['course_name'], "Algorithms")

    def test_solution_model(self):
        sol = Solution(solution_id=5, task_id=1, generated_answer="Initial Gen", edited_answer="Student Edited")
        self.assertEqual(sol.get_best_answer(), "Student Edited")
        
        sol_no_edit = Solution(solution_id=6, task_id=1, generated_answer="Initial Gen")
        self.assertEqual(sol_no_edit.get_best_answer(), "Initial Gen")

    def test_quiz_model(self):
        quiz = Quiz(task_id=2, title="Physics Quiz", questions=[{"question": "What is F=ma?"}])
        self.assertEqual(len(quiz.questions), 1)
        self.assertEqual(quiz.type, "QUIZ")

if __name__ == '__main__':
    unittest.main()
