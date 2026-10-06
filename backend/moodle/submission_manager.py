"""
StudyMate AI - Submission Manager
Manages the recording and status of task submissions to Moodle.
"""
from utils.logger import get_logger

logger = get_logger('studymate.submissions')

class SubmissionManager:
    @staticmethod
    def record_submission(db_conn, task_id, solution_id, result_text='Submitted via StudyMate AI'):
        c = db_conn.cursor()
        c.execute(
            "INSERT INTO submissions (task_id, solution_id, result) VALUES (?, ?, ?)",
            (task_id, solution_id, result_text)
        )
        submission_id = c.lastrowid
        
        c.execute("UPDATE tasks SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", (task_id,))
        c.execute("UPDATE solutions SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE solution_id = ?", (solution_id,))
        db_conn.commit()
        
        logger.info(f"Recorded submission #{submission_id} for Task #{task_id}")
        return submission_id
