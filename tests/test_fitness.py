# tests/test_fitness.py
"""健身计算：Mifflin-St Jeor BMR、安全速率、每日营养目标（含热量下限钳制）。
全是确定性公式，pin 死系数 —— 改公式即触发回归。无需 LLM / 网络。"""
import pytest

from app.fitness import (
    _bmr, _weekly_rate_kg, get_daily_targets, get_profile, save_profile,
)


def test_bmr_male_uses_plus_5():
    # 10*75 + 6.25*175 - 5*30 + 5 = 1698.75
    assert _bmr("男", 30, 175, 75) == pytest.approx(1698.75)


def test_bmr_female_uses_minus_161():
    # 10*60 + 6.25*165 - 5*28 - 161 = 1330.25
    assert _bmr("女", 28, 165, 60) == pytest.approx(1330.25)


def test_bmr_gender_gap_is_constant_166():
    # 同参数下，男(+5) 与 女(-161) 恒差 166
    assert _bmr("男", 30, 175, 75) - _bmr("女", 30, 175, 75) == pytest.approx(166)


@pytest.mark.parametrize("weight, expected", [
    (100, 0.75),   # 100*0.0075=0.75，落在 [0.25, 1.0] 内
    (200, 1.0),    # 1.5 → 上限钳到 1.0
    (20, 0.25),    # 0.15 → 下限钳到 0.25
])
def test_weekly_rate_cut_clamped(weight, expected):
    assert _weekly_rate_kg("减脂", weight) == pytest.approx(expected)


@pytest.mark.parametrize("weight, expected", [
    (100, 0.35),   # 0.35 落在 [0.125, 0.5] 内
    (200, 0.5),    # 0.7 → 上限钳到 0.5
    (30, 0.125),   # 0.105 → 下限钳到 0.125
])
def test_weekly_rate_bulk_clamped(weight, expected):
    assert _weekly_rate_kg("增肌", weight) == pytest.approx(expected)


def test_weekly_rate_maintain_is_zero():
    assert _weekly_rate_kg("维持", 70) == 0.0


def test_daily_targets_none_when_no_profile(temp_db):
    assert get_daily_targets() is None


def test_daily_targets_maintain(temp_db):
    save_profile("男", 30, 175, 75, "中度", "维持")
    t = get_daily_targets()
    assert t["maintenance"] == 2633     # round(1698.75 * 1.55)
    assert t["calories"] == 2633        # 维持：无缺口
    assert t["daily_adjust"] == 0
    assert t["protein"] == 120          # round(75 * 1.6)
    assert t["weeks_to_goal"] is None   # 未设目标体重


def test_daily_targets_respects_calorie_floor(temp_db):
    # 女、轻体重、激进减脂 → 计算热量低于 1200 安全下限，应被钳住并据实回算缺口
    save_profile("女", 25, 160, 45, "久坐", "减脂")
    t = get_daily_targets()
    assert t["calories"] == 1200                                  # 钳到女性下限
    assert t["daily_adjust"] == t["calories"] - t["maintenance"]  # 缺口回算
    assert t["protein"] == 90                                     # round(45*2.0)，减脂高蛋白保肌肉


def test_daily_targets_weeks_to_goal(temp_db):
    # 男 80kg 减到 75kg：rate=clamp(80*0.0075)=0.6 → weeks=round(5/0.6)=8
    save_profile("男", 30, 175, 80, "中度", "减脂", target_weight_kg=75)
    t = get_daily_targets()
    assert t["weekly_rate_kg"] == pytest.approx(0.6)
    assert t["weeks_to_goal"] == 8


def test_save_then_get_profile_roundtrip(temp_db):
    save_profile("女", 26, 168, 58, "轻度", "增肌", target_weight_kg=62)
    p = get_profile()
    assert p["gender"] == "女" and p["goal"] == "增肌"
    assert p["target_weight_kg"] == 62
