# api/server.py
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Any, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.ai_chef import chat_stream
from app.preferences import get_preferences, add_preference, remove_preference
from app.fitness import get_profile, save_profile, get_daily_targets
from app.modes import get_mode, set_mode, list_modes
from app.food_log import get_day_summary, add_entry, delete_entry

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
    mode: Optional[str] = None       # 该对话所属模式(每对话独立)，不传则用全局


class PreferenceRequest(BaseModel):
    preference: str


class FitnessProfileRequest(BaseModel):
    gender: str          # 男 / 女
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str  # 久坐/轻度/中度/高度/极高
    goal: str            # 减脂/维持/增肌
    target_weight_kg: Optional[float] = None  # 目标体重（减脂/增肌用于算周期）


class ModeRequest(BaseModel):
    mode: str            # gourmet / fitness / ...


class FoodEntryRequest(BaseModel):
    name: str
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    date: Optional[str] = None  # 默认今天


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = [msg.model_dump() for msg in request.messages]

    def event_stream():
        try:
            for chunk in chat_stream(messages, thread_id=request.thread_id, mode=request.mode):
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


@app.get("/api/fitness/profile")
async def fitness_profile():
    return {"profile": get_profile(), "targets": get_daily_targets()}


@app.post("/api/fitness/profile")
async def update_fitness_profile(req: FitnessProfileRequest):
    save_profile(req.gender, req.age, req.height_cm, req.weight_kg,
                 req.activity_level, req.goal, req.target_weight_kg)
    return {"profile": get_profile(), "targets": get_daily_targets()}


@app.get("/api/mode")
async def read_mode():
    return {"mode": get_mode(), "modes": list_modes()}


@app.post("/api/mode")
async def update_mode(req: ModeRequest):
    set_mode(req.mode)
    return {"mode": get_mode(), "modes": list_modes()}


@app.get("/api/food-log")
async def read_food_log(date: Optional[str] = None):
    return get_day_summary(date)


@app.post("/api/food-log")
async def create_food_entry(req: FoodEntryRequest):
    add_entry(req.name, req.calories, req.protein, req.carbs, req.fat, req.date)
    return get_day_summary(req.date)


@app.delete("/api/food-log/{entry_id}")
async def remove_food_entry(entry_id: int):
    delete_entry(entry_id)
    return get_day_summary()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ==================== 伺服前端（生产：单容器同源部署）====================
# 若存在已构建的 React 产物（frontend/dist），由本服务同源伺服：
#   - /api/* 路由在上方已注册，优先匹配；
#   - 其余路径交给 StaticFiles，html=True 时 "/" 返回 index.html（单页应用）。
# 本地用 Vite(5173) 开发时没有 dist，这里自动跳过，不影响联调。
_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
