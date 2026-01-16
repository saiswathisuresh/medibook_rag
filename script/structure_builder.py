import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_DIR = os.path.join(BASE_DIR, "data", "pages")
OUT_DIR = os.path.join(BASE_DIR, "data", "structured")
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------
# HEADING DETECTOR
# -------------------------
def is_heading(line):
    line = line.strip()

    if len(line) < 5 or len(line) > 120:
        return False

    # CHAPTER headings
    if re.match(r"(chapter|CHAPTER)\s+\d+", line):
        return True

    # Numeric headings: 1 Introduction, 2.3 Diagnosis
    if re.match(r"\d+(\.\d+)*\s+[A-Za-z]", line):
        return True

    # Uppercase titles
    if line.isupper():
        return True

    return False


# -------------------------
# SENTENCE SPLITTER
# -------------------------
def split_sentences(text):
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if len(s.strip()) > 30]


# -------------------------
# STRUCTURE BUILDER
# -------------------------
def build_structure(pages):

    chapters = []

    # Always create first chapter
    current_chapter = {
        "chapter_id": "AUTO_CH_01",
        "chapter_title": "Auto Chapter 1",
        "sections": [],
        "page_start": pages[0]["page_no"]
    }

    chapter_index = 1
    current_section = None

    for page in pages:
        page_no = page["page_no"]
        lines = page["text"].split("\n")

        for line in lines:
            line = line.strip()

            if len(line) < 15:
                continue

            # CHAPTER detection
            if re.match(r"(chapter|CHAPTER)\s+\d+", line):
                current_chapter["page_end"] = page_no
                chapters.append(current_chapter)

                chapter_index += 1
                current_chapter = {
                    "chapter_id": f"AUTO_CH_{chapter_index:02}",
                    "chapter_title": line,
                    "sections": [],
                    "page_start": page_no
                }
                current_section = None
                continue

            # Section heading
            if is_heading(line):
                current_section = {
                    "heading": line,
                    "content": [],
                    "page_start": page_no
                }
                current_chapter["sections"].append(current_section)
                continue

            # Normal text
            sentences = split_sentences(line)
            if not sentences:
                continue

            if not current_section:
                current_section = {
                    "heading": "General",
                    "content": [],
                    "page_start": page_no
                }
                current_chapter["sections"].append(current_section)

            current_section["content"].extend(sentences)

    current_chapter["page_end"] = pages[-1]["page_no"]
    chapters.append(current_chapter)

    return chapters


# -------------------------
# RUN FOR ALL BOOKS
# -------------------------
if __name__ == "__main__":

    for file in os.listdir(IN_DIR):
        if not file.endswith("_pages.json"):
            continue

        book_id = file.replace("_pages.json", "")
        pages = json.load(open(os.path.join(IN_DIR, file), encoding="utf-8"))

        chapters = build_structure(pages)

        structured = {
            "book_id": book_id,
            "chapters": chapters
        }

        out_path = os.path.join(OUT_DIR, f"{book_id}_structured.json")
        json.dump(structured, open(out_path, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)

        print(f"✅ Structured → {book_id} | Chapters: {len(chapters)}")
