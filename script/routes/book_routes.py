from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from pathlib import Path

router = APIRouter()

print("=" * 50)
print("🚀 book_routes.py loaded successfully!")
print("=" * 50)

# Chunks folder path - medibook/data/chunks
# Go up 2 levels from routes folder to reach medibook root
CHUNKS_FOLDER = Path(__file__).parent.parent.parent / "data" / "chunks"
METADATA_FILE = Path(__file__).parent.parent.parent / "data" / "books_metadata.json"

print(f"📂 CHUNKS_FOLDER: {CHUNKS_FOLDER}")
print(f"📋 METADATA_FILE: {METADATA_FILE}")
print(f"✅ Exists: {CHUNKS_FOLDER.exists()}")
if CHUNKS_FOLDER.exists():
    json_files = list(CHUNKS_FOLDER.glob("*.json"))
    print(f"📄 JSON files found: {len(json_files)}")
    for f in json_files[:3]:  # First 3 files
        print(f"   - {f.name}")
print("=" * 50)

def load_metadata():
    """Load books metadata (chapter/non-chapter info)"""
    try:
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"chapter_books": [], "non_chapter_books": []}
    except:
        return {"chapter_books": [], "non_chapter_books": []}

class Chapter(BaseModel):
    chapter_id: str
    chapter_name: str

class Book(BaseModel):
    book_id: str
    book_name: str
    title: str
    has_chapters: bool
    chapters: List[Chapter] = []

class BooksResponse(BaseModel):
    total_books: int
    books: List[Book]

def load_books_from_chunks():
    """Chunks folder la irunthu books data dynamically load pannum"""
    try:
        if not CHUNKS_FOLDER.exists():
            raise HTTPException(
                status_code=500, 
                detail=f"Chunks folder not found at {CHUNKS_FOLDER}"
            )
        
        # Load metadata
        metadata = load_metadata()
        chapter_books_list = metadata.get("chapter_books", [])
        non_chapter_books_list = metadata.get("non_chapter_books", [])
        
        books = []
        
        # Chunks folder la irukura ella JSON files um read pannu
        for json_file in CHUNKS_FOLDER.glob("*.json"):
            try:
                print(f"\n📖 Reading: {json_file.name}")
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # JSON structure debug
                    if isinstance(data, list) and len(data) > 0:
                        print(f"   Type: List (Chunks format)")
                        print(f"   Total chunks: {len(data)}")
                        
                        # Extract unique book_id, chapter_id, and sections
                        book_ids = set()
                        chapter_ids = set()
                        sections = set()
                        
                        for chunk in data:
                            if isinstance(chunk, dict):
                                if "book_id" in chunk:
                                    book_ids.add(chunk["book_id"])
                                if "chapter_id" in chunk:
                                    chapter_ids.add(chunk["chapter_id"])
                                if "section" in chunk and chunk["section"]:
                                    sections.add(chunk["section"])
                        
                        print(f"   Unique book_ids: {book_ids}")
                        print(f"   Unique chapter_ids: {chapter_ids}")
                        print(f"   Unique sections: {len(sections)}")
                        
                        # Get book info from first chunk
                        if book_ids:
                            book_id = list(book_ids)[0]
                            book_name = json_file.stem.replace("_chunks", "")
                            
                            # Check metadata for chapter/non-chapter
                            has_chapters = book_name in chapter_books_list
                            
                            print(f"   Book: {book_name}")
                            print(f"   Metadata check: {has_chapters}")
                            
                            # Extract chapters only if has_chapters is True
                            chapters_list = []
                            if has_chapters:
                                chapter_data = {}
                                for chunk in data:
                                    if isinstance(chunk, dict):
                                        section_name = chunk.get("section", "General")
                                        ch_id = chunk.get("chapter_id", "default")
                                        key = f"{ch_id}_{section_name}"
                                        
                                        if key not in chapter_data and section_name != "General":
                                            chapter_data[key] = {
                                                "chapter_id": ch_id,
                                                "chapter_name": section_name
                                            }
                                
                                chapters_list = list(chapter_data.values())[:50]
                            
                            # Create book object
                            book = {
                                "book_id": book_id,
                                "book_name": book_name,
                                "title": book_name.replace("_", " ").replace("-", " ").title(),
                                "has_chapters": has_chapters,
                                "chapters": chapters_list
                            }
                            
                            books.append(book)
                            print(f"   ✅ Added: {book['title']} | Chapters: {has_chapters} | Count: {len(chapters_list)}")
                    
                    elif isinstance(data, dict):
                        print(f"   Type: Dictionary")
                        print(f"   Keys: {list(data.keys())[:10]}")
                        # Original dict-based logic (if needed)
                    
                    else:
                        print(f"   ⚠️  Unknown structure: {type(data)}")
                    
            except json.JSONDecodeError as je:
                # Invalid JSON file skip pannu
                print(f"❌ JSON Error in {json_file.name}: {je}")
                continue
            except Exception as e:
                # Other errors skip pannu
                print(f"❌ Error in {json_file.name}: {e}")
                continue
        
        print(f"📚 Total books loaded: {len(books)}")
        return books
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading books: {str(e)}")

