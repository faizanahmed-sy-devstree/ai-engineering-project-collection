import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from app.core.gemini import get_client


router = APIRouter()
client = get_client()

class StreamRequest(BaseModel): 
    message: str


@router.post("/stream")
async def stream_chat(request: StreamRequest):
    """
    This endpoint uses an Async Generator to yield chunks of text 
    as they arrive from Gemini, formatted as Server-Sent Events (SSE).
    """
    async def event_generator():
        # 1. Use the new SDK's async client (.aio) and stream method
        response = await client.aio.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=request.message
        )
        
        # 2. Iterate over the chunks as they arrive over the network
        async for chunk in response:
            if chunk.text:
                # 3. Format as SSE: data: <string>\n\n
                # We JSON encode the text to safely handle newlines and quotes
                data = json.dumps({"text": chunk.text})
                yield f"data: {data}\n\n"
                
        # Optional: Send a specific event to tell the frontend we are done
        yield "data: [DONE]\n\n"

    # 4. Return FastAPI's StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chat-ui", response_class=HTMLResponse)
async def get_chat_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>P02: Streaming Chat</title>
        <style>
            body { font-family: monospace; background: #0a0a0f; color: #e2e8f0; padding: 40px; max-width: 800px; margin: 0 auto; }
            #chat-box { background: #111118; border: 1px solid #1e1e2e; padding: 20px; border-radius: 8px; min-height: 200px; margin-bottom: 20px; white-space: pre-wrap; line-height: 1.5; }
            input { width: 75%; padding: 12px; background: #111118; border: 1px solid #7c3aed; color: white; border-radius: 4px; }
            button { padding: 12px 24px; background: #7c3aed; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
            button:hover { background: #6d28d9; }
            .token { opacity: 0; animation: fadeIn 0.3s forwards; }
            @keyframes fadeIn { to { opacity: 1; } }
        </style>
    </head>
    <body>
        <h2>Project 2: Streaming Chat ⚡</h2>
        <div id="chat-box"></div>
        <div style="display: flex; gap: 10px;">
            <input type="text" id="msg-input" placeholder="Ask me to write a poem..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()">Send</button>
        </div>

        <script>
            async function send() {
                const input = document.getElementById('msg-input');
                const chatBox = document.getElementById('chat-box');
                const msg = input.value;
                if (!msg) return;
                
                // Clear input and add user message
                input.value = '';
                chatBox.innerHTML += `<div style="color: #67e8f9; margin-bottom: 10px;">> ${msg}</div>`;
                
                // Create a container for the AI's streaming response
                const aiResponseDiv = document.createElement('div');
                aiResponseDiv.style.color = '#a78bfa';
                aiResponseDiv.style.marginBottom = '20px';
                chatBox.appendChild(aiResponseDiv);

                try {
                    // Fetch the stream (POST request)
                    const response = await fetch('/p02/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: msg })
                    });

                    // Set up the reader to read the stream piece by piece
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        // Decode the chunk (Uint8Array to String)
                        const chunk = decoder.decode(value, { stream: true });
                        
                        // Parse the SSE "data: ..." format
                        const lines = chunk.split('\\n');
                        for (let line of lines) {
                            if (line.startsWith('data: ')) {
                                const dataStr = line.slice(6);
                                if (dataStr === '[DONE]') return; // Stream finished
                                
                                try {
                                    const parsed = JSON.parse(dataStr);
                                    // Append text to the div
                                    aiResponseDiv.innerHTML += `<span class="token">${parsed.text}</span>`;
                                } catch (e) { console.error("Error parsing JSON chunk", e); }
                            }
                        }
                    }
                } catch (err) {
                    console.error("Stream failed", err);
                    aiResponseDiv.innerHTML += `<br><span style="color: red;">Error connecting to stream.</span>`;
                }
            }
        </script>
    </body>
    </html>
    """