from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
import traceback

# ----------------------------
# ENV + ROUTER
# ----------------------------
load_dotenv()
router = APIRouter()

print("🚀 chat_routes.py loaded")

# ----------------------------
# ENV VARIABLES
# ----------------------------
GROK_API_KEY = os.getenv("GROK_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

print("🔑 GROK_API_KEY exists:", bool(GROK_API_KEY))
print("📦 QDRANT_URL:", QDRANT_URL)

COLLECTION_NAME = "medical_chunks"
EMBEDDING_MODEL = "BAAI/bge-small-en"
GROK_MODEL = "grok-3"
GROK_URL = "https://api.x.ai/v1/chat/completions"

# ----------------------------
# CLIENTS
# ----------------------------
try:
    qdrant = QdrantClient(url=QDRANT_URL)
    print("✅ Qdrant client initialized")
except Exception as e:
    print("❌ Qdrant init failed:", e)

try:
    embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
    print("✅ Embedder loaded:", EMBEDDING_MODEL)
except Exception as e:
    print("❌ Embedder load failed:", e)

# ----------------------------
# MODELS
# ----------------------------
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

# ----------------------------
# GROK CALL
# ----------------------------
def ask_grok(prompt: str, max_tokens: int, temperature: float):
    print("\n🤖 Calling Grok...")
    print("➡️ Prompt length:", len(prompt))
    print("➡️ Max tokens:", max_tokens, "Temp:", temperature)

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

    try:
        r = requests.post(
            GROK_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        print("📡 Grok status:", r.status_code)
        print("📡 Grok raw response:", r.text)

        if r.status_code != 200:
            return None

        data = r.json()
        content = data["choices"][0]["message"]["content"]

        # Grok content may be list or string
        if isinstance(content, list):
            content = content[0].get("text", "")

        return content

    except Exception as e:
        print("❌ Grok call exception:")
        traceback.print_exc()
        return None

# ----------------------------
# QDRANT SEARCH
# ----------------------------
def hybrid_search(query: str, top_k: int):
    print("\n🔎 Hybrid search started")
    print("➡️ Query:", query)
    print("➡️ top_k:", top_k)

    try:
        embedding = embedder.embed([query])[0]
        vector = list(map(float, embedding))
        print("✅ Embedding generated, dim:", len(vector))

        results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k
        )

        print("✅ Qdrant results count:", len(results))
        return results

    except Exception as e:
        print("❌ Hybrid search failed:")
        traceback.print_exc()
        raise

# ----------------------------
# CHAT ENDPOINT
# ----------------------------
@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    print("\n==============================")
    print("📩 /api/chat called")
    print("➡️ Request body:", req)
    print("==============================")

    try:
        # Qdrant search
        results = hybrid_search(req.question, req.top_k)

        if not results:
            print("⚠️ No relevant content found")
            return ChatResponse(
                answer="No relevant content found.",
                sources=[],
                found_relevant_content=False
            )

        context = []
        sources = []

        for r in results:
            payload = r.payload or {}
            text = payload.get("content", "")
            context.append(text)

            sources.append(
                SourceChunk(
                    text=text[:300],
                    score=round(r.score, 3),
                    source="vector"
                )
            )

        print("🧠 Context chunks:", len(context))

        prompt = f"""
Answer ONLY from the context below.

Context:
{" ".join(context)}

Question:
{req.question}
"""

        answer = ask_grok(prompt, req.max_tokens, req.temperature)

        if not answer:
            print("❌ Grok returned empty answer")
            raise HTTPException(status_code=500, detail="AI failed")

        print("✅ Final answer length:", len(answer))

        return ChatResponse(
            answer=answer.strip(),
            sources=sources,
            found_relevant_content=True
        )

    except HTTPException:
        raise

    except Exception as e:
        print("🔥 CHAT ENDPOINT CRASHED")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
