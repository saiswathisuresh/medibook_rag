from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchText
from fastembed import TextEmbedding

load_dotenv()

router = APIRouter()

GROK_API_KEY = os.getenv("GROK_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

COLLECTION_NAME = "medical_chunks"
EMBEDDING_MODEL = "BAAI/bge-small-en"
GROK_MODEL = "grok-3"
GROK_URL = "https://api.x.ai/v1/chat/completions"

qdrant = QdrantClient(url=QDRANT_URL)
embedder = TextEmbedding(model_name=EMBEDDING_MODEL)

class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    max_tokens: int = 1000
    temperature: float = 0.2

class SourceChunk(BaseModel):
    text: str
    score: float
    source: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    found_relevant_content: bool

def ask_grok(prompt, max_tokens, temperature):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    r = requests.post(GROK_URL, headers=headers, json=payload, timeout=30)
    if r.status_code != 200:
        return None
    return r.json()["choices"][0]["message"]["content"]

def hybrid_search(query, top_k):
    vec = list(embedder.embed([query]))[0]
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=vec,
        limit=top_k
    )
    return results

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    results = hybrid_search(req.question, req.top_k)

    if not results:
        return ChatResponse(
            answer="No relevant content found.",
            sources=[],
            found_relevant_content=False
        )

    context = []
    sources = []

    for r in results:
        text = r.payload.get("content", "")
        context.append(text)
        sources.append(SourceChunk(
            text=text[:300],
            score=round(r.score, 3),
            source="vector"
        ))

    prompt = f"""
Answer ONLY from the context below.

Context:
{" ".join(context)}

Question:
{req.question}
"""

    answer = ask_grok(prompt, req.max_tokens, req.temperature)

    if not answer:
        raise HTTPException(status_code=500, detail="AI failed")

    return ChatResponse(
        answer=answer.strip(),
        sources=sources,
        found_relevant_content=True
    )
