"""
Redis 缓存模块
支持价格缓存、会话存储、分布式锁
"""

import os
import json
import hashlib
from typing import Any, Optional, List, Dict
from datetime import timedelta
from dataclasses import dataclass

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    url: str = "redis://localhost:6379/0"
    password: str = ""
    db: int = 0
    # 默认 TTL
    default_ttl: int = 3600  # 1小时
    # 各类型数据的 TTL
    price_ttl: int = 1800  # 价格缓存 30分钟
    search_ttl: int = 3600  # 搜索结果 1小时
    session_ttl: int = 86400  # 会话 24小时


class RedisCache:
    """
    Redis 缓存管理器
    提供价格缓存、结果缓存等功能
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or self._load_config()
        self.client = None
        self._connect()
    
    def _load_config(self) -> CacheConfig:
        """从环境变量加载配置"""
        enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        
        return CacheConfig(
            enabled=enabled,
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            password=os.getenv("REDIS_PASSWORD", ""),
            db=int(os.getenv("REDIS_DB", "0")),
            default_ttl=int(os.getenv("CACHE_TTL", "3600")),
            price_ttl=int(os.getenv("PRICE_CACHE_TTL", "1800")),
            search_ttl=int(os.getenv("SEARCH_CACHE_TTL", "3600")),
            session_ttl=int(os.getenv("SESSION_TTL", "86400")),
        )
    
    def _connect(self):
        """连接 Redis"""
        if not self.config.enabled or not HAS_REDIS:
            self.config.enabled = False
            print("⚠ Redis 缓存未启用")
            return
        
        try:
            self.client = redis.from_url(
                self.config.url,
                password=self.config.password or None,
                db=self.config.db,
                decode_responses=True
            )
            self.client.ping()
            print(f"✓ Redis 连接成功: {self.config.url}")
        except Exception as e:
            print(f"⚠ Redis 连接失败: {e}")
            self.config.enabled = False
    
    # ============ 基础操作 ============
    
    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        if not self.config.enabled or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置值"""
        if not self.config.enabled or not self.client:
            return
        
        ttl = ttl or self.config.default_ttl
        
        try:
            self.client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """删除值"""
        if not self.config.enabled or not self.client:
            return
        
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.config.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except:
            return False
    
    def expire(self, key: str, ttl: int):
        """设置过期时间"""
        if not self.config.enabled or not self.client:
            return
        
        try:
            self.client.expire(key, ttl)
        except:
            pass
    
    # ============ 价格缓存 ============
    
    def get_price(self, product_name: str, brand: str = "") -> Optional[Dict]:
        """获取缓存的价格"""
        key = self._make_price_key(product_name, brand)
        return self.get(key)
    
    def set_price(self, product_name: str, price_data: Dict, brand: str = ""):
        """缓存价格数据"""
        key = self._make_price_key(product_name, brand)
        self.set(key, price_data, self.config.price_ttl)
    
    def _make_price_key(self, product_name: str, brand: str = "") -> str:
        """生成价格缓存键"""
        raw = f"price:{product_name}:{brand}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    # ============ 搜索结果缓存 ============
    
    def get_search_results(self, query: str, sources: List[str] = None) -> Optional[List]:
        """获取缓存的搜索结果"""
        key = self._make_search_key(query, sources)
        return self.get(key)
    
    def set_search_results(self, query: str, results: List, sources: List[str] = None):
        """缓存搜索结果"""
        key = self._make_search_key(query, sources)
        self.set(key, results, self.config.search_ttl)
    
    def _make_search_key(self, query: str, sources: List[str] = None) -> str:
        """生成搜索缓存键"""
        sources_str = ",".join(sorted(sources)) if sources else "all"
        raw = f"search:{query}:{sources_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    # ============ 分布式锁 ============
    
    def acquire_lock(self, key: str, ttl: int = 60) -> bool:
        """获取分布式锁"""
        if not self.config.enabled or not self.client:
            return True  # 回退到无锁模式
        
        lock_key = f"lock:{key}"
        
        try:
            # 使用 SET NX EX
            return bool(self.client.set(lock_key, "1", nx=True, ex=ttl))
        except:
            return True
    
    def release_lock(self, key: str):
        """释放分布式锁"""
        if not self.config.enabled or not self.client:
            return
        
        lock_key = f"lock:{key}"
        try:
            self.client.delete(lock_key)
        except:
            pass
    
    # ============ 会话管理 ============
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话数据"""
        key = f"session:{session_id}"
        return self.get(key)
    
    def set_session(self, session_id: str, data: Dict, ttl: int = None):
        """设置会话数据"""
        key = f"session:{session_id}"
        ttl = ttl or self.config.session_ttl
        self.set(key, data, ttl)
    
    def delete_session(self, session_id: str):
        """删除会话"""
        key = f"session:{session_id}"
        self.delete(key)
    
    # ============ 批量操作 ============
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        if not self.config.enabled or not self.client:
            return {}
        
        result = {}
        try:
            values = self.client.mget(keys)
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
        except:
            pass
        
        return result
    
    def set_many(self, items: Dict[str, Any], ttl: int = None):
        """批量设置"""
        if not self.config.enabled or not self.client:
            return
        
        ttl = ttl or self.config.default_ttl
        
        try:
            pipe = self.client.pipeline()
            for key, value in items.items():
                pipe.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            pipe.execute()
        except Exception as e:
            print(f"Cache set_many error: {e}")
    
    def clear_pattern(self, pattern: str):
        """清除匹配的所有键"""
        if not self.config.enabled or not self.client:
            return
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except:
            pass
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()


# 全局实例
_cache = None

def get_cache() -> RedisCache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
