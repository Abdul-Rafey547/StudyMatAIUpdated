"""
StudyMate AI - Moodle API Connector
Implements BaseLMSConnector for Moodle LMS Web Services REST API.
Handles authentication, error mapping, timeouts, token security, and response normalization.
"""
import urllib.request
import urllib.parse
import json
import uuid
from typing import Dict, List, Optional, Any
from config import Config
from utils.logger import get_logger
from moodle.lms_interface import BaseLMSConnector

logger = get_logger('studymate.moodle')


class MoodleClient(BaseLMSConnector):
    """
    Modular REST API client for Moodle Web Services.
    Communicates via /webservice/rest/server.php using token authentication.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 15):
        self.base_url = (base_url or Config.MOODLE_URL or '').rstrip('/')
        self.token = token if token is not None else Config.MOODLE_TOKEN
        self.timeout = timeout
        self.endpoint = f"{self.base_url}/webservice/rest/server.php" if self.base_url else ""
        self._cached_site_info: Optional[Dict[str, Any]] = None

    def mask_token(self) -> str:
        """Return masked token for secure logging."""
        if not self.token:
            return "<none>"
        if len(self.token) <= 8:
            return "***"
        return f"{self.token[:4]}...{self.token[-4:]}"

    def is_configured(self) -> bool:
        """Check whether base URL and token are configured."""
        return bool(self.base_url and self.token)

    def call(self, wsfunction: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a Moodle Web Services REST call.
        Handles network errors, HTTP codes, Moodle exceptions, and response validation.
        """
        if not self.is_configured():
            logger.info("Moodle client not configured with token; skipping direct API call.")
            return {
                "error": "Moodle token or base URL not configured",
                "errorcode": "not_configured"
            }

        payload = {
            'wstoken': self.token,
            'wsfunction': wsfunction,
            'moodlewsrestformat': 'json',
            **(params or {})
        }

        try:
            logger.debug(f"[Moodle API] Calling {wsfunction} (token: {self.mask_token()})")
            encoded_data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(
                self.endpoint,
                data=encoded_data,
                headers={'User-Agent': 'StudyMate-AI/1.0', 'Accept': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.status
                body = response.read().decode('utf-8')

            if not body or not body.strip():
                return {"error": "Empty response received from Moodle server", "errorcode": "empty_response"}

            parsed = json.loads(body)

            # Check for Moodle exception responses
            if isinstance(parsed, dict) and 'exception' in parsed:
                err_code = parsed.get('errorcode', 'unknown_exception')
                err_msg = parsed.get('message', 'Moodle Web Service Exception')
                logger.warning(f"[Moodle API] Exception from {wsfunction}: {err_code} - {err_msg}")
                return {
                    "error": err_msg,
                    "errorcode": err_code,
                    "exception": parsed.get('exception'),
                    "debuginfo": parsed.get('debuginfo')
                }

            return parsed

        except urllib.error.HTTPError as he:
            logger.error(f"[Moodle API] HTTP {he.code} error calling {wsfunction}: {he.reason}")
            try:
                err_body = he.read().decode('utf-8')
                parsed_err = json.loads(err_body)
                if isinstance(parsed_err, dict) and 'message' in parsed_err:
                    return {"error": parsed_err['message'], "errorcode": parsed_err.get('errorcode', f"http_{he.code}")}
            except Exception:
                pass
            return {"error": f"Moodle HTTP {he.code}: {he.reason}", "errorcode": f"http_{he.code}"}

        except urllib.error.URLError as ue:
            logger.error(f"[Moodle API] Network connection error calling {wsfunction}: {ue.reason}")
            is_timeout = isinstance(ue.reason, TimeoutError) or 'timed out' in str(ue.reason).lower()
            err_code = "connection_timeout" if is_timeout else "connection_failed"
            return {"error": f"Cannot connect to Moodle server: {ue.reason}", "errorcode": err_code}

        except TimeoutError:
            logger.error(f"[Moodle API] Timeout after {self.timeout}s calling {wsfunction}")
            return {"error": f"Moodle request timed out after {self.timeout} seconds", "errorcode": "connection_timeout"}

        except json.JSONDecodeError as je:
            logger.error(f"[Moodle API] Invalid JSON received from {wsfunction}: {je}")
            return {"error": "Invalid JSON response from Moodle server", "errorcode": "invalid_json"}

        except Exception as e:
            logger.error(f"[Moodle API] Unexpected error calling {wsfunction}: {e}")
            return {"error": str(e), "errorcode": "unknown_error"}

    def check_connection(self) -> Dict[str, Any]:
        """
        Verify connection and authorization by calling core_webservice_get_site_info.
        """
        if not self.is_configured():
            return {
                "connected": False,
                "error": "Moodle base URL or Web Services token is not configured in .env",
                "errorcode": "not_configured"
            }

        res = self.call('core_webservice_get_site_info')
        if not res or 'error' in res or 'exception' in res:
            err_code = res.get('errorcode', 'connection_failed') if isinstance(res, dict) else 'connection_failed'
            err_msg = res.get('error', 'Failed to connect to Moodle Web Services') if isinstance(res, dict) else 'Connection error'
            return {
                "connected": False,
                "error": err_msg,
                "errorcode": err_code,
                "base_url": self.base_url
            }

        self._cached_site_info = res
        funcs = [f.get('name') for f in res.get('functions', []) if isinstance(f, dict)]

        return {
            "connected": True,
            "sitename": res.get('sitename'),
            "siteurl": res.get('siteurl', self.base_url),
            "username": res.get('username'),
            "fullname": res.get('fullname'),
            "userid": res.get('userid'),
            "user_id": res.get('userid'),
            "release": res.get('release'),
            "version": res.get('version'),
            "downloadfiles": bool(res.get('downloadfiles')),
            "uploadfiles": bool(res.get('uploadfiles')),
            "functions": funcs,
            "message": f"Connected to {res.get('sitename')} as {res.get('fullname')} (User ID {res.get('userid')})"
        }

    def get_site_info(self) -> Dict[str, Any]:
        """Fetch site information and user details."""
        if self._cached_site_info:
            return self._cached_site_info
        info = self.call('core_webservice_get_site_info')
        if isinstance(info, dict) and 'userid' in info:
            self._cached_site_info = info
        return info

    def get_courses(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve enrolled courses for the student using core_enrol_get_users_courses.
        Falls back to core_course_get_courses if enrol function is unavailable.
        """
        uid = user_id
        if not uid:
            site_info = self.get_site_info()
            if isinstance(site_info, dict) and 'userid' in site_info:
                uid = site_info['userid']

        courses = []
        if uid:
            enrol_res = self.call('core_enrol_get_users_courses', {'userid': uid})
            if isinstance(enrol_res, list):
                courses = enrol_res
            elif isinstance(enrol_res, dict) and 'error' in enrol_res:
                logger.warning(f"[Moodle API] core_enrol_get_users_courses failed: {enrol_res.get('error')}. Falling back to core_course_get_courses.")

        # Fallback if enrolled courses call was empty or errored
        if not courses:
            course_res = self.call('core_course_get_courses')
            if isinstance(course_res, list):
                # Filter out site course (id=1)
                courses = [c for c in course_res if c.get('id') != 1]

        normalized = []
        for c in courses:
            if not isinstance(c, dict):
                continue
            normalized.append({
                'course_id': c.get('id'),
                'id': c.get('id'),
                'course_name': c.get('fullname') or c.get('displayname') or f"Course #{c.get('id')}",
                'shortname': c.get('shortname', ''),
                'visible': bool(c.get('visible', 1)),
                'startdate': c.get('startdate'),
                'enddate': c.get('enddate'),
                'progress': c.get('progress')
            })

        return normalized

    def get_course_contents(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve sections and modules for a course via core_course_get_contents.
        Provides availability, restrictions (uservisible), cmid, and direct URLs.
        """
        res = self.call('core_course_get_contents', {'courseid': course_id})
        if isinstance(res, list):
            return res
        return []

    def get_assignments(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve course assignments via mod_assign_get_assignments.
        """
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid

        res = self.call('mod_assign_get_assignments', params)
        if not isinstance(res, dict) or 'courses' not in res:
            logger.warning(f"[Moodle API] mod_assign_get_assignments returned unexpected data: {res}")
            return []

        all_assignments = []
        for course_entry in res.get('courses', []):
            c_id = course_entry.get('id')
            c_name = course_entry.get('fullname', '')
            for a in course_entry.get('assignments', []):
                a_copy = dict(a)
                a_copy['course_id'] = c_id
                a_copy['course_name'] = c_name
                all_assignments.append(a_copy)

        return all_assignments

    def get_submission_status(self, assignment_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve submission status and attempt details via mod_assign_get_submission_status.
        """
        params: Dict[str, Any] = {'assignid': assignment_id}
        if user_id:
            params['userid'] = user_id

        res = self.call('mod_assign_get_submission_status', params)
        if not isinstance(res, dict) or 'lastattempt' not in res:
            return {
                'status': 'unknown',
                'submission_status': 'No attempt',
                'can_edit': True,
                'is_submitted': False,
                'is_draft': False,
                'raw': res
            }

        lastattempt = res.get('lastattempt', {})
        submission = lastattempt.get('submission', {})
        raw_status = (submission.get('status') or '').lower()
        grading_status = (res.get('gradingsummary', {}).get('gradingstatus') or 'notgraded').lower()

        is_submitted = (raw_status == 'submitted')
        is_draft = (raw_status == 'draft')
        is_new = (raw_status in ('new', '', 'reopened'))
        can_edit = bool(lastattempt.get('canedit', True))
        is_locked = bool(lastattempt.get('locked', False))
        is_graded = bool(lastattempt.get('graded', False) or ('graded' in grading_status and 'notgraded' not in grading_status and 'not graded' not in grading_status))

        if is_submitted:
            status_text = 'Submitted for grading'
        elif is_draft:
            status_text = 'Draft (not submitted)'
        else:
            status_text = 'No attempt'

        return {
            'status': raw_status or 'new',
            'submission_status': status_text,
            'grading_status': 'Graded' if is_graded else 'Not graded',
            'is_submitted': is_submitted,
            'is_draft': is_draft,
            'is_new': is_new,
            'can_edit': can_edit,
            'is_locked': is_locked,
            'is_graded': is_graded,
            'submissions_enabled': bool(lastattempt.get('submissionsenabled', True)),
            'attempt_number': submission.get('attemptnumber', 0),
            'time_modified': submission.get('timemodified'),
            'raw': res
        }

    def get_quizzes(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve course quizzes via mod_quiz_get_quizzes_by_courses.
        """
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid

        res = self.call('mod_quiz_get_quizzes_by_courses', params)
        if not isinstance(res, dict) or 'quizzes' not in res:
            logger.warning(f"[Moodle API] mod_quiz_get_quizzes_by_courses returned unexpected data: {res}")
            return []

        return res.get('quizzes', [])

    def get_quiz_access_information(self, quiz_id: int) -> Dict[str, Any]:
        """
        Check quiz availability and access restrictions via mod_quiz_get_quiz_access_information.
        """
        res = self.call('mod_quiz_get_quiz_access_information', {'quizid': quiz_id})
        if not isinstance(res, dict) or 'canattempt' not in res:
            return {'canattempt': True, 'preventaccessreasons': [], 'raw': res}
        return res

    def get_quiz_user_attempts(self, quiz_id: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve quiz attempts via mod_quiz_get_user_attempts.
        """
        params: Dict[str, Any] = {'quizid': quiz_id, 'status': 'all'}
        if user_id:
            params['userid'] = user_id

        res = self.call('mod_quiz_get_user_attempts', params)
        if isinstance(res, dict) and 'attempts' in res:
            return res.get('attempts', [])
        return []

    def get_resources(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve file resources via mod_resource_get_resources_by_courses.
        """
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid

        res = self.call('mod_resource_get_resources_by_courses', params)
        if isinstance(res, dict) and 'resources' in res:
            return res.get('resources', [])
        return []

    def get_pages(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve Moodle Page resources via mod_page_get_pages_by_courses.
        """
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid

        res = self.call('mod_page_get_pages_by_courses', params)
        if isinstance(res, dict) and 'pages' in res:
            return res.get('pages', [])
        return []

    def get_books(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve Moodle Book resources via mod_book_get_books_by_courses.
        """
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid

        res = self.call('mod_book_get_books_by_courses', params)
        if isinstance(res, dict) and 'books' in res:
            return res.get('books', [])
        return []

    def get_resource_content(self, file_url_or_id: str) -> Optional[bytes]:
        """
        Download learning material binary content with token authentication.
        Appends wstoken to Moodle pluginfile URLs if needed.
        """
        if not file_url_or_id:
            return None

        url = file_url_or_id
        # If token is needed and not present in url
        if self.token and 'token=' not in url:
            delimiter = '&' if '?' in url else '?'
            url = f"{url}{delimiter}token={self.token}"

        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'StudyMate-AI/1.0'}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return resp.read()
                logger.warning(f"[Moodle API] Failed downloading resource ({resp.status}): {url}")
                return None
        except Exception as e:
            logger.error(f"[Moodle API] Error downloading resource content from {file_url_or_id}: {e}")
            return None

    def upload_file_to_draft_area(self, file_data: bytes, file_name: str, item_id: int = 0) -> Optional[int]:
        """
        Upload binary file to Moodle user draft file area via webservice/upload.php.
        Returns the draft itemid for use in mod_assign_save_submission.
        """
        if not self.is_configured() or not file_data:
            return None

        upload_url = f"{self.base_url}/webservice/upload.php?token={self.token}"
        if item_id:
            upload_url += f"&itemid={item_id}"

        boundary = '----StudyMateBoundary' + uuid.uuid4().hex
        header_part = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file_1"; filename="{file_name}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode('utf-8')
        footer_part = f'\r\n--{boundary}--\r\n'.encode('utf-8')
        body = header_part + file_data + footer_part

        try:
            req = urllib.request.Request(
                upload_url,
                data=body,
                headers={
                    'Content-Type': f'multipart/form-data; boundary={boundary}',
                    'User-Agent': 'StudyMate-AI/1.0'
                }
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res_body = resp.read().decode('utf-8')
                parsed = json.loads(res_body)
                if isinstance(parsed, list) and len(parsed) > 0 and 'itemid' in parsed[0]:
                    return int(parsed[0]['itemid'])
                elif isinstance(parsed, dict) and 'error' in parsed:
                    logger.warning(f"[Moodle API] Upload error: {parsed.get('error')}")
        except Exception as e:
            logger.error(f"[Moodle API] Exception uploading file {file_name}: {e}")
        return None

    def submit_assignment(self, assignment_id: int, file_data: Optional[bytes] = None,
                          file_name: Optional[str] = None,
                          text_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Save or submit an assignment solution to Moodle via REST Web Services.
        Supports file attachments (DOCX, PDF, TXT) and online text.
        """
        if not self.is_configured():
            return {"success": False, "error": "Moodle client not configured", "errorcode": "not_configured"}

        params = {'assignmentid': assignment_id}

        # 1. If file data provided, upload to draft file area
        draft_itemid = None
        if file_data and file_name:
            draft_itemid = self.upload_file_to_draft_area(file_data, file_name)
            if draft_itemid:
                params['plugindata[files_filemanager]'] = draft_itemid

        # 2. If text content provided, set online text editor plugin
        if text_content:
            params['plugindata[onlinetext_editor][text]'] = text_content
            params['plugindata[onlinetext_editor][format]'] = 1  # HTML format
            params['plugindata[onlinetext_editor][itemid]'] = 0

        logger.info(f"[Moodle API] Saving submission for assignment {assignment_id} (files: {bool(draft_itemid)}, text: {bool(text_content)})")
        save_res = self.call('mod_assign_save_submission', params)

        # Check for warnings or errors
        warnings = []
        if isinstance(save_res, list):
            warnings = save_res
        elif isinstance(save_res, dict) and 'error' in save_res:
            return {"success": False, "error": save_res['error'], "errorcode": save_res.get('errorcode')}

        # Check submission status to verify
        status = self.get_submission_status(assignment_id)
        is_submitted = status.get('is_submitted', False) or status.get('is_draft', False)

        return {
            "success": True,
            "assignment_id": assignment_id,
            "draft_itemid": draft_itemid,
            "submission_status": status.get('submission_status', 'Submitted for grading'),
            "is_submitted": status.get('is_submitted', False),
            "is_draft": status.get('is_draft', False),
            "warnings": warnings
        }
