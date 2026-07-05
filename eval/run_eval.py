import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from questions import QUESTIONS
import agent


def _normalize(text):
    return text.strip().replace("\\", "/").lower()


def _file_matches(expected_file, haystack):
    """Suffix/substring match so 'scaffold.py' matches '.../sansio/scaffold.py'
    and 'sansio/scaffold.py' matches 'src/flask/sansio/scaffold.py', instead
    of requiring an exact string match against expected_file's format."""
    expected = _normalize(expected_file)
    haystack = _normalize(haystack)
    return expected in haystack


def _function_matches(expected_function, haystack):
    return expected_function.lower() in haystack.lower()


def _get_search_results_text(msgs):
    """Pull out only this question's search_codebase tool_result content —
    this is what hybrid retrieval actually returned, independent of what
    the model chose to say in its final answer."""
    chunks = []
    for msg in msgs:
        if msg.get("role") == "tool_result" and msg.get("content", "").startswith("Result from search_codebase:"):
            chunks.append(msg["content"])
    return "\n".join(chunks)


def evaluate():
    total = len(QUESTIONS)
    passed = 0
    retrieval_hits = 0
    generation_hits = 0

    retrieval_failures = []
    generation_failures = []

    for i, item in enumerate(QUESTIONS, start=1):
        question = item["q"]
        expected_file = item["expected_file"]
        expected_function = item["expected_function"]

        print(f"\n[{i}/{total}] Testing:")
        print(question)

        # Each benchmark question is independent — reset conversation
        # history so an earlier question's context/tool results can't
        # leak into this one. agent.messages is a module-level global
        # that normally persists across calls for real chat sessions.
        agent.messages = []

        answer = agent.run_agent(question)

        retrieved_text = _get_search_results_text(agent.messages)

        retrieval_ok = (
            _file_matches(expected_file, retrieved_text)
            or _function_matches(expected_function, retrieved_text)
        )
        generation_ok = (
            _file_matches(expected_file, answer)
            or _function_matches(expected_function, answer)
        )

        if retrieval_ok:
            retrieval_hits += 1
        if generation_ok:
            generation_hits += 1

        if generation_ok:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            record = {
                "question": question,
                "expected_file": expected_file,
                "expected_function": expected_function,
            }
            if not retrieval_ok:
                print("  Reason: retrieval_failure (expected code never retrieved)")
                retrieval_failures.append(record)
            else:
                print("  Reason: generation_failure (retrieved correctly, answer didn't reflect it)")
                generation_failures.append(record)

    print("\n======================")
    print("Evaluation Complete")
    print("======================")

    overall_accuracy = (passed / total) * 100
    retrieval_accuracy = (retrieval_hits / total) * 100
    generation_accuracy = (generation_hits / total) * 100

    print(f"Overall accuracy (final answer correct): {passed}/{total} = {overall_accuracy:.2f}%")
    print(f"Retrieval accuracy (right chunk found):  {retrieval_hits}/{total} = {retrieval_accuracy:.2f}%")
    print(f"Generation accuracy (answer used it):    {generation_hits}/{total} = {generation_accuracy:.2f}%")

    print(f"\nRetrieval failures ({len(retrieval_failures)}): hybrid search never found the expected code")
    for item in retrieval_failures:
        print("-", item["question"])
        print("  Expected:", item["expected_file"], "/", item["expected_function"])

    print(f"\nGeneration failures ({len(generation_failures)}): retrieved correctly, but final answer didn't reflect it")
    for item in generation_failures:
        print("-", item["question"])
        print("  Expected:", item["expected_file"], "/", item["expected_function"])


if __name__ == "__main__":
    evaluate()