from google import genai
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import MODEL_NAME
from tools import read_file, search_codebase

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def parse_traceback(error_text: str):
    locations = []

    for line in error_text.splitlines():
        line = line.strip()

        if line.startswith('File "') and '", line ' in line:
            parts = line.split('"')
            file_path = parts[1]

            line_part = line.split(", line ")[1]
            line_number = int(line_part.split(",")[0])

            locations.append({
                "file": file_path,
                "line": line_number
            })

    return locations


def find_bug(error_text: str):
    locations = parse_traceback(error_text)

    relevant_code = ""

    for loc in locations:
        file_path = loc["file"]
        line_number = loc["line"]

        start_line = max(1, line_number - 10)
        end_line = line_number + 10

        code = read_file(file_path, start_line, end_line)

        relevant_code += f"\nFile: {file_path}\n"
        relevant_code += f"Lines: {start_line} to {end_line}\n"
        relevant_code += "Code:\n"
        relevant_code += code
        relevant_code += "\n" + "-" * 50 + "\n"

    error_message = error_text.strip().splitlines()[-1]
    search_results = search_codebase(error_message)

    prompt = f"""
You are a senior Python debugging assistant.

Here is a Python error:

{error_text}

Here is the relevant code around the traceback lines:

{relevant_code}

Here is related code from the codebase search:

{search_results}

Explain exactly:
1. What failed
2. Which file and line caused it
3. Why the error happened
4. How to fix it
5. Give the corrected code
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


if __name__ == "__main__":
    error = r"""
Traceback (most recent call last):
  File "C:\Users\anany\Desktop\codebase-agent\features\test_bug_file2.py", line 4, in <module>
    greet()
  File "C:\Users\anany\Desktop\codebase-agent\features\test_bug_file2.py", line 2, in greet
    print(messag)
          ^^^^^^
NameError: name 'messag' is not defined
"""

    print(find_bug(error))