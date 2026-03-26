"""
WebSocket 实时推送模块
支持价格监控实时推送、告警通知
"""

import asyncio
import json
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from starlette.websockets import WebSocketState
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False


class MessageType(Enum):
    """消息类型"""
    PRICE_UPDATE = "price_update"     # 价格更新
    ALERT = "alert"                  # 告警通知
    INQUIRY_RESULT = "inquiry_result"  # 询价结果
    HEARTBEAT = "heartbeat"          # 心跳
    ERROR = "error"                  # 错误


@dataclass
class WSMessage:
    """WebSocket 消息"""
    type: str
    data: Any
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class ConnectionManager:
    """
    WebSocket 连接管理器
    支持多用户、多频道订阅
    """
    
    def __init__(self):
        # user_id -> set of websockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        
        # 频道订阅: channel_name -> set of websockets
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {}
        
        # 全局订阅
        self.global_subscribers: Set[WebSocket] = set()
        
        # 连接锁
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """建立连接"""
        await websocket.accept()
        
        async with self.lock:
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(websocket)
            
            self.global_subscribers.add(websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: str = None):
        """断开连接"""
        async with self.lock:
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            self.global_subscribers.discard(websocket)
            
            # 从所有频道移除
            for channel in list(self.channel_subscribers.keys()):
                self.channel_subscribers[channel].discard(websocket)
                if not self.channel_subscribers[channel]:
                    del self.channel_subscribers[channel]
    
    async def subscribe(self, websocket: WebSocket, channel: str):
        """订阅频道"""
        async with self.lock:
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(websocket)
    
    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """取消订阅"""
        async with self.lock:
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(websocket)
                if not self.channel_subscribers[channel]:
                    del self.channel_subscribers[channel]
    
    async def send_personal(self, user_id: str, message: WSMessage):
        """发送个人消息"""
        if user_id not in self.user_connections:
            return
        
        disconnected = set()
        
        for websocket in self.user_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message.to_json())
                else:
                    disconnected.add(websocket)
            except:
                disconnected.add(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            await self.disconnect(ws, user_id)
    
    async def broadcast_channel(self, channel: str, message: WSMessage):
        """广播到频道"""
        if channel not in self.channel_subscribers:
            return
        
        await self._broadcast(self.channel_subscribers[channel], message)
    
    async def broadcast_all(self, message: WSMessage):
        """广播到所有连接"""
        await self._broadcast(self.global_subscribers, message)
    
    async def _broadcast(self, websockets: Set[WebSocket], message: WSMessage):
        """广播到指定连接集合"""
        disconnected = set()
        
        for websocket in websockets:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message.to_json())
                else:
                    disconnected.add(websocket)
            except:
                disconnected.add(websocket)
        
        # 清理
        for ws in disconnected:
            self.global_subscribers.discard(ws)


class PriceWebSocket:
    """
    价格 WebSocket 服务
    处理实时价格推送和告警
    """
    
    def __init__(self):
        self.manager = ConnectionManager()
        self.subscriptions: Dict[str, set] = {}  # websocket_id -> product_keywords
    
    async def handle_connection(self, websocket: WebSocket, user_id: str = None):
        """处理 WebSocket 连接"""
        await self.manager.connect(websocket, user_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                
                try:
                    msg = json.loads(data)
                    await self.handle_message(websocket, msg)
                except json.JSONDecodeError:
                    await self.send_error(websocket, "Invalid JSON")
                    
        except WebSocketDisconnect:
            pass
        finally:
            await self.manager.disconnect(websocket, user_id)
    
    async def handle_message(self, websocket: WebSocket, msg: Dict):
        """处理客户端消息"""
        action = msg.get("action")
        
        if action == "subscribe":
            # 订阅产品
            products = msg.get("products", [])
            channel = msg.get("channel", "default")
            
            await self.manager.subscribe(websocket, channel)
            
            if id(websocket) not in self.subscriptions:
                self.subscriptions[id(websocket)] = set()
            self.subscriptions[id(websocket)].update(products)
            
            await self.send_ack(websocket, f"Subscribed to {len(products)} products")
        
        elif action == "unsubscribe":
            channel = msg.get("channel", "default")
            await self.manager.unsubscribe(websocket, channel)
            await self.send_ack(websocket, "Unsubscribed")
        
        elif action == "ping":
            await websocket.send_text(WSMessage(
                type=MessageType.HEARTBEAT.value,
                data={"pong": datetime.now().isoformat()}
            ).to_json())
    
    async def push_price_update(
        self,
        product_name: str,
        price: float,
        source: str,
        channel: str = "default"
    ):
        """推送价格更新"""
        message = WSMessage(
            type=MessageType.PRICE_UPDATE.value,
            data={
                "product": product_name,
                "price": price,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await self.manager.broadcast_channel(channel, message)
    
    async def push_alert(
        self,
        product_name: str,
        alert_type: str,
        message: str,
        user_id: str = None
    ):
        """推送告警"""
        ws_message = WSMessage(
            type=MessageType.ALERT.value,
            data={
                "product": product_name,
                "alert_type": alert_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if user_id:
            await self.manager.send_personal(user_id, ws_message)
        else:
            await self.manager.broadcast_all(ws_message)
    
    async def push_inquiry_result(
        self,
        results: list,
        user_id: str = None
    ):
        """推送询价结果"""
        message = WSMessage(
            type=MessageType.INQUIRY_RESULT.value,
            data={
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if user_id:
            await self.manager.send_personal(user_id, message)
        else:
            await self.manager.broadcast_all(message)
    
    async def send_error(self, websocket: WebSocket, error: str):
        """发送错误"""
        message = WSMessage(
            type=MessageType.ERROR.value,
            data={"error": error}
        )
        await websocket.send_text(message.to_json())
    
    async def send_ack(self, websocket: WebSocket, message: str):
        """发送确认"""
        message = WSMessage(
            type="ack",
            data={"message": message}
        )
        await websocket.send_text(message.to_json())


# 全局实例
_price_ws = None

def get_price_websocket() -> PriceWebSocket:
    """获取全局 WebSocket 实例"""
    global _price_ws
    if _price_ws is None:
        _price_ws = PriceWebSocket()
    return _price_ws
