"""
认证模块
JWT Token 管理、用户认证、API Key
"""

import os
import hashlib
import secrets
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
import jwt

try:
    from fastapi import HTTPException, Depends, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@dataclass
class User:
    """用户"""
    id: str
    username: str
    email: str
    hashed_password: str
    api_keys: List[str]
    is_active: bool
    is_admin: bool
    created_at: str


class AuthManager:
    """
    认证管理器
    支持 JWT Token 和 API Key 两种方式
    """
    
    def __init__(self, db_path: str = "data/users.db", secret_key: str = None):
        self.db_path = db_path
        self.secret_key = secret_key or os.getenv("JWT_SECRET", "change-me-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24小时
        
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                hashed_password TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        self.conn.commit()
    
    # ============ 用户管理 ============
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str = ""
    ) -> str:
        """创建用户"""
        import uuid
        
        user_id = str(uuid.uuid4())[:8]
        hashed = self._hash_password(password)
        
        try:
            self.conn.execute("""
                INSERT INTO users (id, username, email, hashed_password)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, email, hashed))
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise ValueError("Username already exists")
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户"""
        cursor = self.conn.execute("""
            SELECT id, username, email, hashed_password, is_active, is_admin, created_at
            FROM users WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        if not self._verify_password(password, row[3]):
            return None
        
        if not row[4]:  # is_active
            return None
        
        return User(
            id=row[0],
            username=row[1],
            email=row[2] or "",
            hashed_password=row[3],
            api_keys=self._get_user_api_keys(row[0]),
            is_active=bool(row[4]),
            is_admin=bool(row[5]),
            created_at=row[6]
        )
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        cursor = self.conn.execute("""
            SELECT id, username, email, hashed_password, is_active, is_admin, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return User(
            id=row[0],
            username=row[1],
            email=row[2] or "",
            hashed_password=row[3],
            api_keys=self._get_user_api_keys(row[0]),
            is_active=bool(row[4]),
            is_admin=bool(row[5]),
            created_at=row[6]
        )
    
    # ============ API Key ============
    
    def create_api_key(self, user_id: str, name: str = "") -> str:
        """创建 API Key"""
        import uuid
        
        key_id = str(uuid.uuid4())[:8]
        api_key = f"ink_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_password(api_key)
        
        self.conn.execute("""
            INSERT INTO api_keys (id, user_id, key_hash, name)
            VALUES (?, ?, ?, ?)
        """, (key_id, user_id, key_hash, name))
        self.conn.commit()
        
        # 返回完整key（只显示一次）
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """验证 API Key，返回 user_id"""
        if not api_key or not api_key.startswith("ink_"):
            return None
        
        # 查找所有key比对
        cursor = self.conn.execute("SELECT id, user_id, key_hash FROM api_keys")
        for row in cursor.fetchall():
            if self._verify_password(api_key, row[2]):
                # 更新最后使用时间
                self.conn.execute("""
                    UPDATE api_keys SET last_used_at = ? WHERE id = ?
                """, (datetime.now().isoformat(), row[0]))
                self.conn.commit()
                return row[1]
        
        return None
    
    def _get_user_api_keys(self, user_id: str) -> List[str]:
        """获取用户的API Key列表（不返回key本身）"""
        cursor = self.conn.execute("""
            SELECT id, name, created_at FROM api_keys WHERE user_id = ?
        """, (user_id,))
        
        return [f"ink_...{row[0]}" for row in cursor.fetchall()]
    
    # ============ JWT Token ============
    
    def create_access_token(self, user_id: str) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[str]:
        """验证 Token，返回 user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "access":
                return None
            
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    # ============ 密码工具 ============
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == hashed
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# ============ FastAPI 依赖 ============

if HAS_FASTAPI:
    security = HTTPBearer(auto_error=False)
    
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """获取当前用户（依赖注入）"""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # 临时获取 auth_manager 实例
        # 实际使用需要在 app 中注入
        auth = AuthManager()
        user_id = auth.verify_token(credentials.credentials)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = auth.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    
    async def get_current_user_optional(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Optional[User]:
        """可选的当前用户"""
        if not credentials:
            return None
        
        try:
            auth = AuthManager()
            user_id = auth.verify_token(credentials.credentials)
            if user_id:
                return auth.get_user(user_id)
        except:
            pass
        
        return None


# 便捷函数
def create_token(user_id: str) -> str:
    """快速创建 Token"""
    auth = AuthManager()
    return auth.create_access_token(user_id)


def verify_token(token: str) -> Optional[str]:
    """快速验证 Token"""
    auth = AuthManager()
    return auth.verify_token(token)
