
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

DEFAULT_CHAT_MODEL = "gpt-4o-mini"  

def generate_rag_answer(query: str, context: str) -> str:
    if not client:
        raise RuntimeError("No OPENAI_API_KEY set in environment")

    prompt = f"""
You are an assistant answering ONLY from the provided context.
If the answer is not present, say "Information not found in the document".

Context:
{context}

Question:
{query}

Answer clearly and concisely.
"""

    resp = client.chat.completions.create(
        model=DEFAULT_CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful document assistant"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return resp.choices[0].message.content.strip()
