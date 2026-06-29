# tests/test_recipe_card.py
"""菜谱卡纯函数：JSON 抽取、数值/食材归一、RecipeData 兜底、本地命中、飞轮质量门槛。
全部不触发 LLM —— 这些是把"模型自由文本"驯化成"前端可渲染结构"的关键防线。"""
import pytest

from app.recipe_card import (
    _extract_json, _to_int, _to_num, _norm, _coerce_ings, _coerce_recipe,
    _pick_local, _is_quality, _clean_local,
)


# ---------------- JSON 抽取（容忍围栏 + 前后说明文字） ----------------
@pytest.mark.parametrize("text, expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('```\n{"a": 1}\n```', {"a": 1}),
    ('说明文字 {"a": 1} 后缀', {"a": 1}),
    ('前言\n```json\n{"a": 1, "b": [2, 3]}\n```\n后语', {"a": 1, "b": [2, 3]}),
])
def test_extract_json_variants(text, expected):
    assert _extract_json(text) == expected


@pytest.mark.parametrize("text", ["", None, "没有任何 JSON", "{坏的"])
def test_extract_json_bad_returns_none(text):
    assert _extract_json(text) is None


# ---------------- 数值/字符串归一 ----------------
@pytest.mark.parametrize("v, expected", [
    ("20分钟", 20), (15, 15), (15.9, 15), ("无数字", 7), (None, 7),
])
def test_to_int(v, expected):
    assert _to_int(v, 7) == expected


@pytest.mark.parametrize("v, expected", [
    ("约 12.5 克", 12.5), (3, 3), ("none", 0),
])
def test_to_num(v, expected):
    assert _to_num(v) == expected


def test_norm_strips_space_and_lowercases():
    assert _norm("  Tomato  Egg ") == "tomatoegg"


# ---------------- 食材归一 ----------------
def test_coerce_ings_filters_and_defaults():
    raw = [
        {"name": "鸡蛋", "amount": "2个", "emoji": "🥚"},
        {"name": "  ", "amount": "x"},   # 空名 → 丢
        "不是字典",                        # 非 dict → 丢
        {"name": "盐"},                    # 缺 amount → 适量
    ]
    out = _coerce_ings(raw, fallback=None)
    assert [i["name"] for i in out] == ["鸡蛋", "盐"]
    assert out[0]["emoji"] == "🥚"
    assert out[1]["amount"] == "适量"


def test_coerce_ings_falls_back_when_empty():
    out = _coerce_ings([], fallback=[{"name": "牛肉", "amount": "200g"}])
    assert out == [{"name": "牛肉", "amount": "200g"}]


# ---------------- RecipeData 兜底 ----------------
def test_coerce_recipe_invalid_difficulty_defaults_to_medium():
    out = _coerce_recipe({"name": "X", "difficulty": "地狱级", "steps": ["s1"]}, "X", None)
    assert out["difficulty"] == "中等"


def test_coerce_recipe_empty_steps_get_placeholder():
    out = _coerce_recipe({"name": "X", "ingredients": [{"name": "a"}]}, "X", None)
    assert out["steps"] and "暂未生成详细步骤" in out["steps"][0]


def test_coerce_recipe_caps_tags_at_four():
    out = _coerce_recipe({"name": "X", "steps": ["s"], "tags": ["1", "2", "3", "4", "5"]}, "X", None)
    assert len(out["tags"]) == 4


def test_coerce_recipe_nutrition_coerced_to_numbers():
    out = _coerce_recipe(
        {"name": "X", "steps": ["s"], "nutrition": {"calories": "600kcal", "protein": "35g"}},
        "X", None,
    )
    assert out["nutrition"]["calories"] == 600
    assert out["nutrition"]["protein"] == 35
    assert out["nutrition"]["carbs"] == 0     # 缺失补 0


def test_coerce_recipe_uses_name_fallback_and_defaults():
    out = _coerce_recipe({}, "红烧肉", None)
    assert out["name"] == "红烧肉"
    assert out["servings"] == 2               # 默认人份


# ---------------- 本地命中 ----------------
def test_pick_local_exact_name_with_steps():
    hits = [
        {"name": "西红柿炒蛋", "steps": ["打蛋", "翻炒"]},
        {"name": "别的菜", "steps": ["x"]},
    ]
    assert _pick_local("西红柿炒蛋", hits)["name"] == "西红柿炒蛋"
    assert _pick_local(" 西红柿炒蛋 ", hits) is not None     # 归一后仍命中


def test_pick_local_no_match_or_no_steps():
    assert _pick_local("不存在", [{"name": "别的", "steps": ["x"]}]) is None
    assert _pick_local("无步骤菜", [{"name": "无步骤菜", "steps": []}]) is None


def test_clean_local_strips_non_recipe_keys():
    r = {"name": "A", "steps": ["s"], "_score": 0.9, "attrs": ["增肌"], "ingredients": []}
    out = _clean_local(r)
    assert "_score" not in out and "attrs" not in out
    assert out["name"] == "A"


# ---------------- 飞轮质量门槛（数据飞轮第一道关） ----------------
def _good_recipe():
    return {
        "name": "番茄牛腩",
        "steps": ["焯水", "炖煮", "收汁"],
        "ingredients": [{"name": "牛腩"}, {"name": "番茄"}],
    }


def test_is_quality_accepts_complete_recipe():
    assert _is_quality(_good_recipe()) is True


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(name=""),                              # 无名
    lambda r: r.update(steps=["只有一步"]),                    # 步骤不足
    lambda r: r.update(steps=["暂未生成详细步骤，可追问"]),      # 兜底占位
    lambda r: r.update(ingredients=[{"name": "番茄"}]),        # 食材不足
])
def test_is_quality_rejects_low_quality(mutate):
    r = _good_recipe()
    mutate(r)
    assert _is_quality(r) is False
