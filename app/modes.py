# app/modes.py
"""推荐模式（美食 / 健身 / …）：用户可切换，agent 行为随当前模式变化。

模式是产品的"元层"：每个模式 = 一个人设 + 一套行为 + 它用到的状态。
加新模式（控糖/减脂/快手…）只需在 MODES 注册表里加一项即可。
当前模式存在 personal_chief.db 的 app_settings 表（通用 key/value）。
"""
import os
import sqlite3
from typing import Dict, Any, List, Optional

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "personal_chief.db",
)

# ==================== 模式注册表 ====================
# uses_fitness=True 的模式会额外注入"每日宏量目标"（见 ai_chef._build_system_prompt）
MODES: Dict[str, Dict[str, Any]] = {
    "gourmet": {
        "name": "美食模式",
        "emoji": "🍜",
        "uses_fitness": False,
        "prompt": (
            "## 当前模式：美食模式 🍜\n"
            "你是讲究的美食家。以「好吃」和「体验」为先：优先推荐有特色、有风味的菜，"
            "介绍它的菜系、口感亮点和地道做法。不强调热量/营养数据，让用户吃得开心。"
        ),
    },
    "fitness": {
        "name": "健身模式",
        "emoji": "💪",
        "uses_fitness": True,
        "prompt": (
            "## 当前模式：健身模式 💪\n"
            "你是健身餐顾问。以用户的训练目标为先：优先推荐高蛋白、贴合每日营养目标的菜，"
            "并在每个 recipe 卡片的 JSON 里补充 "
            '"nutrition":{"calories":数字,"protein":数字,"carbs":数字,"fat":数字} 字段，'
            "标注该菜每份的大致营养（单位 kcal 与 克）。"
        ),
    },
}

DEFAULT_MODE = "gourmet"


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    return sqlite3.connect(_DB_PATH)


def init_mode_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
        )


def get_mode() -> str:
    """当前模式 key；未设置或非法时回退到默认模式。"""
    init_mode_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'mode'"
        ).fetchone()
    mode = row[0] if row else DEFAULT_MODE
    return mode if mode in MODES else DEFAULT_MODE


def set_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"未知模式: {mode}")
    init_mode_db()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO app_settings (key, value) VALUES ('mode', ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (mode,),
        )


def get_mode_config(mode: Optional[str] = None) -> Dict[str, Any]:
    """取某个模式的完整配置（默认取当前模式）。"""
    return MODES[mode or get_mode()]


def list_modes() -> List[Dict[str, str]]:
    """给前端的模式清单（不含 prompt 等内部字段）。"""
    return [
        {"key": k, "name": v["name"], "emoji": v["emoji"]}
        for k, v in MODES.items()
    ]
