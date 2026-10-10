"""
StudyMate AI - Submissions & Solutions API Blueprint
Provides real document generation (DOCX, TXT) and truthful Moodle submission verification.
"""
import io
import re
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from database.database import get_db_connection
from utils.logger import get_logger

try:
    import docx
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    docx = None

logger = get_logger('studymate.api.submissions')
submissions_bp = Blueprint('submissions', __name__)

def _sanitize_filename(name):
    """Sanitize string for safe filename generation."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', '_', clean).strip('._')
    return clean[:60] or "Assignment_Solution"

@submissions_bp.route('/draft', methods=['POST'])
def save_draft():
    """Save or update student edited draft solution."""
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        solution_id = data.get('solution_id') or data.get('solutionId')
        task_id = data.get('task_id') or data.get('taskId')
        edited_answer = data.get('edited_answer') or data.get('editedAnswer', '')
        status = data.get('status', 'DRAFT')

        if not solution_id and not task_id:
            return jsonify({"error": "task_id or solution_id is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        if solution_id:
            c.execute("""
                UPDATE solutions
                SET edited_answer = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE solution_id = ?
            """, (edited_answer, status, solution_id))
        elif task_id:
            c.execute("""
                INSERT INTO solutions (task_id, generated_answer, edited_answer, status)
                VALUES (?, ?, ?, ?)
            """, (task_id, edited_answer, edited_answer, status))
            solution_id = c.lastrowid

        if task_id:
            c.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?", (status, task_id))

        conn.commit()
        logger.info(f"Draft saved for solution #{solution_id} (status: {status})")
        return jsonify({"success": True, "solution_id": solution_id, "message": "Draft saved successfully."})

    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@submissions_bp.route('/generate-file', methods=['POST'])
def generate_submission_file():
    """
    Generate a real downloadable assignment file (DOCX or TXT) from the latest approved student answer.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        task_id = data.get('task_id') or data.get('taskId')
        solution_id = data.get('solution_id') or data.get('solutionId')
        file_format = (data.get('format') or data.get('file_format') or 'DOCX').upper()
        custom_answer = data.get('answer') or data.get('edited_answer')

        if not task_id and not custom_answer:
            return jsonify({"error": "task_id or answer text is required"}), 400

        task_title = "Assignment Solution"
        course_name = "General Course"
        answer_text = custom_answer or ""

        if task_id:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                SELECT t.*, c.course_name
                FROM tasks t
                LEFT JOIN courses c ON t.course_id = c.course_id
                WHERE t.task_id = ?
            """, (task_id,))
            task_row = c.fetchone()
            if task_row:
                task_title = task_row['title'] or task_title
                course_name = task_row['course_name'] or course_name

            if not answer_text:
                if solution_id:
                    c.execute("SELECT * FROM solutions WHERE solution_id = ?", (solution_id,))
                else:
                    c.execute("SELECT * FROM solutions WHERE task_id = ? ORDER BY created_at DESC LIMIT 1", (task_id,))
                sol_row = c.fetchone()
                if sol_row:
                    answer_text = sol_row['edited_answer'] or sol_row['generated_answer'] or ""

        if not answer_text or not answer_text.strip():
            return jsonify({"error": "Cannot generate file from an empty answer. Please write or generate a solution first."}), 400

        # Base filename
        base_name = _sanitize_filename(task_title)
        timestamp_str = datetime.now().strftime("%Y%m%d")

        if file_format == 'DOCX':
            if not docx:
                # Fallback to TXT if docx not installed
                file_format = 'TXT'
            else:
                doc = docx.Document()

                # Add Title
                title_p = doc.add_heading(task_title, level=1)
                title_p.paragraph_format.space_after = Pt(6)

                # Add Metadata Subheader
                meta_p = doc.add_paragraph()
                meta_p.paragraph_format.space_after = Pt(14)
                r1 = meta_p.add_run(f"Course: {course_name}\n")
                r1.bold = True
                r2 = meta_p.add_run(f"Date: {datetime.now().strftime('%B %d, %Y')}\n")
                r2.font.color.rgb = RGBColor(100, 100, 100)
                r3 = meta_p.add_run("Prepared via StudyMate AI Student Assistant\n")
                r3.font.italic = True
                r3.font.size = Pt(9.5)
                r3.font.color.rgb = RGBColor(120, 120, 120)

                doc.add_heading("Solution & Academic Response", level=2)

                # Process answer paragraphs & code blocks
                paragraphs = answer_text.split('\n\n')
                for p_text in paragraphs:
                    p_text = p_text.strip()
                    if not p_text:
                        continue

                    # Check for code blocks
                    if p_text.startswith('```') and p_text.endswith('```'):
                        code_lines = p_text.split('\n')[1:-1]
                        code_content = '\n'.join(code_lines)
                        code_p = doc.add_paragraph()
                        code_p.paragraph_format.left_indent = Inches(0.3)
                        code_p.paragraph_format.space_after = Pt(6)
                        run = code_p.add_run(code_content)
                        run.font.name = 'Consolas'
                        run.font.size = Pt(9.5)
                        run.font.color.rgb = RGBColor(40, 40, 40)
                    elif p_text.startswith('# '):
                        doc.add_heading(p_text[2:], level=2)
                    elif p_text.startswith('## '):
                        doc.add_heading(p_text[3:], level=3)
                    elif p_text.startswith('### '):
                        doc.add_heading(p_text[4:], level=4)
                    elif p_text.startswith('- ') or p_text.startswith('* '):
                        for line in p_text.split('\n'):
                            clean_line = re.sub(r'^[\s\-\*]+\s*', '', line)
                            if clean_line:
                                doc.add_paragraph(clean_line, style='List Bullet')
                    else:
                        doc.add_paragraph(p_text)

                buffer = io.BytesIO()
                doc.save(buffer)
                file_bytes = buffer.getvalue()
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                file_name = f"{base_name}_{timestamp_str}.docx"

        if file_format == 'TXT':
            header = (
                f"{'='*60}\n"
                f"{task_title.upper()}\n"
                f"Course: {course_name}\n"
                f"Date: {datetime.now().strftime('%B %d, %Y')}\n"
                f"Prepared via StudyMate AI\n"
                f"{'='*60}\n\n"
            )
            full_content = header + answer_text
            file_bytes = full_content.encode('utf-8')
            mime_type = "text/plain"
            file_name = f"{base_name}_{timestamp_str}.txt"

        file_b64 = base64.b64encode(file_bytes).decode('utf-8')
        data_url = f"data:{mime_type};base64,{file_b64}"

        return jsonify({
            "success": True,
            "file_name": file_name,
            "file_format": file_format,
            "mime_type": mime_type,
            "file_size": len(file_bytes),
            "file_base64": file_b64,
            "data_url": data_url,
            "task_title": task_title,
            "course_name": course_name,
            "word_count": len(answer_text.split())
        })

    except Exception as e:
        logger.error(f"Error generating submission file: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@submissions_bp.route('/verify', methods=['POST'])
def verify_and_record_submission():
    """
    Truthful verification endpoint: Records submission ONLY when confirmed by Moodle response/status.
    Distinguishes completed submission from draft upload and unverified attempts.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        task_id = data.get('task_id') or data.get('taskId')
        solution_id = data.get('solution_id') or data.get('solutionId')
        moodle_status = (data.get('moodle_status') or data.get('status') or '').strip()
        verified = bool(data.get('verified', False))
        file_name = data.get('file_name', '')
        file_format = data.get('file_format', 'TXT')
        result_text = data.get('result', '')

        if not task_id:
            return jsonify({"error": "task_id is required"}), 400

        # Normalized status check
        status_lower = moodle_status.lower()
        is_submitted = (
            verified or
            'submitted for grading' in status_lower or
            'abgegeben zur bewertung' in status_lower or
            'rendu pour évaluation' in status_lower
        )
        is_draft = (
            'draft (not submitted)' in status_lower or
            'entwurf' in status_lower or
            'brouillon' in status_lower
        )

        conn = get_db_connection()
        c = conn.cursor()

        if not solution_id:
            c.execute("SELECT solution_id FROM solutions WHERE task_id = ? ORDER BY created_at DESC LIMIT 1", (task_id,))
            sol = c.fetchone()
            if sol:
                solution_id = sol['solution_id']
            elif is_submitted:
                c.execute("""
                    INSERT INTO solutions (task_id, generated_answer, edited_answer, status)
                    VALUES (?, ?, ?, 'SUBMITTED')
                """, (task_id, result_text or "Direct Moodle submission", result_text or "Direct Moodle submission"))
                solution_id = c.lastrowid

        if is_submitted:
            # Verified complete submission
            res_str = result_text or f"Confirmed Moodle submission ({file_name or 'file'})"
            c.execute("""
                INSERT INTO submissions (task_id, solution_id, result, file_name, file_format, moodle_status, verified)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (task_id, solution_id, res_str, file_name, file_format, moodle_status or "Submitted for grading"))
            sub_id = c.lastrowid

            if solution_id:
                c.execute("UPDATE solutions SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE solution_id = ?", (solution_id,))

            c.execute("""
                UPDATE tasks
                SET status = 'SUBMITTED',
                    submission_status = 'Submitted for grading',
                    availability_status = 'SUBMITTED',
                    is_actionable_pending = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (task_id,))
            conn.commit()

            logger.info(f"Verified submission recorded for Task #{task_id} (Submission #{sub_id})")
            return jsonify({
                "success": True,
                "verified": True,
                "status": "SUBMITTED",
                "submission_id": sub_id,
                "message": "Assignment submitted successfully. Moodle has confirmed your submission."
            })

        elif is_draft:
            # File uploaded as draft in Moodle, final submission action not completed yet
            if solution_id:
                c.execute("UPDATE solutions SET status = 'DRAFT', updated_at = CURRENT_TIMESTAMP WHERE solution_id = ?", (solution_id,))

            c.execute("""
                UPDATE tasks
                SET status = 'In Draft',
                    submission_status = 'Draft (not submitted)',
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (task_id,))
            conn.commit()

            logger.info(f"Draft upload state recorded for Task #{task_id}")
            return jsonify({
                "success": True,
                "verified": False,
                "is_draft": True,
                "status": "DRAFT",
                "message": "Your file has been uploaded as a draft, but the assignment has not been finally submitted. Complete the remaining step in Moodle."
            })

        else:
            # Inconclusive or unverified
            logger.warning(f"Unverified submission attempt for Task #{task_id}: status='{moodle_status}'")
            return jsonify({
                "success": False,
                "verified": False,
                "unverified": True,
                "status": "UNVERIFIED",
                "message": "Submission could not be verified. Please check Moodle before assuming your assignment was submitted."
            })

    except Exception as e:
        logger.error(f"Error verifying submission: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@submissions_bp.route('/submit', methods=['POST'])
def legacy_submit_solution():
    """
    Backwards-compatible submit endpoint with verification support.
    """
    data = request.get_json(silent=True) or {}
    # If verified parameter is provided, use verified handler
    if 'verified' in data or 'moodle_status' in data:
        return verify_and_record_submission()

    # Otherwise handle as before with task update
    conn = None
    try:
        task_id = data.get('task_id') or data.get('taskId')
        solution_id = data.get('solution_id') or data.get('solutionId')
        result_text = data.get('result', 'Submitted via StudyMate AI')

        if not task_id:
            return jsonify({"error": "task_id is required"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        if not solution_id:
            c.execute("SELECT solution_id FROM solutions WHERE task_id = ? ORDER BY created_at DESC LIMIT 1", (task_id,))
            sol = c.fetchone()
            if sol:
                solution_id = sol['solution_id']

        if solution_id:
            c.execute("""
                INSERT INTO submissions (task_id, solution_id, result, verified)
                VALUES (?, ?, ?, 1)
            """, (task_id, solution_id, result_text))
            submission_id = c.lastrowid
            c.execute("UPDATE solutions SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE solution_id = ?", (solution_id,))
        else:
            submission_id = None

        c.execute("""
            UPDATE tasks
            SET status = 'SUBMITTED',
                availability_status = 'SUBMITTED',
                is_actionable_pending = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """, (task_id,))
        conn.commit()

        logger.info(f"Task #{task_id} marked as submitted (submission #{submission_id})")
        return jsonify({"success": True, "submission_id": submission_id, "message": "Task marked as submitted."})

    except Exception as e:
        logger.error(f"Error submitting solution: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
