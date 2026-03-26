# API 文档

## 概述

询价系统提供 RESTful API，支持询价、报告生成、历史查询等功能。

**基础URL**: `http://localhost:8000`

**认证方式**: API Key

```
X-API-Key: your-api-key
```

---

## 认证

### 获取 API Key

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## 询价

### 提交询价

```
POST /api/v1/inquiry
```

**请求体**:
```json
{
  "products": [
    {
      "name": "网络摄像机",
      "brand": "海康威视",
      "model": "DS-2CD3T86FWDV2-I3S",
      "specs": "分辨率:1920*1080",
      "quantity": 10
    }
  ],
  "methods": ["web", "history", "manufacturer"],
  "notify": true
}
```

**响应**:
```json
{
  "inquiry_id": "inq_123456",
  "status": "processing",
  "total_products": 1,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### 查询询价状态

```
GET /api/v1/inquiry/{inquiry_id}
```

**响应**:
```json
{
  "inquiry_id": "inq_123456",
  "status": "completed",
  "products": [
    {
      "name": "网络摄像机",
      "min_price": 850,
      "confidence": 85,
      "sources": [...]
    }
  ]
}
```

---

## 产品

### 搜索产品

```
GET /api/v1/products/search?q={keyword}&limit=10
```

**响应**:
```json
{
  "total": 25,
  "products": [
    {
      "id": 1,
      "name": "网络摄像机",
      "brand": "海康威视",
      "min_price": 720,
      "last_updated": "2024-01-01"
    }
  ]
}
```

### 获取产品详情

```
GET /api/v1/products/{product_id}
```

---

## 历史价格

### 查询历史

```
GET /api/v1/history?product={name}&days=90
```

**响应**:
```json
{
  "product": "网络摄像机",
  "records": [
    {
      "price": 850,
      "source": "京东",
      "timestamp": "2024-01-01"
    }
  ],
  "trend": {
    "direction": "down",
    "change_pct": -5.2
  }
}
```

---

## 报告

### 生成报告

```
POST /api/v1/reports
```

**请求体**:
```json
{
  "type": "markdown",
  "products": ["product_ids"],
  "include_charts": true,
  "include_specs": true
}
```

### 下载报告

```
GET /api/v1/reports/{report_id}/download
```

---

## 邮件

### 发送询价邮件

```
POST /api/v1/email/inquiry
```

**请求体**:
```json
{
  "to": ["supplier@example.com"],
  "products": [...],
  "template": "standard"
}
```

### 收取回复邮件

```
POST /api/v1/email/receive
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 限流

- 免费用户: 100 请求/分钟
- 付费用户: 1000 请求/分钟

---

## SDK

### Python

```python
from inquiry import InquiryClient

client = InquiryClient(api_key="your-key")
result = client.inquiry(products=[...])
```
