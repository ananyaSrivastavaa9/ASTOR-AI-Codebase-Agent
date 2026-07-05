def get_status_message(tool_name, stage, data=None):
    """
    Returns clean, user-friendly status messages for the UI.

    Parameters
    ----------
    tool_name : str
        Name of the tool being executed.

    stage : str
        Either "before" or "after".

    data : any
        Optional information used to make the status message more specific.
    """

    if stage == "before":

        if tool_name == "search_codebase":
            query = ""
            if isinstance(data, dict):
                query = data.get("query", "")
            return f"Searching the codebase for '{query}'..."

        elif tool_name == "read_file":
            path = ""
            if isinstance(data, dict):
                path = data.get("path", "")
            return f"Reading {path}..."

        elif tool_name == "review_file":
            path = ""
            if isinstance(data, dict):
                path = data.get("file_path", "")
            return f"Reviewing {path}..."

        elif tool_name == "explain_repo":
            repo = ""
            if isinstance(data, dict):
                repo = data.get("repo_path", "")
            return f"Exploring repository '{repo}'..."

        elif tool_name == "run_code":
            return "Running Python code..."

        return "Processing..."

    if stage == "after":

        if tool_name == "search_codebase":

            file_count = 0

            if isinstance(data, str):
                file_count = data.count(".py")

            return f"Found relevant code in approximately {file_count} file(s)."

        elif tool_name == "read_file":
            return "Finished reading the requested file."

        elif tool_name == "review_file":
            return "Code review completed."

        elif tool_name == "explain_repo":
            return "Repository analysis completed."

        elif tool_name == "run_code":
            return "Execution completed."

        return "Done."

    return ""