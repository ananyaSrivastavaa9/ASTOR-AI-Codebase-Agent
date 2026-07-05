from google import genai
import os
import concurrent.futures
from dotenv import load_dotenv
from config import (
    MODEL_NAME,
    MAX_AGENT_STEPS,
    MAX_HISTORY,
    RETRY_ATTEMPTS,
    RETRY_WAIT_SECONDS,
)
from features.code_review import review_file
from features.onboarding import explain_repo
from features.status_messages import get_status_message
import json
import re
import time

from tools import (
    search_codebase,
    read_file,
    run_code,
    search_codebase_tool,
    read_file_tool,
    run_code_tool,
)

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

messages = []

review_file_tool = {
    "name": "review_file",
    "description": "Review a Python file and return issues, security problems, suggestions, and good parts with line numbers",
    "parameters": {
        "file_path": "string"
    }
}

onboarding_tool = {
    "name": "explain_repo",
    "description": "Explain a code repository to a new developer. Returns a guided tour of the project, folder structure, entry point, key files, and application flow.",
    "parameters": {
        "repo_path": "string"
    }
}

TOOLS = [
    onboarding_tool,
    review_file_tool,
    search_codebase_tool,
    read_file_tool,
    run_code_tool,
]

TOOL_FUNCTIONS = {
    "search_codebase": search_codebase,
    "read_file": read_file,
    "run_code": run_code,
    "review_file": review_file,
    "explain_repo": explain_repo,
}

# Tools like explain_repo can legitimately take a while (folder scan + LLM
# call), so give them more headroom than a quick lookup like search_codebase.
TOOL_TIMEOUT_SECONDS = {
    "explain_repo": 90,
    "review_file": 60,
}
DEFAULT_TOOL_TIMEOUT_SECONDS = 30

SYSTEM_PROMPT = """
You are a codebase agent that answers questions about a Python codebase.

You have these tools available:
- explain_repo(repo_path): explains the entire repository to a new developer. It returns a guided tour covering the project purpose, folder structure, entry point, important files, and application flow. Use this whenever the user asks to explain, understand, onboard, or tour a codebase.
- review_file(file_path): reviews an entire Python file and returns ISSUES, SECURITY, SUGGESTIONS, and GOOD PARTS. Use this whenever the user says "review <filepath>".
- search_codebase(query): searches the indexed codebase and returns relevant code chunks with file paths and line numbers.
- read_file(path, start_line, end_line): reads exact lines from a file. Do NOT use this for review requests.
- run_code(code): runs a Python snippet and returns output.

Rules you must follow strictly:
1. Read the full conversation history before deciding what to do.
2. Use "that file", "it", "that function" etc. to refer back to files/functions already found in history.
3. If a file path was already found in history, do NOT call search_codebase again — call read_file directly.
4. Never call search_codebase more than once for the same question.
5. After read_file returns code, give your final answer immediately.
6. When calling a tool, respond ONLY with this JSON and nothing else:
{
  "tool_call": {
    "name": "tool_name",
    "arguments": { "arg_name": "arg_value" }
  }
}
7. When you have the final answer, respond in plain text, not JSON.
8. If the user message starts with "review " or asks to review a file, you MUST call review_file with {"file_path": "..."} and must NOT call read_file.
9. If the user asks to explain a repository, onboard a new developer, understand the codebase, or give a project tour, you MUST call explain_repo with {"repo_path": "..."}.
"""


def extract_tool_call(text):
    try:
        data = json.loads(text)
        return data.get("tool_call")
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        return data.get("tool_call")
    except Exception:
        return None


def build_prompt():
    prompt = SYSTEM_PROMPT + "\n\n--- Conversation history ---\n\n"

    for msg in messages[-20:]:
        role = msg["role"].upper()
        content = msg["content"]
        prompt += f"{role}:\n{content}\n\n"

    prompt += "AGENT:"
    return prompt

def call_gemini_with_retry(prompt):
    last_error = None

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return response.text.strip()

        except Exception as e:
            last_error = e

            if attempt == 0:
                print("API error, retrying...")
                time.sleep(RETRY_WAIT_SECONDS)

    return (
        "API error: Gemini is currently unavailable. "
        "Please try again after some time."
    )

def call_tool_with_timeout(tool_name, arguments):
    """Run a tool function with a hard timeout so a stalled tool (e.g. a
    slow scan or a stuck network call inside it) can never hang the agent
    indefinitely. Returns the tool's result, or an error string on
    timeout/failure — never blocks forever."""
    func = TOOL_FUNCTIONS[tool_name]
    timeout = TOOL_TIMEOUT_SECONDS.get(tool_name, DEFAULT_TOOL_TIMEOUT_SECONDS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, **arguments)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return f"Error running {tool_name}: timed out after {timeout}s"
        except Exception as e:
            return f"Error running {tool_name}: {str(e)}"


_SEARCH_SOURCE_PATTERN = re.compile(r"Repo:\s*([^\n]+)\nFile:\s*([^\n]+)")


