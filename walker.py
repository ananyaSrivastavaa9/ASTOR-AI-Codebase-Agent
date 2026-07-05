import os

def walk_repo(folder_path: str, max_files: int = None):
    python_files = []

    ignored_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".idea",
        ".vscode",
        "build",
        "dist",
        "db",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        # Test suites and docs are the biggest noise source in large repos
        # like Django (thousands of files across tests/, docs/, per-app
        # migrations/) that add nothing to onboarding/code-review answers.
        "tests",
        "test",
        "docs",
        "doc",
        "migrations",
        "htmlcov",
        ".tox",
        ".eggs",
        ".github",
    }

    print(f"[walker] scanning {folder_path} ...")

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = sorted(
            d for d in dirs
            if d not in ignored_dirs and not d.startswith(".")
        )

        for file in sorted(files):
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

        if max_files is not None and len(python_files) >= max_files:
            print(f"[walker] hit max_files={max_files}, stopping scan early")
            break

    python_files.sort()

    if max_files is not None:
        python_files = python_files[:max_files]

    print(f"[walker] found {len(python_files)} Python files in {folder_path}")

    return python_files


if __name__ == "__main__":
    files = walk_repo("flask-main")

    print(f"Found {len(files)} Python files.\n")

    for file in files[:20]:
        print(file)