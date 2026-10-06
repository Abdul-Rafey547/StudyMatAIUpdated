"""
Core generation logic, supporting OpenAI, Anthropic, or an intelligent fallback system if no API key is present.
"""
import os
import json
import urllib.request
import urllib.error

def call_openai_api(api_key, model_name, prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_name or "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are StudyMate AI, an academic assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"OpenAI API error: {e.code} - {error_body}")
    except Exception as e:
        raise Exception(f"Failed to connect to OpenAI API: {str(e)}")

def generate_local_fallback(task_dict):
    """
    Fallback answer generator when no API key is provided, producing structured templates
    so the system remains fully testable offline during demonstrations.
    """
    title = task_dict.get('title', 'Assignment')
    description = task_dict.get('description', '')
    task_type = task_dict.get('type', 'ASSIGNMENT')

    if task_type == 'QUIZ':
        return f"""### StudyMate AI - Generated Quiz Solutions
**Quiz:** {title}

**Question 1:**
- **Answer:** Option B
- **Explanation:** Based on the standard definitions and course material, this is the most accurate solution.

**Question 2:**
- **Answer:** Option A
- **Explanation:** Derived by applying the fundamental principles described in the problem statement.

*(Note: Provide an AI_API_KEY in `.env` to enable full live LLM generation)*"""

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
# Sample solution blueprint generated for demonstration
def solve_coursework():
    print("Executing standard algorithm for {title}...")
    return True
```

#### 4. Conclusion & Summary
This drafted response addresses the fundamental rubric criteria. Please review and refine the solution before final submission.

*(Note: Configure your AI_API_KEY in the backend `.env` to activate full live LLM model generation)*"""
