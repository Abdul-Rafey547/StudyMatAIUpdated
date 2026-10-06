"""
StudyMate AI - Helper Utilities
Common utility functions used across the backend.
"""
import re
import html
from datetime import datetime

def sanitize_html(raw_html):
    """Remove HTML tags and decode entities from raw HTML content."""
    if not raw_html:
        return ''
    clean = re.sub(r'<[^>]+>', '', raw_html)
    clean = html.unescape(clean)
    return clean.strip()

def truncate_text(text, max_length=500):
    """Truncate text to a maximum length with ellipsis."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + '...'

def format_timestamp(dt=None):
    """Return an ISO 8601 formatted timestamp string."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def validate_task_status(status):
    """Validate that a task status is one of the allowed values."""
    valid_statuses = [
        'DISCOVERED', 'PENDING', 'PROCESSING', 'GENERATED',
        'REVIEW', 'APPROVED', 'SUBMITTED', 'COMPLETED', 'FAILED'
    ]
    return status.upper() in valid_statuses if status else False

def safe_int(value, default=None):
    """Safely convert a value to integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
