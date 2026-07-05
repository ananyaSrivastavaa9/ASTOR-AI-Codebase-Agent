import os
import re
import sys
import concurrent.futures
from pathlib import Path


from dotenv import load_dotenv
from google import genai

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import MODEL_NAME
from tools import read_file, search_codebase

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Directories that should never be walked — they're huge, irrelevant to
# onboarding, and were the main cause of explain_repo() hanging.
IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    ".idea", ".mypy_cache", "dist", "build", ".pytest_cache",
}

# Hard caps so a large repo can't blow up the prompt / walk time.
MAX_FOLDERS = 150
MAX_FILES = 2000

GENERATE_TIMEOUT_SECONDS = 30
GENERATE_MAX_RETRIES = 2


def _generate_with_timeout(prompt: str):
    """Call the model with a hard timeout and a couple of retries so a
    slow/stuck network call can't hang the agent forever."""
    last_exc = None

    for attempt in range(1, GENERATE_MAX_RETRIES + 1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model=MODEL_NAME,
                contents=prompt,
            )
            try:
                return future.result(timeout=GENERATE_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError as exc:
                last_exc = exc
            except Exception as exc:
                last_exc = exc

    raise RuntimeError(
        f"explain_repo: generate_content failed after {GENERATE_MAX_RETRIES} attempts"
    ) from last_exc

_FILE_LINE_PATTERN = re.compile(r"File:\s*([^\n]+)")


def _repo_name_from_path(repo_path):
    return os.path.basename(os.path.normpath(repo_path)) or repo_path


def _extract_file_paths(*texts):
    files = []
    seen = set()
    for text in texts:
        if not text:
            continue
        for file_path in _FILE_LINE_PATTERN.findall(text):
            file_path = file_path.strip()
            if file_path and file_path not in seen:
                seen.add(file_path)
                files.append(file_path)
    return files

def explain_repo(repo_path: str):
    print("DEBUG: starting os.walk")

    folder_names = []
    file_names = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)

        for folder in dirs:
            folder_names.append(os.path.join(root, folder))

        for file in sorted(files):
            file_names.append(os.path.join(root, file))

        if len(folder_names) >= MAX_FOLDERS and len(file_names) >= MAX_FILES:
            break

    print(f"DEBUG: finished os.walk, folders={len(folder_names)} files={len(file_names)}")

    readme_text = ""

    for file_path in file_names:
        if os.path.basename(file_path).lower().startswith("readme"):
            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:
                    readme_text = f.read()
            except Exception:
                pass
            break

    print("DEBUG: finished readme read")

    entry_point = None

    possible_entries = [
        "app.py",
        "main.py",
        "index.py",
        "__init__.py",
    ]

    for entry in possible_entries:
        for file_path in file_names:
            if os.path.basename(file_path) == entry:
                entry_point = file_path
                break
        if entry_point:
            break

    print(f"DEBUG: entry_point resolved = {entry_point}")

    entry_code = ""

    if entry_point:
        entry_code = read_file(entry_point, 1, 30)

    print("DEBUG: finished read_file(entry_point)")

    print("DEBUG: starting search_codebase(main function)")
    main_function = search_codebase("main function")
    print("DEBUG: finished search_codebase(main function)")

    print("DEBUG: starting search_codebase(app initialization)")
    app_initialization = search_codebase("app initialization")
    print("DEBUG: finished search_codebase(app initialization)")

    print("DEBUG: starting search_codebase(routes)")
    routes = search_codebase("routes")
    print("DEBUG: finished search_codebase(routes)")

    structure = "\n".join(folder_names[:MAX_FOLDERS])

    prompt = f"""
You are a senior software engineer onboarding a new developer.

Repository Folder Structure:
{structure}

README:
{readme_text[:4000]}

Detected Entry Point:
{entry_point}

Top 30 lines of the entry point:
{entry_code}

Relevant code related to the main function:
{main_function}

Relevant code related to application initialization:
{app_initialization}

Relevant routing code:
{routes}

Write a friendly onboarding guide.

Cover exactly these sections:

1. Project Overview
- What this project does
- Main technologies used

2. Folder Structure
- Explain the purpose of important folders

3. Where to Start Reading
- Which file should a new developer read first
- Why

4. Application Flow
- How execution starts
- How requests move through the application
- Where business logic lives

5. Key Files
- Mention the most important files
- Explain why each matters

Keep the explanation practical and beginner friendly.
"""

    print(f"DEBUG: prompt built, length={len(prompt)} chars")

    print("DEBUG: calling generate_content")
    response = _generate_with_timeout(prompt)
    print("DEBUG: generate_content returned")

    answer_text = response.text

    repo_name = _repo_name_from_path(repo_path)
    file_paths = _extract_file_paths(main_function, app_initialization, routes)

    if entry_point:
        entry_rel = os.path.relpath(entry_point, repo_path)
        if entry_rel not in file_paths:
            file_paths.insert(0, entry_rel)

    if file_paths:
        sources_block = "\n\n".join(f"Repo: {repo_name}\nFile: {f}" for f in file_paths)
        answer_text = f"{answer_text}\n\n---\nSources:\n\n{sources_block}"

    return answer_text


if __name__ == "__main__":
    print(explain_repo("flask-main/flask-main"))