@router.get("/books", response_model=BooksResponse)
async def get_all_books(
    filter_type: Optional[str] = Query(None, description="Filter: 'chapter' or 'non-chapter'")
):
    """
    எல்லா books-ஐயும் get பண்ணும் API
    Chunks folder la irunthu dynamically load aagum
    
    Parameters:
    - filter_type: 'chapter' - chapter books மட்டும்
                   'non-chapter' - non-chapter books மட்டும்
                   None - எல்லா books-ம்
    """
    try:
        all_books = load_books_from_chunks()
        filtered_books = all_books
        
        # Filter based on user selection
        if filter_type == "chapter":
            filtered_books = [book for book in all_books if book.get("has_chapters", False)]
        elif filter_type == "non-chapter":
            filtered_books = [book for book in all_books if not book.get("has_chapters", False)]
        
        return BooksResponse(
            total_books=len(filtered_books),
            books=filtered_books
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/books/{book_id}", response_model=Book)
async def get_book_by_id(book_id: str):
    """
    குறிப்பிட்ட book-ன் details get பண்ணும் API
    """
    try:
        all_books = load_books_from_chunks()
        book = next((b for b in all_books if b["book_id"] == book_id), None)
        
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
        
        return book
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/books/name/{book_name}", response_model=Book)
async def get_book_by_name(book_name: str):
    """
    Book name வச்சு book details get பண்ணும் API
    """
    try:
        all_books = load_books_from_chunks()
        book = next((b for b in all_books if b["book_name"] == book_name), None)
        
        if not book:
            raise HTTPException(status_code=404, detail=f"Book '{book_name}' not found")
        
        return book
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/books/{book_id}/chapters", response_model=List[Chapter])
async def get_book_chapters(book_id: str):
    """
    குறிப்பிட்ட book-ன் chapters மட்டும் get பண்ணும் API
    """
    try:
        all_books = load_books_from_chunks()
        book = next((b for b in all_books if b["book_id"] == book_id), None)
        
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
        
        if not book.get("has_chapters", False):
            raise HTTPException(
                status_code=400, 
                detail=f"Book '{book.get('title', book_id)}' does not have chapters"
            )
        
        return book.get("chapters", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/books/stats/summary")
async def get_books_summary():
    """
    Books statistics - எத்தனை chapter books, non-chapter books என்று
    """
    try:
        all_books = load_books_from_chunks()
        chapter_books = [b for b in all_books if b.get("has_chapters", False)]
        non_chapter_books = [b for b in all_books if not b.get("has_chapters", False)]
        
        return {
            "total_books": len(all_books),
            "chapter_books_count": len(chapter_books),
            "non_chapter_books_count": len(non_chapter_books),
            "chapter_books": [
                {"book_id": b["book_id"], "book_name": b["book_name"], "title": b["title"]} 
                for b in chapter_books
            ],
            "non_chapter_books": [
                {"book_id": b["book_id"], "book_name": b["book_name"], "title": b["title"]} 
                for b in non_chapter_books
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/books/debug/chunks-path")
async def debug_chunks_path():
    """
    Debug purpose - chunks folder path check pannum
    """
    return {
        "chunks_folder": str(CHUNKS_FOLDER),
        "exists": CHUNKS_FOLDER.exists(),
        "json_files_count": len(list(CHUNKS_FOLDER.glob("*.json"))) if CHUNKS_FOLDER.exists() else 0,
        "json_files": [f.name for f in CHUNKS_FOLDER.glob("*.json")] if CHUNKS_FOLDER.exists() else []
    }