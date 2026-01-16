import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchText
from fastembed import TextEmbedding

# ---------------- LOAD ENV ----------------
load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

# ---------------- CONFIG ----------------
COLLECTION_NAME = "medical_chunks"
EMBEDDING_MODEL = "BAAI/bge-small-en"
TOP_K = 5
GROK_MODEL = "grok-3"
GROK_URL = "https://api.x.ai/v1/chat/completions"

# ---------------- INIT ----------------
qdrant = QdrantClient(url=QDRANT_URL)
embedder = TextEmbedding(model_name=EMBEDDING_MODEL)

# ---------------- HELPER ----------------
def ask_grok(prompt: str):
    if not prompt.strip():
        print("❌ Cannot send empty prompt to Grok")
        return None

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000  # INCREASED: More detailed answers
    }

    try:
        response = requests.post(GROK_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            print("❌ Grok API error:", response.status_code, response.text)
            return None
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception as e:
        print("❌ Grok API request failed:", e)
        return None

def extract_keywords(query: str):
    """Extract important keywords from query"""
    # Remove common words
    stop_words = {'what', 'is', 'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of'}
    words = query.lower().split()
    keywords = [w.strip('?.,!') for w in words if w.lower() not in stop_words]
    return keywords

def hybrid_search(query: str, top_k: int = 5):
    """Perform both vector and keyword search, then combine results"""
    
    # 1️⃣ Vector Search
    query_vector = list(embedder.embed([query]))[0]
    vector_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    
    # 2️⃣ Keyword Search (try to match important terms)
    keywords = extract_keywords(query)
    keyword_results = []
    
    if keywords:
        print(f"🔍 Searching for keywords: {keywords}")
        try:
            # Search for chunks containing any of the keywords
            for keyword in keywords:
                results = qdrant.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="text",
                                match=MatchText(text=keyword)
                            )
                        ]
                    ),
                    limit=top_k,
                    with_payload=True
                )[0]  # scroll returns (points, next_page_offset)
                
                if results:
                    keyword_results.extend(results)
                    print(f"  ✅ Found {len(results)} chunks with '{keyword}'")
        except Exception as e:
            print(f"  ⚠️ Keyword search failed: {e}")
    
    # 3️⃣ Combine and deduplicate results
    all_results = {}
    
    # Add vector results with scores
    for r in vector_results:
        all_results[r.id] = {
            'payload': r.payload,
            'score': r.score,
            'source': 'vector'
        }
    
    # Add keyword results (give them high score)
    for r in keyword_results:
        # Handle Point object from scroll
        chunk_id = r.id
        chunk_payload = r.payload if hasattr(r, 'payload') else {}
        
        if chunk_id not in all_results:
            all_results[chunk_id] = {
                'payload': chunk_payload,
                'score': 0.95,  # High score for keyword matches
                'source': 'keyword'
            }
        else:
            # Boost score if found in both
            all_results[chunk_id]['score'] = min(1.0, all_results[chunk_id]['score'] + 0.3)
            all_results[chunk_id]['source'] = 'both'
    
    # Sort by score and return top results
    sorted_results = sorted(all_results.items(), key=lambda x: x[1]['score'], reverse=True)
    return sorted_results[:top_k]

# ---------------- MAIN LOOP ----------------
while True:
    query = input("\nAsk medical question (type 'exit' to quit): ")
    if query.lower() == "exit":
        break

    # 1️⃣ Hybrid Search (Vector + Keyword)
    results = hybrid_search(query, TOP_K)

    if not results:
        print("❌ No relevant content found.")
        continue

    # 2️⃣ Extract text from results
    print(f"\n📊 Found {len(results)} results:")
    context_chunks = []
    for idx, (chunk_id, data) in enumerate(results, 1):
        payload = data.get('payload', {})
        
        # FIXED: Check 'content' field (your actual field name)
        text = payload.get("content") or payload.get("text") or payload.get("chunk_text") or ""
        
        if text and text.strip():
            context_chunks.append(text.strip())
            source = data.get('source', 'unknown')
            score = data.get('score', 0.0)
            print(f"  {idx}. Score: {score:.3f} | Source: {source} | Preview: {text[:80]}...")
        else:
            print(f"  {idx}. ❌ No text content in this chunk")

    if not context_chunks:
        print("❌ No text content found in results.")
        continue

    # 3️⃣ Prepare context
    context = "\n\n".join(context_chunks)
    context = context[:8000]  # INCREASED: More context for better answers

    # 4️⃣ Create prompt
    prompt = f"""You are a medical assistant.
Answer ONLY using the context below.
If the answer is not found, say "Not found in provided books".

Context:
{context}

Question:
{query}"""

    # 5️⃣ Ask Grok
    print("\n🤖 Asking Grok...")
    answer = ask_grok(prompt)
    if answer:
        print("\n🧠 ANSWER:\n")
        print(answer.strip())
    else:
        print("❌ No response from Grok")