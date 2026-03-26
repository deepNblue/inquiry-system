# API 参考

## 认证 API

### POST /auth/register

用户注册

**请求体**
```json
{
  "username": "user",
  "password": "pass123",
  "email": "user@example.com"
}
```

**响应**
```json
{
  "user_id": "abc123",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST /auth/login

用户登录

**请求体**
```json
{
  "username": "user",
  "password": "pass123"
}
```

### GET /auth/me

获取当前用户信息（需认证）

**Headers**
```
Authorization: Bearer <token>
```

## 询价 API

### POST /inquiry

执行询价

**请求体**
```json
{
  "products": [
    {"name": "iPhone 15", "brand": "Apple"}
  ],
  "methods": ["web", "history"],
  "save_history": true
}
```

**响应**
```json
[
  {
    "product_name": "iPhone 15",
    "brand": "Apple",
    "min_price": 6999,
    "max_price": 7999,
    "recommended_source": "京东",
    "recommended_price": 6999,
    "source_count": 3
  }
]
```

### GET /history/{product_name}

查询历史价格

**参数**
- `product_name` - 产品名称
- `brand` - 品牌（可选）
- `top_k` - 返回数量（默认5）

## WebSocket

### WS /ws

实时价格推送

**连接**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<token>');
```

**订阅**
```json
{
  "action": "subscribe",
  "products": ["iPhone 15", "MacBook Pro"],
  "channel": "default"
}
```

**接收消息类型**
- `price_update` - 价格更新
- `alert` - 告警通知
- `inquiry_result` - 询价结果
