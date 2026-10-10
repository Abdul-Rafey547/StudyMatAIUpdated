"""
StudyMate AI - Common LMS Connector Interface
Defines the uniform abstraction layer for LMS platforms (Moodle, Canvas, Blackboard).
Ensures task models, UI, and AI logic remain platform-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseLMSConnector(ABC):
    """
    Abstract LMS Connector Interface.
    Each supported LMS (e.g. Moodle, Canvas, Blackboard) implements this interface
    using its official REST API, OAuth2 or web-service protocols.
    """

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """
        Verify connection and authentication with the LMS server.
        Returns a dict with 'connected': bool, 'user_info': dict, 'message': str.
        """
        pass

    @abstractmethod
    def get_courses(self) -> List[Dict[str, Any]]:
        """
        Retrieve list of courses the authorized user is enrolled in.
        Returns normalized list of course dicts (course_id, course_name, shortname, visible, etc.).
        """
        pass

    @abstractmethod
    def get_assignments(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve assignments for the specified course IDs (or all enrolled courses).
        """
        pass

    @abstractmethod
    def get_quizzes(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve quizzes for the specified course IDs.
        """
        pass

    @abstractmethod
    def get_resources(self, course_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve learning materials (PDFs, docs, pages, books) for the specified course IDs.
        """
        pass

    @abstractmethod
    def get_submission_status(self, assignment_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve submission status and attempt details for an assignment.
        """
        pass

    @abstractmethod
    def get_resource_content(self, file_url_or_id: str) -> Optional[bytes]:
        """
        Download binary or text content of a learning resource with authentication.
        """
        pass

    def submit_assignment(self, assignment_id: int, file_data: Optional[bytes] = None,
                          text_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit solution to the assignment where supported by the LMS API.
        Default raises NotImplementedError until verified for the specific LMS.
        """
        raise NotImplementedError("Assignment submission API is not yet implemented or verified for this connector.")
