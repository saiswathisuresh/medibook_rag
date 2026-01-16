from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import chat_routes, lesson_routes, exam_routes
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Medical Education API",
    version="1.0.0",
    description="Unified API for Chat, Lesson Plans, and Exams"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_routes.router, prefix="/api/chat", tags=["Chat"])
app.include_router(lesson_routes.router, prefix="/api/lesson", tags=["Lesson Plans"])
app.include_router(exam_routes.router, prefix="/api/exam", tags=["Exams"])

@app.get("/")
async def root():
    return {
        "message": "Medical Education API",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
