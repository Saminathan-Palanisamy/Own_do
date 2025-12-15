
import os
from openai import OpenAI 
from typing import List
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY") 
client = OpenAI(api_key=API_KEY)
# model choices: text-embedding-3-small / text-embedding-3-large
DEFAULT_EMBED_MODEL = "text-embedding-3-small"

def embed_texts(texts: List[str], model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:
    """
    Batch embed a list of texts using openai==0.28 style API.
    Returns list of vectors (list of floats).
    """
    if not client:
        raise RuntimeError("No OPENAI_API_KEY set in environment")

    out: List[List[float]] = []

    for i in range(0, len(texts), 16):
        batch = texts[i:i+16]
        resp = client.embeddings.create(model=model, input=batch)
        print(resp)
        vectors = [d.embedding for d in resp.data]
        out.extend(vectors)
    return out

def embed_query(text: str, model: str = DEFAULT_EMBED_MODEL) -> List[float]:
    """
    Embed a single query string, returns a single vector.
    """
    if not client:
        raise RuntimeError("No OPENAI_API_KEY set in environment")
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding
