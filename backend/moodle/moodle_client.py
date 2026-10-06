"""
StudyMate AI - Moodle Client
Interface for Moodle LMS integration via REST API / Web Services (when enabled).
"""
import urllib.request
import urllib.parse
import json
from config import Config
from utils.logger import get_logger

logger = get_logger('studymate.moodle')

class MoodleClient:
    def __init__(self, base_url=None, token=None):
        self.base_url = (base_url or Config.MOODLE_URL or '').rstrip('/')
        self.token = token or Config.MOODLE_TOKEN
        self.endpoint = f"{self.base_url}/webservice/rest/server.php"

    def is_configured(self):
        return bool(self.base_url and self.token)

    def call(self, wsfunction, params=None):
        if not self.is_configured():
            logger.info("Moodle client not configured with token; skipping direct API call.")
            return {"error": "Moodle token not configured"}

        payload = {
            'wstoken': self.token,
            'wsfunction': wsfunction,
            'moodlewsrestformat': 'json',
            **(params or {})
        }

        try:
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(self.endpoint, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                return json.loads(res_body)
        except Exception as e:
            logger.error(f"Failed to communicate with Moodle Web Services: {e}")
            return {"error": str(e)}

    def get_site_info(self):
        return self.call('core_webservice_get_site_info')

    def get_courses(self):
        return self.call('core_course_get_courses')

    def get_assignments(self, course_ids=None):
        params = {}
        if course_ids:
            for idx, cid in enumerate(course_ids):
                params[f'courseids[{idx}]'] = cid
        return self.call('mod_assign_get_assignments', params)
