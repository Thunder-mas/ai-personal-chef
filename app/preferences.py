# app/preferences.py
"""用户饮食偏好的持久化存储（SQLite）。

复用 resources/personal_chief.db 的 preferences 表，与 Streamlit 版共享，
让 Web / CLI / Streamlit 三个入口的偏好统一。单用户应用，偏好为全局。
"""
import os
import sqlite3
from typing import List

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "personal_chief.db",
)


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    return sqlite3.connect(_DB_PATH)


def init_pref_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def add_preference(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    with _connect() as conn:
        # 去重：已存在则跳过
        exists = conn.execute(
            "SELECT 1 FROM preferences WHERE preference = ?", (text,)
        ).fetchone()
        if exists:
            return
        conn.execute("INSERT INTO preferences (preference) VALUES (?)", (text,))


def get_preferences() -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT preference FROM preferences ORDER BY created_at"
        ).fetchall()
    return [r[0] for r in rows if r[0]]


def remove_preference(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM preferences WHERE preference = ?", (text,))
