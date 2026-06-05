# app/agents/ai_chef.py
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.preferences import add_preference, remove_preference, get_preferences, init_pref_db

logger = logging.getLogger(__name__)

# 确保偏好表存在
init_pref_db()

# ==================== 1. 定义 State ====================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ==================== 2. 定义系统提示 ====================
system_prompt = """你是私人厨师。根据用户食材推荐菜谱。优先用 search_recipe 工具搜索。

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
{"title":"本周食谱","days":[{"day":"周一","meals":[{"name":"菜名","brief":"一句话简述","ingredients":[{"name":"食材","amount":"用量","emoji":"图标"}]}]}]}
```

规则：
- days 必须是完整的7天（周一到周日）
- 每天1-2道菜，每道菜都要带 ingredients（食材名+用量），方便生成购物清单
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
def search_recipe(query: str) -> str:
    """搜索菜谱，根据食材查找推荐菜谱"""
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

# 工具列表
tools = [search_recipe, save_preference, forget_preference]

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
    """把当前已记录的用户偏好动态拼进系统提示，让每次推荐都遵守。"""
    prefs = get_preferences()
    if not prefs:
        return system_prompt
    pref_lines = "\n".join(f"- {p}" for p in prefs)
    return (
        system_prompt
        + "\n\n## 用户偏好（必须遵守）\n"
        + pref_lines
        + "\n推荐菜谱时务必避开以上忌口/过敏项，并尽量贴合口味偏好。"
    )

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

# 编译图
graph = workflow.compile()

# ==================== 8. 流式输出函数 ====================
def chat_stream(messages):
    """流式聊天 - 使用 LangGraph"""
    # 转换消息格式（保留完整对话历史）
    input_messages = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            if isinstance(content, list):
                input_messages.append(HumanMessage(content=content))
            else:
                input_messages.append(HumanMessage(content=content))
        elif role == "assistant" and isinstance(content, str):
            input_messages.append(AIMessage(content=content))

    # messages 模式实现逐 token 流式输出；updates 模式捕获工具节点，给出搜索提示
    for mode, chunk in graph.stream(
        {"messages": input_messages},
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
