from indexer import search
import subprocess


def search_codebase(query: str):
    results = search(query, top_k=5)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return "No matching code chunks found."

    output = ""

    for i, code in enumerate(documents):
        metadata = metadatas[i]

        output += f"Result {i + 1}\n"
        output += f"Repo: {metadata.get('repo_name', 'unknown')}\n"
        output += f"File: {metadata.get('file', 'unknown')}\n"
        output += f"Name: {metadata.get('name', 'unknown')}\n"
        output += f"Lines: {metadata.get('start', '?')} to {metadata.get('end', '?')}\n"
        output += "Code:\n"
        output += code
        output += "\n\n" + "-" * 50 + "\n\n"

    return output


def read_file(path: str, start_line: int, end_line: int):
    if start_line < 1:
        start_line = 1

    if end_line < start_line:
        return "Invalid line range: end_line must be greater than or equal to start_line."

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

    selected_lines = lines[start_line - 1:end_line]

    if not selected_lines:
        return f"No lines found in {path} for range {start_line}-{end_line}."

    output = ""

    for line_number, line in enumerate(selected_lines, start=start_line):
        output += f"{line_number}: {line}"

    return output


def run_code(code: str):
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.stderr:
            return result.stderr

        return result.stdout

    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out after 5 seconds."

    except Exception as e:
        return f"Error running code: {str(e)}"


search_codebase_tool = {
    "name": "search_codebase",
    "description": "Search the codebase and return the top 5 matching code chunks with file names, function/class names, line numbers, and code.",
    "parameters": {
        "query": "string"
    }
}

read_file_tool = {
    "name": "read_file",
    "description": "Read specific line numbers from a file and return the code with line numbers.",
    "parameters": {
        "path": "string",
        "start_line": "integer",
        "end_line": "integer"
    }
}

run_code_tool = {
    "name": "run_code",
    "description": "Execute a small Python code snippet safely with a 5 second timeout and return stdout or stderr.",
    "parameters": {
        "code": "string"
    }
}


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING search_codebase")
    print("=" * 80)
    print(search_codebase("routing")[:1000])

    print("\n" + "=" * 80)
    print("TESTING read_file")
    print("=" * 80)
    print(read_file("flask-main/flask-main/src/flask/app.py", 1, 10))

    print("\n" + "=" * 80)
    print("TESTING run_code")
    print("=" * 80)
    print(run_code("print(2+2)"))