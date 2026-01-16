import os
import json
import uuid
import time
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from qdrant_client.http.exceptions import ResponseHandlingException

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# =========================================================
# CONFIG
# =========================================================
COLLECTION_NAME = "medical_chunks"
VECTOR_DIM = 384
BATCH_SIZE = 8              # 🔥 VERY SAFE
TIMEOUT = 120               # 🔥 HIGH TIMEOUT
RETRY_LIMIT = 5             # 🔁 retries
SLEEP_BETWEEN_BATCH = 0.3   # 🐢 throttle

# =========================================================
# PATH HANDLING
# =========================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_DIR = os.path.join(PROJECT_ROOT, "data", "chunks")

print(f"[INFO] Using chunks folder: {CHUNKS_DIR}")

# =========================================================
# LOAD EMBEDDING MODEL
# =========================================================
print("[INFO] Loading BAAI/bge-small-en-v1.5 model...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

def get_embedding(text: str) -> list:
    text = "Represent this sentence for retrieval: " + text
    return model.encode(text, normalize_embeddings=True).tolist()

# =========================================================
# INIT QDRANT
# =========================================================
client = QdrantClient(url=QDRANT_URL, timeout=TIMEOUT)

print("[INFO] Resetting Qdrant collection...")
try:
    client.delete_collection(collection_name=COLLECTION_NAME)
except Exception:
    pass

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=VECTOR_DIM,
        distance=Distance.COSINE
    )
)

print("[INFO] Qdrant collection ready (384-dim)")

# =========================================================
# LOAD CHUNKS
# =========================================================
all_chunks = []

for file in os.listdir(CHUNKS_DIR):
    if file.endswith(".json"):
        with open(os.path.join(CHUNKS_DIR, file), "r", encoding="utf-8") as f:
            all_chunks.extend(json.load(f))

total = len(all_chunks)
print(f"[INFO] Total chunks loaded: {total}")

# =========================================================
# SAFE UPSERT WITH RETRY
# =========================================================
points = []
uploaded = 0

def safe_upsert(points):
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True
            )
            return True
        except ResponseHandlingException as e:
            print(f"[WARN] Upsert failed (attempt {attempt}/{RETRY_LIMIT})")
            time.sleep(2 * attempt)
    return False

for chunk in all_chunks:
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=get_embedding(chunk["text"]),
            payload={
                "content": chunk["text"],
                "source": chunk.get("source"),
                "chapter": chunk.get("chapter")
            }
        )
    )

    if len(points) >= BATCH_SIZE:
        if safe_upsert(points):
            uploaded += len(points)
            print(f"[INFO] Uploaded {uploaded}/{total}")
            points = []
            time.sleep(SLEEP_BETWEEN_BATCH)
        else:
            print("[FATAL] Failed after retries. Exiting safely.")
            break

# remaining points
if points:
    safe_upsert(points)
    uploaded += len(points)

print(f"[SUCCESS] Uploaded {uploaded}/{total} vectors 🚀")
