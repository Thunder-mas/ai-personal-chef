# app/fitness.py
"""健身档案与每日宏量目标：持久化（SQLite）+ 计算。

复用 resources/personal_chief.db，新增 fitness_profile 表（单行、单用户全局）。
基于 体重/身高/年龄/活动量/目标，用 Mifflin-St Jeor 公式算出
每日 热量 / 蛋白质 / 碳水 / 脂肪 目标——这是"健身垂直版"的核心持久状态。
"""
import os
import sqlite3
from typing import Optional, Dict, Any

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "personal_chief.db",
)

# 活动水平 → TDEE 系数（基础代谢 × 系数 = 每日总消耗）
ACTIVITY_FACTORS = {
    "久坐": 1.2,    # 几乎不运动
    "轻度": 1.375,  # 每周运动 1-3 次
    "中度": 1.55,   # 每周运动 3-5 次
    "高度": 1.725,  # 每周运动 6-7 次
    "极高": 1.9,    # 体力劳动 / 一天两练
}

# 目标 → 热量调整系数 与 蛋白质摄入(g/每公斤体重)
# 减脂热量赤字、蛋白拉高保肌肉；增肌热量盈余、蛋白适中。
GOAL_CONFIG = {
    "减脂": {"calorie_factor": 0.8, "protein_per_kg": 2.0},
    "维持": {"calorie_factor": 1.0, "protein_per_kg": 1.6},
    "增肌": {"calorie_factor": 1.1, "protein_per_kg": 1.8},
}


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    return sqlite3.connect(_DB_PATH)


def init_fitness_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS fitness_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                gender TEXT,
                age INTEGER,
                height_cm REAL,
                weight_kg REAL,
                activity_level TEXT,
                goal TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def save_profile(gender: str, age: int, height_cm: float, weight_kg: float,
                 activity_level: str, goal: str) -> None:
    """保存（覆盖）健身档案。单行表，id 固定为 1。"""
    init_fitness_db()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO fitness_profile
                 (id, gender, age, height_cm, weight_kg, activity_level, goal, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
                 gender=excluded.gender, age=excluded.age,
                 height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
                 activity_level=excluded.activity_level, goal=excluded.goal,
                 updated_at=CURRENT_TIMESTAMP""",
            (gender, age, height_cm, weight_kg, activity_level, goal),
        )


def get_profile() -> Optional[Dict[str, Any]]:
    """读取健身档案；未设置返回 None。"""
    init_fitness_db()
    with _connect() as conn:
        row = conn.execute(
            """SELECT gender, age, height_cm, weight_kg, activity_level, goal
               FROM fitness_profile WHERE id = 1"""
        ).fetchone()
    if not row:
        return None
    return {
        "gender": row[0], "age": row[1], "height_cm": row[2],
        "weight_kg": row[3], "activity_level": row[4], "goal": row[5],
    }


def _bmr(gender: str, age: int, height_cm: float, weight_kg: float) -> float:
    """Mifflin-St Jeor 基础代谢率(BMR)：业界最常用的估算公式。"""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "男" else base - 161


def get_daily_targets() -> Optional[Dict[str, Any]]:
    """根据档案算每日宏量目标。档案不完整则返回 None。

    步骤：BMR → ×活动系数=TDEE → ×目标系数=目标热量
         蛋白=体重×目标系数；脂肪=总热量25%；碳水=剩余热量。
    （蛋白/碳水 4 kcal/g，脂肪 9 kcal/g）
    """
    p = get_profile()
    if not p or not all([p["gender"], p["age"], p["height_cm"], p["weight_kg"]]):
        return None

    activity = ACTIVITY_FACTORS.get(p["activity_level"], 1.375)
    goal_cfg = GOAL_CONFIG.get(p["goal"], GOAL_CONFIG["维持"])

    tdee = _bmr(p["gender"], p["age"], p["height_cm"], p["weight_kg"]) * activity
    calories = round(tdee * goal_cfg["calorie_factor"])

    protein_g = round(p["weight_kg"] * goal_cfg["protein_per_kg"])
    fat_g = round(calories * 0.25 / 9)
    carbs_g = max(round((calories - protein_g * 4 - fat_g * 9) / 4), 0)

    return {
        "goal": p["goal"],
        "calories": calories,
        "protein": protein_g,
        "carbs": carbs_g,
        "fat": fat_g,
    }
