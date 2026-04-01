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
    # Notice the 'r' before the quotes! This makes it a Python raw string, 
    # preventing it from messing with our Javascript escape sequences.
    return r"""
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
            <input type="text" id="msg-input" placeholder="Ask me to write a poem..." onkeypress="if(event.key === 'Enter') sendMsg()">
            <button onclick="sendMsg()">Send</button>
        </div>

        <script>
            async function sendMsg() {
                const input = document.getElementById('msg-input');
                const chatBox = document.getElementById('chat-box');
                const msg = input.value.trim();
                if (!msg) return;
                
                input.value = '';
                chatBox.innerHTML += `<div style="color: #67e8f9; margin-bottom: 10px;">> ${msg}</div>`;
                
                const aiResponseDiv = document.createElement('div');
                aiResponseDiv.style.color = '#a78bfa';
                aiResponseDiv.style.marginBottom = '20px';
                chatBox.appendChild(aiResponseDiv);

                try {
                    const response = await fetch('/p02/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: msg })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        
                        // Using JS Regex (/\n\n/) avoids Python string escaping issues entirely!
                        const events = buffer.split(/\n\n/);
                        
                        buffer = events.pop(); 

                        for (let event of events) {
                            if (event.startsWith('data: ')) {
                                const dataStr = event.slice(6);
                                if (dataStr === '[DONE]') return;
                                
                                try {
                                    const parsed = JSON.parse(dataStr);
                                    
                                    const span = document.createElement('span');
                                    span.className = 'token';
                                    span.textContent = parsed.text;
                                    
                                    aiResponseDiv.appendChild(span);
                                    
                                } catch (e) { 
                                    console.error("Error parsing JSON chunk", e, "Data:", dataStr); 
                                }
                            }
                        }
                    }
                } catch (err) {
                    console.error("Stream failed", err);
                    aiResponseDiv.appendChild(document.createElement('br'));
                    const errSpan = document.createElement('span');
                    errSpan.style.color = '#ef4444';
                    errSpan.textContent = "Error connecting to stream.";
                    aiResponseDiv.appendChild(errSpan);
                }
            }
        </script>
    </body>
    </html>
 """