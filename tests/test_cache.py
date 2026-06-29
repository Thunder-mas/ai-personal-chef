# tests/test_cache.py
"""缓存层：LRU 淘汰/最近使用、内存后端读写、Redis 故障静默降级、key 稳定性。
不依赖真实 Redis —— 用"会抛错的假 redis"验证降级承诺，确定性。"""
import pytest

from app.cache import Cache, _LRU, make_key


# ---------------- 进程内有界 LRU ----------------
def test_lru_evicts_oldest_over_capacity():
    lru = _LRU(capacity=2)
    lru.set("a", b"1")
    lru.set("b", b"2")
    lru.set("c", b"3")            # 超容量 → 淘汰最旧的 a
    assert lru.get("a") is None
    assert lru.get("b") == b"2"
    assert lru.get("c") == b"3"


def test_lru_get_refreshes_recency():
    lru = _LRU(capacity=2)
    lru.set("a", b"1")
    lru.set("b", b"2")
    assert lru.get("a") == b"1"   # 访问 a → a 变最近
    lru.set("c", b"3")            # 应淘汰最旧的 b（不是刚访问过的 a）
    assert lru.get("a") == b"1"
    assert lru.get("b") is None
    assert lru.get("c") == b"3"


def test_lru_get_missing_returns_none():
    assert _LRU().get("nope") is None


# ---------------- Cache（内存后端） ----------------
@pytest.fixture
def mem_cache(monkeypatch):
    """无 REDIS_URL → 纯内存后端的 Cache（与全局单例隔离，避免 .env 干扰）。"""
    monkeypatch.delenv("REDIS_URL", raising=False)
    return Cache()


def test_memory_backend_when_no_redis(mem_cache):
    assert mem_cache.backend == "memory"


def test_bytes_roundtrip_and_hit_miss(mem_cache):
    assert mem_cache.get_bytes("k") is None       # miss
    mem_cache.set_bytes("k", b"v")
    assert mem_cache.get_bytes("k") == b"v"        # hit
    assert mem_cache.hits == 1 and mem_cache.misses == 1


def test_json_roundtrip_unicode(mem_cache):
    mem_cache.set_json("k", {"a": 1, "中文": "值"})
    assert mem_cache.get_json("k") == {"a": 1, "中文": "值"}


def test_json_on_corrupt_bytes_returns_none(mem_cache):
    mem_cache.set_bytes("k", b"not-json{")
    assert mem_cache.get_json("k") is None         # 解析失败兜底为 None，不抛


def test_stats_hit_rate(mem_cache):
    mem_cache.set_bytes("k", b"v")
    mem_cache.get_bytes("k")       # hit
    mem_cache.get_bytes("x")       # miss
    s = mem_cache.stats()
    assert s["backend"] == "memory"
    assert s["hits"] == 1 and s["misses"] == 1
    assert s["hit_rate"] == 0.5


def test_stats_hit_rate_zero_when_empty(mem_cache):
    assert mem_cache.stats()["hit_rate"] == 0.0    # 无访问不除零


# ---------------- Redis 故障静默降级（核心设计承诺） ----------------
class _RaisingRedis:
    """模拟"配了 Redis 但运行时读写都失败"的客户端。"""
    def get(self, key):
        raise RuntimeError("redis down")

    def set(self, key, value, ex=None):
        raise RuntimeError("redis down")


def test_redis_failure_falls_back_to_memory(mem_cache):
    # 关键承诺：Redis 读写异常 → 静默降级到内存，绝不拖垮主流程
    mem_cache._redis = _RaisingRedis()
    mem_cache.set_bytes("k", b"v")            # set 抛错 → 落内存
    assert mem_cache.get_bytes("k") == b"v"    # get 抛错 → 读内存命中


# ---------------- key 生成 ----------------
def test_make_key_stable_and_order_sensitive():
    assert make_key("a", "b") == make_key("a", "b")   # 稳定可复现
    assert make_key("a", "b") != make_key("b", "a")   # 顺序敏感
    assert len(make_key("x")) == 32                    # md5 hex 长度
