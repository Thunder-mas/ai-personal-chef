# tests/test_modes.py
"""推荐模式：注册表不变量、配置回退、模式切换持久化、非法值处理。"""
import sqlite3

import pytest

from app.modes import (
    MODES, DEFAULT_MODE, get_mode, set_mode, get_mode_config, list_modes,
)


def test_registry_invariants():
    assert DEFAULT_MODE in MODES
    assert MODES["fitness"]["uses_fitness"] is True
    assert MODES["gourmet"]["uses_fitness"] is False
    for cfg in MODES.values():
        assert {"name", "emoji", "uses_fitness", "prompt"} <= set(cfg)


def test_list_modes_shape_hides_internal_fields():
    items = list_modes()
    assert {i["key"] for i in items} == set(MODES)
    for i in items:
        assert set(i) == {"key", "name", "emoji"}   # 不泄漏 prompt / uses_fitness


def test_get_mode_config_explicit():
    assert get_mode_config("fitness")["name"] == "健身模式"


def test_get_mode_config_falls_back_for_unknown(temp_db):
    # 非法 / None → 回退到全局当前模式（默认 gourmet）
    assert get_mode_config("不存在")["name"] == MODES[DEFAULT_MODE]["name"]
    assert get_mode_config(None)["name"] == MODES[DEFAULT_MODE]["name"]


def test_default_mode_when_unset(temp_db):
    assert get_mode() == DEFAULT_MODE


def test_set_and_get_mode_roundtrip(temp_db):
    set_mode("fitness")
    assert get_mode() == "fitness"


def test_set_invalid_mode_raises(temp_db):
    with pytest.raises(ValueError):
        set_mode("keto")


def test_get_mode_falls_back_on_corrupt_stored_value(temp_db):
    # 库里存了非法 mode（如老版本遗留）→ get_mode 回退默认，而非返回脏值
    set_mode("fitness")
    with sqlite3.connect(str(temp_db)) as conn:
        conn.execute("UPDATE app_settings SET value='legacy_bad' WHERE key='mode'")
    assert get_mode() == DEFAULT_MODE
