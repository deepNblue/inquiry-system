#!/usr/bin/env python3
"""
自动询价系统 - FastAPI 服务 (增强版)
支持 JWT 认证 + WebSocket 实时推送
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import yaml

# 添加 src 目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper import WebScraper
from src.history import HistoryMatcher
from src.aggregator import PriceAggregator
from src.auth import AuthManager, User
from src.realtime import get_price_websocket, PriceWebSocket


# ============ 安全配置 ============

auth_manager = AuthManager()
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """获取当前用户（可选认证）"""
    if not credentials:
        return None
    
    user_id = auth_manager.verify_token(credentials.credentials)
    if user_id:
        return auth_manager.get_user(user_id)
    return None


async def require_user(
    user: User = Depends(get_current_user)
) -> User:
    """要求用户认证"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


# ============ 请求/响应模型 ============

class Product(BaseModel):
    name: str
    brand: Optional[str] = ""
    model: Optional[str] = ""
    category: Optional[str] = ""
    specs: Optional[str] = ""


class InquiryRequest(BaseModel):
    products: List[Product]
    methods: List[str] = ["web", "history"]
    save_history: bool = True
    notify_websocket: bool = True  # 是否推送 WebSocket


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = ""


class PriceResult(BaseModel):
    product_name: str
    brand: str
    model: str
    min_price: float
    max_price: float
    avg_price: float
    recommended_source: str
    recommended_price: float
    source_count: int
    prices: List[Dict]


# ============ FastAPI 应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 询价系统 API 启动 (认证版)")
    yield
    print("👋 询价系统 API 关闭")


app = FastAPI(
    title="自动询价系统 API",
    description="三渠道综合询价：网页 + 厂家 + 历史 (支持 JWT 认证)",
    version="0.2.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局询价系统实例
_system = None

def get_system():
    global _system
    if _system is None:
        _system = InquirySystem()
    return _system


# ============ 认证 API ============

@app.post("/auth/register", tags=["认证"])
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        user_id = auth_manager.create_user(
            username=request.username,
            password=request.password,
            email=request.email
        )
        token = auth_manager.create_access_token(user_id)
        
        return {
            "user_id": user_id,
            "access_token": token,
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", tags=["认证"])
async def login(request: LoginRequest):
    """用户登录"""
    user = auth_manager.authenticate(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = auth_manager.create_access_token(user.id)
    
    return {
        "user_id": user.id,
        "username": user.username,
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/auth/me", tags=["认证"])
async def get_me(user: User = Depends(require_user)):
    """获取当前用户信息"""
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin
    }


@app.post("/auth/api-key", tags=["认证"])
async def create_api_key(user: User = Depends(require_user)):
    """创建 API Key"""
    api_key = auth_manager.create_api_key(user.id, name="default")
    
    return {
        "api_key": api_key,
        "warning": "API Key 只显示一次，请妥善保存！"
    }


# ============ 询价 API ============

@app.post("/inquiry", response_model=List[PriceResult])
async def inquiry(
    request: InquiryRequest,
    user: User = Depends(get_current_user)
):
    """执行询价（可选认证）"""
    system = get_system()
    
    products = [p.model_dump() for p in request.products]
    results = {}
    
    # 网页询价
    if "web" in request.methods:
        web_results = await system.web_scraper.batch_search(products)
        results["web"] = web_results
    
    # 历史询价
    if "history" in request.methods:
        history_results = []
        for p in products:
            matches = system.history.search_similar(
                product_name=p.get("name", ""),
                brand=p.get("brand", ""),
                model=p.get("model", ""),
                top_k=3
            )
            history_results.extend(matches)
        results["history"] = history_results
    
    # 聚合
    aggregated = system.aggregator.aggregate(
        web_results=results.get("web"),
        history_results=results.get("history")
    )
    
    # WebSocket 推送
    if request.notify_websocket:
        ws = get_price_websocket()
        await ws.push_inquiry_result(
            [r.product_name for r in aggregated],
            user_id=user.id if user else None
        )
    
    return [
        PriceResult(
            product_name=r.product_name,
            brand=r.brand,
            model=r.model,
            min_price=r.min_price,
            max_price=r.max_price,
            avg_price=r.avg_price,
            recommended_source=r.recommended_source,
            recommended_price=r.recommended_price,
            source_count=r.source_count,
            prices=r.prices
        )
        for r in aggregated
    ]


@app.get("/history/{product_name}")
async def get_history(
    product_name: str,
    brand: str = "",
    top_k: int = 5,
    user: User = Depends(get_current_user)
):
    """查询历史价格"""
    system = get_system()
    
    results = system.history.search_similar(
        product_name=product_name,
        brand=brand,
        top_k=top_k
    )
    
    return [
        {
            "product_name": r.product_name,
            "brand": r.brand,
            "model": r.model,
            "price": r.price,
            "source": r.source,
            "timestamp": r.timestamp,
            "similarity": r.similarity
        }
        for r in results
    ]


# ============ WebSocket API ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    # 获取token（可选）
    token = websocket.query_params.get("token")
    user_id = None
    
    if token:
        user_id = auth_manager.verify_token(token)
    
    ws = get_price_websocket()
    await ws.handle_connection(websocket, user_id)


# ============ 健康检查 ============

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/")
async def root():
    return {
        "message": "自动询价系统 API v0.2.0",
        "docs": "/docs",
        "auth": "支持 JWT 认证"
    }


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
