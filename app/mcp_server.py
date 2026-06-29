# app/mcp_server.py
"""把 AI 私人厨师的现有能力暴露成 MCP Server（Model Context Protocol）。

MCP 是"AI 应用 ↔ 外部工具/数据源"的开放协议：任何 MCP 客户端
（Claude Desktop、支持 MCP 的 IDE、自研 Agent）都能即插即用地发现并调用
这里注册的工具，无需为每个客户端各写一套对接。

实现上只是把项目里已有的纯函数（菜谱 RAG 检索 / 偏好 / 每日营养目标 / 饮食记录）
包一层协议：复用同一套向量检索与同一个 SQLite，不引入第二份业务逻辑。
工具的 docstring 会作为"工具说明"暴露给客户端的大模型，决定它何时调用，故写得明确。

运行（stdio 传输，供 MCP 客户端拉起）：
    python -m app.mcp_server

接入 Claude Desktop（claude_desktop_config.json）：
    {
      "mcpServers": {
        "ai-personal-chef": {
          "command": "python",
          "args": ["-m", "app.mcp_server"],
          "cwd": "<项目根目录>"
        }
      }
    }
"""
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.recipe_rag import search as rag_search
from app.preferences import get_preferences, add_preference as _add_preference
from app.fitness import get_daily_targets
from app.food_log import add_entry, get_day_summary

mcp = FastMCP("ai-personal-chef")


@mcp.tool()
def search_recipes(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """按自然语言检索本地菜谱知识库（RAG 向量检索）。
    query 可为菜名（"宫保鸡丁"）、手头食材（"我有西红柿和鸡蛋"）或概念
    （"清淡少油"、"高蛋白增肌"、"降火"）。返回最相关的 k 道菜及相似度分。"""
    hits = rag_search(query, k=k)
    return [
        {
            "name": h.get("name"),
            "description": h.get("description", ""),
            "tags": h.get("tags", []),
            "score": h.get("_score"),
        }
        for h in hits
    ]


@mcp.tool()
def list_preferences() -> List[str]:
    """读取用户已保存的饮食偏好（如"不吃香菜"、"少油"、"清真"）。"""
    return get_preferences()


@mcp.tool()
def add_preference(text: str) -> Dict[str, Any]:
    """新增一条饮食偏好（自动去重）。返回更新后的完整偏好列表。"""
    _add_preference(text)
    return {"added": (text or "").strip(), "preferences": get_preferences()}


@mcp.tool()
def get_daily_nutrition_targets() -> Optional[Dict[str, Any]]:
    """读取用户的每日营养目标（热量/蛋白/碳水/脂肪，由健身档案循证计算）。
    未设置健身档案时返回 null。"""
    return get_daily_targets()


@mcp.tool()
def log_food(name: str, calories: float = 0, protein: float = 0,
             carbs: float = 0, fat: float = 0) -> Dict[str, Any]:
    """把一道吃过的菜记入今日饮食。返回今日营养合计与距离每日目标的剩余额度。"""
    add_entry(name, calories, protein, carbs, fat)
    return get_day_summary()


@mcp.tool()
def get_today_nutrition() -> Dict[str, Any]:
    """查看今日已记录的饮食、营养合计、每日目标与剩余额度。"""
    return get_day_summary()


if __name__ == "__main__":
    mcp.run()  # 默认 stdio 传输
