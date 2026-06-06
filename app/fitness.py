# app/fitness.py
"""健身档案与每日营养计划：持久化（SQLite）+ 循证计算。

复用 resources/personal_chief.db，新增/迁移 fitness_profile 表（单行、单用户全局）。
计算依据（均为营养学通用准则，非随意系数）：
  · 维持热量(TDEE) = BMR(Mifflin-St Jeor) × 活动系数
  · 能量平衡：约 7700 kcal ≈ 1 kg 脂肪（Wishnofsky 经验法则，长期略高估，作规划起点）
  · 安全速率：减脂 每周 0.5–1% 体重、增肌 每周 0.25–0.5% 体重（过快伤肌肉/易反弹）
  · 每日缺口/盈余 = 周速率 × 7700 ÷ 7，再据此调整热量
  · 热量下限：男 ≥1500、女 ≥1200 kcal（临床安全底线，不允许更低）
  · 蛋白质：减脂 2.0 / 增肌 1.8 / 维持 1.6 g/kg（减脂期高蛋白保肌肉）
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

KCAL_PER_KG = 7700          # 约 7700 kcal ≈ 1 kg 体重（脂肪）
CALORIE_FLOOR = {"男": 1500, "女": 1200}  # 每日热量安全下限
PROTEIN_PER_KG = {"减脂": 2.0, "增肌": 1.8, "维持": 1.6}  # g/每公斤体重


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
                target_weight_kg REAL,
                activity_level TEXT,
                goal TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        # 兼容旧表：缺 target_weight_kg 列就补上
        cols = [r[1] for r in conn.execute("PRAGMA table_info(fitness_profile)").fetchall()]
        if "target_weight_kg" not in cols:
            conn.execute("ALTER TABLE fitness_profile ADD COLUMN target_weight_kg REAL")


def save_profile(gender: str, age: int, height_cm: float, weight_kg: float,
                 activity_level: str, goal: str,
                 target_weight_kg: Optional[float] = None) -> None:
    """保存（覆盖）健身档案。单行表，id 固定为 1。"""
    init_fitness_db()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO fitness_profile
                 (id, gender, age, height_cm, weight_kg, target_weight_kg,
                  activity_level, goal, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
                 gender=excluded.gender, age=excluded.age,
                 height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
                 target_weight_kg=excluded.target_weight_kg,
                 activity_level=excluded.activity_level, goal=excluded.goal,
                 updated_at=CURRENT_TIMESTAMP""",
            (gender, age, height_cm, weight_kg, target_weight_kg, activity_level, goal),
        )


def get_profile() -> Optional[Dict[str, Any]]:
    """读取健身档案；未设置返回 None。"""
    init_fitness_db()
    with _connect() as conn:
        row = conn.execute(
            """SELECT gender, age, height_cm, weight_kg, target_weight_kg,
                      activity_level, goal
               FROM fitness_profile WHERE id = 1"""
        ).fetchone()
    if not row:
        return None
    return {
        "gender": row[0], "age": row[1], "height_cm": row[2],
        "weight_kg": row[3], "target_weight_kg": row[4],
        "activity_level": row[5], "goal": row[6],
    }


def _bmr(gender: str, age: int, height_cm: float, weight_kg: float) -> float:
    """Mifflin-St Jeor 基础代谢率(BMR)：业界最常用的估算公式。"""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "男" else base - 161


def _weekly_rate_kg(goal: str, weight_kg: float) -> float:
    """安全的每周体重变化（kg）。减脂 0.5–1% 体重、增肌 0.25–0.5% 体重，并加绝对值上下限。"""
    if goal == "减脂":
        return min(max(weight_kg * 0.0075, 0.25), 1.0)   # 约 0.75%/周，夹在 0.25–1.0kg
    if goal == "增肌":
        return min(max(weight_kg * 0.0035, 0.125), 0.5)  # 约 0.35%/周，夹在 0.125–0.5kg
    return 0.0  # 维持


def get_daily_targets() -> Optional[Dict[str, Any]]:
    """据档案算每日营养计划。档案不完整返回 None。返回字段见末尾 dict。"""
    p = get_profile()
    if not p or not all([p["gender"], p["age"], p["height_cm"], p["weight_kg"]]):
        return None

    gender, weight, goal = p["gender"], p["weight_kg"], p["goal"]
    activity = ACTIVITY_FACTORS.get(p["activity_level"], 1.375)
    maintenance = round(_bmr(gender, p["age"], p["height_cm"], weight) * activity)

    # 由安全速率推每日热量缺口/盈余（有依据，而非随意系数）
    rate = _weekly_rate_kg(goal, weight)
    if goal == "减脂":
        daily_adjust = -round(rate * KCAL_PER_KG / 7)
    elif goal == "增肌":
        daily_adjust = round(rate * KCAL_PER_KG / 7)
    else:
        daily_adjust = 0

    calories = maintenance + daily_adjust
    floor = CALORIE_FLOOR.get(gender, 1200)
    if calories < floor:                 # 卡安全下限，并据实回算缺口
        calories = floor
        daily_adjust = calories - maintenance

    protein = round(weight * PROTEIN_PER_KG.get(goal, 1.6))
    fat = round(calories * 0.25 / 9)     # 脂肪占 25% 热量（9 kcal/g）
    carbs = max(round((calories - protein * 4 - fat * 9) / 4), 0)  # 碳水填剩余

    # 预计周数：仅当设了目标体重且方向与目标一致
    target_w = p.get("target_weight_kg")
    weeks_to_goal = None
    if target_w and rate > 0:
        diff = (weight - target_w) if goal == "减脂" else (target_w - weight)
        if diff > 0:
            weeks_to_goal = max(round(diff / rate), 1)

    return {
        "goal": goal,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "maintenance": maintenance,        # 维持热量(TDEE)
        "daily_adjust": daily_adjust,      # 每日缺口(负)/盈余(正)
        "weekly_rate_kg": round(rate, 2),  # 每周目标变化
        "target_weight": target_w,
        "weeks_to_goal": weeks_to_goal,    # 预计达成周数（可能为 None）
    }
