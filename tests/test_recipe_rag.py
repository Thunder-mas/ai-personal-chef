# tests/test_recipe_rag.py
"""RAG 知识库的非向量逻辑：名称归一、指纹失效、检索文本拼装、
回流库读写、库存统计、回流去重/容量上限。均不加载 embedding 模型、不连网络。"""
import json

import pytest

import app.recipe_rag as rag
from app.recipe_rag import (
    _norm_name, _fingerprint, _recipe_to_text, _load_generated, _save_generated,
    library_counts, add_generated_recipe,
)


# ---------------- 名称归一 ----------------
def test_norm_name():
    assert _norm_name("  Kung Pao ") == "kungpao"
    assert _norm_name(None) == ""


# ---------------- 指纹失效（菜谱/模型一变即重建索引） ----------------
def test_fingerprint_stable_and_content_sensitive():
    a = [{"name": "甲"}]
    b = [{"name": "甲"}, {"name": "乙"}]
    assert _fingerprint(a) == _fingerprint(a)      # 同输入稳定
    assert _fingerprint(a) != _fingerprint(b)      # 内容变 → 指纹变 → 缓存失效


def test_fingerprint_includes_model_name(monkeypatch):
    a = [{"name": "甲"}]
    fp1 = _fingerprint(a)
    monkeypatch.setattr(rag, "_MODEL_NAME", "another-model")
    assert _fingerprint(a) != fp1                  # 换模型 → 指纹变 → 重建


# ---------------- 检索文本拼装 ----------------
def test_recipe_to_text_includes_key_fields():
    text = _recipe_to_text({
        "name": "宫保鸡丁", "tags": ["川菜"], "attrs": ["下饭"],
        "description": "酸甜微辣", "ingredients": [{"name": "鸡丁"}, {"name": "花生"}],
    })
    for token in ["宫保鸡丁", "川菜", "下饭", "酸甜微辣", "鸡丁", "花生"]:
        assert token in text


# ---------------- 回流库读写（best-effort，坏文件不拖垮 RAG） ----------------
def test_load_generated_missing_returns_empty(temp_generated):
    assert _load_generated() == []                 # 文件不存在 → []


def test_load_generated_corrupt_returns_empty(temp_generated):
    temp_generated.write_text("{ not json", encoding="utf-8")
    assert _load_generated() == []                 # 坏文件 → 降级 []，不抛


def test_load_generated_non_list_returns_empty(temp_generated):
    temp_generated.write_text('{"a": 1}', encoding="utf-8")
    assert _load_generated() == []                 # 非列表 → []


def test_save_load_generated_roundtrip(temp_generated):
    items = [{"name": "回流菜", "steps": ["s1", "s2"]}]
    _save_generated(items)
    assert _load_generated() == items


# ---------------- 库存统计 ----------------
def test_library_counts_tracks_generated(temp_generated):
    base = library_counts()
    assert base["generated"] == 0
    assert base["human"] >= 1
    assert base["total"] == base["human"] + base["generated"]
    _save_generated([{"name": "新菜"}])
    after = library_counts()
    assert after["generated"] == 1
    assert after["total"] == after["human"] + 1


# ---------------- 回流入库：去重 + 容量上限 ----------------
def test_add_generated_recipe_success_then_dedup(temp_generated):
    r = {"name": "全新独创菜_xyz", "steps": ["a", "b"], "ingredients": [{"name": "x"}]}
    assert add_generated_recipe(r) is True          # 首次写入
    assert add_generated_recipe(r) is False         # 同名去重
    assert len(_load_generated()) == 1


def test_add_generated_recipe_empty_name_rejected(temp_generated):
    assert add_generated_recipe({"name": "  "}) is False


def test_add_generated_recipe_dedup_against_human_library(temp_generated):
    # 用人工库里已存在的菜名 → 不应重复入回流库
    with open(rag._RECIPES_PATH, encoding="utf-8") as f:
        existing_name = json.load(f)[0]["name"]
    r = {"name": existing_name, "steps": ["a", "b"], "ingredients": [{"name": "x"}]}
    assert add_generated_recipe(r) is False


def test_add_generated_recipe_respects_capacity(temp_generated, monkeypatch):
    monkeypatch.setattr(rag, "_MAX_GENERATED", 1)
    assert add_generated_recipe({"name": "菜A", "steps": ["a"]}) is True
    assert add_generated_recipe({"name": "菜B", "steps": ["b"]}) is False  # 已达上限
    assert len(_load_generated()) == 1
