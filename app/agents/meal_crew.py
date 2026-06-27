# app/agents/meal_crew.py
"""多 Agent 套餐规划：营养师 → 主厨 → 采购 三个角色用 LangGraph 协作完成一次配餐。

与单 Agent 聊天（ai_chef.py）完全独立、互不影响：那条链路线上在跑，这里是新增能力。

为什么用 LangGraph 多节点、而不是 CrewAI/AutoGen：
  - 角色分工 + 状态在节点间显式传递，LangGraph 的 StateGraph 已经表达得很清楚；
  - 零额外依赖、流程可控、可逐节点流式（前端能看到每个 Agent 的产出）；
  - 工程上更透明，出问题好定位。数据量/角色更复杂时再考虑专门框架。

协作流水线（状态机）：
  营养师 nutritionist —— 读健康目标 + 偏好/忌口，定下本次配餐的营养约束；
  主厨   chef        —— 按营养约束 + 本地菜谱检索(RAG)，设计具体菜单；
  采购   procurement —— 把菜单食材去重合并、分类，产出购物清单。
"""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import logging
from typing import TypedDict, List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from app.recipe_rag import search as rag_search
from app.preferences import get_preferences, init_pref_db
from app.fitness import get_daily_targets, init_fitness_db
from app.cache import get_cache, make_key

logger = logging.getLogger(__name__)

# 独立 CLI 运行时（没经过 ai_chef）也要保证依赖的表存在
init_pref_db()
init_fitness_db()


# ==================== State ====================
class CrewState(TypedDict):
    request: str                          # 用户原始需求
    nutrition_brief: str                  # 营养师产出（营养约束/建议）
    menu: List[Dict[str, Any]]            # 主厨产出（菜单）
    retrieved: List[str]                  # 主厨实际参考到的本地菜谱名（透明可见）
    shopping_list: List[Dict[str, Any]]   # 采购产出（分类购物清单）


# ==================== LLM ====================
# 注意：mimo-v2.5 是推理模型，会先消耗 reasoning_tokens 再产出正文。
# max_tokens 必须给足（推理 + 正文都算在内），否则正文会被截断甚至为空。
def _llm(temperature: float = 0.4, max_tokens: int = 4096) -> ChatOpenAI:
    return ChatOpenAI(
        model="mimo-v2.5",
        openai_api_key=os.getenv("MIMO_API_KEY"),
        openai_api_base=os.getenv("MIMO_BASE_URL"),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _try_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def _extract_json(text: str):
    """从模型输出里抠出 JSON（容忍 ```json 围栏与前后说明文字）。失败返回 None。"""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    candidate = (fenced.group(1) if fenced else text).strip()
    # 1) 整体直接解析；2) 退而截取最外层 [..] / {..}
    obj = _try_load(candidate)
    if obj is None:
        for pattern in (r"\[.*\]", r"\{.*\}"):
            m = re.search(pattern, candidate, re.S)
            if m:
                obj = _try_load(m.group(0))
                if obj is not None:
                    break
    return obj


def _coerce_list(obj) -> list:
    """把解析结果归一成数组：是数组直接用；是 {"menu":[...]} 这类包裹则取其中的数组。"""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list):
                return v
    return []


def _invoke_list(sys_msg, human_msg, label: str, base_temp: float, max_tokens: int = 4096) -> list:
    """调用 LLM 并解析出 JSON 数组；解析为空时用 temp=0 再严格重试一次，杜绝偶发空结果。"""
    for temp in (base_temp, 0.0):
        resp = _llm(temperature=temp, max_tokens=max_tokens).invoke([sys_msg, human_msg])
        items = _coerce_list(_extract_json(resp.content))
        if items:
            return items
        logger.warning("%s 解析为空，重试 temp=%s", label, temp)
    return []


# ==================== Node 1：营养师 ====================
def nutritionist_node(state: CrewState) -> Dict[str, Any]:
    targets = get_daily_targets()
    prefs = get_preferences()

    ctx = []
    if targets:
        ctx.append(
            f"用户每日营养目标：热量约 {targets['calories']} kcal、蛋白质 {targets['protein']}g、"
            f"碳水 {targets['carbs']}g、脂肪 {targets['fat']}g（目标：{targets.get('goal', '维持')}）。"
        )
    else:
        ctx.append("用户暂未设置健康档案，按健康均衡的通用标准给建议即可。")
    if prefs:
        ctx.append("用户偏好/忌口：" + "；".join(prefs) + "。配餐必须避开忌口与过敏项。")

    sys = SystemMessage(content=(
        "你是专业营养师。根据用户需求和健康目标，给出本次配餐的营养约束与建议，"
        "包括：热量/蛋白质大致区间、宜多/宜少的食材类型、需要规避的忌口。"
        "只输出 4-6 行要点，简洁、可执行，不要寒暄、不要写菜谱。"
    ))
    human = HumanMessage(content=f"用户需求：{state['request']}\n\n背景信息：\n" + "\n".join(ctx))
    resp = _llm(temperature=0.3, max_tokens=3072).invoke([sys, human])
    brief = (resp.content or "").strip()
    if not brief:
        # 极端兜底：营养师为空时给通用约束，保证下游主厨/采购不受影响
        brief = "本次配餐以均衡健康为原则：优质蛋白为主，搭配复合碳水与蔬菜，少油少盐，规避用户忌口。"
    return {"nutrition_brief": brief}


# ==================== Node 2：主厨 ====================
def chef_node(state: CrewState) -> Dict[str, Any]:
    # RAG：用需求检索本地菜谱作为主厨的设计参考
    try:
        hits = rag_search(state["request"], k=5)
    except Exception as e:
        logger.warning("主厨检索本地菜谱失败：%s", e)
        hits = []
    retrieved = [h.get("name", "") for h in hits]
    candidates = "\n".join(
        f"- {h.get('name')}：{h.get('description', '')}（食材：" +
        "、".join(i.get("name", "") for i in h.get("ingredients", [])) + "）"
        for h in hits
    ) or "（本地菜谱库暂无参考，请基于常识设计）"

    sys = SystemMessage(content=(
        "你是经验丰富的主厨。请严格遵守营养师给出的营养约束，"
        "参考下方本地菜谱候选（可改良、可自创），设计一套 3-4 道菜的菜单。\n"
        "只输出 JSON 数组，每个元素形如："
        '{"name":"菜名","reason":"为何契合营养约束(一句)","ingredients":[{"name":"食材","amount":"用量"}]}'
        "。不要输出 JSON 以外的任何文字。"
    ))
    human = HumanMessage(content=(
        f"用户需求：{state['request']}\n\n"
        f"营养师的约束：\n{state['nutrition_brief']}\n\n"
        f"本地菜谱候选：\n{candidates}"
    ))
    menu = _invoke_list(sys, human, "主厨菜单", base_temp=0.5, max_tokens=4096)
    return {"menu": menu, "retrieved": retrieved}


# ==================== Node 3：采购 ====================
def _combine_amounts(amounts: List[str]) -> str:
    """合并同一食材的多份用量：
    - 全是"数字+相同单位"(如 150g、150g)→ 相加(300g)；
    - 非数字(少许/适量)→ 去重后用 + 连接(少许+少许 → 少许)；
    - 混合 → 去重后 + 连接。"""
    if not amounts:
        return "适量"
    total, unit, numeric = 0.0, None, True
    for a in amounts:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([^\d\s]*)\s*", a)
        if not m:
            numeric = False
            break
        val, u = float(m.group(1)), m.group(2)
        if unit is None:
            unit = u
        elif u != unit:
            numeric = False
            break
        total += val
    if numeric:
        num = int(total) if total == int(total) else round(total, 2)
        return f"{num}{unit}"
    uniq = list(dict.fromkeys(a for a in amounts if a))  # 保序去重
    return " + ".join(uniq) if uniq else "适量"


def _merge_ingredients(menu: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """把各菜的食材按名字合并（确定性逻辑，不靠模型，保证不漏不重）。"""
    merged: "Dict[str, List[str]]" = {}
    for dish in menu:
        for ing in dish.get("ingredients", []):
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            amount = (ing.get("amount") or "").strip()
            merged.setdefault(name, [])
            if amount:
                merged[name].append(amount)
    return [{"name": n, "amount": _combine_amounts(a)} for n, a in merged.items()]


def procurement_node(state: CrewState) -> Dict[str, Any]:
    flat = _merge_ingredients(state.get("menu", []))
    if not flat:
        return {"shopping_list": []}

    items_text = "、".join(f"{i['name']}({i['amount']})" for i in flat)
    sys = SystemMessage(content=(
        "你是采购助手。把下面这份合并后的食材清单，按超市采购动线分类"
        "（如：蔬菜瓜果、肉禽蛋、水产、米面粮油、调味品、其他）。"
        "只输出 JSON 数组，每个元素形如："
        '{"category":"分类名","items":[{"name":"食材","amount":"用量"}]}'
        "。保持食材与用量不变，只做归类。不要输出 JSON 以外的文字。"
    ))
    human = HumanMessage(content=f"合并后的食材清单：{items_text}")
    grouped = _invoke_list(sys, human, "采购清单", base_temp=0.2, max_tokens=3072)
    if not grouped:
        # 分类失败兜底：不分类，整袋给出，保证功能可用
        return {"shopping_list": [{"category": "采购清单", "items": flat}]}

    # 校验：LLM 归类时可能漏写/改名，把没被覆盖的食材补进"其他"，确保不丢项
    covered = {
        (it.get("name") or "").strip()
        for g in grouped
        for it in (g.get("items") or [])
    }
    missing = [i for i in flat if i["name"] not in covered]
    if missing:
        grouped.append({"category": "其他", "items": missing})
    return {"shopping_list": grouped}


# ==================== 构建 Graph ====================
_workflow = StateGraph(CrewState)
_workflow.add_node("nutritionist", nutritionist_node)
_workflow.add_node("chef", chef_node)
_workflow.add_node("procurement", procurement_node)
_workflow.set_entry_point("nutritionist")
_workflow.add_edge("nutritionist", "chef")
_workflow.add_edge("chef", "procurement")
_workflow.add_edge("procurement", END)
_graph = _workflow.compile()


# ==================== 缓存键 ====================
def _cache_key(request: str) -> str:
    targets = get_daily_targets() or {}
    prefs = get_preferences()
    return "mealcrew:" + make_key(
        request,
        json.dumps(targets, ensure_ascii=False, sort_keys=True),
        "|".join(sorted(prefs)),
    )


def _assemble(request: str, state: Dict[str, Any], cached: bool) -> Dict[str, Any]:
    return {
        "request": request,
        "nutrition_brief": state.get("nutrition_brief", ""),
        "menu": state.get("menu", []),
        "retrieved": state.get("retrieved", []),
        "shopping_list": state.get("shopping_list", []),
        "_cached": cached,
    }


# ==================== 对外：一次性结果 ====================
def run_crew(request: str) -> Dict[str, Any]:
    """跑完整流水线，返回结构化结果。相同请求+健康档案+偏好会命中缓存。"""
    cache = get_cache()
    key = _cache_key(request)
    hit = cache.get_json(key)
    if hit:
        hit["_cached"] = True
        return hit
    final = _graph.invoke({"request": request})
    out = _assemble(request, final, cached=False)
    cache.set_json(key, out)
    return out


# ==================== 对外：逐 Agent 流式 ====================
def crew_stream(request: str):
    """逐节点流式产出，便于前端/CLI 看到每个 Agent 的贡献。yield 的是事件 dict。"""
    cache = get_cache()
    key = _cache_key(request)
    hit = cache.get_json(key)
    if hit:
        yield {"type": "cached", "content": "命中缓存，直接返回历史规划"}
        yield {"type": "nutrition", "content": hit.get("nutrition_brief", "")}
        yield {"type": "menu", "content": hit.get("menu", []), "retrieved": hit.get("retrieved", [])}
        yield {"type": "shopping", "content": hit.get("shopping_list", [])}
        hit["_cached"] = True
        yield {"type": "done", "result": hit}
        return

    yield {"type": "start", "content": "🧑‍⚕️ 营养师 → 👨‍🍳 主厨 → 🛒 采购，多 Agent 协作中..."}
    acc: Dict[str, Any] = {}
    # stream_mode="updates"：每个节点跑完推一次它的状态增量，真正逐 Agent 可见
    for chunk in _graph.stream({"request": request}, stream_mode="updates"):
        for node, delta in chunk.items():
            acc.update(delta)
            if node == "nutritionist":
                yield {"type": "nutrition", "content": delta.get("nutrition_brief", "")}
            elif node == "chef":
                yield {"type": "menu", "content": delta.get("menu", []),
                       "retrieved": delta.get("retrieved", [])}
            elif node == "procurement":
                yield {"type": "shopping", "content": delta.get("shopping_list", [])}

    out = _assemble(request, acc, cached=False)
    cache.set_json(key, out)
    yield {"type": "done", "result": out}


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    req = " ".join(sys.argv[1:]) or "我想增肌，帮我规划接下来两天的午晚餐"
    print(f"\n=== 需求：{req} ===\n")
    for ev in crew_stream(req):
        t = ev["type"]
        if t == "start" or t == "cached":
            print(ev["content"], "\n")
        elif t == "nutrition":
            print("🧑‍⚕️ 营养师：")
            print("  " + ev["content"].replace("\n", "\n  "), "\n")
        elif t == "menu":
            print("👨‍🍳 主厨菜单：")
            for d in ev["content"]:
                print(f"  • {d.get('name')} —— {d.get('reason', '')}")
            if ev.get("retrieved"):
                print("  (参考本地菜谱：" + "、".join(ev["retrieved"]) + ")")
            print()
        elif t == "shopping":
            print("🛒 采购清单：")
            for g in ev["content"]:
                items = "、".join(f"{i['name']}({i['amount']})" for i in g.get("items", []))
                print(f"  [{g.get('category')}] {items}")
            print()
        elif t == "done":
            print("（缓存：%s）" % ev["result"]["_cached"])
