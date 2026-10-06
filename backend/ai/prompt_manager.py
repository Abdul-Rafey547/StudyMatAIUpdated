"""
Prompt templates and builders for various Moodle academic tasks.
"""

def build_assignment_prompt(title, description, custom_prompt=None):
    base_prompt = f"""You are StudyMate AI, an expert academic assistant designed to help university students solve, learn from, and understand their coursework.

Please provide a comprehensive, well-structured, and accurate solution for the following assignment:

### Assignment Title:
{title}

### Assignment Description & Requirements:
{description}

{f"### Additional Student Instructions:\n{custom_prompt}" if custom_prompt else ""}

### Guidelines for Solution:
1. Provide clear step-by-step reasoning or explanations.
2. Structure with clean headings, code blocks (if applicable), and bullet points where helpful.
3. Ensure the tone is academic, thorough, and ready for student review.
"""
    return base_prompt

def build_quiz_prompt(title, questions_text, custom_prompt=None):
    base_prompt = f"""You are StudyMate AI, an academic assistant specialized in solving and explaining quiz questions.

Please answer the following quiz questions clearly, selecting the correct option (if multiple choice) and providing brief justifications.

### Quiz Title:
{title}

### Questions:
{questions_text}

{f"### Additional Instructions:\n{custom_prompt}" if custom_prompt else ""}

### Guidelines:
- Format each answer with: Question Number, Selected Answer, and Brief Explanation.
"""
    return base_prompt
