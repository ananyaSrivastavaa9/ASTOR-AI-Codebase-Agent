import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

import agent

QUESTION = "Where are URL rules added?"

agent.messages = []

print(f"Running: {QUESTION}\n")
answer = agent.run_agent(QUESTION)

print("=" * 70)
print(f"agent.messages has {len(agent.messages)} entries")
print("=" * 70)

for i, msg in enumerate(agent.messages):
    role = msg.get("role", "MISSING_ROLE")
    content = msg.get("content", "")
    print(f"\n--- [{i}] role={role!r} ---")
    print(repr(content[:400]))

print("\n" + "=" * 70)
print("Checking tool_result messages specifically")
print("=" * 70)

tool_result_msgs = [m for m in agent.messages if m.get("role") == "tool_result"]
print(f"Found {len(tool_result_msgs)} tool_result message(s)")

for i, msg in enumerate(tool_result_msgs):
    content = msg.get("content", "")
    starts_with_check = content.startswith("Result from search_codebase:")
    print(f"\ntool_result[{i}] startswith('Result from search_codebase:') = {starts_with_check}")
    print("First 60 chars:", repr(content[:60]))

print("\n" + "=" * 70)
print("Final answer returned by run_agent()")
print("=" * 70)
print(repr(answer[:500]))