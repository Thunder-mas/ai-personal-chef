# app/food_log.py
"""今日饮食记录：记录每天吃了什么 + 累加营养，并对比每日目标。

这是"健身闭环"的最后一环：目标(fitness) → 推荐 → 记录(本模块) → 看还差多少。
持久化在 resources/personal_chief.db 的 food_log 表，按日期(date)归集。
"""
import os
import sqlite3
from datetime import date
from typing import List, Dict, Any, Optional

from app.fitness import get_daily_targets

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "personal_chief.db",
)


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    return sqlite3.connect(_DB_PATH)


def _today() -> str:
    return date.today().isoformat()


def init_food_log_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS food_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                name TEXT NOT NULL,
                calories REAL DEFAULT 0,
                protein REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                fat REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def add_entry(name: str, calories: float = 0, protein: float = 0,
              carbs: float = 0, fat: float = 0, on_date: Optional[str] = None) -> None:
    init_food_log_db()
    on_date = on_date or _today()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO food_log (date, name, calories, protein, carbs, fat)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (on_date, name, calories, protein, carbs, fat),
        )


def get_entries(on_date: Optional[str] = None) -> List[Dict[str, Any]]:
    init_food_log_db()
    on_date = on_date or _today()
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, name, calories, protein, carbs, fat
               FROM food_log WHERE date = ? ORDER BY created_at""",
            (on_date,),
        ).fetchall()
    return [
        {"id": r[0], "name": r[1], "calories": r[2],
         "protein": r[3], "carbs": r[4], "fat": r[5]}
        for r in rows
    ]


def delete_entry(entry_id: int) -> None:
    init_food_log_db()
    with _connect() as conn:
        conn.execute("DELETE FROM food_log WHERE id = ?", (entry_id,))


def get_day_summary(on_date: Optional[str] = None) -> Dict[str, Any]:
    """某天的记录 + 营养合计 + 对比每日目标 + 剩余额度。"""
    on_date = on_date or _today()
    entries = get_entries(on_date)

    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for e in entries:
        for k in totals:
            totals[k] += e.get(k) or 0
    totals = {k: round(v) for k, v in totals.items()}

    targets = get_daily_targets()  # 没设健身档案时为 None
    remaining = None
    if targets:
        remaining = {
            k: round(targets[k] - totals[k])
            for k in ("calories", "protein", "carbs", "fat")
        }

    return {
        "date": on_date,
        "entries": entries,
        "totals": totals,
        "targets": targets,
        "remaining": remaining,
    }
