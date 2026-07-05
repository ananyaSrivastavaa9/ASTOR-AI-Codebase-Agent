from google import genai
from dotenv import load_dotenv
import os

from config import MODEL_NAME
from indexer import search

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def answer(question: str):
    results = search(question, top_k=5)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return "No relevant code found for this question."

    context = ""

    for i, code in enumerate(documents):
        metadata = metadatas[i]

        context += f"Result {i + 1}\n"
        context += f"File: {metadata.get('file', 'unknown')}\n"
        context += f"Function/Class: {metadata.get('name', 'unknown')}\n"
        context += f"Lines: {metadata.get('start', '?')} to {metadata.get('end', '?')}\n"
        context += "Code:\n"
        context += code
        context += "\n\n" + "-" * 50 + "\n\n"

    prompt = f"""
You are a senior codebase assistant.

Use only the provided code context to answer the user's question.

Rules:
- Be clear and practical.
- Cite the file name, function/class name, and line numbers.
- If the answer is not present in the context, say that the provided context is not enough.
- Do not invent details.

Code context:
{context}

User question:
{question}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


if __name__ == "__main__":
    questions = [
        "Where is routing handled?",
        "How does Flask handle errors?",
        "What does the app.run() function do?",
        "Where is request parsing done?",
        "How is the Flask app created?",
    ]

    for question in questions:
        print("=" * 80)
        print("QUESTION:", question)
        print("=" * 80)

        response = answer(question)

        print(response)
        print()