def _collect_search_sources(msgs):
    """Pull Repo/File pairs out of any search_codebase tool results already
    sitting in the conversation history for this question — the model's
    final-answer text doesn't reliably repeat that formatting verbatim,
    which is what app.py's extract_sources() scans for."""
    pairs = []
    seen = set()
    for msg in msgs:
        if msg.get("role") != "tool_result":
            continue
        if not msg.get("content", "").startswith("Result from search_codebase:"):
            continue
        for repo, file in _SEARCH_SOURCE_PATTERN.findall(msg["content"]):
            key = (repo.strip(), file.strip())
            if key not in seen:
                seen.add(key)
                pairs.append(key)
    return pairs


def _append_sources(text, msgs):
    pairs = _collect_search_sources(msgs)
    if not pairs:
        return text
    sources_block = "\n\n".join(f"Repo: {r}\nFile: {f}" for r, f in pairs)
    return f"{text}\n\n---\nSources:\n\n{sources_block}"


def run_agent(question):
    global messages

    messages.append({"role": "user", "content": question})

    print(f"\nQuestion: {question}")

    used_tools_this_question = set()

    for step in range(1, MAX_AGENT_STEPS + 1):
        prompt = build_prompt()
        text = call_gemini_with_retry(prompt)

        tool_call = extract_tool_call(text)

        if tool_call:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})

            if tool_name == "search_codebase" and "search_codebase" in used_tools_this_question:
                messages.append({
                    "role": "system_note",
                    "content": "You already searched for this question. Use the search result in history and either call read_file or answer."
                })
                continue

            used_tools_this_question.add(tool_name)

            print(f"  Step {step}: calling {tool_name}({arguments})")

            messages.append({
                "role": "agent",
                "content": f"I will call {tool_name} with arguments: {json.dumps(arguments)}"
            })

            if tool_name not in TOOL_FUNCTIONS:
                tool_result = f"Error: unknown tool '{tool_name}'"
            else:
                tool_result = call_tool_with_timeout(tool_name, arguments)

            messages.append({
                "role": "tool_result",
                "content": f"Result from {tool_name}:\n{tool_result}"
            })

            if tool_name in ["review_file", "explain_repo"]:
                print(f"  Step {step + 1}: final answer ready")

                messages.append({
                    "role": "assistant",
                    "content": tool_result
                })

                if len(messages) > MAX_HISTORY:
                    messages = messages[-MAX_HISTORY:]
                return tool_result

            if tool_name == "search_codebase" and ".py" in tool_result:
                messages.append({
                    "role": "system_note",
                    "content": "Search is complete. Do NOT call search_codebase again for this question. Use the file paths and line numbers above to call read_file, or give the final answer."
                })

        else:
            print(f"  Step {step}: final answer ready")

            messages.append({"role": "assistant", "content": text})

            if len(messages) > MAX_HISTORY:
                messages = messages[-MAX_HISTORY:]
            return text

    fallback = "I could not complete this in the allowed steps. Please rephrase your question."
    messages.append({"role": "assistant", "content": fallback})

    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]

    return fallback

def run_agent_stream(question):
    global messages

    yield "Understanding your question..."

    messages.append({"role": "user", "content": question})

    used_tools_this_question = set()

    for step in range(1, MAX_AGENT_STEPS + 1):
        yield "Planning the next action..."

        prompt = build_prompt()
        text = call_gemini_with_retry(prompt)

        tool_call = extract_tool_call(text)

        if tool_call:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})

            if tool_name == "search_codebase" and "search_codebase" in used_tools_this_question:
                yield "Using the earlier search results instead of searching again."

                messages.append({
                    "role": "system_note",
                    "content": "You already searched for this question. Use the search result in history and either call read_file or answer."
                })
                continue

            used_tools_this_question.add(tool_name)

            yield get_status_message(
                tool_name,
                "before",
                arguments,
            )

            messages.append({
                "role": "agent",
                "content": f"I will call {tool_name} with arguments: {json.dumps(arguments)}"
            })

            if tool_name not in TOOL_FUNCTIONS:
                tool_result = f"Error: unknown tool '{tool_name}'"
            else:
                tool_result = call_tool_with_timeout(tool_name, arguments)

            yield get_status_message(
                tool_name,
                "after",
                tool_result,
            )

            messages.append({
                "role": "tool_result",
                "content": f"Result from {tool_name}:\n{tool_result}"
            })

            if tool_name in ["review_file", "explain_repo"]:
                yield "Preparing the final answer..."

                messages.append({
                    "role": "assistant",
                    "content": tool_result
                })

                if len(messages) > MAX_HISTORY:
                    messages = messages[-MAX_HISTORY:]

                yield tool_result
                return

            if tool_name == "search_codebase" and ".py" in tool_result:
                yield "Using the matched files for the next step."

                messages.append({
                    "role": "system_note",
                    "content": "Search is complete. Do NOT call search_codebase again for this question. Use the file paths and line numbers above to call read_file, or give the final answer."
                })

        else:
            yield "Preparing the final answer..."

            final_text = _append_sources(text, messages)

            messages.append({
                "role": "assistant",
                "content": final_text
            })

            if len(messages) > MAX_HISTORY:
                messages = messages[-MAX_HISTORY:]

            yield final_text
            return

    fallback = "I could not complete this in the allowed steps. Please rephrase your question."

    messages.append({
        "role": "assistant",
        "content": fallback
    })

    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]

    yield fallback

if __name__ == "__main__":
    question = "explain this repository flask-main/flask-main"

    for update in run_agent_stream(question):
        print(update)
        print("-" * 60)
        time.sleep(0.1)