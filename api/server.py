# api/server.py
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Any, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.ai_chef import chat_stream
from app.preferences import get_preferences, add_preference, remove_preference

app = FastAPI(title="AI Personal Chef API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: Any


class ChatRequest(BaseModel):
    messages: List[Message]
    thread_id: Optional[str] = None  # 对话记忆线程：同一对话用同一个 id，后端按它记住历史


class PreferenceRequest(BaseModel):
    preference: str


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = [msg.model_dump() for msg in request.messages]

    def event_stream():
        try:
            for chunk in chat_stream(messages, thread_id=request.thread_id):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/preferences")
async def list_preferences():
    return {"preferences": get_preferences()}


@app.post("/api/preferences")
async def create_preference(req: PreferenceRequest):
    add_preference(req.preference)
    return {"preferences": get_preferences()}


@app.delete("/api/preferences")
async def delete_preference(req: PreferenceRequest):
    remove_preference(req.preference)
    return {"preferences": get_preferences()}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
