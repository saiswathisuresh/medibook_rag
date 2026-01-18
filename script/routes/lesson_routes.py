from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os, requests
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3"

class LessonRequest(BaseModel):
    lesson_plan_name: str
    topic: str

class LessonResponse(BaseModel):
    lesson_plan_name: str
    content: str

def ask_grok(prompt):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000
    }
    
    try:
        r = requests.post(GROK_URL, headers=headers, json=payload, timeout=60)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")  # First 500 chars
        
        if r.status_code != 200:
            print(f"Error: {r.text}")
            return None
            
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

@router.post("/generate-lesson-plan", response_model=LessonResponse)
async def generate_lesson(req: LessonRequest):
    prompt = f"Create a detailed medical lesson plan on {req.topic}"
    content = ask_grok(prompt)
    if not content:
        raise HTTPException(status_code=500, detail="AI failed")

    return LessonResponse(
        lesson_plan_name=req.lesson_plan_name,
        content=content
    )
