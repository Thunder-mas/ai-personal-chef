# tests/test_flywheel.py
"""数据飞轮端到端：ingest_recipe 三道关（质量门槛 → 近似重复 → 同名去重）+ 总开关。
显式传 hits 避开真实检索，因而不加载 embedding 模型、不连网络。"""
import pytest

from app.recipe_card import ingest_recipe
import app.recipe_rag as rag


def _good():
    return {
        "name": "孜然羊肉_flywheel",
        "description": "西北风味",
        "difficulty": "中等",
        "cookingTime": "20分钟",
        "servings": 2,
        "ingredients": [{"name": "羊肉"}, {"name": "孜然"}],
        "steps": ["腌制", "爆炒", "撒孜然"],
    }


def test_ingest_writes_and_tags_provenance(temp_generated):
    assert ingest_recipe(_good(), source="favorite", hits=[]) is True
    saved = rag._load_generated()
    assert len(saved) == 1
    assert saved[0]["source"] == "favorite"      # 标注来源（provenance）
    assert "createdAt" in saved[0]               # 打时间戳
    # 只持久化 RecipeData 字段 + provenance，不带运行时 _flags
    assert "_source" not in saved[0] and "_score" not in saved[0]


def test_ingest_rejects_low_quality(temp_generated):
    bad = _good()
    bad["steps"] = ["只有一步"]                   # 步骤不足 → 质量门槛挡掉
    assert ingest_recipe(bad, source="log", hits=[]) is False
    assert rag._load_generated() == []


def test_ingest_rejects_near_duplicate(temp_generated):
    # 库里已有高度相似项（score>=0.95）→ 视为同一道菜，不重复入库
    hits = [{"name": "近似项", "_score": 0.97}]
    assert ingest_recipe(_good(), source="ai", hits=hits) is False
    assert rag._load_generated() == []


def test_ingest_allows_when_similarity_below_threshold(temp_generated):
    hits = [{"name": "不太像", "_score": 0.50}]
    assert ingest_recipe(_good(), source="ai", hits=hits) is True


def test_ingest_disabled_by_env(temp_generated, monkeypatch):
    monkeypatch.setenv("RECIPE_WRITEBACK", "0")   # 总开关关停
    assert ingest_recipe(_good(), source="favorite", hits=[]) is False


def test_ingest_hits_none_does_not_crash(temp_generated, monkeypatch):
    # hits=None 时会自行检索；mock 掉 rag_search 避免加载 embedding 模型
    monkeypatch.setattr("app.recipe_card.rag_search", lambda name, k=1: [])
    assert ingest_recipe(_good(), source="favorite", hits=None) is True
