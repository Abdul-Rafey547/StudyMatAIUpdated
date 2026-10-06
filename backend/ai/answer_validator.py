"""
Answer validation and completeness checking.
"""

def validate_answer(answer_text, task_dict):
    """
    Validates if the generated answer meets basic criteria.
    """
    if not answer_text or len(answer_text.strip()) < 20:
        return {
            "valid": False,
            "score": 0,
            "message": "Answer is too short or empty."
        }

    # Simple heuristic checks
    has_code = "```" in answer_text
    word_count = len(answer_text.split())

    return {
        "valid": True,
        "word_count": word_count,
        "has_code_blocks": has_code,
        "message": "Answer passed completeness checks."
    }
