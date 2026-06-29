# tests/test_tracing.py
"""LangSmith 接入的开关逻辑：env-gated —— 没配 key 必须完全 no-op（不改线上行为）。
只测门控与变量映射，不真连 LangSmith。"""
import os

import pytest

from app.tracing import init_tracing

_KEYS = ["LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_API_KEY",
         "LANGCHAIN_API_KEY", "LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"]


@pytest.fixture
def clean_env(monkeypatch):
    """清掉所有相关变量；monkeypatch 在测试后还原（含 init_tracing 直接写入的那几个）。"""
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_disabled_without_api_key(clean_env):
    assert init_tracing() is False
    assert os.getenv("LANGCHAIN_TRACING_V2") is None   # 没开 → 不污染 langchain 开关


def test_disabled_when_tracing_not_truthy(clean_env):
    clean_env.setenv("LANGSMITH_API_KEY", "ls__fake")   # 有 key 但没显式开 TRACING
    assert init_tracing() is False
    clean_env.setenv("LANGSMITH_TRACING", "false")      # 显式 false 也不开
    assert init_tracing() is False


def test_enabled_with_key_sets_langchain_env(clean_env):
    clean_env.setenv("LANGSMITH_API_KEY", "ls__fake")
    clean_env.setenv("LANGSMITH_TRACING", "true")
    assert init_tracing() is True
    assert os.getenv("LANGCHAIN_TRACING_V2") == "true"      # langchain 实际读这个
    assert os.getenv("LANGCHAIN_API_KEY") == "ls__fake"     # 旧变量名补齐
    assert os.getenv("LANGCHAIN_PROJECT") == "ai-personal-chef"  # 默认 project


def test_enabled_respects_custom_project(clean_env):
    clean_env.setenv("LANGSMITH_API_KEY", "ls__fake")
    clean_env.setenv("LANGSMITH_TRACING", "TRUE")           # 大小写不敏感
    clean_env.setenv("LANGSMITH_PROJECT", "chef-prod")
    assert init_tracing() is True
    assert os.getenv("LANGCHAIN_PROJECT") == "chef-prod"
