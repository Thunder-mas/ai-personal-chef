# app/cache.py
"""轻量缓存层：配了 REDIS_URL 就用 Redis，否则回落到进程内有界 LRU。

两个用途：
  ① 缓存 query 的 embedding —— 确定性、重复 query 命中率高，省下 embedding 计算与延迟；
  ② 缓存多 Agent 套餐规划的最终结果 —— 按请求 + 健康目标 + 偏好哈希。

设计原则（关键）：缺 Redis / 连接失败 / 读写异常，全部静默降级到内存，
线上 demo（ModelScope 未配 Redis）零影响、绝不因为缓存把主流程拖垮。
"""
import os
import json
import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Optional, Any

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 60 * 60 * 24 * 7  # 7 天


class _LRU:
    """进程内有界 LRU（Redis 不可用时的回落）。按容量淘汰，线程安全。"""

    def __init__(self, capacity: int = 4096):
        self.capacity = capacity
        self._d: "OrderedDict[str, bytes]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            if key not in self._d:
                return None
            self._d.move_to_end(key)
            return self._d[key]

    def set(self, key: str, value: bytes) -> None:
        with self._lock:
            self._d[key] = value
            self._d.move_to_end(key)
            while len(self._d) > self.capacity:
                self._d.popitem(last=False)


class Cache:
    """Redis 优先、内存兜底的 KV 缓存，自带命中/未命中计数（便于量化缓存收益）。"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self._redis = None
        self._lru = _LRU()
        self.backend = "memory"

        url = os.getenv("REDIS_URL")
        if url:
            try:
                import redis  # 懒导入：没装 redis 也不影响内存回落
                client = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
                client.ping()
                self._redis = client
                self.backend = "redis"
                logger.info("缓存后端：Redis")
            except Exception as e:
                logger.warning("Redis 不可用，回落到进程内缓存：%s", e)

    # ---------- bytes 接口（embedding 等二进制用）----------
    def get_bytes(self, key: str) -> Optional[bytes]:
        v = self._get_raw(key)
        if v is None:
            self.misses += 1
            return None
        self.hits += 1
        return v

    def set_bytes(self, key: str, value: bytes, ttl: int = _DEFAULT_TTL) -> None:
        self._set_raw(key, value, ttl)

    # ---------- json 接口（结构化结果用）----------
    def get_json(self, key: str) -> Optional[Any]:
        v = self._get_raw(key)
        if v is None:
            self.misses += 1
            return None
        self.hits += 1
        try:
            return json.loads(v)
        except Exception:
            return None

    def set_json(self, key: str, obj: Any, ttl: int = _DEFAULT_TTL) -> None:
        self._set_raw(key, json.dumps(obj, ensure_ascii=False).encode("utf-8"), ttl)

    # ---------- 底层读写（Redis 出错即回落内存）----------
    def _get_raw(self, key: str) -> Optional[bytes]:
        if self._redis is not None:
            try:
                return self._redis.get(key)
            except Exception as e:
                logger.warning("Redis get 失败，回落内存：%s", e)
        return self._lru.get(key)

    def _set_raw(self, key: str, value: bytes, ttl: int) -> None:
        if self._redis is not None:
            try:
                self._redis.set(key, value, ex=ttl)
                return
            except Exception as e:
                logger.warning("Redis set 失败，回落内存：%s", e)
        self._lru.set(key, value)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "backend": self.backend,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }


_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """全局缓存单例（懒加载：首次用到才探测 Redis）。"""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def make_key(*parts) -> str:
    """把任意多个片段拼成稳定的缓存 key（md5）。"""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
