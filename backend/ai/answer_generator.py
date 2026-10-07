"""
StudyMate AI - Answer Generator & Live Provider Dispatcher
Supports Google Gemini, Anthropic Claude, Groq, OpenAI, DeepSeek, Ollama, and offline intelligent fallback.
"""
import os
import json
from typing import Optional, Dict, Any
from ai.providers import (
    GeminiProvider,
    ClaudeProvider,
    GroqProvider,
    OpenAIProvider,
    DeepSeekProvider,
    OllamaProvider,
    get_provider
)

def call_gemini_api(api_key: str, model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call Google Gemini API."""
    provider = GeminiProvider(api_key=api_key, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def call_claude_api(api_key: str, model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call Anthropic Claude API."""
    provider = ClaudeProvider(api_key=api_key, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def call_groq_api(api_key: str, model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call Groq Cloud API."""
    provider = GroqProvider(api_key=api_key, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def call_openai_api(api_key: str, model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call OpenAI API."""
    provider = OpenAIProvider(api_key=api_key, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def call_deepseek_api(api_key: str, model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call DeepSeek API."""
    provider = DeepSeekProvider(api_key=api_key, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def call_ollama_api(base_url: Optional[str], model_name: Optional[str], prompt: str, system_prompt: Optional[str] = None) -> str:
    """Direct helper to call Ollama local API."""
    provider = OllamaProvider(base_url=base_url, model_name=model_name)
    return provider.generate_response(prompt, system_prompt=system_prompt)

def generate_local_fallback(task_dict: Dict[str, Any], action: Optional[str] = None, topic: Optional[str] = None) -> str:
    """
    Fallback answer generator when no API key is provided or offline mode is chosen, producing structured templates
    so the system remains fully testable offline during demonstrations and local testing.
    """
    if action and topic:
        return (
            f"### {action.capitalize()}: {topic.capitalize()}\n\n"
            f"#### Overview & Core Concepts\n"
            f"- **Subject Area**: {topic}\n"
            f"- **Summary**: An academic synthesis detailing fundamental principles, practical applications, and key mechanisms related to {topic}.\n\n"
            f"#### Detailed Breakdown\n"
            f"1. **Core Concept Definition**: Fundamental theoretical framework and mathematical/algorithmic context.\n"
            f"2. **Practical Application**: Real-world scenarios, case studies, and code/computational implementations.\n"
            f"3. **Key Takeaways & Review**: Critical points for exams, assignments, and practical coursework.\n\n"
            f"*(Generated via StudyMate AI Local Engine. Configure your AI API key in Settings or `.env` for real-time model completions)*"
        )

    title = task_dict.get('title', 'Assignment')
    description = task_dict.get('description', '')
    task_type = task_dict.get('type', 'ASSIGNMENT')

    if task_type == 'QUIZ':
        return f"""### StudyMate AI - Generated Quiz Solutions
**Quiz:** {title}

**Question 1:**
- **Answer:** Option B
- **Explanation:** Based on standard academic definitions and course material, this is the most accurate solution.

**Question 2:**
- **Answer:** Option A
- **Explanation:** Derived by applying the fundamental principles described in the problem statement.

*(Note: Provide a Google, Claude, Groq, or OpenAI API key in Settings or `.env` to enable full live LLM generation)*"""

    return f"""### StudyMate AI - Solution Draft
**Task:** {title}

#### 1. Problem Overview & Analysis
The assignment requires addressing:
> {description[:200] + '...' if len(description) > 200 else description}

#### 2. Key Objectives & Methodology
- Step 1: Theoretical foundation and requirements mapping.
- Step 2: Implementation / Core argumentation.
- Step 3: Result validation and synthesis.

#### 3. Proposed Solution
```python
# Solution blueprint generated for {title}
def solve_coursework():
    \"\"\"Academic implementation for {title}\"\"\"
    print("Executing coursework solution algorithm...")
    return True
```

#### 4. Conclusion & Summary
This drafted response addresses the fundamental rubric criteria. Please review and refine the solution in the Solution Editor before final submission.

*(Note: Configure your Google Gemini, Claude, Groq, or OpenAI API key in `.env` or Settings to activate full live LLM generation)*"""
