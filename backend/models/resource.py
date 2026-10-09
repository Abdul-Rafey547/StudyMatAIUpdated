"""
StudyMate AI - Resource Model
Represents learning materials (PDFs, DOCX, PPTX, TXT, Pages, Books, URLs) detected from Moodle.
"""

RESOURCE_TYPES = ['PDF', 'DOCX', 'PPTX', 'TXT', 'PAGE', 'BOOK', 'URL', 'FILE', 'OTHER']

class Resource:
    def __init__(self, resource_id=None, course_id=None, moodle_resource_id=None,
                 title='', resource_type='PDF', file_name='', mime_type='',
                 file_size='', description='', moodle_url='', direct_url='',
                 availability_status='AVAILABLE', extracted_text='', is_scanned_image=False,
                 course_name='', created_at=None, updated_at=None):
        self.resource_id = resource_id
        self.course_id = course_id
        self.moodle_resource_id = moodle_resource_id
        self.title = title
        self.resource_type = resource_type.upper() if resource_type else 'FILE'
        self.file_name = file_name
        self.mime_type = mime_type
        self.file_size = file_size
        self.description = description
        self.moodle_url = moodle_url
        self.direct_url = direct_url
        self.availability_status = availability_status
        self.extracted_text = extracted_text
        self.is_scanned_image = bool(is_scanned_image)
        self.course_name = course_name
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            'resource_id': self.resource_id,
            'id': self.resource_id,
            'course_id': self.course_id,
            'course_name': self.course_name,
            'courseName': self.course_name,
            'moodle_resource_id': self.moodle_resource_id,
            'title': self.title,
            'resource_type': self.resource_type,
            'resourceType': self.resource_type,
            'file_name': self.file_name,
            'fileName': self.file_name,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'fileSize': self.file_size,
            'description': self.description,
            'moodle_url': self.moodle_url,
            'url': self.moodle_url,
            'direct_url': self.direct_url,
            'availability_status': self.availability_status,
            'extracted_text_preview': self.extracted_text[:200] if self.extracted_text else '',
            'has_extracted_text': bool(self.extracted_text and self.extracted_text.strip()),
            'is_scanned_image': self.is_scanned_image,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Resource(
            resource_id=data.get('resource_id') or data.get('id'),
            course_id=data.get('course_id'),
            course_name=data.get('course_name') or data.get('courseName') or data.get('course', ''),
            moodle_resource_id=data.get('moodle_resource_id') or data.get('moodle_id'),
            title=data.get('title', ''),
            resource_type=data.get('resource_type') or data.get('resourceType') or 'FILE',
            file_name=data.get('file_name') or data.get('fileName', ''),
            mime_type=data.get('mime_type', ''),
            file_size=data.get('file_size') or data.get('fileSize', ''),
            description=data.get('description', ''),
            moodle_url=data.get('moodle_url') or data.get('url', ''),
            direct_url=data.get('direct_url') or data.get('directUrl', ''),
            availability_status=data.get('availability_status', 'AVAILABLE'),
            extracted_text=data.get('extracted_text', ''),
            is_scanned_image=data.get('is_scanned_image', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
