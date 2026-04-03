from fastapi import FastAPI
from app.projects.p01_chatbot.router import router as p01_router
from app.projects.p02_streaming.router import router as p02_router
from app.projects.p03_summarizer.router import router as p03_router
# you'll add p02, p03 ... p10 here as you build them

app = FastAPI(
    title="AI Engineering Portfolio",
    description="10 AI projects in one API",
    version="1.0.0"
)

app.include_router(p01_router, prefix="/p01", tags=["01 - Chatbot"])
app.include_router(p02_router, prefix="/p02", tags=["02 - Streaming"])
app.include_router(p03_router, prefix="/p03", tags=["03 - Summarizer"])
# ... uncomment as you build each one

@app.get("/")
def root():
    return {"message": "AI Engineering Portfolio running 🚀", "projects": 10}