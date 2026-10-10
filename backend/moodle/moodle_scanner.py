"""
StudyMate AI - Moodle Activity & Resource Scanner
Performs reliable, API-backed scanning of enrolled courses, activities, availability, and learning materials.
Reconciles database records with truth from Moodle Web Services API.
"""
import io
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from config import Config
from database.database import get_db_connection
from moodle.moodle_client import MoodleClient
from utils.helpers import sanitize_html
from utils.logger import get_logger

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

logger = get_logger('studymate.moodle.scanner')


class MoodleScanner:
    """
    Coordinates scanning student activities and study materials across enrolled Moodle courses.
    Applies strict availability categorization and preserves student drafts.
    """

    def __init__(self, client: Optional[MoodleClient] = None):
        self.client = client or MoodleClient()

    @staticmethod
    def _timestamp_to_iso(ts: Optional[int]) -> Optional[str]:
        if not ts or ts <= 0:
            return None
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    def scan_enrolled_courses(self, user_id: Optional[int] = None,
                              extract_text: bool = True) -> Dict[str, Any]:
        """
        Scan all enrolled courses via Moodle API.
        Normalizes activities, checks availability, stores verified records in SQLite,
        and returns clean tasks and resources.
        """
        conn_check = self.client.check_connection()
        if not conn_check.get('connected'):
            err_msg = conn_check.get('error', 'Cannot connect to Moodle Web Services')
            logger.error(f"[Scanner] Moodle connection failed: {err_msg}")
            return {
                "success": False,
                "error": err_msg,
                "errorcode": conn_check.get('errorcode', 'connection_failed')
            }

        student_uid = user_id or conn_check.get('userid')
        logger.info(f"[Scanner] Starting API scan for student user ID {student_uid}...")

        # 1. Retrieve enrolled courses
        courses = self.client.get_courses(user_id=student_uid)
        if not courses:
            logger.info("[Scanner] No enrolled courses returned by Moodle API.")
            return {
                "success": True,
                "message": "No enrolled courses found for the current student in Moodle.",
                "courses": [],
                "tasks": [],
                "resources": []
            }

        course_ids = [c['course_id'] for c in courses if c.get('course_id')]
        db_conn = get_db_connection()
        try:
            c_cursor = db_conn.cursor()

            # Map local course_id in database for each Moodle course
            db_course_map: Dict[int, int] = {}  # moodle_course_id -> db_course_id
            db_course_names: Dict[int, str] = {}

            for c_info in courses:
                m_cid = str(c_info['course_id'])
                c_name = c_info['course_name']
                db_course_names[c_info['course_id']] = c_name

                c_cursor.execute("SELECT course_id FROM courses WHERE moodle_course_id = ?", (m_cid,))
                existing_c = c_cursor.fetchone()

                if not existing_c:
                    c_cursor.execute("SELECT course_id FROM courses WHERE course_name = ?", (c_name,))
                    existing_c = c_cursor.fetchone()

                if existing_c:
                    db_cid = existing_c['course_id']
                    c_cursor.execute("""
                        UPDATE courses
                        SET course_name = ?, moodle_course_id = ?, scanned_at = CURRENT_TIMESTAMP,
                            lms_type = 'moodle', lms_instance = ?
                        WHERE course_id = ?
                    """, (c_name, m_cid, self.client.base_url, db_cid))
                else:
                    c_cursor.execute("""
                        INSERT INTO courses (course_name, moodle_course_id, scanned_at, lms_type, lms_instance)
                        VALUES (?, ?, CURRENT_TIMESTAMP, 'moodle', ?)
                    """, (c_name, m_cid, self.client.base_url))
                    db_cid = c_cursor.lastrowid

                db_course_map[c_info['course_id']] = db_cid

            # 2. Build course module visibility & metadata index via core_course_get_contents
            cm_metadata: Dict[str, Dict[str, Any]] = {}  # "assign_1" -> metadata
            for cid in course_ids:
                sections = self.client.get_course_contents(cid)
                for sec in sections:
                    for mod in sec.get('modules', []):
                        mod_name = mod.get('modname', '')
                        instance_id = mod.get('instance')
                        key = f"{mod_name}_{instance_id}"
                        cm_metadata[key] = {
                            'cmid': mod.get('id'),
                            'name': mod.get('name'),
                            'visible': bool(mod.get('visible', 1)),
                            'uservisible': bool(mod.get('uservisible', True)),
                            'availabilityinfo': mod.get('availabilityinfo', ''),
                            'url': mod.get('url', ''),
                            'contents': mod.get('contents', [])
                        }

            # 3. Fetch Assignments and evaluate availability
            now_ts = int(time.time())
            raw_assignments = self.client.get_assignments(course_ids)
            scanned_task_ids: List[int] = []

            for a in raw_assignments:
                assign_id = a.get('id')
                c_id = a.get('course_id') or a.get('course')
                db_cid = db_course_map.get(c_id)
                course_name = db_course_names.get(c_id, 'General Course')

                cm_info = cm_metadata.get(f"assign_{assign_id}", {})
                cmid = a.get('cmid') or cm_info.get('cmid')
                assign_url = f"{self.client.base_url}/mod/assign/view.php?id={cmid}" if cmid else a.get('moodle_url', '')

                title = (a.get('name') or 'Assignment').strip()
                description = sanitize_html(a.get('intro', ''))
                due_ts = a.get('duedate', 0)
                cutoff_ts = a.get('cutoffdate', 0)
                allowfrom_ts = a.get('allowsubmissionsfromdate', 0)

                due_date_str = self._timestamp_to_iso(due_ts)
                cutoff_date_str = self._timestamp_to_iso(cutoff_ts)
                open_date_str = self._timestamp_to_iso(allowfrom_ts)

                # Determine availability from API data
                is_uservisible = cm_info.get('uservisible', True)
                is_mod_visible = cm_info.get('visible', True)

                # Check submission status
                sub_status = self.client.get_submission_status(assign_id, user_id=student_uid)
                submission_status_str = sub_status.get('submission_status', 'No attempt')
                grading_status_str = sub_status.get('grading_status', 'Not graded')
                is_submitted = sub_status.get('is_submitted', False)
                is_draft = sub_status.get('is_draft', False)
                is_graded = sub_status.get('is_graded', False)
                can_edit = sub_status.get('can_edit', True)
                resubmission_allowed = (is_submitted and can_edit)

                if not is_uservisible or not is_mod_visible:
                    avail_status = 'UNAVAILABLE'
                    is_actionable = False
                elif is_graded and not resubmission_allowed:
                    avail_status = 'COMPLETED'
                    is_actionable = False
                elif is_submitted and not resubmission_allowed:
                    avail_status = 'SUBMITTED'
                    is_actionable = False
                elif allowfrom_ts and allowfrom_ts > now_ts:
                    avail_status = 'UPCOMING'
                    is_actionable = False
                elif cutoff_ts and cutoff_ts > 0 and cutoff_ts < now_ts and not is_submitted:
                    avail_status = 'CLOSED'
                    is_actionable = False
                else:
                    avail_status = 'AVAILABLE'
                    is_actionable = True

                # Stable Deduplication & SQLite Sync
                task_row = self._sync_task_record(
                    c_cursor,
                    course_id=db_cid,
                    moodle_activity_id=str(assign_id),
                    task_type='ASSIGNMENT',
                    title=title,
                    description=description,
                    due_date=due_date_str,
                    cutoff_date=cutoff_date_str,
                    open_date=open_date_str,
                    close_date=cutoff_date_str or due_date_str,
                    moodle_url=assign_url,
                    submission_status=submission_status_str,
                    grading_status=grading_status_str,
                    availability_status=avail_status,
                    is_actionable_pending=1 if is_actionable else 0,
                    resubmission_allowed=1 if resubmission_allowed else 0,
                    lms_instance=self.client.base_url
                )
                if task_row:
                    scanned_task_ids.append(task_row)

            # 4. Fetch Quizzes and evaluate availability
            raw_quizzes = self.client.get_quizzes(course_ids)
            for q in raw_quizzes:
                quiz_id = q.get('id')
                c_id = q.get('course')
                db_cid = db_course_map.get(c_id)
                course_name = db_course_names.get(c_id, 'General Course')

                cm_info = cm_metadata.get(f"quiz_{quiz_id}", {})
                cmid = q.get('coursemodule') or cm_info.get('cmid')
                quiz_url = f"{self.client.base_url}/mod/quiz/view.php?id={cmid}" if cmid else ''

                title = (q.get('name') or 'Quiz').strip()
                description = sanitize_html(q.get('intro', ''))
                timeopen_ts = q.get('timeopen', 0)
                timeclose_ts = q.get('timeclose', 0)

                open_date_str = self._timestamp_to_iso(timeopen_ts)
                close_date_str = self._timestamp_to_iso(timeclose_ts)

                is_uservisible = cm_info.get('uservisible', True)
                is_mod_visible = cm_info.get('visible', True)

                access_info = self.client.get_quiz_access_information(quiz_id)
                can_attempt = access_info.get('canattempt', True)
                prevent_reasons = access_info.get('preventaccessreasons', [])

                attempts = self.client.get_quiz_user_attempts(quiz_id, user_id=student_uid)
                has_finished_attempt = any(att.get('state') == 'finished' for att in attempts)
                has_inprogress_attempt = any(att.get('state') == 'inprogress' for att in attempts)

                if has_finished_attempt and not can_attempt:
                    avail_status = 'COMPLETED'
                    sub_status_str = 'Completed'
                    is_actionable = False
                elif not is_uservisible or not is_mod_visible:
                    avail_status = 'UNAVAILABLE'
                    sub_status_str = 'Restricted'
                    is_actionable = False
                elif timeopen_ts and timeopen_ts > now_ts:
                    avail_status = 'UPCOMING'
                    sub_status_str = 'Not yet open'
                    is_actionable = False
                elif timeclose_ts and timeclose_ts > 0 and timeclose_ts < now_ts:
                    avail_status = 'CLOSED'
                    sub_status_str = 'Closed'
                    is_actionable = False
                elif not can_attempt and not has_inprogress_attempt:
                    avail_status = 'CLOSED'
                    sub_status_str = 'Closed / Max attempts reached'
                    is_actionable = False
                else:
                    avail_status = 'AVAILABLE'
                    sub_status_str = 'In progress' if has_inprogress_attempt else 'No attempt'
                    is_actionable = True

                task_row = self._sync_task_record(
                    c_cursor,
                    course_id=db_cid,
                    moodle_activity_id=str(quiz_id),
                    task_type='QUIZ',
                    title=title,
                    description=description,
                    due_date=close_date_str,
                    cutoff_date=close_date_str,
                    open_date=open_date_str,
                    close_date=close_date_str,
                    moodle_url=quiz_url,
                    submission_status=sub_status_str,
                    grading_status='Graded' if has_finished_attempt else 'Not graded',
                    availability_status=avail_status,
                    is_actionable_pending=1 if is_actionable else 0,
                    resubmission_allowed=0,
                    lms_instance=self.client.base_url
                )
                if task_row:
                    scanned_task_ids.append(task_row)

            # 5. Fetch Study Resources (File resources, Pages, Books)
            raw_resources = self.client.get_resources(course_ids)
            scanned_res_ids: List[int] = []

            for r in raw_resources:
                res_id = r.get('id')
                c_id = r.get('course')
                db_cid = db_course_map.get(c_id)

                cm_info = cm_metadata.get(f"resource_{res_id}", {})
                cmid = r.get('coursemodule') or cm_info.get('cmid')
                moodle_page_url = f"{self.client.base_url}/mod/resource/view.php?id={cmid}" if cmid else ''

                title = (r.get('name') or 'Study Material').strip()
                description = sanitize_html(r.get('intro', ''))

                files = r.get('contentfiles', [])
                file_info = files[0] if files else {}
                file_name = file_info.get('filename', '')
                file_size_bytes = file_info.get('filesize', 0)
                file_url = file_info.get('fileurl', '')
                mime_type = file_info.get('mimetype', '')

                # Determine type
                r_type = 'FILE'
                lower_name = file_name.lower()
                if lower_name.endswith('.pdf') or 'pdf' in mime_type.lower():
                    r_type = 'PDF'
                elif lower_name.endswith('.docx') or lower_name.endswith('.doc'):
                    r_type = 'DOCX'
                elif lower_name.endswith('.pptx') or lower_name.endswith('.ppt'):
                    r_type = 'PPTX'
                elif lower_name.endswith('.txt'):
                    r_type = 'TXT'

                file_size_str = f"{round(file_size_bytes / 1024, 1)} KB" if file_size_bytes > 0 else ""

                # Download content & extract text if requested
                extracted_text = ""
                is_scanned_img = 0

                if extract_text and file_url:
                    extracted_text, is_scanned_img = self._extract_resource_text(file_url, r_type)

                res_row = self._sync_resource_record(
                    c_cursor,
                    course_id=db_cid,
                    moodle_resource_id=str(res_id),
                    title=title,
                    resource_type=r_type,
                    file_name=file_name,
                    mime_type=mime_type,
                    file_size=file_size_str,
                    description=description,
                    moodle_url=moodle_page_url or file_url,
                    direct_url=file_url,
                    availability_status='AVAILABLE',
                    extracted_text=extracted_text,
                    is_scanned_image=is_scanned_img
                )
                if res_row:
                    scanned_res_ids.append(res_row)

            # 6. Reconcile stale database tasks & resources:
            # A. Mark tasks that belong to non-enrolled courses as not actionable pending
            enrolled_db_cids = list(db_course_map.values())
            if enrolled_db_cids:
                placeholders = ','.join('?' for _ in enrolled_db_cids)
                c_cursor.execute(f"""
                    UPDATE tasks
                    SET is_actionable_pending = 0
                    WHERE course_id NOT IN ({placeholders})
                """, tuple(enrolled_db_cids))

                # B. Mark tasks within enrolled courses that are no longer returned by Moodle as UNAVAILABLE & non-pending
                if scanned_task_ids:
                    scanned_placeholders = ','.join('?' for _ in scanned_task_ids)
                    c_cursor.execute(f"""
                        UPDATE tasks
                        SET is_actionable_pending = 0,
                            availability_status = 'UNAVAILABLE'
                        WHERE course_id IN ({placeholders})
                          AND task_id NOT IN ({scanned_placeholders})
                    """, tuple(enrolled_db_cids + scanned_task_ids))
                else:
                    c_cursor.execute(f"""
                        UPDATE tasks
                        SET is_actionable_pending = 0,
                            availability_status = 'UNAVAILABLE'
                        WHERE course_id IN ({placeholders})
                    """, tuple(enrolled_db_cids))

                # C. Mark resources within enrolled courses that are no longer returned as UNAVAILABLE
                if scanned_res_ids:
                    res_placeholders = ','.join('?' for _ in scanned_res_ids)
                    c_cursor.execute(f"""
                        UPDATE resources
                        SET availability_status = 'UNAVAILABLE'
                        WHERE course_id IN ({placeholders})
                          AND resource_id NOT IN ({res_placeholders})
                    """, tuple(enrolled_db_cids + scanned_res_ids))

            db_conn.commit()

            # 7. Fetch fresh results for response
            c_cursor.execute("""
                SELECT t.*, c.course_name
                FROM tasks t
                LEFT JOIN courses c ON t.course_id = c.course_id
                WHERE t.course_id IN ({})
                ORDER BY t.created_at DESC
            """.format(','.join('?' for _ in enrolled_db_cids)), tuple(enrolled_db_cids))
            synced_tasks = [dict(r) for r in c_cursor.fetchall()]

            c_cursor.execute("""
                SELECT r.*, c.course_name
                FROM resources r
                LEFT JOIN courses c ON r.course_id = c.course_id
                WHERE r.course_id IN ({})
                ORDER BY r.created_at DESC
            """.format(','.join('?' for _ in enrolled_db_cids)), tuple(enrolled_db_cids))
            synced_resources = [dict(r) for r in c_cursor.fetchall()]

            pending_tasks = [t for t in synced_tasks if t.get('is_actionable_pending') == 1]

            logger.info(f"[Scanner] API Scan complete: {len(synced_tasks)} tasks ({len(pending_tasks)} actionable pending), {len(synced_resources)} resources.")

            return {
                "success": True,
                "message": f"Successfully scanned {len(courses)} enrolled courses via Moodle API.",
                "total_tasks": len(synced_tasks),
                "pending_tasks": len(pending_tasks),
                "total_resources": len(synced_resources),
                "tasks": synced_tasks,
                "resources": synced_resources,
                "courses": courses
            }

        except Exception as e:
            logger.error(f"[Scanner] Error during API scan: {e}")
            if db_conn:
                db_conn.rollback()
            return {"success": False, "error": str(e), "errorcode": "scan_exception"}
        finally:
            if db_conn:
                db_conn.close()

    def _extract_resource_text(self, file_url: str, resource_type: str) -> Tuple[str, int]:
        """Download and extract text from PDF or DOCX file."""
        try:
            content_bytes = self.client.get_resource_content(file_url)
            if not content_bytes:
                return "", 0

            stream = io.BytesIO(content_bytes)

            if resource_type == 'PDF' and pypdf:
                reader = pypdf.PdfReader(stream)
                pages = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text() or ''
                    if t.strip():
                        pages.append(f"[Page {idx + 1}]\n{t.strip()}")
                if pages:
                    return "\n\n".join(pages), 0
                else:
                    return "", 1  # Scanned image-only PDF

            elif resource_type in ('DOCX', 'DOC') and docx:
                doc = docx.Document(stream)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n\n".join(paras), 0

            elif resource_type == 'TXT':
                try:
                    return content_bytes.decode('utf-8'), 0
                except UnicodeDecodeError:
                    return content_bytes.decode('latin-1', errors='ignore'), 0

        except Exception as e:
            logger.warning(f"[Scanner] Could not extract text from {file_url}: {e}")

        return "", 0

    def _sync_task_record(self, cursor, course_id: int, moodle_activity_id: str,
                          task_type: str, title: str, description: str, due_date: Optional[str],
                          cutoff_date: Optional[str], open_date: Optional[str], close_date: Optional[str],
                          moodle_url: str, submission_status: str, grading_status: str,
                          availability_status: str, is_actionable_pending: int,
                          resubmission_allowed: int, lms_instance: str) -> Optional[int]:
        """
        Deduplicate and insert/update task record, preserving student drafts.
        """
        # Look up existing task by (moodle_activity_id, type, course_id) or moodle_url or (title, course_id)
        existing = None
        if moodle_activity_id:
            cursor.execute(
                "SELECT * FROM tasks WHERE moodle_activity_id = ? AND type = ? AND course_id = ?",
                (moodle_activity_id, task_type, course_id)
            )
            existing = cursor.fetchone()

        if not existing and moodle_url:
            cursor.execute("SELECT * FROM tasks WHERE moodle_url = ? AND course_id = ?", (moodle_url, course_id))
            existing = cursor.fetchone()

        if not existing:
            cursor.execute("SELECT * FROM tasks WHERE title = ? AND type = ? AND course_id = ?", (title, task_type, course_id))
            existing = cursor.fetchone()

        if existing:
            task_id = existing['task_id']
            curr_status = existing['status']

            # Preserve human draft workflow states unless Moodle confirmed final submission
            if curr_status in ('GENERATED', 'Draft Ready', 'REVIEW', 'In Draft', 'APPROVED') and availability_status == 'AVAILABLE':
                new_status = curr_status
            elif availability_status in ('SUBMITTED', 'COMPLETED', 'CLOSED', 'UPCOMING', 'UNAVAILABLE'):
                new_status = availability_status
            else:
                new_status = 'PENDING' if is_actionable_pending else availability_status

            cursor.execute("""
                UPDATE tasks
                SET course_id = ?, description = ?, due_date = ?, cutoff_date = ?, open_date = ?, close_date = ?,
                    moodle_url = ?, type = ?, moodle_activity_id = ?, submission_status = ?,
                    grading_status = ?, availability_status = ?, is_actionable_pending = ?,
                    resubmission_allowed = ?, status = ?, lms_type = 'moodle', lms_instance = ?,
                    source = 'api', last_scanned_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (course_id, description, due_date, cutoff_date, open_date, close_date,
                  moodle_url, task_type, moodle_activity_id, submission_status,
                  grading_status, availability_status, is_actionable_pending,
                  resubmission_allowed, new_status, lms_instance, task_id))
            return task_id
        else:
            initial_status = 'PENDING' if is_actionable_pending else availability_status
            cursor.execute("""
                INSERT INTO tasks (
                    course_id, moodle_activity_id, type, title, description,
                    due_date, cutoff_date, open_date, close_date, status,
                    submission_status, grading_status, availability_status,
                    is_actionable_pending, resubmission_allowed, moodle_url,
                    lms_type, lms_instance, source, last_scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'moodle', ?, 'api', CURRENT_TIMESTAMP)
            """, (course_id, moodle_activity_id, task_type, title, description,
                  due_date, cutoff_date, open_date, close_date, initial_status,
                  submission_status, grading_status, availability_status,
                  is_actionable_pending, resubmission_allowed, moodle_url, lms_instance))
            return cursor.lastrowid

    def _sync_resource_record(self, cursor, course_id: int, moodle_resource_id: str,
                              title: str, resource_type: str, file_name: str, mime_type: str,
                              file_size: str, description: str, moodle_url: str, direct_url: str,
                              availability_status: str, extracted_text: str, is_scanned_image: int) -> Optional[int]:
        """
        Deduplicate and insert/update resource record.
        """
        existing = None
        if moodle_url:
            cursor.execute("SELECT * FROM resources WHERE moodle_url = ?", (moodle_url,))
            existing = cursor.fetchone()

        if not existing and moodle_resource_id:
            cursor.execute(
                "SELECT * FROM resources WHERE moodle_resource_id = ? AND course_id = ?",
                (moodle_resource_id, course_id)
            )
            existing = cursor.fetchone()

        if existing:
            res_id = existing['resource_id']
            saved_text = extracted_text or existing['extracted_text'] or ''
            cursor.execute("""
                UPDATE resources
                SET course_id = ?, moodle_resource_id = ?, title = ?, resource_type = ?,
                    file_name = ?, mime_type = ?, file_size = ?,
                    description = ?, direct_url = ?, availability_status = ?,
                    extracted_text = ?, is_scanned_image = ?, updated_at = CURRENT_TIMESTAMP
                WHERE resource_id = ?
            """, (course_id, moodle_resource_id, title, resource_type, file_name, mime_type, file_size,
                  description, direct_url, availability_status,
                  saved_text, is_scanned_image, res_id))
            return res_id
        else:
            cursor.execute("""
                INSERT INTO resources (
                    course_id, moodle_resource_id, title, resource_type,
                    file_name, mime_type, file_size, description,
                    moodle_url, direct_url, availability_status, extracted_text, is_scanned_image
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (course_id, moodle_resource_id, title, resource_type,
                  file_name, mime_type, file_size, description,
                  moodle_url, direct_url, availability_status, extracted_text, is_scanned_image))
            return cursor.lastrowid
