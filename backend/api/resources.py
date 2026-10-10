"""
StudyMate AI - Resources & Study Materials API Blueprint
Handles discovery, processing, text extraction (PDF, DOCX, TXT), and AI study tools for Moodle learning materials.
"""
import io
import re
import base64
from flask import Blueprint, request, jsonify
from database.database import get_db_connection
from ai.ai_service import generate_study_material
from ai.providers import get_provider
from config import Config
from utils.logger import get_logger

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

logger = get_logger('studymate.api.resources')
resources_bp = Blueprint('resources', __name__)

@resources_bp.route('/sync', methods=['POST'])
def sync_resources():
    """
    Sync learning resources discovered on Moodle pages (PDFs, DOCX, Books, Pages, URLs).
    """
    conn = None
    try:
        data = request.json or {}
        raw_resources = data.get('resources') or data.get('resource')
        if not raw_resources:
            return jsonify({"error": "No resource data provided"}), 400

        if isinstance(raw_resources, dict):
            resource_list = [raw_resources]
        else:
            resource_list = raw_resources

        conn = get_db_connection()
        c = conn.cursor()
        synced_count = 0

        for r_data in resource_list:
            title = (r_data.get('title') or 'Untitled Resource').strip()
            course_name = (r_data.get('course') or r_data.get('courseName') or 'General').strip()
            resource_type = (r_data.get('type') or r_data.get('resource_type') or 'PDF').upper()
            moodle_url = (r_data.get('url') or r_data.get('moodle_url') or '').strip()
            direct_url = (r_data.get('direct_url') or r_data.get('directUrl') or '').strip()
            moodle_resource_id = str(r_data.get('id') or r_data.get('moodle_id') or r_data.get('resource_id') or '')
            file_name = r_data.get('file_name') or r_data.get('fileName') or ''
            file_size = r_data.get('file_size') or r_data.get('fileSize') or ''
            mime_type = r_data.get('mime_type') or ''
            description = r_data.get('description') or ''
            availability = r_data.get('availability_status') or 'AVAILABLE'
            extracted_text = r_data.get('extracted_text') or ''

            if not moodle_url and not title:
                continue

            # 1. Course deduplication
            c.execute("SELECT course_id FROM courses WHERE course_name = ?", (course_name,))
            course_row = c.fetchone()
            if course_row:
                course_id = course_row['course_id']
                c.execute("UPDATE courses SET scanned_at = CURRENT_TIMESTAMP WHERE course_id = ?", (course_id,))
            else:
                c.execute("INSERT INTO courses (course_name, scanned_at) VALUES (?, CURRENT_TIMESTAMP)", (course_name,))
                course_id = c.lastrowid

            # 2. Resource deduplication by moodle_url or (moodle_resource_id and course_id)
            existing = None
            if moodle_url:
                c.execute("SELECT resource_id, extracted_text FROM resources WHERE moodle_url = ?", (moodle_url,))
                existing = c.fetchone()

            if not existing and moodle_resource_id:
                c.execute("SELECT resource_id, extracted_text FROM resources WHERE moodle_resource_id = ? AND course_id = ?", (moodle_resource_id, course_id))
                existing = c.fetchone()

            if existing:
                res_id = existing['resource_id']
                saved_text = extracted_text or existing['extracted_text'] or ''
                c.execute("""
                    UPDATE resources
                    SET title = ?, resource_type = ?, file_name = ?, file_size = ?,
                        description = ?, direct_url = ?, availability_status = ?,
                        extracted_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE resource_id = ?
                """, (title, resource_type, file_name, file_size, description,
                      direct_url, availability, saved_text, res_id))
            else:
                c.execute("""
                    INSERT INTO resources (
                        course_id, moodle_resource_id, title, resource_type,
                        file_name, mime_type, file_size, description,
                        moodle_url, direct_url, availability_status, extracted_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (course_id, moodle_resource_id, title, resource_type,
                      file_name, mime_type, file_size, description,
                      moodle_url, direct_url, availability, extracted_text))
                res_id = c.lastrowid

            synced_count += 1

        conn.commit()
        logger.info(f"Successfully synced {synced_count} study materials.")
        return jsonify({"success": True, "synced_count": synced_count, "message": f"Synced {synced_count} resources"})

    except Exception as e:
        logger.error(f"Error syncing resources: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@resources_bp.route('', methods=['GET'])
def get_resources():
    """
    List all discovered study materials, with optional course filtering.
    """
    conn = None
    try:
        course_id = request.args.get('course_id')
        conn = get_db_connection()
        c = conn.cursor()

        if course_id:
            c.execute("""
                SELECT r.*, c.course_name
                FROM resources r
                LEFT JOIN courses c ON r.course_id = c.course_id
                WHERE r.course_id = ?
                ORDER BY r.created_at DESC
            """, (course_id,))
        else:
            c.execute("""
                SELECT r.*, c.course_name
                FROM resources r
                LEFT JOIN courses c ON r.course_id = c.course_id
                ORDER BY r.created_at DESC
            """)

        rows = c.fetchall()
        resources = []
        for row in rows:
            r_dict = dict(row)
            r_dict['has_extracted_text'] = bool(r_dict.get('extracted_text') and r_dict.get('extracted_text').strip())
            if r_dict.get('extracted_text'):
                r_dict['extracted_text_preview'] = r_dict['extracted_text'][:200]
                del r_dict['extracted_text']
            resources.append(r_dict)

        c.execute("SELECT course_id, course_name, scanned_at FROM courses ORDER BY course_name ASC")
        courses = [dict(row) for row in c.fetchall()]

        return jsonify({
            "success": True,
            "resources": resources,
            "courses": courses,
            "total": len(resources)
        })

    except Exception as e:
        logger.error(f"Error fetching resources: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@resources_bp.route('/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    """
    Get full resource details and extracted text preview.
    """
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT r.*, c.course_name
            FROM resources r
            LEFT JOIN courses c ON r.course_id = c.course_id
            WHERE r.resource_id = ?
        """, (resource_id,))
        row = c.fetchone()

        if not row:
            return jsonify({"error": "Resource not found"}), 404

        r_dict = dict(row)
        r_dict['has_extracted_text'] = bool(r_dict.get('extracted_text') and r_dict.get('extracted_text').strip())
        return jsonify({"success": True, "resource": r_dict})

    except Exception as e:
        logger.error(f"Error fetching resource #{resource_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@resources_bp.route('/process', methods=['POST'])
def process_document():
    """
    Extract text from uploaded binary / base64 content or document payload.
    Supports PDF (via pypdf), DOCX (via python-docx), and UTF-8 text.
    Handles scanned/image-only PDFs without fabricating text.
    """
    conn = None
    try:
        data = request.json or {}
        resource_id = data.get('resource_id')
        file_base64 = data.get('file_base64')
        raw_text = data.get('raw_text')
        file_type = (data.get('file_type') or 'PDF').upper()
        file_name = data.get('file_name', 'document')

        extracted_text = ""
        is_scanned = False
        ocr_required = False
        page_count = 0

        if raw_text is not None:
            if not raw_text.strip():
                is_scanned = True
                ocr_required = True
                extracted_text = ""
            else:
                extracted_text = raw_text.strip()
        elif file_base64:
            file_bytes = base64.b64decode(file_base64)
            byte_stream = io.BytesIO(file_bytes)

            if file_type == 'PDF' or file_name.lower().endswith('.pdf'):
                if not pypdf:
                    return jsonify({"error": "pypdf library not available on backend"}), 500
                reader = pypdf.PdfReader(byte_stream)
                page_count = len(reader.pages)
                pages_text = []

                for idx, page in enumerate(reader.pages):
                    p_txt = page.extract_text() or ''
                    if p_txt.strip():
                        pages_text.append(f"[Page {idx + 1}]\n{p_txt.strip()}")

                if pages_text:
                    extracted_text = "\n\n".join(pages_text)
                else:
                    is_scanned = True
                    ocr_required = True
                    extracted_text = ""

            elif file_type in ('DOCX', 'DOC') or file_name.lower().endswith('.docx'):
                if not docx:
                    return jsonify({"error": "python-docx library not available on backend"}), 500
                doc = docx.Document(byte_stream)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            paras.append(row_text)
                extracted_text = "\n\n".join(paras)

            elif file_type == 'TXT' or file_name.lower().endswith('.txt'):
                try:
                    extracted_text = file_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    extracted_text = file_bytes.decode('latin-1', errors='ignore')

        if ocr_required or (page_count > 0 and len(extracted_text.strip()) < 30):
            is_scanned = True
            ocr_required = True
            msg = "This document appears to be a scanned image-only PDF with no extractable text. Text extraction requires OCR."
        else:
            msg = f"Successfully extracted text ({len(extracted_text.split())} words, {page_count or 1} pages/sections)."

        if resource_id:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE resources
                SET extracted_text = ?, is_scanned_image = ?, updated_at = CURRENT_TIMESTAMP
                WHERE resource_id = ?
            """, (extracted_text, 1 if is_scanned else 0, resource_id))
            conn.commit()

        return jsonify({
            "success": not ocr_required,
            "ocr_required": ocr_required,
            "is_scanned_image": is_scanned,
            "word_count": len(extracted_text.split()) if extracted_text else 0,
            "page_count": page_count,
            "message": msg,
            "extracted_text": extracted_text
        })

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


def _chunk_text(text, max_words=1200, overlap=150):
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += max_words - overlap
    return chunks


def _select_relevant_chunks(chunks, query, max_chunks=3):
    if len(chunks) <= max_chunks:
        return chunks

    query_terms = set(re.findall(r'\w+', query.lower()))
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for term in query_terms if term in chunk_lower)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:max_chunks]]


@resources_bp.route('/study', methods=['POST'])
def study_resource():
    """
    Perform AI study actions on a learning material (PDF, book, notes, page):
    Actions: 'summarize', 'explain', 'notes', 'mcqs', 'practice', 'guide'
    """
    conn = None
    try:
        data = request.json or {}
        resource_id = data.get('resource_id')
        action = (data.get('action') or 'summarize').lower()
        topic = data.get('topic') or ''
        input_text = data.get('text') or ''
        provider_name = data.get('provider')
        model_name = data.get('model')
        api_key = data.get('api_key')

        valid_actions = ['summarize', 'explain', 'notes', 'mcqs', 'practice', 'guide']
        if action not in valid_actions:
            return jsonify({"error": f"Invalid action. Choose from: {', '.join(valid_actions)}"}), 400

        doc_title = "Study Material"
        course_id = None

        if resource_id:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM resources WHERE resource_id = ?", (resource_id,))
            res_row = c.fetchone()

            if not res_row:
                return jsonify({"error": "Resource not found"}), 404

            doc_title = res_row['title']
            course_id = res_row['course_id']
            if not input_text:
                input_text = res_row['extracted_text'] or ''
                if res_row['is_scanned_image'] or (not input_text and res_row['resource_type'] == 'PDF'):
                    return jsonify({
                        "error": "This document has no extracted text (scanned image-only PDF). Text extraction requires OCR.",
                        "ocr_required": True
                    }), 400

        if not input_text or not input_text.strip():
            return jsonify({
                "error": "No readable document text available. Please open or fetch the resource text first."
            }), 400

        chunks = _chunk_text(input_text, max_words=1200)
        query = f"{action} {topic} {doc_title}"
        relevant_chunks = _select_relevant_chunks(chunks, query, max_chunks=3)
        context_text = "\n\n--- SECTION BREAK ---\n\n".join(relevant_chunks)

        action_prompts = {
            'summarize': f"Summarize the key concepts, core themes, and essential takeaways of the document '{doc_title}'. Include major section headings and bullet points.",
            'explain': f"Explain the topic '{topic or doc_title}' clearly step-by-step using the context from '{doc_title}'. Give clear examples and cite section/page references where mentioned.",
            'notes': f"Create structured, high-yield revision study notes from '{doc_title}'. Use hierarchical bullet points, key terms, definitions, and formulas where applicable.",
            'mcqs': f"Generate 5 Multiple Choice Practice Questions (MCQs) with 4 options each (A, B, C, D), the correct answer, and an explanatory rationale based on '{doc_title}'.",
            'practice': f"Generate 4 short-answer conceptual practice questions with detailed model answers and grading rubrics based on '{doc_title}'.",
            'guide': f"Create a comprehensive exam revision guide for '{doc_title}' covering key definitions, major formulas/algorithms, common exam pitfalls, and summary bullet points."
        }

        task_prompt = action_prompts.get(action, action_prompts['summarize'])
        if topic and action != 'explain':
            task_prompt += f"\n\nSpecial Focus Area: {topic}"

        full_prompt = (
            f"StudyMate AI acting as an academic tutor.\n\n"
            f"Document Title: {doc_title}\n"
            f"Action: {action.upper()}\n\n"
            f"--- RELEVANT DOCUMENT EXCERPTS ---\n"
            f"{context_text}\n"
            f"--- END EXCERPTS ---\n\n"
            f"Task: {task_prompt}\n\n"
            f"Please structure your response cleanly with clear headings, bullet points, and page/section references where available in the excerpt."
        )

        system_prompt = (
            "You are StudyMate AI, an expert academic tutor. You provide clear, rigorous, "
            "accurate study materials, summaries, explanations, and practice questions strictly based "
            "on university course materials."
        )

        selected_provider = (provider_name or Config.AI_PROVIDER or "google").strip().lower()

        if selected_provider == "fallback":
            material = generate_study_material(action, topic or doc_title, provider_name="fallback")
        else:
            try:
                provider = get_provider(selected_provider, api_key=api_key, model_name=model_name)
                if provider.is_configured():
                    logger.info(f"[StudyMate AI] Generating resource {action} via {provider.display_name} for '{doc_title}'...")
                    material = provider.generate_response(full_prompt, system_prompt=system_prompt)
                else:
                    logger.warning(f"Provider {selected_provider} not configured; using local study fallback.")
                    material = generate_study_material(action, topic or doc_title, provider_name="fallback")
            except Exception as e:
                logger.error(f"Error in study action: {e}")
                material = generate_study_material(action, topic or doc_title, provider_name="fallback")

        if not conn:
            conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO study_sessions (resource_id, course_id, topic)
            VALUES (?, ?, ?)
        """, (resource_id, course_id, f"{doc_title}: {action.upper()} - {topic or 'Full Document'}"))
        session_id = c.lastrowid

        c.execute("""
            INSERT INTO notes (session_id, content, type)
            VALUES (?, ?, ?)
        """, (session_id, material, action.upper()))
        conn.commit()

        return jsonify({
            "success": True,
            "action": action,
            "topic": topic or doc_title,
            "doc_title": doc_title,
            "resource_id": resource_id,
            "provider": selected_provider,
            "material": material
        })

    except Exception as e:
        logger.error(f"Error studying resource: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@resources_bp.route('/fetch-content/<int:resource_id>', methods=['POST'])
def fetch_resource_content(resource_id):
    """
    Download and extract text from Moodle learning material using backend authenticated client.
    """
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM resources WHERE resource_id = ?", (resource_id,))
        res = c.fetchone()
        if not res:
            return jsonify({"error": "Resource not found"}), 404

        target_url = res['direct_url'] or res['moodle_url']
        if not target_url:
            return jsonify({"error": "Resource has no accessible file URL"}), 400

        from moodle.moodle_client import MoodleClient
        client = MoodleClient()
        content_bytes = client.get_resource_content(target_url)

        if not content_bytes:
            return jsonify({"error": "Failed to download resource content from Moodle. Check authentication or file permissions."}), 502

        r_type = (res['resource_type'] or 'PDF').upper()
        extracted_text = ""
        is_scanned = 0

        stream = io.BytesIO(content_bytes)
        if r_type == 'PDF' and pypdf:
            reader = pypdf.PdfReader(stream)
            pages = []
            for idx, p in enumerate(reader.pages):
                t = p.extract_text() or ''
                if t.strip():
                    pages.append(f"[Page {idx + 1}]\n{t.strip()}")
            if pages:
                extracted_text = "\n\n".join(pages)
            else:
                is_scanned = 1
        elif r_type in ('DOCX', 'DOC') and docx:
            doc = docx.Document(stream)
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            extracted_text = "\n\n".join(paras)
        elif r_type == 'TXT':
            try:
                extracted_text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                extracted_text = content_bytes.decode('latin-1', errors='ignore')

        c.execute("""
            UPDATE resources
            SET extracted_text = ?, is_scanned_image = ?, updated_at = CURRENT_TIMESTAMP
            WHERE resource_id = ?
        """, (extracted_text, is_scanned, resource_id))
        conn.commit()

        return jsonify({
            "success": True,
            "resource_id": resource_id,
            "extracted_text": extracted_text,
            "word_count": len(extracted_text.split()) if extracted_text else 0,
            "is_scanned_image": bool(is_scanned)
        })

    except Exception as e:
        logger.error(f"Error fetching content for resource #{resource_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

