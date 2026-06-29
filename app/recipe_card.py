# app/recipe_card.py
"""按菜名产出一张完整菜谱卡（RecipeData 形状），供前端「点击配餐里的菜品看做法」。

策略（先检索、后生成，复用项目的 RAG 主题）：
  1) 用 RAG 在本地菜谱库检索菜名；命中同名菜谱 → 直接返回真实菜谱(零 LLM、即时)；
  2) 没有同名 → 让 LLM 参考检索到的本地菜谱「现编」一张同结构卡片(保证完整可渲染)。
结果带缓存(app/cache.py)，重复点同一道菜瞬时返回。

与单 Agent 聊天、多 Agent 配餐都解耦：这是新增能力，默认行为不受影响。
"""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import time
import logging
from typing import Dict, Any, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.recipe_rag import search as rag_search, add_generated_recipe
from app.cache import get_cache, make_key

logger = logging.getLogger(__name__)

# RecipeData 关心的字段（与前端 types/chat.ts 对齐；本地菜谱多出的 attrs/_score 会被剔除）
_RECIPE_KEYS = ("name", "description", "difficulty", "cookingTime",
                "servings", "ingredients", "steps", "tips", "tags", "nutrition")
_DIFFICULTY = {"简单", "中等", "复杂"}


# ==================== LLM ====================
def _llm(temperature: float = 0.4, max_tokens: int = 4096, streaming: bool = False) -> ChatOpenAI:
    # mimo-v2.5 是推理模型，max_tokens 要给足(推理+正文都算)，否则正文截断/为空
    return ChatOpenAI(
        model="mimo-v2.5",
        openai_api_key=os.getenv("MIMO_API_KEY"),
        openai_api_base=os.getenv("MIMO_BASE_URL"),
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def _extract_json(text: str):
    """从模型输出里抠出 JSON 对象（容忍 ```json 围栏与前后说明文字）。"""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    candidate = (fenced.group(1) if fenced else text).strip()
    try:
        return json.loads(candidate)
    except Exception:
        pass
    m = re.search(r"\{.*\}", candidate, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# ==================== 归一化/兜底 ====================
def _norm(s: str) -> str:
    return "".join((s or "").split()).lower()


def _to_int(v: Any, default: int) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"\d+", str(v or ""))
    return int(m.group(0)) if m else default


def _to_num(v: Any, default: float = 0) -> float:
    if isinstance(v, (int, float)):
        return v
    m = re.search(r"\d+(?:\.\d+)?", str(v or ""))
    return float(m.group(0)) if m else default


def _coerce_ings(raw: Any, fallback: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for it in (raw or []):
        if not isinstance(it, dict):
            continue
        name = (it.get("name") or "").strip()
        if not name:
            continue
        item = {"name": name, "amount": (it.get("amount") or "适量").strip()}
        if it.get("emoji"):
            item["emoji"] = it["emoji"]
        out.append(item)
    if out:
        return out
    # LLM 没给食材 → 回退用配餐里那道菜的食材，至少不空
    return [
        {"name": (i.get("name") or "").strip(), "amount": (i.get("amount") or "适量").strip()}
        for i in (fallback or []) if (i.get("name") or "").strip()
    ]


def _coerce_recipe(obj: Any, name: str, ingredients: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """把 LLM 产出归一成前端可直接渲染的 RecipeData，缺字段给安全默认值。"""
    if not isinstance(obj, dict):
        obj = {}
    diff = (obj.get("difficulty") or "").strip()
    out: Dict[str, Any] = {
        "name": (obj.get("name") or name or "菜谱").strip(),
        "description": (obj.get("description") or "").strip(),
        "difficulty": diff if diff in _DIFFICULTY else "中等",
        "cookingTime": str(obj.get("cookingTime") or "约30分钟").strip(),
        "servings": _to_int(obj.get("servings"), 2),
        "ingredients": _coerce_ings(obj.get("ingredients"), ingredients),
        "steps": [str(s).strip() for s in (obj.get("steps") or []) if str(s).strip()],
    }
    if obj.get("tips"):
        out["tips"] = str(obj["tips"]).strip()
    if obj.get("tags"):
        out["tags"] = [str(t).strip() for t in obj["tags"] if str(t).strip()][:4]
    if isinstance(obj.get("nutrition"), dict):
        n = obj["nutrition"]
        out["nutrition"] = {k: _to_num(n.get(k), 0) for k in ("calories", "protein", "carbs", "fat")}
    if not out["steps"]:
        out["steps"] = ["暂未生成详细步骤，可在对话里向 AI 私厨追问这道菜的具体做法。"]
    return out


def _clean_local(r: Dict[str, Any]) -> Dict[str, Any]:
    """本地命中的真实菜谱：只取 RecipeData 字段（剔除 _score / attrs）。"""
    return {k: r[k] for k in _RECIPE_KEYS if k in r}


def _pick_local(name: str, hits: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """检索结果里若有与菜名完全同名、且带步骤的真实菜谱，直接用它（零 LLM）。"""
    target = _norm(name)
    for h in hits:
        if _norm(h.get("name", "")) == target and h.get("steps"):
            return h
    return None


# ==================== Prompt ====================
def _build_messages(name: str, ingredients: Optional[List[Dict[str, Any]]],
                    notes: Optional[str], hits: List[Dict[str, Any]]):
    ref = "\n".join(
        f"- {h.get('name')}（难度{h.get('difficulty','')}/{h.get('cookingTime','')}）："
        f"{h.get('description','')}；食材：" +
        "、".join(i.get("name", "") for i in h.get("ingredients", []))
        for h in hits
    ) or "（本地菜谱库暂无相近参考，请基于常识设计）"

    sys = SystemMessage(content=(
        "你是经验丰富的主厨。请为指定菜名输出一张【完整、可照做】的菜谱卡。\n"
        "严格只输出 JSON 对象，字段如下（不要输出 JSON 以外任何文字）：\n"
        '{"name":"菜名","description":"一句简短描述","difficulty":"简单|中等|复杂",'
        '"cookingTime":"如 20分钟","servings":2,'
        '"ingredients":[{"name":"食材","amount":"用量","emoji":"对应emoji"}],'
        '"steps":["步骤1","步骤2","..."],"tips":"一条小贴士","tags":["标签"],'
        '"nutrition":{"calories":数字,"protein":数字,"carbs":数字,"fat":数字}}\n'
        "要求：difficulty 必须是 简单/中等/复杂 三选一；每个食材配一个贴切 emoji；"
        "steps 给 3-6 步、清晰可操作；nutrition 为每份的大致估算。"
    ))
    extra = []
    if ingredients:
        extra.append("尽量包含这些食材：" + "、".join(
            f"{i.get('name')}{('('+i.get('amount')+')') if i.get('amount') else ''}"
            for i in ingredients if i.get("name")))
    if notes:
        extra.append("这道菜在本次配餐中的定位：" + notes)
    human = HumanMessage(content=(
        f"菜名：{name}\n"
        + ("\n".join(extra) + "\n" if extra else "")
        + f"\n可参考的本地菜谱：\n{ref}"
    ))
    return sys, human


# ==================== 自进化：AI 菜谱回流入库 ====================
def _is_quality(recipe: Dict[str, Any]) -> bool:
    """回流质量门槛：字段完整、步骤够、非兜底占位，才允许进库，避免污染检索库。"""
    if not (recipe.get("name") or "").strip():
        return False
    steps = recipe.get("steps") or []
    if len(steps) < 2:
        return False
    if any("暂未生成详细步骤" in str(s) for s in steps):  # 拒绝兜底占位步骤
        return False
    if len(recipe.get("ingredients") or []) < 2:
        return False
    return True


def ingest_recipe(recipe: Dict[str, Any], source: str = "user",
                  hits: Optional[List[Dict[str, Any]]] = None) -> bool:
    """把一条完整菜谱回流进本地库（统一入口，best-effort，绝不抛错影响调用方）。
    三道关：质量门槛 → 近似重复(与库中已有高度相似不入) → 同名去重(在 add 里)。
    source 记录来源做 provenance：'ai'(配餐现编) / 'favorite'(对话收藏) / 'log'(对话记录)。
    hits 传入则复用(省一次检索)；不传则自己检索一次做近似重复判断。
    RECIPE_WRITEBACK=0 可整体关闭。返回是否真的写入。"""
    if os.getenv("RECIPE_WRITEBACK", "1") == "0":
        return False
    try:
        if not _is_quality(recipe):
            return False
        name = (recipe.get("name") or "").strip()
        if hits is None:
            try:
                hits = rag_search(name, k=1)
            except Exception:
                hits = []
        # 近似重复：库里已有高度相似的菜（多半是同一道菜换个名字）→ 不重复入库
        if hits and max((h.get("_score") or 0) for h in hits) >= 0.95:
            return False
        persist = {k: recipe[k] for k in _RECIPE_KEYS if k in recipe}
        persist["source"] = source                # 标注来源，便于日后审核/清理/晋升
        persist["createdAt"] = int(time.time())
        if add_generated_recipe(persist):
            logger.info("菜谱已回流入库(%s)：%s", source, persist.get("name"))
            return True
    except Exception as e:
        logger.warning("菜谱回流入库失败：%s", e)
    return False


def _maybe_write_back(recipe: Dict[str, Any], hits: List[Dict[str, Any]]) -> None:
    """配餐现编路径的回流：复用已检索的 hits，标来源 ai。"""
    ingest_recipe(recipe, source="ai", hits=hits)


# ==================== 对外：流式（带 token 心跳，规避网关在 LLM 思考期间判超时）====================
def stream_recipe(name: str, ingredients: Optional[List[Dict[str, Any]]] = None,
                  notes: Optional[str] = None):
    """yield 事件 dict：
       {"type":"progress"} —— 生成中的心跳(前端忽略，仅为保活连接)；
       {"type":"recipe","recipe":{...}} —— 最终完整菜谱卡；
       {"type":"error","content":"..."} —— 失败。"""
    name = (name or "").strip()
    if not name:
        yield {"type": "error", "content": "缺少菜名"}
        return

    cache = get_cache()
    key = "recipe:" + make_key(name, json.dumps(ingredients or [], ensure_ascii=False, sort_keys=True))
    hit = cache.get_json(key)
    if hit:
        hit["_cached"] = True
        yield {"type": "recipe", "recipe": hit}
        return

    # 先检索本地库
    try:
        hits = rag_search(name, k=3)
    except Exception as e:
        logger.warning("菜谱卡检索本地菜谱失败：%s", e)
        hits = []

    local = _pick_local(name, hits)
    if local:
        out = _clean_local(local)
        out["_source"] = "local"   # 命中本地真实菜谱
        out["_cached"] = False
        cache.set_json(key, out)
        yield {"type": "recipe", "recipe": out}
        return

    # 本地没有同名 → LLM 现编（边流式边发心跳，攒齐再解析，避免暴露半截 JSON）
    sys, human = _build_messages(name, ingredients, notes, hits)
    content = ""
    try:
        for chunk in _llm(temperature=0.4, streaming=True).stream([sys, human]):
            if getattr(chunk, "content", ""):
                content += chunk.content
                yield {"type": "progress"}
    except Exception as e:
        logger.warning("菜谱卡流式生成失败，转一次性重试：%s", e)
        content = ""

    obj = _extract_json(content)
    if not isinstance(obj, dict) or not obj.get("steps"):
        # 兜底：temp=0 严格再来一次（一次性，不流式）
        resp = _llm(temperature=0.0).invoke([sys, human])
        obj = _extract_json(resp.content)

    recipe = _coerce_recipe(obj, name, ingredients)
    recipe["_source"] = "ai"       # AI 生成
    recipe["_cached"] = False
    cache.set_json(key, recipe)
    # 自进化：把这条 AI 菜谱回流进本地库（带质量门槛/去重），下次同名直接走本地命中
    _maybe_write_back(recipe, hits)
    yield {"type": "recipe", "recipe": recipe}


# ==================== 对外：一次性（CLI/测试用）====================
def generate_recipe(name: str, ingredients: Optional[List[Dict[str, Any]]] = None,
                    notes: Optional[str] = None) -> Dict[str, Any]:
    recipe: Dict[str, Any] = {}
    for ev in stream_recipe(name, ingredients, notes):
        if ev["type"] == "recipe":
            recipe = ev["recipe"]
        elif ev["type"] == "error":
            raise RuntimeError(ev["content"])
    return recipe


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    dish = " ".join(sys.argv[1:]) or "西红柿炒蛋"
    r = generate_recipe(dish)
    print(f"来源：{r.get('_source')}  缓存：{r.get('_cached')}")
    print(json.dumps(r, ensure_ascii=False, indent=2))
