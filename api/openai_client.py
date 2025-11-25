import os
from openai import OpenAI

# Create a single OpenAI client using the API key from env
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def chat_with_openai(messages: list[dict]) -> str:
    """
    Thin wrapper around OpenAI chat completions.
    Expects a list of {role: 'system'|'user'|'assistant', content: '...'}.
    Returns the assistant's reply text.
    """
    if not client.api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
    )

    return resp.choices[0].message.content
