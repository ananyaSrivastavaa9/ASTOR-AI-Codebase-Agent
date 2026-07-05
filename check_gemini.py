from google import genai
from dotenv import load_dotenv
import os

from config import MODEL_NAME

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def check_gemini():
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="Say hello in one sentence."
    )

    return response.text


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Gemini Connection")
    print("=" * 50)

    print(check_gemini())