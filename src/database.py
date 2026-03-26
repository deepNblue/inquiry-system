"""
数据库模块
支持 PostgreSQL + TimescaleDB 和 SQLite 回退
"""

import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass

try:
    import asyncpg
    import psycopg2
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    HAS_POSTGRES = True
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_POSTGRES = False
    HAS_SQLALCHEMY = False
    # 提供 mock 函数
    def create_engine(*args, **kwargs):
        return MockEngine()
    def text(sql):
        return sql
    def sessionmaker(*args, **kwargs):
        return MockSessionMaker()


@dataclass
class DBConfig:
    """数据库配置"""
    type: str = "sqlite"  # sqlite / postgres
    url: str = ""
    # PostgreSQL 单独配置
    host: str = "localhost"
    port: int = 5432
    database: str = "inquiry"
    user: str = "postgres"
    password: str = ""


class DatabaseManager:
    """
    数据库管理器
    支持 PostgreSQL (优先) 和 SQLite 回退
    """
    
    def __init__(self, config: DBConfig = None):
        self.config = config or self._load_config()
        self.engine = None
        self.session_factory = None
        self.async_engine = None
        self._connect()
    
    def _load_config(self) -> DBConfig:
        """从环境变量加载配置"""
        db_type = os.getenv("DB_TYPE", "sqlite")
        
        if db_type == "postgres":
            return DBConfig(
                type="postgres",
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "inquiry"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
            )
        else:
            return DBConfig(type="sqlite")
    
    def _connect(self):
        """建立连接"""
        if self.config.type == "postgres" and HAS_POSTGRES:
            self._connect_postgres()
        else:
            self._connect_sqlite()
    
    def _connect_postgres(self):
        """连接 PostgreSQL"""
        try:
            url = f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            self.engine = create_engine(url, pool_size=10, max_overflow=20)
            self.session_factory = sessionmaker(bind=self.engine)
            print(f"✓ PostgreSQL 连接成功: {self.config.host}:{self.config.port}")
        except Exception as e:
            print(f"⚠ PostgreSQL 连接失败: {e}")
            print("回退到 SQLite...")
            self._connect_sqlite()
    
    def _connect_sqlite(self):
        """连接 SQLite"""
        db_path = os.getenv("DB_PATH", "data/inquiry.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        url = f"sqlite:///{db_path}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        self.session_factory = sessionmaker(bind=self.engine)
        print(f"✓ SQLite 连接成功: {db_path}")
    
    def init_schema(self):
        """初始化表结构"""
        with self.engine.connect() as conn:
            # 价格历史表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    category TEXT,
                    specs TEXT,
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'CNY',
                    source TEXT,
                    source_type TEXT DEFAULT 'web',
                    url TEXT,
                    raw_data TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 索引
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_product_name ON price_history(product_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_brand ON price_history(brand)"))
            
            # 告警规则表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    min_price REAL DEFAULT 0,
                    max_price REAL DEFAULT 0,
                    change_threshold REAL DEFAULT 0.05,
                    webhook_url TEXT,
                    enabled INTEGER DEFAULT 1,
                    cooldown_hours INTEGER DEFAULT 24,
                    last_alert_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 告警历史表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT,
                    product_name TEXT NOT NULL,
                    brand TEXT,
                    alert_type TEXT NOT NULL,
                    old_price REAL,
                    new_price REAL,
                    change_percent REAL,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    notes TEXT
                )
            """))
            
            # 用户表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    hashed_password TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # API Keys 表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            
            conn.commit()
            
            # 如果是 PostgreSQL，尝试创建 TimescaleDB 超表
            if self.config.type == "postgres":
                try:
                    conn.execute(text("SELECT CREATE_HYPERTABLE('price_history', 'timestamp', migrate_data => true)"))
                    conn.commit()
                    print("✓ TimescaleDB 超表创建成功")
                except Exception as e:
                    print(f"⚠ TimescaleDB 超表创建失败 (可能需要扩展): {e}")
    
    @contextmanager
    def get_session(self):
        """获取数据库会话"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute(self, sql: str, params: tuple = None):
        """执行 SQL"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result
    
    def fetch_all(self, sql: str, params: tuple = None) -> List:
        """查询所有"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return list(result.fetchall())
    
    def fetch_one(self, sql: str, params: tuple = None):
        """查询一条"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchone()
    
    def close(self):
        """关闭连接"""
        if self.engine:
            self.engine.dispose()


# 全局实例
_db = None

def get_db() -> DatabaseManager:
    """获取全局数据库实例"""
    global _db
    if _db is None:
        _db = DatabaseManager()
        _db.init_schema()
    return _db


# Mock 类用于没有 SQLAlchemy 的情况
class MockEngine:
    def connect(self):
        return MockConnection()
    def dispose(self):
        pass

class MockConnection:
    def execute(self, sql, params=None):
        return MockResult()
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass

class MockResult:
    def fetchone(self):
        return None
    def fetchall(self):
        return []

class MockSessionMaker:
    def __call__(self):
        return MockSession()

class MockSession:
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass
