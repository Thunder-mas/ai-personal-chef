# app/agents/ai_chef.py
from dotenv import load_dotenv
load_dotenv()

import os
import json
import logging
import uuid
import sqlite3
from pathlib import Path
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from app.preferences import add_preference, remove_preference, get_preferences, init_pref_db
from app.recipe_rag import search as rag_search
from app.fitness import get_daily_targets, init_fitness_db
from app.modes import get_mode_config, init_mode_db

logger = logging.getLogger(__name__)

# 确保偏好表、健身档案表、模式设置表存在
init_pref_db()
init_fitness_db()
init_mode_db()

# ==================== 1. 定义 State ====================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ==================== 2. 定义系统提示 ====================
system_prompt = """你是私人厨师。根据用户食材推荐菜谱。

## 检索优先级
- 推荐菜谱时，先调用 search_local_recipes 从本地菜谱库按语义检索；命中合适的就基于它来回答（可直接用返回的食材与步骤填充下方 recipe 卡片）。
- 只有本地库没有合适结果时，才用 search_recipe 联网搜索。

## 菜谱格式（必须严格遵守）

推荐菜谱时，用以下格式返回（前端会渲染为卡片）：

```recipe
{"name":"菜名","description":"简短描述","difficulty":"简单","cookingTime":"20分钟","servings":2,"ingredients":[{"name":"食材","amount":"用量","emoji":"图标"}],"steps":["步骤1","步骤2"],"tips":"小贴士","tags":["标签"]}
```

规则：
- 必须是完整合法的单行JSON，包含所有字段
- difficulty只能是"简单""中等""复杂"
- JSON前后可加简短说明（不超过2句话）

## 一周食谱规划格式

当用户要求"规划一周食谱/每周菜单/安排一周吃什么"等，用以下格式返回（前端渲染为周计划卡片）：

```mealplan
{"title":"本周食谱","days":[{"day":"周一","meals":[{"slot":"早餐","name":"菜名","brief":"一句话简述","ingredients":[{"name":"食材","amount":"用量","emoji":"图标"}]},{"slot":"午餐","name":"菜名","brief":"简述","ingredients":[...]},{"slot":"晚餐","name":"菜名","brief":"简述","ingredients":[...]}]}]}
```

规则：
- days 必须是完整的7天（周一到周日）
- 每天必须包含早餐、午餐、晚餐三餐，每餐的 slot 字段只能是"早餐""午餐""晚餐"
- 每餐都要带 ingredients（食材名+用量），方便生成购物清单
- 食材精简，整体必须是合法的单行JSON

## 偏好记忆
- 用户提到口味偏好、忌口、过敏、不吃的食材时，调用 save_preference 工具逐条记录（如"不吃香菜"、"对花生过敏"、"喜欢清淡"），然后回复"已记住"。
- 用户说不再需要某条偏好时，调用 forget_preference 删除。
- 推荐菜谱时，必须避开用户的忌口与过敏项，并尽量贴合口味偏好。

其他：用户说"收藏"就回复"已收藏"。"""

# ==================== 3. 定义 Tools ====================
from langchain_tavily import TavilySearch

_tavily_search = TavilySearch(
    max_results=3,
    topic='general',
    tavily_api_key=os.getenv('TAVILY_API_KEY')
)

@tool
def search_local_recipes(query: str) -> str:
    """从本地菜谱知识库按语义检索最相关的菜谱（首选工具）。
    输入用户的食材或需求（如"番茄鸡蛋""想吃辣的下饭菜""清淡的菜"），
    返回库中匹配的菜谱（含食材、步骤等结构化信息）。库里有合适的就别再联网搜。"""
    try:
        hits = rag_search(query, k=3)
    except Exception as e:
        # embedding 模型加载/网络失败时不拖垮对话，让 agent 退回联网搜索
        logger.warning("本地菜谱检索失败: %s", e)
        return "本地菜谱库暂时不可用，请改用 search_recipe 联网搜索。"
    if not hits:
        return "本地菜谱库没有相关结果。"
    # 去掉内部的相似度分，避免被写进给用户的菜谱 JSON
    clean = [{k: v for k, v in r.items() if k != "_score"} for r in hits]
    return json.dumps(clean, ensure_ascii=False)


@tool
def search_recipe(query: str) -> str:
    """联网搜索菜谱（本地知识库没有合适结果时再用）。"""
    result = _tavily_search.invoke(query)
    return str(result)

@tool
def save_preference(preference: str) -> str:
    """记录用户的饮食偏好、忌口、过敏或不吃的食材。每条单独记录，如"不吃香菜""对花生过敏""喜欢清淡"。"""
    add_preference(preference)
    return f"已记住：{preference}"

@tool
def forget_preference(preference: str) -> str:
    """删除之前记录的某条用户偏好。"""
    remove_preference(preference)
    return f"已删除偏好：{preference}"

# 工具列表（本地知识库检索放最前，优先级最高）
tools = [search_local_recipes, search_recipe, save_preference, forget_preference]

# ==================== 4. 定义模型 ====================
model = ChatOpenAI(
    model="mimo-v2.5",
    openai_api_key=os.getenv('MIMO_API_KEY'),
    openai_api_base=os.getenv('MIMO_BASE_URL'),
    max_tokens=4096,
    streaming=True,
).bind_tools(tools)

# ==================== 5. 定义 Nodes ====================
def _build_system_prompt() -> str:
    """按 当前模式 + 用户偏好 +（健身模式下）每日宏量目标，动态拼系统提示。"""
    prompt = system_prompt

    # 偏好：所有模式都遵守
    prefs = get_preferences()
    if prefs:
        pref_lines = "\n".join(f"- {p}" for p in prefs)
        prompt += (
            "\n\n## 用户偏好（必须遵守）\n"
            + pref_lines
            + "\n推荐菜谱时务必避开以上忌口/过敏项，并尽量贴合口味偏好。"
        )

    # 当前模式的人设/行为
    mode_cfg = get_mode_config()
    prompt += "\n\n" + mode_cfg["prompt"]

    # 仅健身类模式且已设档案 → 注入具体的每日营养计划
    if mode_cfg.get("uses_fitness"):
        targets = get_daily_targets()
        if targets:
            plan = f"维持热量约 {targets['maintenance']} kcal"
            if targets["daily_adjust"] != 0:
                kind = "缺口" if targets["daily_adjust"] < 0 else "盈余"
                plan += f"，每日{kind} {abs(targets['daily_adjust'])} kcal"
            plan += f"，目标 {targets['calories']} kcal/天"
            if targets.get("weeks_to_goal") and targets.get("target_weight"):
                plan += (
                    f"；按每周约 {targets['weekly_rate_kg']}kg 的健康速度，"
                    f"预计 {targets['weeks_to_goal']} 周达 {targets['target_weight']}kg"
                )
            prompt += (
                "\n\n## 每日营养目标（必须贴合）\n"
                f"- 目标：{targets['goal']}（{plan}）\n"
                f"- 每日：热量 {targets['calories']} kcal、蛋白质 {targets['protein']}g、"
                f"碳水 {targets['carbs']}g、脂肪 {targets['fat']}g\n"
                "- 推荐时贴合以上热量与蛋白，并简要说明这道菜如何契合该计划；"
                "菜谱的 nutrition 营养值要按实际食材与份量合理估算，不要瞎写。"
            )

    return prompt

def agent_node(state: AgentState):
    """AI 模型思考并决定是否调用工具"""
    messages = state["messages"]
    system_message = SystemMessage(content=_build_system_prompt())
    response = model.invoke([system_message] + messages)

    # 调试信息
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc.name if hasattr(tc, 'name') else str(tc) for tc in response.tool_calls]
        logger.debug("AI 决定调用工具: %s", tool_names)
    else:
        logger.debug("AI 直接回复，不调用工具")

    return {"messages": [response]}

# 节点2：调用工具
tool_node = ToolNode(tools)

# 包装 tool_node 添加调试信息
def tool_node_with_debug(state: AgentState):
    """调用工具并添加调试信息"""
    logger.debug("正在调用工具...")
    result = tool_node.invoke(state)
    logger.debug("工具调用完成")
    return result

# ==================== 6. 定义 Conditions ====================
def should_use_tools(state: AgentState):
    """判断是否需要调用工具"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# ==================== 7. 构建 Graph ====================
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node_with_debug)

# 设置起点
workflow.set_entry_point("agent")

# 添加边
workflow.add_conditional_edges(
    "agent",
    should_use_tools,
    {
        "tools": "tools",
        END: END
    }
)

# 工具调用后回到 agent
workflow.add_edge("tools", "agent")

# ==================== 7.5 持久化记忆（checkpointer）====================
# SqliteSaver 把每个 thread_id 的对话状态（messages 等）存进 SQLite。
# 这样后端自己就"记得"整段对话，前端不必每次重发全量历史。
# check_same_thread=False：FastAPI 在线程池里跑同步生成器，需允许跨线程共享连接。
_CHECKPOINT_DB = Path(__file__).resolve().parents[2] / "resources" / "checkpoints.db"
_checkpoint_conn = sqlite3.connect(str(_CHECKPOINT_DB), check_same_thread=False)
checkpointer = SqliteSaver(_checkpoint_conn)
checkpointer.setup()  # 幂等：首次创建 checkpoints 相关表

# 编译图（挂上 checkpointer，graph 从此按 thread_id 具备记忆）
graph = workflow.compile(checkpointer=checkpointer)

# ==================== 8. 流式输出函数 ====================
def _to_lc_messages(messages):
    """把 [{"role","content"}] 转成 LangChain 消息对象。"""
    result = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant" and isinstance(content, str):
            result.append(AIMessage(content=content))
    return result


def _split_images_and_text(content):
    """从（可能是多模态的）content 里分出图片 data-url 列表和文本。"""
    if isinstance(content, str):
        return [], content
    if not isinstance(content, list):
        return [], str(content or "")
    images, texts = [], []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "image_url":
            url = (part.get("image_url") or {}).get("url")
            if url:
                images.append(url)
        elif part.get("type") == "text":
            texts.append(part.get("text", ""))
    return images, " ".join(t for t in texts if t)


def _thread_has_history(thread_id: str) -> bool:
    """该 thread 在 checkpointer 里是否已有持久化历史。
    有 → 只需把新消息喂给 graph；无 → 用前端传来的全量历史"播种"。"""
    try:
        snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
        return bool(snapshot.values.get("messages"))
    except Exception:
        return False


def chat_stream(messages, thread_id=None):
    """流式聊天 - 使用 LangGraph + checkpointer 记忆。

    - 传 thread_id：对话历史由 SqliteSaver 持久化在后端。
      · 线程已有历史 → 只把最新一条用户消息交给 graph，其余由 checkpointer 自动补上。
      · 线程是新的   → 用前端传来的全量历史播种（兼容升级前已存在的老对话）。
    - 不传 thread_id → 用一次性 ephemeral 线程，行为等同无记忆（每次发全量历史，如 Streamlit）。
    """
    # graph 已挂 checkpointer，调用必须带 thread_id，否则会报错；没有就给个一次性的。
    if not thread_id:
        thread_id = f"ephemeral-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    # 视觉前置：最新用户消息若带图片，先用多模态模型识别食材，
    # 再把这条消息改写成纯文本喂给 agent（agent 用 mimo-v2.5，不处理图片）。
    if messages and messages[-1].get("role") == "user":
        image_urls, user_text = _split_images_and_text(messages[-1].get("content"))
        if image_urls:
            yield "📷 正在识别食材...\n\n"
            try:
                from app.vision import recognize_ingredients
                ingredients = recognize_ingredients(image_urls, user_text)
            except Exception as e:
                logger.warning("食材识别失败: %s", e)
                ingredients = ""
            if ingredients and "未识别到食材" not in ingredients:
                yield f"📷 识别到食材：{ingredients}\n\n"
                if user_text:
                    new_text = f"{user_text}\n\n（照片中识别到的食材：{ingredients}）请据此推荐菜谱。"
                else:
                    new_text = f"我有这些食材：{ingredients}。请推荐合适的菜谱。"
            else:
                yield "📷 没能从照片里识别出食材，你可以直接用文字告诉我有什么。\n\n"
                new_text = user_text or "请根据我的描述推荐菜谱。"
            # 用纯文本替换带图片的最新消息
            messages = messages[:-1] + [{"role": "user", "content": new_text}]

    input_messages = _to_lc_messages(messages)

    # 已有记忆的线程：只发最新用户消息，避免和持久化历史重复堆叠
    if _thread_has_history(thread_id):
        last_user = next(
            (m for m in reversed(input_messages) if isinstance(m, HumanMessage)),
            None,
        )
        if last_user is not None:
            input_messages = [last_user]

    # messages 模式实现逐 token 流式输出；updates 模式捕获工具节点，给出搜索提示
    for mode, chunk in graph.stream(
        {"messages": input_messages},
        config=config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "updates":
            # 工具节点执行完毕后提示正在搜索
            if "tools" in chunk:
                yield "🔍 正在搜索菜谱...\n\n"
        elif mode == "messages":
            token, _metadata = chunk
            # 只输出 AI 生成的文本 token（跳过工具调用的空内容和工具返回结果）
            if isinstance(token, AIMessageChunk) and token.content:
                yield token.content
