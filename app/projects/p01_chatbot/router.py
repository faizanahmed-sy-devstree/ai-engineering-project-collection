# app/projects/p01_chatbot/router.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.gemini import get_client

router = APIRouter()

# Get our new Gemini Client
client = get_client()

# We use the SDK's built-in Chat object to easily maintain conversation history in memory
# We also inject a system prompt to give the AI a persona
chat_session = client.chats.create(
    model="gemini-2.5-flash-lite",
    config={
        "system_instruction": "You are a helpful, expert AI Engineer mentoring a frontend developer. Keep your answers concise and encouraging."
    }
)

# Pydantic model for incoming requests
class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    # Send the user's message to the chat session (this automatically handles history!)
    response = chat_session.send_message(request.message)
    
    return {
        "user_message": request.message,
        "bot_reply": response.text
    }