import fitz
import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data/pdfs")
OUT_DIR = os.path.join(BASE_DIR, "data/pages")
os.makedirs(OUT_DIR, exist_ok=True)

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_pdf(pdf_path):
    book_id = os.path.splitext(os.path.basename(pdf_path))[0]
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text()
        if text:
            pages.append({
                "page_no": i + 1,
                "text": clean(text)
            })

    out = os.path.join(OUT_DIR, f"{book_id}_pages.json")
    json.dump(pages, open(out, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print(f"✅ Pages extracted → {book_id}")

if __name__ == "__main__":
    for pdf in os.listdir(PDF_DIR):
        if pdf.lower().endswith(".pdf"):
            extract_pdf(os.path.join(PDF_DIR, pdf))
