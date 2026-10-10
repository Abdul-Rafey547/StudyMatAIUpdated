"""
Unit tests for Bug 2: Learning Materials & Resource Scanner.
Tests discovery, metadata extraction, PDF/DOCX text processing, OCR warning on image PDFs, and AI study tools.
"""
import unittest
import json
import base64
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from database.database import init_db
import docx

class ResourceScannerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    def tearDown(self):
        from database.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM resources WHERE course_id IN (SELECT course_id FROM courses WHERE course_name = 'AI 101')")
        c.execute("DELETE FROM courses WHERE course_name = 'AI 101'")
        conn.commit()
        conn.close()

    def test_resource_sync_and_list(self):
        """Course resources (PDF book, lecture slides, DOCX) sync and display properly."""
        payload = {
            "resources": [
                {
                    "title": "Introduction to Artificial Intelligence.pdf",
                    "course": "AI 101",
                    "type": "PDF",
                    "url": "http://moodle.local/mod/resource/view.php?id=301",
                    "file_size": "4.2 MB",
                    "description": "Comprehensive textbook on AI search algorithms and logic."
                },
                {
                    "title": "Machine Learning Lecture Notes.docx",
                    "course": "AI 101",
                    "type": "DOCX",
                    "url": "http://moodle.local/mod/resource/view.php?id=302",
                    "file_size": "1.1 MB"
                }
            ]
        }
        res_sync = self.app.post('/api/resources/sync', data=json.dumps(payload), content_type='application/json')
        sync_data = json.loads(res_sync.data)
        self.assertEqual(res_sync.status_code, 200)
        self.assertTrue(sync_data['success'])
        self.assertEqual(sync_data['synced_count'], 2)

        # Fetch resources list
        res_get = self.app.get('/api/resources')
        get_data = json.loads(res_get.data)
        self.assertEqual(res_get.status_code, 200)
        self.assertTrue(get_data['success'])
        self.assertTrue(any(r['title'] == "Introduction to Artificial Intelligence.pdf" for r in get_data['resources']))
        self.assertTrue(any(r['resource_type'] == "DOCX" for r in get_data['resources']))

    def test_docx_document_text_extraction(self):
        """Extract text from real DOCX binary stream."""
        doc = docx.Document()
        doc.add_heading("Chapter 1: Graph Search Algorithms", level=1)
        doc.add_paragraph("A* search algorithm evaluates nodes by combining g(n), the cost to reach the node, and h(n), the estimated cost.")
        doc.add_paragraph("Dijkstra algorithm is a special case of A* where h(n) = 0.")
        buf = io.BytesIO()
        doc.save(buf)
        docx_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        res_proc = self.app.post('/api/resources/process', data=json.dumps({
            "file_base64": docx_b64,
            "file_type": "DOCX",
            "file_name": "Graph_Search.docx"
        }), content_type='application/json')
        data = json.loads(res_proc.data)
        self.assertEqual(res_proc.status_code, 200)
        self.assertTrue(data['success'])
        self.assertFalse(data['ocr_required'])
        self.assertIn("A* search algorithm", data['extracted_text'])
        self.assertIn("Dijkstra", data['extracted_text'])

    def test_scanned_image_only_pdf_handling(self):
        """Scanned image-only PDF does not fabricate summaries and informs OCR is required."""
        # Empty text representation for scanned image PDF
        res_proc = self.app.post('/api/resources/process', data=json.dumps({
            "raw_text": "",
            "file_type": "PDF",
            "file_name": "Scanned_Book.pdf"
        }), content_type='application/json')
        data = json.loads(res_proc.data)
        self.assertEqual(res_proc.status_code, 200)
        self.assertTrue(data['ocr_required'])
        self.assertIn("OCR", data['message'])

    def test_ai_study_actions_on_resource(self):
        """AI study tools (summarize, explain, notes, mcqs, practice, guide) operate on extracted document content."""
        sample_doc = (
            "Relational Database Normalization: Normalization is the process of structuring a relational database "
            "in accordance with normal forms in order to reduce data redundancy and improve data integrity.\n\n"
            "First Normal Form (1NF): Each column must contain atomic values and each record must be unique.\n\n"
            "Second Normal Form (2NF): Must be in 1NF and all non-key attributes must be fully functionally dependent on the primary key.\n\n"
            "Third Normal Form (3NF): Must be in 2NF and no non-key attribute is transitively dependent on the primary key."
        )

        for action in ['summarize', 'notes', 'mcqs', 'practice', 'guide']:
            res = self.app.post('/api/resources/study', data=json.dumps({
                "action": action,
                "text": sample_doc,
                "provider": "fallback"
            }), content_type='application/json')
            data = json.loads(res.data)
            self.assertEqual(res.status_code, 200)
            self.assertTrue(data['success'])
            self.assertEqual(data['action'], action)
            self.assertTrue(len(data['material']) > 0)

    def test_resource_deduplication(self):
        """Repeated scans of course page do not duplicate resource cards."""
        res_payload = {
            "resources": [
                {
                    "title": "Computer Networks Syllabus.pdf",
                    "course": "CS 401",
                    "type": "PDF",
                    "url": "http://moodle.local/mod/resource/view.php?id=555"
                }
            ]
        }
        # First sync
        self.app.post('/api/resources/sync', data=json.dumps(res_payload), content_type='application/json')
        # Second sync
        self.app.post('/api/resources/sync', data=json.dumps(res_payload), content_type='application/json')

        res_get = self.app.get('/api/resources')
        resources = json.loads(res_get.data)['resources']
        matches = [r for r in resources if r['moodle_url'] == "http://moodle.local/mod/resource/view.php?id=555"]
        self.assertEqual(len(matches), 1)

if __name__ == '__main__':
    unittest.main()
