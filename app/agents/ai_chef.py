# app/agents/ai_chef.py
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

# ==================== 1. 定义 State ====================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ==================== 2. 定义系统提示 ====================
system_prompt = """
你是一名私人厨师。根据用户提供的食材，推荐合适的菜谱。
优先调用 search_recipe 工具搜索菜谱，再搜索不到的情况下才能自己发挥。

## 菜谱返回格式

当你推荐菜谱时，请使用以下JSON格式返回结构化数据：

```recipe
{
  "name": "菜名",
  "description": "简短描述",
  "difficulty": "简单/中等/复杂",
  "cookingTime": "时间",
  "servings": 人数,
  "ingredients": [{"name": "食材", "amount": "用量", "emoji": "可选图标"}],
  "steps": ["步骤1", "步骤2"],
  "tips": "可选小贴士",
  "tags": ["标签1", "标签2"]
}
```

这样前端可以渲染精美的菜谱卡片。在JSON前后可以添加说明文字。

## 其他说明

- 如果用户说"收藏这个菜谱"，请回复"已收藏"并提取菜谱名称。
- 如果用户说"我的偏好是..."或"我忌口..."，请记住并回复"已记住你的偏好"。
"""

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

# 工具列表
tools = [search_recipe]

# ==================== 4. 定义模型 ====================
model = ChatOpenAI(
    model="mimo-v2.5",
    openai_api_key=os.getenv('MIMO_API_KEY'),
    openai_api_base=os.getenv('MIMO_BASE_URL'),
    streaming=True,
).bind_tools(tools)

# ==================== 5. 定义 Nodes ====================
def agent_node(state: AgentState):
    """AI 模型思考并决定是否调用工具"""
    messages = state["messages"]
    system_message = SystemMessage(content=system_prompt)
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

    # 使用 stream 模式运行图
    for chunk in graph.stream({"messages": input_messages}):
        # 工具调用阶段提示
        if "tools" in chunk:
            yield "🔍 正在搜索菜谱...\n\n"

        # 检查是否是 agent 节点的输出
        if "agent" in chunk:
            agent_output = chunk["agent"]
            if "messages" in agent_output:
                for msg in agent_output["messages"]:
                    # 只输出 AI 的文本回复
                    if isinstance(msg, AIMessage) and msg.content:
                        yield msg.content
