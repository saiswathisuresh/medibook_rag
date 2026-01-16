import os
import json
import uuid
import math
import re
from nanoid import generate   # ✅ NEW (only addition)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_DIR = os.path.join(BASE_DIR, "data/structured")
OUT_DIR = os.path.join(BASE_DIR, "data/chunks")
os.makedirs(OUT_DIR, exist_ok=True)

MAX_TOKENS = 700
OVERLAP_TOKENS = 100
BOOK_PARTS = 21          # ✅ one book → 21 nano ids
CHUNKS_PER_PART = 50     # adjust if needed

# -------------------------
# TOKEN ESTIMATE
# -------------------------
def token_len(text):
    return max(1, math.ceil(len(text) / 4))

# -------------------------
# TEXT CLEANER
# -------------------------
def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\S+@\S+", "", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    blacklist = [
        "all rights reserved",
        "no part of this publication",
        "printed and bound",
        "library of congress",
        "isbn",
        "copyright",
        "registered office",
        "fax:",
        "tel.:",
        "published by",
        "editor",
        "prelims"
    ]

    lower = text.lower()
    for b in blacklist:
        if b in lower:
            return ""

    text = re.sub(r"[^A-Za-z0-9.,;:%()\- ]+", "", text)
    return text.strip()

# -------------------------
# CHUNK SPLITTER
# -------------------------
def split_chunks(sentences):
    chunks = []
    current = []
    current_tokens = 0

    for sent in sentences:
        sent = clean_text(sent)
        if len(sent) < 80:
            continue

        t = token_len(sent)

        if current_tokens + t > MAX_TOKENS:
            chunks.append(" ".join(current))

            overlap = []
            overlap_tokens = 0
            for s in reversed(current):
                overlap_tokens += token_len(s)
                overlap.insert(0, s)
                if overlap_tokens >= OVERLAP_TOKENS:
                    break

            current = overlap[:]
            current_tokens = token_len(" ".join(current))

        current.append(sent)
        current_tokens += t

    if current:
        chunks.append(" ".join(current))

    return chunks

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":

    for file in os.listdir(IN_DIR):
        if not file.endswith("_structured.json"):
            continue

        structured = json.load(open(os.path.join(IN_DIR, file), encoding="utf-8"))

        # ✅ generate 21 nano book ids
        book_part_ids = [
            generate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", 21)
            for _ in range(BOOK_PARTS)
        ]

        part_index = 0
        part_chunk_count = 0
        chunks = []

        for chapter in structured.get("chapters", []):
            chapter_id = chapter.get("chapter_id")

            for section in chapter.get("sections", []):
                content = section.get("content", [])
                if len(content) < 5:
                    continue

                section_name = section.get("heading", "General")
                section_chunks = split_chunks(content)

                for text in section_chunks:
                    if token_len(text) < 120:
                        continue

                    chunks.append({
                        "chunk_id": str(uuid.uuid4()),
                        "book_id": book_part_ids[part_index],  # ✅ ONLY CHANGE
                        "chapter_id": chapter_id,
                        "section": section_name,
                        "text": text
                    })

                    part_chunk_count += 1
                    if part_chunk_count >= CHUNKS_PER_PART and part_index < BOOK_PARTS - 1:
                        part_index += 1
                        part_chunk_count = 0

        out_path = os.path.join(OUT_DIR, f"{file.replace('_structured.json','')}_chunks.json")
        json.dump(chunks, open(out_path, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)

        print(f"✅ Clean chunks → nano book ids used ({len(chunks)})")
