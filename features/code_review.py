from google import genai
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import MODEL_NAME
from tools import read_file

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def review_file(file_path: str):
    code = read_file(file_path, 1, 100000)

    prompt = f"""
You are a senior software engineer doing a careful code review.

Review this file and return your findings in exactly this format:

ISSUES:
- List bugs, errors, risky logic, confusing behavior, or fragile assumptions.
- Include line numbers whenever possible.

SECURITY:
- List hardcoded secrets, unsafe subprocess use, unsafe file handling, missing validation, path traversal risks, or exposed sensitive data.
- If there are no security issues, write: None found.

SUGGESTIONS:
- List improvements for readability, maintainability, structure, performance, typing, error handling, and documentation.
- Include line numbers whenever possible.

GOOD PARTS:
- List what is implemented well.

Rules:
- Be specific.
- Be practical.
- Do not invent issues that are not supported by the code.
- Mention exact line numbers wherever possible.

File path:
{file_path}

Code:
{code}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


if __name__ == "__main__":
    file_path = "flask-main/flask-main/src/flask/app.py"
    print(review_file(file_path))