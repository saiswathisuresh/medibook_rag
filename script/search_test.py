from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from fastembed import TextEmbedding
import uuid

# =========================
# CONFIG
# =========================
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "medical_chunks"

# =========================
# EMBEDDING MODEL (OFFLINE)
# =========================
model = TextEmbedding(model_name="BAAI/bge-small-en")

def embed(text: str):
    return list(model.embed([text]))[0]

# =========================
# QDRANT CLIENT
# =========================
client = QdrantClient(url=QDRANT_URL)

# =========================
# CREATE COLLECTION (RUN ONCE)
# =========================
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=384,               # bge-small vector size
        distance=Distance.COSINE
    )
)

print("✅ Collection created")

# =========================
# INSERT SAMPLE MEDICAL DATA
# =========================
documents = [
    {
        "content": "Diabetes is a chronic disease that occurs when blood sugar levels are too high.",
        "source": "Medical Textbook",
        "chapter": "Diabetes Overview"
    },
    {
        "content": "Type 1 diabetes is caused by the pancreas producing little or no insulin.",
        "source": "Medical Textbook",
        "chapter": "Types of Diabetes"
    },
    {
        "content": "Type 2 diabetes occurs when the body becomes resistant to insulin.",
        "source": "Medical Textbook",
        "chapter": "Types of Diabetes"
    },
    {
        "content": "Common symptoms of diabetes include increased thirst, frequent urination, and fatigue.",
        "source": "Medical Textbook",
        "chapter": "Symptoms"
    }
]

points = []
for doc in documents:
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embed(doc["content"]),
            payload=doc
        )
    )

client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)

print("✅ Medical data inserted")

# =========================
# SEARCH QUERY
# =========================
query = "What is diabetes?"

results = client.search(
    collection_name=COLLECTION_NAME,
    query_vector=embed(query),
    limit=5
)

# =========================
# SHOW RESULTS
# =========================
for i, hit in enumerate(results, 1):
    print(f"\n🔹 Result {i}")
    print("Score:", hit.score)
    print("Content:", hit.payload["content"])
    print("Source:", hit.payload.get("source"))
    print("Chapter:", hit.payload.get("chapter"))
